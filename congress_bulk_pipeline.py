###############################################################################
# Name:        Congress Bulk Legislative Pipeline
# Date:        2025-10-01
# Script Name: congress_bulk_pipeline.py
# Version:     1.0
# Log Summary: Single-file end-to-end discovery, download, extract, parse,
#              normalize, and ingest pipeline for legislative bulk data.
# Description: Discovers authoritative bulk-data URLs (govinfo, GovTrack,
#              theunitedstates, OpenStates, Data.gov pointers), validates
#              candidates, optionally downloads with concurrent resume/retry,
#              auto-extracts archives, post-processes XML/JSON into a
#              normalized PostgreSQL schema (bills, votes, members), and
#              optionally runs on a schedule. Produces retry_report.json.
# Change Summary:
#   - 1.0: Initial release adding:
#       * discovery (templates + index crawling)
#       * HEAD validation, filtered candidate list
#       * concurrent downloader with resume and retries
#       * automatic extraction (zip/tar/tgz)
#       * post-processing parser/normalizer for bill and vote files into Postgres
#       * retry-report + periodic retry logic
#       * scheduling wrapper and dry-run mode
# Inputs:
#   - CLI arguments: start/end congress, discovery toggle, download toggle,
#     collection filters, validate flag, extract, schedule interval, dry-run, etc.
# Outputs:
#   - bulk_urls.json (discovered candidates)
#   - retry_report.json (failed download attempts / retry history)
#   - downloaded archives and extracted files under outdir
#   - normalized PostgreSQL tables (when DB options provided)
###############################################################################

import os
import re
import sys
import json
import time
import asyncio
import argparse
import logging
import shutil
import tarfile
import zipfile
from html import unescape
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin

# Network + DB libs
try:
    import requests
    import aiohttp
    import psycopg2
    import psycopg2.extras
except Exception as e:
    # We'll handle missing libs at runtime with a clear error
    pass

# Optional progress bars
try:
    from tqdm import tqdm
    TQDM = True
except Exception:
    TQDM = False

# ----------------------------- Logging ------------------------------------- #
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("congress_bulk")

# -------------------------- Default Config --------------------------------- #
REQUESTS_TIMEOUT = 20
DEFAULT_OUTPUT_FILE = "bulk_urls.json"
DEFAULT_RETRY_REPORT = "retry_report.json"
DEFAULT_OUTDIR = "./bulk_data"
DEFAULT_CONCURRENCY = 6
DEFAULT_RETRIES = 5
DEFAULT_START_CONGRESS = 93

# --------------------------- Source Templates ------------------------------ #
SOURCES = {
    "govinfo": {
        "index_url": "https://www.govinfo.gov/bulkdata",
        "templates": {
            "billstatus": "https://www.govinfo.gov/bulkdata/BILLSTATUS/{congress}/{chamber}/BILLSTATUS-{congress}{chamber}.zip",
            "rollcall": "https://www.govinfo.gov/bulkdata/ROLLCALLVOTE/{congress}/{chamber}/ROLLCALLVOTE-{congress}-{chamber}.zip",
            "bills": "https://www.govinfo.gov/bulkdata/BILLS/{congress}/{chamber}/BILLS-{congress}{chamber}.zip",
            "plaw": "https://www.govinfo.gov/bulkdata/PLAW/{congress}/PLAW-{congress}.zip",
            "crec": "https://www.govinfo.gov/bulkdata/CREC/{congress}/CREC-{congress}.zip",
        },
        "chambers": ["hr", "house", "h", "senate", "s"],
    },
    "congress_legislators": {
        "urls": [
            "https://theunitedstates.io/congress-legislators/legislators-current.json",
            "https://theunitedstates.io/congress-legislators/legislators-historical.json",
        ]
    },
    "govtrack": {
        "base": "https://www.govtrack.us/data",
        "templates": {"per_congress_dir": "https://www.govtrack.us/data/us/{congress}/", "bulk_export_example": "https://www.govtrack.us/data/us/bills/bills.csv"}
    },
    "openstates": {
        "downloads_page": "https://openstates.org/downloads/",
        "plural_mirror": "https://open.pluralpolicy.com/data/",
    },
    "data_gov": {
        "ckan_search_api": "https://catalog.data.gov/api/3/action/package_search?q=congress OR congressional OR legislative"
    }
}

