###############################################################################
# Name:        Congress Bulk Legislative Pipeline (OOP single-file)
# Date:        2025-10-02
# Script Name: congress_pipeline_oop.py
# Version:     1.0
# Log Summary: End-to-end OOP refactor of discovery, validation, concurrent
#              download/resume, extraction, parsing/normalization, and
#              PostgreSQL ingestion. Includes retry scheduler and reports.
# Description: Single executable Python script organized into classes:
#                A) DiscoveryManager - templates + index discovery
#                B) Validator - HEAD checks and filtering
#                C) DownloadManager - async concurrent download with resume/retry
#                D) Extractor - unzip/tar extraction
#                E) ParserNormalizer - simple parsers for bills/votes/legislators
#                F) DBIngestor - PostgreSQL schema + upsert ingestion
#                G) RetryManager - record failed downloads and automatic retries
#                H) Pipeline - glue + scheduler + CLI
#
# Change Summary:
#   - 1.0: Initial OOP single-file implementation. Provides working flows and
#          clear extension points for robust parsing, mapping, and schema.
#
# Inputs:
#   - CLI flags (see --help). Key: --start-congress, --end-congress,
#     --collections, --download, --validate, --extract, --postprocess,
#     --db (Postgres conn string), --schedule-interval, --retry-interval
#
# Outputs:
#   - bulk_urls.json (discovered URLs)
#   - retry_report.json (failed download records)
#   - downloaded archives & extracted files in outdir
#   - PostgreSQL tables populated when --postprocess and --db specified
#
###############################################################################

import os
import re
import sys
import json
import time
import asyncio
import logging
import argparse
import shutil
import tarfile
import zipfile
from html import unescape
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urlparse, urljoin

# External dependencies
# pip install requests aiohttp tqdm psycopg2-binary
try:
    import requests
    import aiohttp
    import psycopg2
    import psycopg2.extras
except Exception:
    # We'll raise helpful errors at runtime if missing
    pass

# Optional progress bar
try:
    from tqdm import tqdm
    TQDM = True
except Exception:
    TQDM = False

# ---------------------------- Logging -------------------------------------- #
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("congress_pipeline")

# ---------------------------- Constants ------------------------------------ #
DEFAULT_OUTDIR = "./bulk_data"
DEFAULT_OUTPUT = "bulk_urls.json"
DEFAULT_RETRY_REPORT = "retry_report.json"

US_STATES = [
 'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
 'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
 'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','PR'
]

# ---------------------------- Config Class --------------------------------- #
class Config:
    def __init__(self,
                 start_congress: int = 93,
                 end_congress: int = None,
                 outdir: str = DEFAULT_OUTDIR,
                 output_file: str = DEFAULT_OUTPUT,
                 retry_report: str = DEFAULT_RETRY_REPORT,
                 concurrency: int = 6,
                 retries: int = 5,
                 collections: Optional[List[str]] = None,
                 do_discovery: bool = True):
        now = datetime.utcnow()
        current_cong = 1 + (now.year - 1789) // 2
        self.start_congress = start_congress
        self.end_congress = end_congress if end_congress is not None else max(current_cong + 1, 119)
        self.outdir = outdir
        self.output_file = output_file
        self.retry_report = retry_report
        self.concurrency = concurrency
        self.retries = retries
        self.collections = [c.lower() for c in collections] if collections else None
        self.do_discovery = do_discovery

