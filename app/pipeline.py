###############################################################################
# Name:        Pipeline classes and orchestration
# Date:        2025-10-02
# Script Name: pipeline.py
# Version:     1.0
# Log Summary: Contains DiscoveryManager, Validator, DownloadManager, Extractor,
#              ParserNormalizer, RetryManager, HTTPControlServer, and Pipeline.
# Description: OOP organization for the end-to-end pipeline. Uses utils and db helpers.
# Change Summary:
#   - 1.0: Basic class implementations and orchestration methods with decorators,
#          verbose logging, and error handling.
# Inputs: configuration values and CLI args
# Outputs: discovery JSON, retry reports, logs, DB ingestion
###############################################################################

import os
import re
import json
import glob
import asyncio
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

from app.utils import configure_logger, labeled, save_json_atomic, load_json_safe, ensure_dirs
from app.db import DBIngestor, run_migrations

logger = configure_logger("pipeline", level=20)

# Import aiohttp dynamically where needed to avoid startup errors if not installed
try:
    import aiohttp
except Exception:
    aiohttp = None

# DiscoveryManager (reuses app/utils for logging)
class DiscoveryManager:
    def __init__(self, cfg):
        self.cfg = cfg
        self.logger = configure_logger("discovery")
        self.GOVINFO_INDEX = "https://www.govinfo.gov/bulkdata"
        self.TEMPLATES = {
            "billstatus": "https://www.govinfo.gov/bulkdata/BILLSTATUS/{congress}/{chamber}/BILLSTATUS-{congress}{chamber}.zip",
            "rollcall": "https://www.govinfo.gov/bulkdata/ROLLCALLVOTE/{congress}/{chamber}/ROLLCALLVOTE-{congress}-{chamber}.zip",
            "bills": "https://www.govinfo.gov/bulkdata/BILLS/{congress}/{chamber}/BILLS-{congress}{chamber}.zip",
            "plaw": "https://www.govinfo.gov/bulkdata/PLAW/{congress}/PLAW-{congress}.zip",
            "crec": "https://www.govinfo.gov/bulkdata/CREC/{congress}/CREC-{congress}.zip",
        }
        self.CHAMBERS = ["hr", "house", "h", "senate", "s"]

    @labeled("discovery_expand")
    def expand_templates(self):
        out = []
        for c in range(self.cfg.start_congress, self.cfg.end_congress + 1):
            for key, tpl in self.TEMPLATES.items():
                if self.cfg.collections and key not in self.cfg.collections:
                    continue
                if "{chamber}" in tpl:
                    for ch in self.CHAMBERS:
                        out.append(tpl.format(congress=c, chamber=ch))
                else:
                    out.append(tpl.format(congress=c))
        # dedupe
        seen = set(); dedup = []
        for u in out:
            if u not in seen:
                dedup.append(u); seen.add(u)
        return dedup

    @labeled("discovery_index_crawl")
    def crawl_index(self):
        # lightweight index crawl: fetch GOVINFO_INDEX and regex hrefs
        res = []
        try:
            import requests
            r = requests.get(self.GOVINFO_INDEX, timeout=20)
            if r.status_code == 200:
                for m in re.finditer(r'href=["\']([^"\']+)["\']', r.text, re.IGNORECASE):
                    href = m.group(1)
                    if href.startswith("/"):
                        full = "https://www.govinfo.gov" + href
                    elif href.startswith("http"):
                        full = href
                    else:
                        continue
                    if re.search(r'\.(zip|tar\.gz|tgz|json|xml|csv)$', full, re.IGNORECASE):
                        res.append(full)
        except Exception:
            self.logger.exception("Index crawl failed")
        return list(dict.fromkeys(res))

# Validator
class Validator:
    def __init__(self):
        self.logger = configure_logger("validator")

    @labeled("validator_head")
    def head_ok(self, url: str) -> bool:
        try:
            import requests
            r = requests.head(url, timeout=20, allow_redirects=True)
            if r.status_code < 400:
                return True
            # fallback to small GET
            r2 = requests.get(url, timeout=20, stream=True)
            ok = r2.status_code < 400
            r2.close()
            return ok
        except Exception:
            return False