US_STATES = [
 'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
 'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
 'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','PR'
]

# ----------------------------- Utilities ----------------------------------- #
def now_congress() -> int:
    dt = datetime.utcnow()
    return 1 + (dt.year - 1789) // 2

def congress_first_year(congress: int) -> int:
    return 1789 + 2 * (congress - 1)

def http_get_text(url: str, timeout=REQUESTS_TIMEOUT) -> Optional[str]:
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.text
        logger.debug("GET %s -> status %s", url, r.status_code)
    except Exception as e:
        logger.debug("GET %s failed: %s", url, e)
    return None

def is_likely_archive(url: str) -> bool:
    return bool(re.search(r'\.(zip|tar\.gz|tgz|tar|json|xml|csv)$', url, re.IGNORECASE))

# ---------------------------- Discovery ------------------------------------ #
def expand_govinfo_templates(start: int, end: int, collections: Optional[List[str]] = None) -> List[str]:
    urls = []
    templates = SOURCES["govinfo"]["templates"]
    chambers = SOURCES["govinfo"]["chambers"]
    for c in range(start, end + 1):
        for key, tpl in templates.items():
            if collections and key not in collections:
                continue
            if "{chamber}" in tpl:
                for ch in set(chambers):
                    try:
                        urls.append(tpl.format(congress=c, chamber=ch))
                    except Exception:
                        pass
            else:
                try:
                    year = congress_first_year(c)
                    urls.append(tpl.format(congress=c, year=year))
                except Exception:
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

def discover_govinfo_index(index_url: str = SOURCES["govinfo"]["index_url"]) -> List[str]:
    html = http_get_text(index_url)
    links = []
    if not html:
        return links
    for match in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
        href = unescape(match.group(1))
        if href.startswith("/"):
            full = "https://www.govinfo.gov" + href
        elif href.startswith("http"):
            full = href
        else:
            continue
        if is_likely_archive(full):
            links.append(full)
    return list(dict.fromkeys(links))

def discover_govtrack(congress_range: range) -> List[str]:
    urls = []
    urls.append(SOURCES["govtrack"]["templates"]["bulk_export_example"])
    for c in congress_range:
        dir_url = SOURCES["govtrack"]["templates"]["per_congress_dir"].format(congress=c)
        html = http_get_text(dir_url)
        if not html:
            continue
        for match in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
            href = unescape(match.group(1))
            candidate = href if href.startswith("http") else urljoin(dir_url, href)
            if is_likely_archive(candidate):
                urls.append(candidate)
    return list(dict.fromkeys(urls))

def discover_openstates(do_discovery=True) -> Dict[str, Any]:
    result = {"downloads_page": SOURCES["openstates"]["downloads_page"], "plural_mirror": SOURCES["openstates"]["plural_mirror"], "discovered": []}
    if not do_discovery:
        return result
    html = http_get_text(SOURCES["openstates"]["downloads_page"])
    if html:
        for match in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
            href = unescape(match.group(1))
            if href.startswith("http"):
                candidate = href
            elif href.startswith("/"):
                candidate = "https://openstates.org" + href
            else:
                continue
            if re.search(r'\.(zip|json|csv|tgz|tar\.gz)$', candidate, re.IGNORECASE):
                result["discovered"].append(candidate)
    plural_html = http_get_text(SOURCES["openstates"]["plural_mirror"])
    if plural_html:
        for match in re.finditer(r'href=["\']([^"\']+)["\']', plural_html, re.IGNORECASE):
            href = unescape(match.group(1))
            candidate = href if href.startswith("http") else SOURCES["openstates"]["plural_mirror"].rstrip("/") + "/" + href
            if re.search(r'\.(zip|json|csv|tgz|tar\.gz)$', candidate, re.IGNORECASE):
                result["discovered"].append(candidate)
    # guessed per-state patterns
    mirror_base = SOURCES["openstates"]["plural_mirror"].rstrip("/") + "/"
    for st in US_STATES:
        patterns = [
            f"openstates-{st.lower()}.zip",
            f"{st.lower()}.zip",
            f"openstates-{st.lower()}.json.zip",
            f"openstates-{st.lower()}-latest.json.zip",
        ]
        for p in patterns:
            result["discovered"].append(mirror_base + p)
    result["discovered"] = list(dict.fromkeys([u for u in result["discovered"] if u]))
    return result