# ------------------------- DiscoveryManager (A) ----------------------------- #
class DiscoveryManager:
    """
    Responsible for templated URL generation and index-page discovery.
    """
    GOVINFO_INDEX = "https://www.govinfo.gov/bulkdata"
    GOVINFO_TEMPLATES = {
        "billstatus": "https://www.govinfo.gov/bulkdata/BILLSTATUS/{congress}/{chamber}/BILLSTATUS-{congress}{chamber}.zip",
        "rollcall": "https://www.govinfo.gov/bulkdata/ROLLCALLVOTE/{congress}/{chamber}/ROLLCALLVOTE-{congress}-{chamber}.zip",
        "bills": "https://www.govinfo.gov/bulkdata/BILLS/{congress}/{chamber}/BILLS-{congress}{chamber}.zip",
        "plaw": "https://www.govinfo.gov/bulkdata/PLAW/{congress}/PLAW-{congress}.zip",
        "crec": "https://www.govinfo.gov/bulkdata/CREC/{congress}/CREC-{congress}.zip",
    }
    GOVINFO_CHAMBERS = ["hr", "house", "h", "senate", "s"]

    OPENSTATES_DOWNLOADS = "https://openstates.org/downloads/"
    OPENSTATES_MIRROR = "https://open.pluralpolicy.com/data/"

    THEUNITEDSTATES_LEGISLATORS = [
        "https://theunitedstates.io/congress-legislators/legislators-current.json",
        "https://theunitedstates.io/congress-legislators/legislators-historical.json"
    ]

    GOVTRACK_BASE = "https://www.govtrack.us/data"
    GOVTRACK_EXAMPLE = "https://www.govtrack.us/data/us/bills/bills.csv"

    def __init__(self, cfg: Config):
        self.cfg = cfg

    @staticmethod
    def _http_get_text(url: str, timeout: int = 20) -> Optional[str]:
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                return r.text
            logger.debug("GET %s -> %s", url, r.status_code)
        except Exception as e:
            logger.debug("GET %s failed: %s", url, e)
        return None

    @staticmethod
    def _is_archive(url: str) -> bool:
        return bool(re.search(r'\.(zip|tar\.gz|tgz|tar|json|xml|csv)$', url, re.IGNORECASE))

    def expand_govinfo_templates(self) -> List[str]:
        urls = []
        for c in range(self.cfg.start_congress, self.cfg.end_congress + 1):
            for key, tpl in self.GOVINFO_TEMPLATES.items():
                if self.cfg.collections and key not in self.cfg.collections:
                    continue
                if "{chamber}" in tpl:
                    for ch in self.GOVINFO_CHAMBERS:
                        try:
                            urls.append(tpl.format(congress=c, chamber=ch))
                        except Exception:
                            pass
                else:
                    try:
                        urls.append(tpl.format(congress=c))
                    except Exception:
                        pass
        # dedupe
        seen = set(); out = []
        for u in urls:
            if u not in seen:
                out.append(u); seen.add(u)
        return out

    def discover_govinfo_index(self) -> List[str]:
        html = self._http_get_text(self.GOVINFO_INDEX)
        links = []
        if not html:
            return links
        for m in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
            href = unescape(m.group(1))
            if href.startswith("/"):
                full = "https://www.govinfo.gov" + href
            elif href.startswith("http"):
                full = href
            else:
                continue
            if self._is_archive(full):
                links.append(full)
        return list(dict.fromkeys(links))

    def discover_govtrack(self) -> List[str]:
        urls = [self.GOVTRACK_EXAMPLE]
        for c in range(self.cfg.start_congress, self.cfg.end_congress + 1):
            dir_url = f"https://www.govtrack.us/data/us/{c}/"
            html = self._http_get_text(dir_url)
            if not html: 
                continue
            for m in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
                href = unescape(m.group(1))
                candidate = href if href.startswith("http") else urljoin(dir_url, href)
                if self._is_archive(candidate):
                    urls.append(candidate)
        return list(dict.fromkeys(urls))

    def discover_openstates(self) -> List[str]:
        discovered = []
        html = self._http_get_text(self.OPENSTATES_DOWNLOADS)
        if html:
            for m in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
                href = unescape(m.group(1))
                if href.startswith("http"):
                    candidate = href
                elif href.startswith("/"):
                    candidate = "https://openstates.org" + href
                else:
                    continue
                if self._is_archive(candidate):
                    discovered.append(candidate)
        mirror_html = self._http_get_text(self.OPENSTATES_MIRROR)
        if mirror_html:
            for m in re.finditer(r'href=["\']([^"\']+)["\']', mirror_html, re.IGNORECASE):
                href = unescape(m.group(1))
                candidate = href if href.startswith("http") else self.OPENSTATES_MIRROR.rstrip("/") + "/" + href
                if self._is_archive(candidate):
                    discovered.append(candidate)
        # guessed per-state patterns on mirror
        base = self.OPENSTATES_MIRROR.rstrip("/") + "/"
        for st in US_STATES:
            for p in (f"openstates-{st.lower()}.zip", f"{st.lower()}.zip", f"openstates-{st.lower()}.json.zip"):
                discovered.append(base + p)
        return list(dict.fromkeys(discovered))

    def build(self) -> Dict[str, List[str]]:
        logger.info("Discovery: expanding templates and (optionally) crawling indices")
        data = {
            "govinfo_templates_expanded": self.expand_govinfo_templates()
        }
        if self.cfg.do_discovery:
            data["govinfo_index_discovered"] = self.discover_govinfo_index()
            data["govtrack"] = self.discover_govtrack()
            data["openstates"] = self.discover_openstates()
        else:
            data["govinfo_index_discovered"] = []
            data["govtrack"] = []
            data["openstates"] = []
        data["congress_legislators"] = self.THEUNITEDSTATES_LEGISLATORS
        # aggregate list
        agg = []
        for v in data.values():
            if isinstance(v, list):
                agg.extend([u for u in v if isinstance(u, str)])
            elif isinstance(v, dict):
                for iv in v.values():
                    if isinstance(iv, list):
                        agg.extend([u for u in iv if isinstance(u, str)])
        data["aggregate_urls"] = list(dict.fromkeys(agg))
        logger.info("Discovery produced %d aggregate candidates", len(data["aggregate_urls"]))
        return data