# DownloadManager
class DownloadManager:
    def __init__(self, outdir: str, concurrency: int = 6, retries: int = 5):
        ensure_dirs(outdir)
        self.outdir = outdir
        self.concurrency = concurrency
        self.retries = retries
        self.logger = configure_logger("downloader")

    async def _head_info(self, session, url):
        try:
            async with session.head(url, timeout=aiohttp.ClientTimeout(total=30), allow_redirects=True) as resp:
                status = resp.status
                cl = resp.headers.get("Content-Length")
                ar = resp.headers.get("Accept-Ranges", "")
                return {"status": status, "size": int(cl) if cl and cl.isdigit() else None, "resumable": "bytes" in ar.lower()}
        except Exception:
            return {"status": None, "size": None, "resumable": False}

    async def _fetch(self, session, url, dest):
        attempt = 0
        while attempt <= self.retries:
            attempt += 1
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
                    if resp.status >= 400:
                        raise Exception(f"HTTP {resp.status}")
                    # write stream
                    chunk = 1 << 16
                    written = existing
                    with open(dest, mode) as fh:
                        async for ch in resp.content.iter_chunked(chunk):
                            if not ch:
                                break
                            fh.write(ch)
                            written += len(ch)
                    return {"ok": True, "bytes": written, "path": dest}
            except Exception as e:
                self.logger.warning("Download attempt %d failed for %s: %s", attempt, url, e)
                await asyncio.sleep(min(30, 2 ** attempt))
        return {"ok": False, "error": f"Failed after {self.retries} attempts", "path": dest}

    @labeled("downloader_batch")
    def download_all(self, urls: List[str]) -> List[Dict[str, Any]]:
        if aiohttp is None:
            raise RuntimeError("aiohttp not installed")
        async def runner():
            sem = asyncio.Semaphore(self.concurrency)
            connector = aiohttp.TCPConnector(limit_per_host=self.concurrency, limit=0)
            results = []
            async with aiohttp.ClientSession(connector=connector) as session:
                tasks = []
                for i, u in enumerate(urls):
                    filename = u.split("?")[0].rstrip("/").split("/")[-1] or f"file_{i}"
                    domain = urlparse(u).netloc.replace(":", "_")
                    ddir = os.path.join(self.outdir, domain)
                    ensure_dirs(ddir)
                    dest = os.path.join(ddir, filename)
                    async def sem_task(u=u, dest=dest):
                        async with sem:
                            return await self._fetch(session, u, dest)
                    tasks.append(asyncio.create_task(sem_task()))
                for fut in asyncio.as_completed(tasks):
                    res = await fut
                    results.append(res)
            return results
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(runner())

# Extractor
class Extractor:
    def __init__(self):
        self.logger = configure_logger("extractor")

    @labeled("extractor_extract")
    def extract(self, filepath: str, remove_archive: bool = False) -> Dict[str, Any]:
        dest = filepath + "_extracted"
        os.makedirs(dest, exist_ok=True)
        try:
            if zipfile.is_zipfile(filepath):
                with zipfile.ZipFile(filepath, "r") as z:
                    z.extractall(dest)
            else:
                with tarfile.open(filepath, "r:*") as t:
                    t.extractall(dest)
            if remove_archive:
                try:
                    os.remove(filepath)
                except Exception:
                    pass
            return {"ok": True, "dest": dest}
        except Exception as e:
            self.logger.exception("Extraction failed for %s", filepath)
            return {"ok": False, "error": str(e)}

# ParserNormalizer (simple)
class ParserNormalizer:
    def __init__(self):
        self.logger = configure_logger("parser")

    @labeled("parser_parse_bill")
    def parse_bill(self, path: str) -> Optional[Dict[str, Any]]:
        # Minimal conservative parse; extend per real schemas
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(path); root = tree.getroot()
            def first(names):
                for n in names:
                    el = root.find(".//" + n)
                    if el is not None and el.text:
                        return el.text.strip()
                return None
            return {"source_file": path, "bill_number": first(["billNumber", "bill_number"]), "title": first(["title", "shortTitle", "officialTitle"]), "sponsor": first(["sponsor/name", "sponsor/fullName"])}
        except Exception:
            self.logger.debug("Bill parse failed for %s", path)
            return None

    @labeled("parser_parse_vote")
    def parse_vote(self, path: str) -> Optional[Dict[str, Any]]:
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(path); root = tree.getroot()
            def first(names):
                for n in names:
                    el = root.find(".//" + n)
                    if el is not None and el.text:
                        return el.text.strip()
                return None
            return {"source_file": path, "vote_id": first(["vote_id", "voteNumber"]), "date": first(["voteDate", "date"]), "result": first(["result"])}
        except Exception:
            self.logger.debug("Vote parse failed for %s", path)
            return None

    @labeled("parser_parse_legislators")
    def parse_legislators(self, path: str) -> List[Dict[str, Any]]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                j = json.load(f)
            out = []
            for m in j:
                name = m.get("name", {}).get("official_full") or m.get("name")
                bio = m.get("id", {}).get("bioguide") or m.get("id")
                terms = m.get("terms", [])
                cur = terms[-1] if terms else {}
                out.append({"name": name, "bioguide": bio, "current_party": cur.get("party"), "state": cur.get("state"), "source_file": path})
            return out
        except Exception:
            self.logger.debug("Legislator parse failed for %s", path)
            return []