def assemble_bulk_url_dict(start_congress: int, end_congress: int, do_discovery=True, collections: Optional[List[str]] = None) -> Dict[str, Any]:
    logger.info("Expanding templates for congress range %d..%d", start_congress, end_congress)
    result = {}
    result["govinfo_templates_expanded"] = expand_govinfo_templates(start_congress, end_congress, collections)
    result["govinfo_index_discovered"] = discover_govinfo_index() if do_discovery else []
    result["congress_legislators"] = SOURCES["congress_legislators"]["urls"]
    result["govtrack"] = discover_govtrack(range(start_congress, end_congress + 1)) if do_discovery else []
    result["openstates"] = discover_openstates(do_discovery)
    result["data_gov"] = {"ckan_search_api": SOURCES["data_gov"]["ckan_search_api"], "notes": "Use CKAN to find additional datasets"}
    # flatten aggregate URLs
    aggregate = []
    for k, v in result.items():
        if isinstance(v, list):
            aggregate.extend([u for u in v if isinstance(u, str) and u.startswith("http")])
        elif isinstance(v, dict):
            for iv in v.values():
                if isinstance(iv, list):
                    aggregate.extend([u for u in iv if isinstance(u, str) and u.startswith("http")])
                elif isinstance(iv, str) and iv.startswith("http"):
                    aggregate.append(iv)
    # apply simple collection filtering
    if collections:
        filtered = []
        coll_set = set(collections)
        for u in aggregate:
            lower = u.lower()
            keep = False
            if "openstates" in coll_set and ("openstates" in lower or "pluralpolicy" in lower):
                keep = True
            if "legislators" in coll_set and ("congress-legislators" in lower or "legislators" in lower):
                keep = True
            for c in coll_set:
                if c in lower:
                    keep = True
            if keep:
                filtered.append(u)
        if filtered:
            aggregate = filtered
    result["aggregate_urls"] = list(dict.fromkeys(aggregate))
    logger.info("Assembled %d aggregate candidate URLs", len(result["aggregate_urls"]))
    return result

# ------------------------- HEAD Validation --------------------------------- #
def validate_urls_head(urls: List[str], timeout: int = 20) -> List[str]:
    valid = []
    session = requests.Session()
    for u in urls:
        try:
            r = session.head(u, timeout=timeout, allow_redirects=True)
            status = r.status_code
            if status >= 400:
                r2 = session.get(u, timeout=timeout, stream=True)
                status = r2.status_code
                r2.close()
            if status < 400:
                valid.append(u)
            else:
                logger.debug("HEAD/GET %s returned %d", u, status)
        except Exception as e:
            logger.debug("HEAD failed for %s: %s", u, e)
    session.close()
    return valid

# ---------------------------- Async Downloader ------------------------------ #
async def head_info(session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
    result = {"url": url, "ok": False, "size": None, "resumable": False, "status": None}
    try:
        async with session.head(url, timeout=aiohttp.ClientTimeout(total=30), allow_redirects=True) as resp:
            result["status"] = resp.status
            if resp.status < 400:
                result["ok"] = True
                cl = resp.headers.get("Content-Length")
                if cl and cl.isdigit():
                    result["size"] = int(cl)
                accept = resp.headers.get("Accept-Ranges", "")
                result["resumable"] = "bytes" in accept.lower()
    except Exception:
        pass
    return result

async def stream_download(session: aiohttp.ClientSession, url: str, dest: str, sem: asyncio.Semaphore,
                          retries: int = DEFAULT_RETRIES, show_progress: bool = True) -> Dict[str, Any]:
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    attempt = 0
    result = {"url": url, "path": dest, "ok": False, "bytes": 0, "error": None}
    while attempt <= retries:
        attempt += 1
        try:
            async with sem:
                head = await head_info(session, url)
                size = head.get("size")
                resumable = head.get("resumable", False)
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
                    if TQDM and show_progress:
                        desc = os.path.basename(dest)
                        with open(dest, mode) as fh, tqdm(total=total, unit="B", unit_scale=True, unit_divisor=1024,
                                                         initial=existing, desc=desc[:40], leave=False) as pbar:
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
            logger.warning("Attempt %d/%d failed for %s: %s", attempt, retries, url, e)
            await asyncio.sleep(min(30, 2 ** attempt))
            continue
    return result

async def download_all_async(urls: List[str], outdir: str, concurrency: int = DEFAULT_CONCURRENCY, retries: int = DEFAULT_RETRIES):
    os.makedirs(outdir, exist_ok=True)
    sem = asyncio.Semaphore(concurrency)
    connector = aiohttp.TCPConnector(limit_per_host=concurrency, limit=0)
    tasks = []
    async with aiohttp.ClientSession(connector=connector) as session:
        for i, u in enumerate(urls):
            filename = u.split("?")[0].rstrip("/").split("/")[-1] or f"file_{i}"
            domain = urlparse(u).netloc.replace(":", "_")
            dest_dir = os.path.join(outdir, domain)
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, filename)
            tasks.append(stream_download(session, u, dest, sem, retries=retries, show_progress=TQDM))
        if TQDM:
            results = []
            for f in asyncio.as_completed(tasks):
                r = await f; results.append(r)
            return results
        else:
            return await asyncio.gather(*tasks)