# ------------------------------ Validator (B) ------------------------------- #
class Validator:
    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    def head_check(self, url: str) -> bool:
        try:
            r = requests.head(url, timeout=self.timeout, allow_redirects=True)
            status = r.status_code
            if status >= 400:
                r2 = requests.get(url, timeout=self.timeout, stream=True)
                status = r2.status_code
                r2.close()
            return status < 400
        except Exception:
            return False

    def filter(self, urls: List[str]) -> List[str]:
        out = []
        for u in urls:
            if self.head_check(u):
                out.append(u)
        return out

# -------------------------- DownloadManager (C) ---------------------------- #
class DownloadManager:
    """
    Async downloader with resume and retries.
    """
    def __init__(self, outdir: str, concurrency: int = 6, retries: int = 5):
        self.outdir = outdir
        self.concurrency = concurrency
        self.retries = retries
        os.makedirs(self.outdir, exist_ok=True)

    @staticmethod
    async def _head_info(session: aiohttp.ClientSession, url: str) -> Dict[str, Optional[int]]:
        info = {"size": None, "resumable": False, "status": None}
        try:
            async with session.head(url, timeout=aiohttp.ClientTimeout(total=30), allow_redirects=True) as resp:
                info["status"] = resp.status
                if resp.status < 400:
                    cl = resp.headers.get("Content-Length")
                    if cl and cl.isdigit():
                        info["size"] = int(cl)
                    accept = resp.headers.get("Accept-Ranges", "")
                    info["resumable"] = "bytes" in accept.lower()
        except Exception:
            pass
        return info

    async def _download_one(self, session: aiohttp.ClientSession, url: str, dest: str) -> Dict[str, Any]:
        # handle resume using Range header when supported
        attempts = 0
        result = {"url": url, "path": dest, "ok": False, "bytes": 0, "error": None}
        while attempts <= self.retries:
            attempts += 1
            try:
                info = await self._head_info(session, url)
                resumable = info.get("resumable", False)
                existing = os.path.getsize(dest) if os.path.exists(dest) else 0
                headers = {}
                mode = "wb"
                if existing and resumable:
                    headers["Range"] = f"bytes={existing}-"
                    mode = "ab"
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=None)) as resp:
                    if resp.status in (416,):
                        result["ok"] = True; result["bytes"] = existing; return result
                    if resp.status >= 400:
                        raise aiohttp.ClientResponseError(resp.request_info, resp.history, status=resp.status, message=await resp.text())
                    total = None
                    cl = resp.headers.get("Content-Length")
                    if cl and cl.isdigit():
                        total = int(cl) + (existing if mode == "ab" else 0)
                    written = existing
                    chunk = 1 << 16
                    if TQDM:
                        desc = os.path.basename(dest)
                        with open(dest, mode) as fh, tqdm(total=total, initial=existing, unit="B", unit_scale=True, unit_divisor=1024, desc=desc[:40], leave=False) as pbar:
                            async for data in resp.content.iter_chunked(chunk):
                                if not data:
                                    break
                                fh.write(data); written += len(data); pbar.update(len(data))
                    else:
                        with open(dest, mode) as fh:
                            async for data in resp.content.iter_chunked(chunk):
                                if not data: break
                                fh.write(data); written += len(data)
                    result["ok"] = True; result["bytes"] = written; return result
            except Exception as e:
                result["error"] = str(e)
                logger.debug("Download attempt %d/%d failed for %s: %s", attempts, self.retries, url, e)
                await asyncio.sleep(min(30, 2 ** attempts))
        return result

    async def download_all(self, urls: List[str]) -> List[Dict[str, Any]]:
        tasks = []
        sem = asyncio.Semaphore(self.concurrency)
        connector = aiohttp.TCPConnector(limit_per_host=self.concurrency, limit=0)
        async with aiohttp.ClientSession(connector=connector) as session:
            for i, u in enumerate(urls):
                filename = u.split("?")[0].rstrip("/").split("/")[-1] or f"file_{i}"
                domain = urlparse(u).netloc.replace(":", "_")
                dest_dir = os.path.join(self.outdir, domain)
                os.makedirs(dest_dir, exist_ok=True)
                dest = os.path.join(dest_dir, filename)
                # wrap each call to respect concurrency semaphore
                async def sem_task(u=u, dest=dest):
                    async with sem:
                        return await self._download_one(session, u, dest)
                tasks.append(asyncio.create_task(sem_task()))
            # collect with as_completed for incremental reporting
            results = []
            for fut in asyncio.as_completed(tasks):
                r = await fut
                results.append(r)
            return results