# RetryManager
class RetryManager:
    def __init__(self, path: str):
        self.path = path
        self._load()

    @labeled("retry_load")
    def _load(self):
        if os.path.exists(self.path):
            self.data = load_json_safe(self.path) or {"failures": []}
        else:
            self.data = {"failures": []}

    @labeled("retry_add")
    def add(self, url: str, error: str):
        now = datetime.utcnow().isoformat()
        rec = next((r for r in self.data["failures"] if r["url"] == url), None)
        if rec:
            rec["attempts"] = rec.get("attempts", 0) + 1
            rec["last_error"] = error
            rec["last_attempted"] = now
        else:
            self.data["failures"].append({"url": url, "attempts": 1, "last_error": error, "first_failed": now, "last_attempted": now})
        save_json_atomic(self.path, self.data)

    @labeled("retry_list")
    def list_to_retry(self, max_attempts: int = 5):
        return [r["url"] for r in self.data["failures"] if r.get("attempts", 0) < max_attempts]

    @labeled("retry_remove")
    def remove(self, url: str):
        self.data["failures"] = [r for r in self.data["failures"] if r["url"] != url]
        save_json_atomic(self.path, self.data)

# Pipeline orchestrator
class Pipeline:
    def __init__(self, cfg, db_conn: Optional[str] = None):
        self.cfg = cfg
        self.discovery = DiscoveryManager(cfg)
        self.validator = Validator()
        self.downloader = DownloadManager(cfg.outdir, cfg.concurrency, cfg.retries)
        self.extractor = Extractor()
        self.parser = ParserNormalizer()
        self.retry = RetryManager(cfg.retry_report)
        self.db_conn = db_conn
        self.db_ingestor = DBIngestor(db_conn) if db_conn else None

    @labeled("pipeline_discover")
    def discover(self):
        out = {}
        out["templates"] = self.discovery.expand_templates()
        if self.cfg.do_discovery:
            out["index"] = self.discovery.crawl_index()
        else:
            out["index"] = []
        out["legislators"] = DiscoveryManager.THEUNITEDSTATES_LEGISLATORS if hasattr(DiscoveryManager, "THEUNITEDSTATES_LEGISLATORS") else []
        # aggregate
        agg = []
        for v in out.values():
            if isinstance(v, list):
                agg.extend(v)
        out["aggregate_urls"] = list(dict.fromkeys(agg))
        save_json_atomic(self.cfg.output_file, out)
        return out

    @labeled("pipeline_run")
    def run_once(self, validate=False, download=False, extract=False, postprocess=False):
        data = self.discover()
        urls = data.get("aggregate_urls", [])
        if validate:
            urls = [u for u in urls if self.validator.head_ok(u)]
        if download and urls:
            results = self.downloader.download_all(urls)
            for r in results:
                if not r.get("ok"):
                    self.retry.add(r.get("path") or "unknown", r.get("error", "download failed"))
            if extract:
                self.extractor  # placeholder: extraction loop in real run
        if postprocess and self.db_conn:
            # run migrations and ingest
            run_migrations(self.db_conn, os.path.join(os.path.dirname(__file__), "db", "migrations"))
            dbi = DBIngestor(self.db_conn); dbi.connect()
            dbi.ensure_schema(os.path.join(os.path.dirname(__file__), "db", "migrations"))
            # naive ingestion: walk extracted content and insert
            for root, dirs, files in os.walk(self.cfg.outdir):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    lower = fname.lower()
                    if lower.endswith(".json") and "legislators" in fname.lower():
                        rows = self.parser.parse_legislators(fpath)
                        for row in rows:
                            dbi.upsert_legislator(row)
                    elif lower.endswith(".xml") and "bill" in lower:
                        rec = self.parser.parse_bill(fpath)
                        if rec: dbi.upsert_bill(rec)
                    elif lower.endswith(".xml") and "vote" in lower:
                        rec = self.parser.parse_vote(fpath)
                        if rec: dbi.upsert_vote(rec)
            dbi.close()