# ---------------------------- Extraction ----------------------------------- #
def extract_archive(path: str, dest_dir: str) -> Dict[str, Any]:
    res = {"path": path, "extracted_to": None, "ok": False, "error": None}
    try:
        os.makedirs(dest_dir, exist_ok=True)
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path, 'r') as z: z.extractall(dest_dir)
            res["extracted_to"] = dest_dir; res["ok"] = True; return res
        try:
            with tarfile.open(path, 'r:*') as t:
                t.extractall(dest_dir)
            res["extracted_to"] = dest_dir; res["ok"] = True; return res
        except tarfile.ReadError:
            pass
        res["error"] = "Not a supported archive format"
    except Exception as e:
        res["error"] = str(e)
    return res

# ------------------------- Post-processing / Normalization ----------------- #
# NOTE: This parser is intentionally conservative and handles common fields.
# Expand with more robust XPaths / field mappings for production usage.

def parse_bill_xml_simple(xml_path: str) -> Optional[Dict[str, Any]]:
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(xml_path); root = tree.getroot()
        def text(xpath):
            el = root.find(xpath)
            return el.text.strip() if el is not None and el.text else None
        # heuristics for common fields
        bill_number = text('.//billNumber') or text('.//bill_number') or os.path.basename(xml_path)
        title = text('.//title') or text('.//shortTitle') or text('.//officialTitle')
        sponsor = text('.//sponsor//name') or text('.//sponsor//fullName')
        introduced = text('.//introducedDate') or text('.//introduced_on')
        return {"bill_number": bill_number, "title": title, "sponsor": sponsor, "introduced_date": introduced, "source_file": xml_path}
    except Exception as e:
        logger.debug("parse_bill_xml_simple failed for %s: %s", xml_path, e)
        return None

def parse_vote_xml_simple(xml_path: str) -> Optional[Dict[str, Any]]:
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(xml_path); root = tree.getroot()
        def text(xpath):
            el = root.find(xpath)
            return el.text.strip() if el is not None and el.text else None
        vote_id = text('.//vote_id') or text('.//voteNumber') or os.path.basename(xml_path)
        date = text('.//voteDate') or text('.//date')
        result = text('.//result')
        return {"vote_id": vote_id, "date": date, "result": result, "source_file": xml_path}
    except Exception as e:
        logger.debug("parse_vote_xml_simple failed for %s: %s", xml_path, e)
        return None

def parse_legislators_json(json_path: str) -> List[Dict[str, Any]]:
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            j = json.load(f)
            out = []
            for m in j:
                name = m.get("name", {}).get("official_full") or m.get("name")
                bio = m.get("id", {}).get("bioguide") or m.get("id")
                terms = m.get("terms", [])
                current = terms[-1] if terms else {}
                out.append({"name": name, "bioguide": bio, "current_party": current.get("party"), "state": current.get("state")})
            return out
    except Exception as e:
        logger.debug("parse_legislators_json failed for %s: %s", json_path, e)
        return []