# ------------------------------- Extractor (D) -------------------------------- #
class Extractor:
    def __init__(self, outdir: str):
        self.outdir = outdir

    def extract(self, filepath: str, remove_archive: bool = False) -> Dict[str, Any]:
        dest = filepath + "_extracted"
        res = {"path": filepath, "dest": dest, "ok": False, "error": None}
        try:
            os.makedirs(dest, exist_ok=True)
            if zipfile.is_zipfile(filepath):
                with zipfile.ZipFile(filepath, 'r') as z: z.extractall(dest)
                res["ok"] = True
            else:
                try:
                    with tarfile.open(filepath, 'r:*') as t:
                        t.extractall(dest)
                    res["ok"] = True
                except tarfile.ReadError:
                    res["error"] = "Not a tar/zip archive"
            if res["ok"] and remove_archive:
                try: os.remove(filepath)
                except Exception: pass
        except Exception as e:
            res["error"] = str(e)
        return res

# --------------------- ParserNormalizer (E) ------------------------------- #
class ParserNormalizer:
    """
    Simple parsers that extract common fields from bill XML, vote XML, and legislators JSON.
    These are intentionally minimal and are extension points for robust XPaths or lxml usage.
    """

    @staticmethod
    def parse_bill_xml(path: str) -> Optional[Dict[str, Any]]:
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(path); root = tree.getroot()
            def first_text(tag_list):
                for t in tag_list:
                    el = root.find('.//' + t)
                    if el is not None and el.text:
                        return el.text.strip()
                return None
            bill_num = first_text(['billNumber', 'bill_number', 'billnum'])
            title = first_text(['title', 'shortTitle', 'officialTitle'])
            sponsor = first_text(['sponsor/fullName', 'sponsor/name', 'sponsor'])
            introduced = first_text(['introducedDate', 'introduced_on', 'introduced'])
            return {"bill_number": bill_num, "title": title, "sponsor": sponsor, "introduced_date": introduced, "source_file": path}
        except Exception as e:
            logger.debug("parse_bill_xml error %s: %s", path, e)
            return None

    @staticmethod
    def parse_vote_xml(path: str) -> Optional[Dict[str, Any]]:
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(path); root = tree.getroot()
            def first_text(tag_list):
                for t in tag_list:
                    el = root.find('.//' + t)
                    if el is not None and el.text:
                        return el.text.strip()
                return None
            vote_id = first_text(['vote_id', 'voteNumber', 'vote-number'])
            date = first_text(['voteDate', 'date'])
            result = first_text(['result', 'outcome'])
            return {"vote_id": vote_id, "date": date, "result": result, "source_file": path}
        except Exception as e:
            logger.debug("parse_vote_xml error %s: %s", path, e)
            return None

    @staticmethod
    def parse_legislators_json(path: str) -> List[Dict[str, Any]]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                j = json.load(f)
            rows = []
            for m in j:
                name = m.get("name", {}).get("official_full") or m.get("name")
                bio = m.get("id", {}).get("bioguide") or m.get("id")
                terms = m.get("terms", [])
                current = terms[-1] if terms else {}
                rows.append({"name": name, "bioguide": bio, "current_party": current.get("party"), "state": current.get("state"), "source_file": path})
            return rows
        except Exception as e:
            logger.debug("parse_legislators_json error %s: %s", path, e)
            return []

# ---------------------------- DBIngestor (F) -------------------------------- #
class DBIngestor:
    """
    Connects to Postgres, ensures schema and upserts parsed records.
    """
    SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS bills (
      id SERIAL PRIMARY KEY,
      source_file TEXT,
      congress INTEGER,
      chamber TEXT,
      bill_number TEXT,
      title TEXT,
      sponsor TEXT,
      introduced_date TIMESTAMP,
      inserted_at TIMESTAMP DEFAULT now(),
      UNIQUE (congress, chamber, bill_number)
    );
    CREATE TABLE IF NOT EXISTS votes (
      id SERIAL PRIMARY KEY,
      source_file TEXT,
      congress INTEGER,
      chamber TEXT,
      vote_id TEXT,
      vote_date TIMESTAMP,
      result TEXT,
      inserted_at TIMESTAMP DEFAULT now(),
      UNIQUE (congress, chamber, vote_id)
    );
    CREATE TABLE IF NOT EXISTS legislators (
      id SERIAL PRIMARY KEY,
      name TEXT,
      bioguide TEXT,
      current_party TEXT,
      state TEXT,
      inserted_at TIMESTAMP DEFAULT now(),
      UNIQUE (bioguide)
    );
    """

    def __init__(self, conn_str: str):
        self.conn_str = conn_str
        self.conn = None

    def connect(self):
        if not psycopg2:
            raise RuntimeError("psycopg2 not installed. pip install psycopg2-binary")
        self.conn = psycopg2.connect(self.conn_str)
        self.conn.autocommit = False

    def ensure_schema(self):
        with self.conn.cursor() as cur:
            cur.execute(self.SCHEMA_SQL)
        self.conn.commit()

    def upsert_bill(self, data: Dict[str, Any], congress: Optional[int] = None, chamber: Optional[str] = None):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bills (source_file, congress, chamber, bill_number, title, sponsor, introduced_date)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (congress,chamber,bill_number) DO UPDATE
                SET title = EXCLUDED.title, sponsor = EXCLUDED.sponsor, introduced_date = EXCLUDED.introduced_date
                RETURNING id
            """, (data.get("source_file"), congress, chamber, data.get("bill_number"), data.get("title"), data.get("sponsor"), data.get("introduced_date")))
            res = cur.fetchone()
        self.conn.commit()
        return res[0] if res else None

    def upsert_vote(self, data: Dict[str, Any], congress: Optional[int] = None, chamber: Optional[str] = None):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO votes (source_file, congress, chamber, vote_id, vote_date, result)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (congress,chamber,vote_id) DO UPDATE
                SET result = EXCLUDED.result, vote_date = EXCLUDED.vote_date
                RETURNING id
            """, (data.get("source_file"), congress, chamber, data.get("vote_id"), data.get("date"), data.get("result")))
            res = cur.fetchone()
        self.conn.commit()
        return res[0] if res else None

    def upsert_legislator(self, data: Dict[str, Any]):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO legislators (name, bioguide, current_party, state)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (bioguide) DO UPDATE
                SET name = EXCLUDED.name, current_party = EXCLUDED.current_party, state = EXCLUDED.state
                RETURNING id
            """, (data.get("name"), data.get("bioguide"), data.get("current_party"), data.get("state")))
            res = cur.fetchone()
        self.conn.commit()
        return res[0] if res else None

    def close(self):
        if self.conn:
            self.conn.close()

# -------------------------- RetryManager (G) ------------------------------- #
class RetryManager:
    def __init__(self, report_path: str = DEFAULT_RETRY_REPORT):
        self.report_path = report_path
        self._load()

    def _load(self):
        if os.path.exists(self.report_path):
            with open(self.report_path, "r", encoding="utf-8") as f:
                self.report = json.load(f)
        else:
            self.report = {"failures": []}

    def add_failure(self, url: str, error: str):
        rec = next((r for r in self.report["failures"] if r["url"] == url), None)
        now = datetime.utcnow().isoformat()
        if rec:
            rec["attempts"] = rec.get("attempts", 0) + 1
            rec["last_error"] = error
            rec["last_attempted"] = now
        else:
            self.report["failures"].append({"url": url, "attempts": 1, "first_failed": now, "last_attempted": now, "last_error": error})
        self._save()

    def _save(self):
        with open(self.report_path, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)

    def get_retry_list(self, max_attempts: int = 5) -> List[str]:
        return [r["url"] for r in self.report["failures"] if r.get("attempts", 0) < max_attempts]

    def remove_success(self, url: str):
        self.report["failures"] = [r for r in self.report["failures"] if r["url"] != url]
        self._save()