# ------------------------- PostgreSQL Ingestion ----------------------------- #
SQL_SCHEMA = """
-- bills table
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

-- votes table
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

-- legislators table
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

def db_connect(connstr: str):
    conn = psycopg2.connect(connstr)
    return conn

def ensure_schema(conn):
    with conn.cursor() as cur:
        cur.execute(SQL_SCHEMA)
    conn.commit()

def upsert_bill(conn, data: Dict[str, Any], congress: Optional[int] = None, chamber: Optional[str] = None):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO bills (source_file, congress, chamber, bill_number, title, sponsor, introduced_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (congress,chamber,bill_number) DO UPDATE
            SET title = EXCLUDED.title, sponsor = EXCLUDED.sponsor, introduced_date = EXCLUDED.introduced_date
            RETURNING id
        """, (data.get("source_file"), congress, chamber, data.get("bill_number"), data.get("title"), data.get("sponsor"), data.get("introduced_date")))
        conn.commit()
        return cur.fetchone()[0]

def upsert_vote(conn, data: Dict[str, Any], congress: Optional[int] = None, chamber: Optional[str] = None):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO votes (source_file, congress, chamber, vote_id, vote_date, result)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (congress,chamber,vote_id) DO UPDATE
            SET result = EXCLUDED.result, vote_date = EXCLUDED.vote_date
            RETURNING id
        """, (data.get("source_file"), congress, chamber, data.get("vote_id"), data.get("date"), data.get("result")))
        conn.commit()
        return cur.fetchone()[0]

def upsert_legislator(conn, data: Dict[str, Any]):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO legislators (name, bioguide, current_party, state)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (bioguide) DO UPDATE
            SET name = EXCLUDED.name, current_party = EXCLUDED.current_party, state = EXCLUDED.state
            RETURNING id
        """, (data.get("name"), data.get("bioguide"), data.get("current_party"), data.get("state")))
        conn.commit()
        return cur.fetchone()[0]

# ----------------------- Post-processing Pipeline -------------------------- #
def post_process_and_ingest(outdir: str, db_connstr: Optional[str], collections: Optional[List[str]] = None):
    """
    Walk outdir for extracted/unpacked files, apply simple parsers and insert into Postgres.
    """
    logger.info("Starting post-processing under %s", outdir)
    if not db_connstr:
        logger.warning("No DB connection string provided; skipping ingestion.")
        return
    conn = db_connect(db_connstr)
    ensure_schema(conn)
    # walk files
    for root, dirs, files in os.walk(outdir):
        for f in files:
            path = os.path.join(root, f)
            lower = f.lower()
            # try JSON legislators
            if (not collections or "legislators" in collections) and lower.endswith(".json") and "legislators" in f.lower():
                leglist = parse_legislators_json(path)
                for l in leglist:
                    upsert_legislator(conn, l)
            # bills XML heuristics
            elif (not collections or any(c in ["bills", "billstatus"] for c in (collections or []))) and lower.endswith(".xml") and ("bill" in lower or "billstatus" in lower):
                rec = parse_bill_xml_simple(path)
                if rec:
                    upsert_bill(conn, rec)
            # votes XML heuristics
            elif (not collections or "rollcall" in (collections or [])) and lower.endswith(".xml") and ("vote" in lower or "rollcall" in lower or "rollcallvote" in lower):
                rec = parse_vote_xml_simple(path)
                if rec:
                    upsert_vote(conn, rec)
    conn.close()
    logger.info("Post-processing complete.")

# ----------------------------- Retry Logic --------------------------------- #
def load_retry_report(path: str) -> Dict[str, Any]:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"failures": []}

def save_retry_report(path: str, report: Dict[str, Any]):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