# ------------------------------- Pipeline (H) ------------------------------ #
class Pipeline:
    def __init__(self, cfg: Config, db_conn: Optional[str] = None):
        self.cfg = cfg
        self.discovery = DiscoveryManager(cfg)
        self.validator = Validator()
        self.downloader = DownloadManager(cfg.outdir, concurrency=cfg.concurrency, retries=cfg.retries)
        self.extractor = Extractor(cfg.outdir)
        self.parser = ParserNormalizer()
        self.retry_mgr = RetryManager(cfg.retry_report)
        self.db_conn = db_conn
        self.db_ingestor = DBIngestor(db_conn) if db_conn else None

    def discover(self) -> Dict[str, List[str]]:
        data = self.discovery.build()
        with open(self.cfg.output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Discovery written to %s", self.cfg.output_file)
        return data

    def validate(self, urls: List[str]) -> List[str]:
        logger.info("Validating %d candidate URLs", len(urls))
        valid = []
        for u in urls:
            if self.validator.head_check(u):
                valid.append(u)
        logger.info("%d URLs validated", len(valid))
        return valid

    def download(self, urls: List[str]) -> List[Dict[str, Any]]:
        logger.info("Beginning download of %d files", len(urls))
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(self.downloader.download_all(urls))
        logger.info("Download finished")
        for r in results:
            if not r.get("ok"):
                self.retry_mgr.add_failure(r["url"], r.get("error", "unknown"))
        return results

    def extract_all(self, download_results: List[Dict[str, Any]], remove_archives: bool = False):
        extracted = []
        for r in download_results:
            if not r.get("ok"): continue
            p = r.get("path")
            if not p: continue
            if re.search(r'\.(zip|tar\.gz|tgz|tar)$', p, re.IGNORECASE):
                res = self.extractor.extract(p, remove_archive=remove_archives)
                if res.get("ok"):
                    extracted.append(res)
        logger.info("Extraction complete: %d archives extracted", len(extracted))
        return extracted

    def postprocess_and_ingest(self, collections: Optional[List[str]] = None):
        if not self.db_ingestor:
            logger.warning("No DB connection provided; skipping postprocessing ingestion")
            return
        self.db_ingestor.connect()
        self.db_ingestor.ensure_schema()
        # Walk outdir for extracted paths
        for root, dirs, files in os.walk(self.cfg.outdir):
            for fname in files:
                path = os.path.join(root, fname)
                lower = fname.lower()
                # legislators JSON
                if (not collections or "legislators" in collections) and lower.endswith(".json") and "legislators" in fname.lower():
                    rows = self.parser.parse_legislators_json(path)
                    for r in rows:
                        self.db_ingestor.upsert_legislator(r)
                # bills XML
                elif (not collections or any(c in ["bills", "billstatus"] for c in (collections or []))) and lower.endswith(".xml") and ("bill" in lower or "billstatus" in lower):
                    rec = self.parser.parse_bill_xml(path)
                    if rec:
                        self.db_ingestor.upsert_bill(rec)
                # votes XML
                elif (not collections or "rollcall" in (collections or [])) and lower.endswith(".xml") and ("vote" in lower or "rollcall" in lower or "rollcallvote" in lower):
                    rec = self.parser.parse_vote_xml(path)
                    if rec:
                        self.db_ingestor.upsert_vote(rec)
        self.db_ingestor.close()
        logger.info("Post-processing ingestion complete")

    def run_once(self, do_validate: bool = False, do_download: bool = False, do_extract: bool = False, do_postprocess: bool = False, db_conn: Optional[str] = None, limit: int = 0, remove_archives: bool = False):
        discovery = self.discover()
        agg = discovery.get("aggregate_urls", [])
        if limit and limit > 0:
            agg = agg[:limit]
        if do_validate:
            agg = self.validate(agg)
        if do_download and agg:
            results = self.download(agg)
            if do_extract:
                self.extract_all(results, remove_archives)
            if do_postprocess and db_conn:
                self.postprocess_and_ingest(self.cfg.collections)
        logger.info("Run once complete")

    def schedule_loop(self, interval_minutes: int, retry_interval: int = 60, max_attempts: int = 5, **kwargs):
        logger.info("Entering schedule loop every %d minutes", interval_minutes)
        try:
            while True:
                self.run_once(**kwargs)
                # attempt retries
                retry_list = self.retry_mgr.get_retry_list(max_attempts)
                if retry_list:
                    logger.info("Retrying %d failed URLs", len(retry_list))
                    results = self.download(retry_list)
                    for r in results:
                        if r.get("ok"):
                            self.retry_mgr.remove_success(r["url"])
                logger.info("Sleeping %d minutes", interval_minutes)
                time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            logger.info("Schedule loop stopped by user")

# ------------------------------ CLI Entrypoint ------------------------------ #
def parse_args():
    parser = argparse.ArgumentParser(description="OOP End-to-end Congress bulk data pipeline")
    now = datetime.utcnow()
    current_cong = 1 + (now.year - 1789) // 2
    parser.add_argument("--start-congress", type=int, default=93)
    parser.add_argument("--end-congress", type=int, default=max(current_cong+1, 119))
    parser.add_argument("--outdir", type=str, default=DEFAULT_OUTDIR)
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT)
    parser.add_argument("--retry-report", type=str, default=DEFAULT_RETRY_REPORT)
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--collections", type=str, default="", help="Comma-separated: bills,rollcall,legislators,openstates,plaw,crec")
    parser.add_argument("--no-discovery", dest="do_discovery", action="store_false")
    parser.add_argument("--validate", dest="do_validate", action="store_true")
    parser.add_argument("--download", dest="do_download", action="store_true")
    parser.add_argument("--extract", dest="do_extract", action="store_true")
    parser.add_argument("--remove-archives", dest="remove_archives", action="store_true")
    parser.add_argument("--postprocess", dest="do_postprocess", action="store_true", help="Run DB ingestion after extract")
    parser.add_argument("--db", type=str, default="", help="Postgres conn string (psycopg2)")
    parser.add_argument("--schedule-interval", type=int, default=0, help="Minutes between scheduled runs (0 = no schedule)")
    parser.add_argument("--retry-interval", type=int, default=60, help="Minutes between retry rounds")
    parser.add_argument("--retry-max-attempts", type=int, default=5)
    parser.add_argument("--limit", type=int, default=0, help="Limit candidate URLs processed (0 = all)")
    parser.add_argument("--dry-run", action="store_true", help="Discover and print sample without downloads")
    return parser.parse_args()

def main():
    args = parse_args()
    collections = [c.strip().lower() for c in args.collections.split(",") if c.strip()] if args.collections else None
    cfg = Config(start_congress=args.start_congress, end_congress=args.end_congress, outdir=args.outdir, output_file=args.output, retry_report=args.retry_report, concurrency=args.concurrency, retries=args.retries, collections=collections, do_discovery=args.do_discovery)
    pipeline = Pipeline(cfg, db_conn=args.db if args.db else None)

    # Dry run: discover only and show sample
    if args.dry_run:
        data = pipeline.discover()
        sample = data.get("aggregate_urls", [])[:20]
        print("DRY-RUN SAMPLE (first 20 aggregate URLs):")
        for s in sample:
            print(" -", s)
        return

    # Single run
    pipeline.run_once(do_validate=args.do_validate, do_download=args.do_download, do_extract=args.do_extract, do_postprocess=args.do_postprocess, db_conn=args.db if args.db else None, limit=args.limit, remove_archives=args.remove_archives)

    # Schedule loop if requested
    if args.schedule_interval and args.schedule_interval > 0:
        pipeline.schedule_loop(interval_minutes=args.schedule_interval, retry_interval=args.retry_interval, max_attempts=args.retry_max_attempts, do_validate=args.do_validate, do_download=args.do_download, do_extract=args.do_extract, do_postprocess=args.do_postprocess, db_conn=args.db if args.db else None, limit=args.limit, remove_archives=args.remove_archives)

if __name__ == "__main__":
    main()