def schedule_retries(report_path: str, outdir: str, concurrency: int, retries: int, interval_minutes: int, max_attempts: int):
    """
    Periodically try to redownload failed URLs recorded in retry_report.json.
    This is a blocking scheduler; call it in its own thread/process if you want to run in background.
    """
    logger.info("Starting retry scheduler: interval %d minutes, max_attempts %d", interval_minutes, max_attempts)
    while True:
        report = load_retry_report(report_path)
        failures = report.get("failures", [])
        to_retry = [f for f in failures if f.get("attempts", 0) < max_attempts]
        if not to_retry:
            logger.info("No failures to retry; sleeping %d minutes", interval_minutes)
            time.sleep(interval_minutes * 60)
            continue
        urls = [f["url"] for f in to_retry]
        logger.info("Retrying %d failed URLs", len(urls))
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(download_all_async(urls, outdir, concurrency=concurrency, retries=retries))
        loop.close()
        # update report
        new_failures = []
        for r in results:
            if not r.get("ok"):
                # find original record
                original = next((x for x in failures if x["url"] == r["url"]), None)
                attempts = original.get("attempts", 0) + 1 if original else 1
                new_failures.append({"url": r["url"], "last_error": r.get("error"), "attempts": attempts, "last_attempted": datetime.utcnow().isoformat()})
        # append older failures exceeding max attempts? keep history
        report["failures"] = new_failures
        save_retry_report(report_path, report)
        logger.info("Retry round complete. Sleeping %d minutes", interval_minutes)
        time.sleep(interval_minutes * 60)

# ------------------------------- CLI -------------------------------------- #
def parse_args():
    parser = argparse.ArgumentParser(description="End-to-end bulk legislative pipeline.")
    now = datetime.utcnow()
    current_cong = now_congress()
    parser.add_argument("--start-congress", type=int, default=DEFAULT_START_CONGRESS)
    parser.add_argument("--end-congress", type=int, default=max(current_cong + 1, 119))
    parser.add_argument("--no-discovery", dest="do_discovery", action="store_false", help="Skip index discovery")
    parser.add_argument("--download", dest="do_download", action="store_true", help="Download discovered files")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_FILE, help="Output JSON for discovery")
    parser.add_argument("--outdir", type=str, default=DEFAULT_OUTDIR, help="Directory for downloaded/extracted files")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    parser.add_argument("--limit", type=int, default=0, help="Limit number of aggregate URLs processed (0=no limit)")
    parser.add_argument("--collections", type=str, default="", help="Comma-separated filters: bills,rollcall,legislators,openstates,plaw,crec")
    parser.add_argument("--validate", dest="do_validate", action="store_true", help="Validate URLs with HEAD before downloading")
    parser.add_argument("--extract", dest="do_extract", action="store_true", help="Auto-extract archives after download")
    parser.add_argument("--keep-archives", dest="keep_archives", action="store_true", help="Keep archive files after extraction")
    parser.add_argument("--db", type=str, default="", help="Postgres connection string (psycopg2 format) for ingestion")
    parser.add_argument("--postprocess", dest="do_postprocess", action="store_true", help="Run post-processing ingestion into DB after download/extraction")
    parser.add_argument("--schedule-interval", type=int, default=0, help="If >0, run discovery+download periodically every N minutes")
    parser.add_argument("--retry-interval", type=int, default=60, help="Minutes between retry rounds for failed downloads")
    parser.add_argument("--retry-max-attempts", type=int, default=5, help="Max attempts per failed URL during retries")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Do discovery only and print example bulk_urls.json (no network download)")
    return parser.parse_args()

# ------------------------------- Main Flow --------------------------------- #
def main():
    args = parse_args()
    collections = [c.strip().lower() for c in args.collections.split(",") if c.strip()] if args.collections else None
    logger.info("Running pipeline: discovery=%s download=%s postprocess=%s schedule=%s", args.do_discovery, args.do_download, args.do_postprocess, args.schedule_interval)
    # Discovery
    data = assemble_bulk_url_dict(args.start_congress, args.end_congress, do_discovery=args.do_discovery, collections=collections)
    save_path = args.output
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("Wrote discovery output to %s", save_path)
    agg = data.get("aggregate_urls", [])
    if args.limit and args.limit > 0:
        agg = agg[:args.limit]
        logger.info("Limiting to first %d aggregate URLs", args.limit)
    # If dry-run, print a small sample and exit
    if args.dry_run:
        sample = agg[:10]
        print("DRY RUN - sample aggregate URLs (first 10):")
        for s in sample:
            print(" -", s)
        print("\nWrote bulk_urls.json to", save_path)
        return
    # Optional validation
    if args.do_validate and agg:
        logger.info("Validating candidate URLs with HEAD (this may be slow)...")
        agg = validate_urls_head(agg)
        logger.info("Validation result: %d reachable URLs", len(agg))
    # Download
    retry_report = load_retry_report(DEFAULT_RETRY_REPORT)
    if args.do_download and agg:
        logger.info("Downloading %d files to %s", len(agg), args.outdir)
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(download_all_async(agg, args.outdir, concurrency=args.concurrency, retries=args.retries))
        ok = sum(1 for r in results if r.get("ok"))
        failed = [r for r in results if not r.get("ok")]
        logger.info("Download finished: %d succeeded, %d failed", ok, len(failed))
        # record failures to retry_report
        new_failures = []
        for f in failed:
            new_failures.append({"url": f["url"], "last_error": f.get("error"), "attempts": 1, "last_attempted": datetime.utcnow().isoformat()})
        # merge failures
        existing = retry_report.get("failures", [])
        # update attempts for existing
        for nf in new_failures:
            e = next((x for x in existing if x["url"] == nf["url"]), None)
            if e:
                e["attempts"] = e.get("attempts", 0) + 1
                e["last_error"] = nf["last_error"]
                e["last_attempted"] = nf["last_attempted"]
            else:
                existing.append(nf)
        retry_report["failures"] = existing
        save_retry_report(DEFAULT_RETRY_REPORT, retry_report)
        # Extraction
        if args.do_extract:
            logger.info("Extracting archives under %s", args.outdir)
            extracted_count = 0
            for r in results:
                if not r.get("ok"): continue
                p = r.get("path")
                if not p: continue
                if re.search(r'\.(zip|tar\.gz|tgz|tar)$', p, re.IGNORECASE):
                    dest_dir = p + "_extracted"
                    res = extract_archive(p, dest_dir)
                    if res.get("ok"):
                        extracted_count += 1
                        if not args.keep_archives:
                            try: os.remove(p)
                            except Exception: pass
            logger.info("Extraction complete: %d archives extracted", extracted_count)
    # Post-processing / DB ingestion
    if args.do_postprocess and args.db:
        post_process_and_ingest(args.outdir, args.db, collections)
    # Scheduling wrapper
    if args.schedule_interval and args.schedule_interval > 0:
        interval = args.schedule_interval
        logger.info("Entering schedule loop every %d minutes (CTRL-C to stop)", interval)
        try:
            while True:
                # re-run discovery and optionally download+postprocess
                data = assemble_bulk_url_dict(args.start_congress, args.end_congress, do_discovery=args.do_discovery, collections=collections)
                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                agg = data.get("aggregate_urls", [])
                if args.limit and args.limit > 0:
                    agg = agg[:args.limit]
                if args.do_download and agg:
                    loop = asyncio.get_event_loop()
                    results = loop.run_until_complete(download_all_async(agg, args.outdir, concurrency=args.concurrency, retries=args.retries))
                    # update retry_report as above
                    failed = [r for r in results if not r.get("ok")]
                    existing = retry_report.get("failures", [])
                    for f in failed:
                        e = next((x for x in existing if x["url"] == f["url"]), None)
                        rec = {"url": f["url"], "last_error": f.get("error"), "attempts": (e.get("attempts",0)+1) if e else 1, "last_attempted": datetime.utcnow().isoformat()}
                        if e:
                            e.update(rec)
                        else:
                            existing.append(rec)
                    retry_report["failures"] = existing
                    save_retry_report(DEFAULT_RETRY_REPORT, retry_report)
                    if args.do_extract:
                        for r in results:
                            if not r.get("ok"): continue
                            p = r.get("path")
                            if not p: continue
                            if re.search(r'\.(zip|tar\.gz|tgz|tar)$', p, re.IGNORECASE):
                                dest_dir = p + "_extracted"
                                extract_archive(p, dest_dir)
                                if not args.keep_archives:
                                    try: os.remove(p)
                                    except: pass
                    if args.do_postprocess and args.db:
                        post_process_and_ingest(args.outdir, args.db, collections)
                logger.info("Sleeping %d minutes until next scheduled run...", interval)
                time.sleep(interval * 60)
        except KeyboardInterrupt:
            logger.info("Schedule loop interrupted by user; exiting.")
    logger.info("Pipeline run complete. Retry report path: %s", DEFAULT_RETRY_REPORT)

if __name__ == "__main__":
    main()