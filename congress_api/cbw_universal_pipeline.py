###############################################################################
# Name:        cbw_universal_pipeline.py
# Date:        2025-10-02
# Script Name: cbw_universal_pipeline.py
# Version:     1.0
# Log Summary: Universal OOP pipeline to discover, download, extract, parse,
#              normalize and ingest legislative bulk data (OpenStates, OpenLegislation,
#              govinfo/congress.gov, GovTrack) into a single PostgreSQL schema.
# Description:
#   - Single-file executable that implements modular OOP components:
#       * Config: CLI/configuration handling
#       * Logging utilities and decorators (labeled entry/exit/exception)
#       * DiscoveryManager: expand templates and crawl indices
#       * Validator: HEAD/GET checks for reachability
#       * DownloadManager: async downloader with resume/retry
#       * Extractor: archives extraction
#       * ParserNormalizer: conservative parsers for OpenStates/OpenLegislation/govinfo
#       * Mapper: map source-specific objects to universal normalized shape
#       * DBManager: migrations and upsert ingestion into PostgreSQL
#       * RetryManager: store and retry failed downloads
#       * HTTPControlServer: control endpoints and optional metrics
#       * Pipeline: orchestration (sync + async entrypoints)
#       * Simple interactive console for local control
#   - Goal: single script run for full pipeline; detailed logging and diagnostics
# Change Summary:
#   - 1.0: Consolidated and upgraded earlier scripts to a single OOP program.
# Inputs:
#   - CLI flags (see --help), environment variables DATABASE_URL and CONGRESS_LOG_DIR,
#     and local data files (OpenStates JSON, OpenLegislation files, govinfo XMLs).
# Outputs:
#   - bulk_urls.json, retry_report.json, rotating log files, DB tables in Postgres,
#     downloaded archives and extracted directories.
###############################################################################

import os
import sys
import re
import json
import time
import gzip
import zipfile
import shutil
import tarfile
import asyncio
import logging
import argparse
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin

# Optional third-party modules - script will provide helpful messages if missing.
try:
    import requests
except Exception:
    requests = None

try:
    import aiohttp
except Exception:
    aiohttp = None

try:
    from lxml import etree
except Exception:
    etree = None

try:
    import psycopg2
    import psycopg2.extras
except Exception:
    psycopg2 = None

try:
    from prometheus_client import Counter, Gauge, start_http_server, generate_latest
except Exception:
    Counter = Gauge = start_http_server = generate_latest = None

# Optional nice-to-have
try:
    from tqdm import tqdm
    TQDM = True
except Exception:
    TQDM = False

# -----------------------------------------------------------------------------
# Default constants and embedded universal DB migrations (single-list)
# -----------------------------------------------------------------------------
DEFAULT_LOG_DIR = os.getenv("CONGRESS_LOG_DIR", "./logs")
os.makedirs(DEFAULT_LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(DEFAULT_LOG_DIR, f"cbw_universal_{datetime.utcnow().strftime('%Y%m%d')}.log")

DEFAULT_OUTDIR = "./bulk_data"
DEFAULT_BULK_JSON = "bulk_urls.json"
DEFAULT_RETRY_JSON = "retry_report.json"

MIGRATIONS = [
    ("001_universal_schema", """
BEGIN;
CREATE TABLE IF NOT EXISTS jurisdictions (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  jurisdiction_type TEXT,
  state_code TEXT,
  UNIQUE(name, state_code)
);

CREATE TABLE IF NOT EXISTS sessions (
  id SERIAL PRIMARY KEY,
  jurisdiction_id INTEGER REFERENCES jurisdictions(id) ON DELETE CASCADE,
  identifier TEXT,
  start_date TIMESTAMP,
  end_date TIMESTAMP,
  UNIQUE(jurisdiction_id, identifier)
);

CREATE TABLE IF NOT EXISTS persons (
  id SERIAL PRIMARY KEY,
  source TEXT,
  source_id TEXT,
  name TEXT,
  given_name TEXT,
  family_name TEXT,
  sort_name TEXT,
  birth_date DATE,
  death_date DATE,
  inserted_at TIMESTAMP DEFAULT now(),
  UNIQUE(source, source_id)
);

CREATE TABLE IF NOT EXISTS members (
  id SERIAL PRIMARY KEY,
  person_id INTEGER REFERENCES persons(id) ON DELETE CASCADE,
  jurisdiction_id INTEGER REFERENCES jurisdictions(id) ON DELETE CASCADE,
  current_party TEXT,
  state TEXT,
  district TEXT,
  chamber TEXT,
  role TEXT,
  term_start TIMESTAMP,
  term_end TIMESTAMP,
  source TEXT,
  source_id TEXT,
  inserted_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bills (
  id SERIAL PRIMARY KEY,
  source TEXT,
  source_id TEXT,
  jurisdiction_id INTEGER REFERENCES jurisdictions(id) ON DELETE CASCADE,
  session_id INTEGER REFERENCES sessions(id),
  bill_number TEXT,
  chamber TEXT,
  title TEXT,
  summary TEXT,
  status TEXT,
  introduced_date TIMESTAMP,
  updated_at TIMESTAMP,
  inserted_at TIMESTAMP DEFAULT now(),
  UNIQUE(source, source_id)
);

CREATE TABLE IF NOT EXISTS sponsors (
  id SERIAL PRIMARY KEY,
  bill_id INTEGER REFERENCES bills(id) ON DELETE CASCADE,
  person_id INTEGER REFERENCES persons(id),
  name TEXT,
  role TEXT,
  sponsor_order INTEGER
);

CREATE TABLE IF NOT EXISTS actions (
  id SERIAL PRIMARY KEY,
  bill_id INTEGER REFERENCES bills(id) ON DELETE CASCADE,
  action_date TIMESTAMP,
  description TEXT,
  type TEXT
);

CREATE TABLE IF NOT EXISTS bill_texts (
  id SERIAL PRIMARY KEY,
  bill_id INTEGER REFERENCES bills(id) ON DELETE CASCADE,
  text_type TEXT,
  text_url TEXT,
  content TEXT
);

CREATE TABLE IF NOT EXISTS votes (
  id SERIAL PRIMARY KEY,
  source TEXT,
  source_id TEXT,
  bill_id INTEGER REFERENCES bills(id),
  jurisdiction_id INTEGER REFERENCES jurisdictions(id),
  session_id INTEGER REFERENCES sessions(id),
  chamber TEXT,
  vote_date TIMESTAMP,
  result TEXT,
  yeas INTEGER,
  nays INTEGER,
  others INTEGER
);

CREATE TABLE IF NOT EXISTS vote_records (
  id SERIAL PRIMARY KEY,
  vote_id INTEGER REFERENCES votes(id) ON DELETE CASCADE,
  person_id INTEGER REFERENCES persons(id),
  member_name TEXT,
  vote_choice TEXT
);
COMMIT;
""")
]

# -----------------------------------------------------------------------------
# Logging and diagnostic decorators
# -----------------------------------------------------------------------------
def configure_logger(level: int = logging.INFO) -> logging.Logger:
    """
    Configure a rotating file logger and console logger. Messages are labeled via LoggerAdapter.
    """
    logger = logging.getLogger("cbw_universal")
    logger.setLevel(level)
    if not getattr(logger, "_configured", False):
        fmt = "%(asctime)s %(levelname)s %(label)s %(message)s"
        formatter = logging.Formatter(fmt)
        fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=20 * 1024 * 1024, backupCount=10)
        fh.setFormatter(formatter)
        fh.setLevel(level)
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        ch.setLevel(level)
        logger.addHandler(fh)
        logger.addHandler(ch)
        logger._configured = True
    return logger

def adapter(label: str):
    """
    Return a LoggerAdapter that injects label metadata for easier tracing.
    """
    return logging.LoggerAdapter(configure_logger(), {"label": f"[{label}]"})

def labeled(label: str):
    """
    Decorator for sync functions: logs entry, args summary, exit duration, and exceptions.
    """
    def deco(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            log = adapter(label)
            log.info("ENTER %s args=%d kwargs=%s", fn.__name__, len(args), list(kwargs.keys()))
            start = datetime.utcnow()
            try:
                result = fn(*args, **kwargs)
                dur = (datetime.utcnow() - start).total_seconds()
                log.info("EXIT %s duration=%.3fs", fn.__name__, dur)
                return result
            except Exception as e:
                log.exception("EXCEPTION in %s: %s\n%s", fn.__name__, e, traceback.format_exc())
                raise
        return wrapper
    return deco

def trace_async(label: str):
    """
    Decorator for async functions: logs entry/exit and exceptions with timing.
    """
    def deco(fn: Callable):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            log = adapter(label)
            log.info("ENTER async %s", fn.__name__)
            start = datetime.utcnow()
            try:
                res = await fn(*args, **kwargs)
                dur = (datetime.utcnow() - start).total_seconds()
                log.info("EXIT async %s duration=%.3fs", fn.__name__, dur)
                return res
            except Exception as e:
                log.exception("EXCEPTION async %s: %s\n%s", fn.__name__, e, traceback.format_exc())
                raise
        return wrapper
    return deco

# -----------------------------------------------------------------------------
# Utility helpers (atomic JSON, ensure dirs)
# -----------------------------------------------------------------------------
@labeled("utils_save_json")
def save_json_atomic(path: str, data: Any):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def load_json_safe(path: str) -> Optional[Any]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        bkp = f"{path}.corrupt.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        shutil.move(path, bkp)
        adapter("utils").warning("Corrupt JSON moved %s -> %s", path, bkp)
        return None

@labeled("utils_ensure_dirs")
def ensure_dirs(*paths: str):
    for p in paths:
        os.makedirs(p, exist_ok=True)

# -----------------------------------------------------------------------------
# Configuration object that collects CLI inputs and defaults
# -----------------------------------------------------------------------------
class Config:
    def __init__(self,
                 start_congress: int = 93,
                 end_congress: Optional[int] = None,
                 outdir: str = DEFAULT_OUTDIR,
                 bulk_json: str = DEFAULT_BULK_JSON,
                 retry_json: str = DEFAULT_RETRY_JSON,
                 concurrency: int = DEFAULT_CONCURRENCY,
                 retries: int = DEFAULT_RETRIES,
                 collections: Optional[List[str]] = None,
                 do_discovery: bool = True,
                 db_url: str = "",
                 metrics_port: int = 8000,
                 http_port: int = 8080):
        now = datetime.utcnow()
        current_cong = 1 + (now.year - 1789) // 2
        self.start_congress = start_congress
        self.end_congress = end_congress if end_congress is not None else max(current_cong + 1, 119)
        self.outdir = outdir
        self.bulk_json = bulk_json
        self.retry_json = retry_json
        self.concurrency = concurrency
        self.retries = retries
        self.collections = [c.lower() for c in collections] if collections else None
        self.do_discovery = do_discovery
        self.db_url = db_url
        self.metrics_port = metrics_port
        self.http_port = http_port

# -----------------------------------------------------------------------------
# DiscoveryManager: builds candidate URLs for govinfo, GovTrack, OpenStates
# -----------------------------------------------------------------------------
class DiscoveryManager:
    GOVINFO_INDEX = "https://www.govinfo.gov/bulkdata"
    GOVINFO_TEMPLATES = {
        "billstatus": "https://www.govinfo.gov/bulkdata/BILLSTATUS/{congress}/{chamber}/BILLSTATUS-{congress}{chamber}.zip",
        "rollcall":  "https://www.govinfo.gov/bulkdata/ROLLCALLVOTE/{congress}/{chamber}/ROLLCALLVOTE-{congress}-{chamber}.zip",
        "bills":     "https://www.govinfo.gov/bulkdata/BILLS/{congress}/{chamber}/BILLS-{congress}{chamber}.zip",
        "plaw":      "https://www.govinfo.gov/bulkdata/PLAW/{congress}/PLAW-{congress}.zip",
        "crec":      "https://www.govinfo.gov/bulkdata/CREC/{congress}/CREC-{congress}.zip",
    }
    GOVINFO_CHAMBERS = ["hr", "house", "h", "senate", "s"]
    OPENSTATES_DOWNLOADS = "https://openstates.org/downloads/"
    OPENSTATES_MIRROR = "https://open.pluralpolicy.com/data/"
    THEUNITEDSTATES_LEGISLATORS = [
        "https://theunitedstates.io/congress-legislators/legislators-current.json",
        "https://theunitedstates.io/congress-legislators/legislators-historical.json",
    ]

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.log = adapter("discovery")

    @labeled("discovery_expand_templates")
    def expand_templates(self) -> List[str]:
        """
        Expand govinfo patterns across the configured congress range and chambers.
        Returns deduplicated list of candidate URLs.
        """
        urls: List[str] = []
        for c in range(self.cfg.start_congress, self.cfg.end_congress + 1):
            for key, tpl in self.GOVINFO_TEMPLATES.items():
                if self.cfg.collections and key not in self.cfg.collections:
                    continue
                if "{chamber}" in tpl:
                    for ch in self.GOVINFO_CHAMBERS:
                        urls.append(tpl.format(congress=c, chamber=ch))
                else:
                    urls.append(tpl.format(congress=c))
        # dedupe preserving order
        seen = set(); out = []
        for u in urls:
            if u not in seen:
                out.append(u); seen.add(u)
        self.log.info("Expanded %d govinfo template URLs", len(out))
        return out

    @labeled("discovery_govinfo_index")
    def discover_govinfo_index(self) -> List[str]:
        """
        Crawl the govinfo bulkdata index page to find real archive links.
        """
        if requests is None:
            self.log.warning("requests missing: cannot crawl govinfo index")
            return []
        try:
            r = requests.get(self.GOVINFO_INDEX, timeout=20)
            if r.status_code != 200:
                self.log.warning("govinfo index returned %s", r.status_code)
                return []
            html = r.text
            links: List[str] = []
            for m in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
                href = m.group(1)
                if href.startswith("/"):
                    full = "https://www.govinfo.gov" + href
                elif href.startswith("http"):
                    full = href
                else:
                    continue
                if re.search(r'\.(zip|tar\.gz|tgz|json|xml|csv)$', full, re.IGNORECASE):
                    links.append(full)
            self.log.info("Discovered %d govinfo index links", len(links))
            return list(dict.fromkeys(links))
        except Exception as e:
            self.log.exception("Error crawling govinfo index: %s", e)
            return []

    @labeled("discovery_govtrack")
    def discover_govtrack(self) -> List[str]:
        """
        Crawl known govtrack per-congress directories to find dataset files.
        """
        urls = ["https://www.govtrack.us/data/us/bills/bills.csv"]
        if requests is None:
            self.log.warning("requests missing; returning default govtrack urls")
            return urls
        for c in range(self.cfg.start_congress, self.cfg.end_congress + 1):
            dir_url = f"https://www.govtrack.us/data/us/{c}/"
            try:
                r = requests.get(dir_url, timeout=10)
                if r.status_code != 200:
                    continue
                for m in re.finditer(r'href=["\']([^"\']+)["\']', r.text, re.IGNORECASE):
                    href = m.group(1)
                    candidate = href if href.startswith("http") else urljoin(dir_url, href)
                    if re.search(r'\.(zip|tar\.gz|tgz|json|xml|csv)$', candidate, re.IGNORECASE):
                        urls.append(candidate)
            except Exception:
                self.log.debug("govtrack crawl failed for %s", dir_url)
        self.log.info("Discovered %d govtrack urls", len(urls))
        return list(dict.fromkeys(urls))

    @labeled("discovery_openstates")
    def discover_openstates(self) -> List[str]:
        """
        Discover OpenStates bulk downloads via official downloads page and PluralPolicy mirror.
        Adds guessed per-state filenames on the mirror as candidates.
        """
        found: List[str] = []
        if requests is None:
            self.log.warning("requests missing; cannot crawl openstates pages")
            return found
        try:
            r = requests.get(self.OPENSTATES_DOWNLOADS, timeout=15)
            if r.status_code == 200:
                for m in re.finditer(r'href=["\']([^"\']+)["\']', r.text, re.IGNORECASE):
                    href = m.group(1)
                    candidate = href if href.startswith("http") else "https://openstates.org" + href
                    if re.search(r'\.(zip|json|csv|tgz|tar\.gz)$', candidate, re.IGNORECASE):
                        found.append(candidate)
        except Exception:
            self.log.debug("openstates downloads fetch failed")
        try:
            r2 = requests.get(self.OPENSTATES_MIRROR, timeout=10)
            if r2.status_code == 200:
                for m in re.finditer(r'href=["\']([^"\']+)["\']', r2.text, re.IGNORECASE):
                    href = m.group(1)
                    candidate = href if href.startswith("http") else self.OPENSTATES_MIRROR.rstrip("/") + "/" + href
                    if re.search(r'\.(zip|json|csv|tgz|tar\.gz)$', candidate, re.IGNORECASE):
                        found.append(candidate)
        except Exception:
            self.log.debug("openstates mirror fetch failed")
        # heuristic per-state guesses
        mirror_base = self.OPENSTATES_MIRROR.rstrip("/") + "/"
        states = ["al","ak","az","ar","ca","co","ct","de","fl","ga","hi","id","il","in","ia","ks","ky","la","me","md","ma","mi","mn","ms","mo","mt","ne","nv","nh","nj","nm","ny","nc","nd","oh","ok","or","pa","ri","sc","sd","tn","tx","ut","vt","va","wa","wv","wi","wy","dc","pr"]
        for st in states:
            for p in (f"openstates-{st}.zip", f"{st}.zip", f"openstates-{st}.json.zip"):
                found.append(mirror_base + p)
        self.log.info("OpenStates candidate count: %d", len(found))
        return list(dict.fromkeys(found))

    @labeled("discovery_build")
    def build(self) -> Dict[str, Any]:
        """
        Build a dictionary of sources and an aggregate candidate list to be downloaded.
        """
        out: Dict[str, Any] = {}
        out["govinfo_templates"] = self.expand_templates()
        if self.cfg.do_discovery:
            out["govinfo_index"] = self.discover_govinfo_index()
            out["govtrack"] = self.discover_govtrack()
            out["openstates"] = self.discover_openstates()
        else:
            out["govinfo_index"] = []
            out["govtrack"] = []
            out["openstates"] = []
        out["congress_legislators"] = self.THEUNITEDSTATES_LEGISLATORS
        # flatten into aggregate
        agg: List[str] = []
        for v in out.values():
            if isinstance(v, list):
                agg.extend(v)
            elif isinstance(v, dict):
                for iv in v.values():
                    if isinstance(iv, list):
                        agg.extend(iv)
        out["aggregate_urls"] = list(dict.fromkeys([u for u in agg if isinstance(u, str)]))
        self.log.info("Discovery built: %d aggregate URLs", len(out["aggregate_urls"]))
        return out

# -----------------------------------------------------------------------------
# Validator: simple HEAD/GET checks to avoid unnecessary downloads
# -----------------------------------------------------------------------------
class Validator:
    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.log = adapter("validator")

    @labeled("validator_head_ok")
    def head_ok(self, url: str) -> bool:
        if requests is None:
            self.log.warning("requests not installed; cannot validate %s", url)
            return False
        try:
            r = requests.head(url, timeout=self.timeout, allow_redirects=True)
            if r.status_code < 400:
                return True
            # fallback to GET
            r2 = requests.get(url, timeout=self.timeout, stream=True)
            ok = r2.status_code < 400
            r2.close()
            return ok
        except Exception as e:
            self.log.debug("HEAD/GET failed %s: %s", url, e)
            return False

    @labeled("validator_filter_list")
    def filter_list(self, urls: List[str]) -> List[str]:
        return [u for u in urls if self.head_ok(u)]

# -----------------------------------------------------------------------------
# DownloadManager: async downloader with resume & retry (aiohttp)
# -----------------------------------------------------------------------------
class DownloadManager:
    def __init__(self, outdir: str = DEFAULT_OUTDIR, concurrency: int = DEFAULT_CONCURRENCY, retries: int = DEFAULT_RETRIES):
        ensure_dirs(outdir, DEFAULT_LOG_DIR)
        self.outdir = outdir
        self.concurrency = concurrency
        self.retries = retries
        self.log = adapter("downloader")

    async def _head_info(self, session: "aiohttp.ClientSession", url: str) -> Dict[str, Any]:
        try:
            async with session.head(url, timeout=aiohttp.ClientTimeout(total=30), allow_redirects=True) as resp:
                cl = resp.headers.get("Content-Length")
                ar = resp.headers.get("Accept-Ranges", "")
                return {"status": resp.status, "size": int(cl) if cl and cl.isdigit() else None, "resumable": "bytes" in ar.lower()}
        except Exception:
            return {"status": None, "size": None, "resumable": False}

    async def _download_single(self, session: "aiohttp.ClientSession", url: str, dest: str) -> Dict[str, Any]:
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
                    if resp.status >= 400:
                        raise Exception(f"HTTP {resp.status}")
                    cl = resp.headers.get("Content-Length")
                    total = int(cl) + (existing if mode == "ab" else 0) if cl and cl.isdigit() else None
                    written = existing
                    chunk = 1 << 16
                    if TQDM:
                        desc = os.path.basename(dest)
                        with open(dest, mode) as fh, tqdm(total=total, initial=existing, unit="B", unit_scale=True, unit_divisor=1024, desc=desc[:40], leave=False) as pbar:
                            async for data in resp.content.iter_chunked(chunk):
                                if not data:
                                    break
                                fh.write(data)
                                written += len(data)
                                pbar.update(len(data))
                    else:
                        with open(dest, mode) as fh:
                            async for data in resp.content.iter_chunked(chunk):
                                if not data:
                                    break
                                fh.write(data)
                                written += len(data)
                    result["ok"] = True
                    result["bytes"] = written
                    self.log.info("Downloaded %s -> %s (%d bytes)", url, dest, written)
                    return result
            except Exception as e:
                result["error"] = str(e)
                self.log.warning("Attempt %d/%d failed for %s: %s", attempts, self.retries, url, e)
                await asyncio.sleep(min(30, 2 ** attempts))
        return result

    @labeled("downloader_download_all")
    def download_all(self, urls: List[str]) -> List[Dict[str, Any]]:
        if aiohttp is None:
            raise RuntimeError("aiohttp is required for downloads (pip install aiohttp)")
        async def runner():
            sem = asyncio.Semaphore(self.concurrency)
            connector = aiohttp.TCPConnector(limit_per_host=self.concurrency, limit=0)
            async with aiohttp.ClientSession(connector=connector) as session:
                tasks = []
                for i, u in enumerate(urls):
                    filename = u.split("?")[0].rstrip("/").split("/")[-1] or f"file_{i}"
                    domain = urlparse(u).netloc.replace(":", "_")
                    dest_dir = os.path.join(self.outdir, domain)
                    ensure_dirs(dest_dir)
                    dest = os.path.join(dest_dir, filename)
                    async def sem_task(u=u, dest=dest):
                        async with sem:
                            return await self._download_single(session, u, dest)
                    tasks.append(asyncio.create_task(sem_task()))
                results = []
                for fut in asyncio.as_completed(tasks):
                    r = await fut
                    results.append(r)
                return results
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(runner())

# -----------------------------------------------------------------------------
# Extractor: extract zip/tar archives safely
# -----------------------------------------------------------------------------
class Extractor:
    def __init__(self):
        self.log = adapter("extractor")

    @labeled("extractor_extract")
    def extract(self, archive_path: str, remove_archive: bool = False) -> Dict[str, Any]:
        dest = archive_path + "_extracted"
        ensure_dirs(dest)
        try:
            if zipfile.is_zipfile(archive_path):
                with zipfile.ZipFile(archive_path, "r") as z:
                    z.extractall(dest)
            else:
                with tarfile.open(archive_path, "r:*") as t:
                    t.extractall(dest)
            if remove_archive:
                try:
                    os.remove(archive_path)
                except Exception:
                    pass
            self.log.info("Extracted %s -> %s", archive_path, dest)
            return {"ok": True, "dest": dest}
        except Exception as e:
            self.log.exception("Extraction failed for %s: %s", archive_path, e)
            return {"ok": False, "error": str(e)}

# -----------------------------------------------------------------------------
# Parsers & Mappers: conservative parsers for OpenStates, OpenLegislation, govinfo
# -----------------------------------------------------------------------------
class ParserNormalizer:
    def __init__(self):
        self.log = adapter("parser")
        if etree is None:
            self.log.warning("lxml not installed; XML parsing will be limited.")

    @labeled("parser_openstates_map")
    def map_openstates_bill(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map an OpenStates bill JSON record into the universal bill shape.
        This function is conservative; extend for more fields as needed.
        """
        source_id = rec.get("id") or rec.get("openstates_id") or rec.get("identifier")
        session = rec.get("legislative_session") or rec.get("session")
        jurisdiction = rec.get("jurisdiction") or (rec.get("from_organization", {}) .get("name") if rec.get("from_organization") else None)
        bill_number = None
        for ident in rec.get("identifiers", []) if isinstance(rec.get("identifiers", []), list) else []:
            if isinstance(ident, dict) and ident.get("identifier"):
                bill_number = ident.get("identifier"); break
            elif isinstance(ident, str):
                bill_number = ident; break
        title = rec.get("title") or rec.get("short_title")
        summary = rec.get("abstract") or rec.get("summary")
        status = rec.get("latest_action")
        introduced_date = rec.get("created_at") or rec.get("created")
        return {
            "source": "openstates",
            "source_id": source_id,
            "session": session,
            "jurisdiction": jurisdiction,
            "bill_number": bill_number,
            "chamber": rec.get("from_organization", {}).get("classification") if rec.get("from_organization") else rec.get("chamber"),
            "title": title,
            "summary": summary,
            "status": status,
            "introduced_date": introduced_date,
            "raw": rec
        }

    @labeled("parser_openleg_map")
    def map_openleg_bill(self, rec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map an OpenLegislation-style record into universal shape (best effort).
        """
        source_id = rec.get("id") or rec.get("bill_id") or rec.get("number") or rec.get("bill_number")
        return {
            "source": "openlegislation",
            "source_id": source_id,
            "session": rec.get("session"),
            "jurisdiction": rec.get("jurisdiction"),
            "bill_number": rec.get("bill_number") or rec.get("number"),
            "chamber": rec.get("chamber"),
            "title": rec.get("title"),
            "summary": rec.get("summary") or rec.get("description"),
            "status": rec.get("status"),
            "introduced_date": rec.get("introduced_date"),
            "raw": rec
        }

    @labeled("parser_govinfo_map")
    def map_govinfo_bill_from_xml(self, xml_path: str) -> Dict[str, Any]:
        """
        Conservative mapping from govinfo billstatus XML (tries to use local-name XPaths).
        If lxml is unavailable returns minimal info.
        """
        if etree is None:
            return {"source": "govinfo", "source_id": os.path.basename(xml_path), "title": None, "raw": None}
        try:
            tree = etree.parse(xml_path)
            root = tree.getroot()
            def first_x(xps):
                for xp in xps:
                    try:
                        found = root.xpath(xp, namespaces=root.nsmap)
                    except Exception:
                        found = []
                    if found:
                        v = found[0]
                        if hasattr(v, "text") and v.text:
                            return v.text.strip()
                        else:
                            return str(v).strip()
                return None
            source_id = first_x([".//*[local-name()='billId']", ".//*[local-name()='bill_number']"]) or os.path.basename(xml_path)
            bill_number = first_x([".//*[local-name()='billNumber']"])
            title = first_x([".//*[local-name()='officialTitle']", ".//*[local-name()='title']"])
            sponsor = first_x([".//*[local-name()='sponsor']//*[local-name()='name']", ".//*[local-name()='sponsor']"])
            introduced = first_x([".//*[local-name()='introducedDate']"])
            return {
                "source": "govinfo",
                "source_id": source_id,
                "session": None,
                "jurisdiction": "federal",
                "bill_number": bill_number,
                "chamber": None,
                "title": title,
                "summary": None,
                "status": None,
                "introduced_date": introduced,
                "raw": None
            }
        except Exception as e:
            self.log.exception("map_govinfo_bill_from_xml failed for %s: %s", xml_path, e)
            return {"source": "govinfo", "source_id": os.path.basename(xml_path)}

# -----------------------------------------------------------------------------
# DB Manager: migrations + upserts to the universal schema
# -----------------------------------------------------------------------------
class DBManager:
    def __init__(self, conn_str: str):
        if psycopg2 is None:
            raise RuntimeError("psycopg2 not installed; install psycopg2-binary")
        self.conn_str = conn_str
        self.conn = None
        self.log = adapter("db")

    @labeled("db_connect")
    def connect(self):
        self.conn = psycopg2.connect(self.conn_str)
        self.conn.autocommit = False
        self.log.info("Connected to Postgres")

    @labeled("db_run_migrations")
    def run_migrations(self, migrations: List[Tuple[str,str]]):
        if self.conn is None:
            self.connect()
        cur = self.conn.cursor()
        try:
            for name, sql in migrations:
                self.log.info("Applying migration: %s", name)
                cur.execute(sql)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            self.log.exception("Migration failure")
            raise

    @labeled("db_upsert_jurisdiction")
    def upsert_jurisdiction(self, name: str, jurisdiction_type: str, state_code: Optional[str]=None) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO jurisdictions (name, jurisdiction_type, state_code)
            VALUES (%s,%s,%s)
            ON CONFLICT (name,state_code) DO UPDATE SET jurisdiction_type=EXCLUDED.jurisdiction_type
            RETURNING id
        """, (name, jurisdiction_type, state_code))
        row = cur.fetchone()
        self.conn.commit()
        return row[0]

    @labeled("db_upsert_session")
    def upsert_session(self, jurisdiction_id: int, identifier: str, start_date: Optional[str]=None, end_date: Optional[str]=None) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO sessions (jurisdiction_id, identifier, start_date, end_date)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (jurisdiction_id, identifier) DO UPDATE SET start_date=COALESCE(EXCLUDED.start_date, sessions.start_date), end_date=COALESCE(EXCLUDED.end_date, sessions.end_date)
            RETURNING id
        """, (jurisdiction_id, identifier, start_date, end_date))
        row = cur.fetchone()
        self.conn.commit()
        return row[0]

    @labeled("db_upsert_person")
    def upsert_person(self, source: str, source_id: str, name: str, given_name: Optional[str]=None, family_name: Optional[str]=None) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO persons (source, source_id, name, given_name, family_name, sort_name)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (source, source_id) DO UPDATE SET name=EXCLUDED.name
            RETURNING id
        """, (source, source_id, name, given_name, family_name, name))
        row = cur.fetchone()
        self.conn.commit()
        return row[0]

    @labeled("db_insert_member")
    def insert_member(self, person_id: int, jurisdiction_id: int, data: Dict[str,Any]):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO members (person_id, jurisdiction_id, current_party, state, district, chamber, role, term_start, term_end, source, source_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (person_id, jurisdiction_id, data.get("current_party"), data.get("state"), data.get("district"), data.get("chamber"), data.get("role"), data.get("term_start"), data.get("term_end"), data.get("source"), data.get("source_id")))
        self.conn.commit()

    @labeled("db_upsert_bill")
    def upsert_bill(self, source: str, source_id: str, jurisdiction_id: int, session_id: Optional[int], bill_number: Optional[str], chamber: Optional[str], title: Optional[str], summary: Optional[str], status: Optional[str], introduced_date: Optional[str]) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO bills (source, source_id, jurisdiction_id, session_id, bill_number, chamber, title, summary, status, introduced_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (source, source_id) DO UPDATE
            SET title=COALESCE(EXCLUDED.title, bills.title), summary=COALESCE(EXCLUDED.summary, bills.summary), status=COALESCE(EXCLUDED.status, bills.status), updated_at=now()
            RETURNING id
        """, (source, source_id, jurisdiction_id, session_id, bill_number, chamber, title, summary, status, introduced_date))
        row = cur.fetchone()
        self.conn.commit()
        return row[0]

    @labeled("db_insert_sponsor")
    def insert_sponsor(self, bill_id: int, person_id: Optional[int], name: str, role: str, order: int):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO sponsors (bill_id, person_id, name, role, sponsor_order) VALUES (%s,%s,%s,%s,%s)
        """, (bill_id, person_id, name, role, order))
        self.conn.commit()

    @labeled("db_insert_action")
    def insert_action(self, bill_id: int, action_date: Optional[str], description: str, type_: Optional[str]=None):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO actions (bill_id, action_date, description, type) VALUES (%s,%s,%s,%s)
        """, (bill_id, action_date, description, type_))
        self.conn.commit()

    @labeled("db_insert_vote")
    def insert_vote(self, source: str, source_id: str, bill_id: Optional[int], jurisdiction_id: Optional[int], session_id: Optional[int], chamber: Optional[str], vote_date: Optional[str], result: Optional[str], yeas: Optional[int], nays: Optional[int], others: Optional[int]) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO votes (source, source_id, bill_id, jurisdiction_id, session_id, chamber, vote_date, result, yeas, nays, others)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (source, source_id, bill_id, jurisdiction_id, session_id, chamber, vote_date, result, yeas, nays, others))
        row = cur.fetchone()
        self.conn.commit()
        return row[0]

    @labeled("db_insert_vote_record")
    def insert_vote_record(self, vote_id: int, person_id: Optional[int], member_name: str, vote_choice: str):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO vote_records (vote_id, person_id, member_name, vote_choice) VALUES (%s,%s,%s,%s)
        """, (vote_id, person_id, member_name, vote_choice))
        self.conn.commit()

    @labeled("db_close")
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.log.info("DB connection closed")

# -----------------------------------------------------------------------------
# Retry manager: persistent JSON of failures
# -----------------------------------------------------------------------------
class RetryManager:
    def __init__(self, path: str = DEFAULT_RETRY_JSON):
        self.path = path
        self.log = adapter("retry")
        self._load()

    @labeled("retry_load")
    def _load(self):
        data = load_json_safe(self.path)
        self.data = data if data else {"failures": []}

    @labeled("retry_add")
    def add_failure(self, url: str, error: str):
        now = datetime.utcnow().isoformat()
        rec = next((r for r in self.data["failures"] if r["url"] == url), None)
        if rec:
            rec["attempts"] = rec.get("attempts", 0) + 1
            rec["last_error"] = error
            rec["last_attempted"] = now
        else:
            self.data["failures"].append({"url": url, "attempts": 1, "first_failed": now, "last_attempted": now, "last_error": error})
        save_json_atomic(self.path, self.data)
        self.log.info("Recorded failure for %s", url)

    @labeled("retry_list")
    def list_to_retry(self, max_attempts: int = 5) -> List[str]:
        return [r["url"] for r in self.data["failures"] if r.get("attempts", 0) < max_attempts]

    @labeled("retry_remove")
    def remove(self, url: str):
        self.data["failures"] = [r for r in self.data["failures"] if r["url"] != url]
        save_json_atomic(self.path, self.data)
        self.log.info("Removed failure record %s", url)

# -----------------------------------------------------------------------------
# HTTPControlServer: lightweight aiohttp-based control interface
# -----------------------------------------------------------------------------
class HTTPControlServer:
    def __init__(self, pipeline, host: str = "0.0.0.0", port: int = 8080):
        if aiohttp is None:
            raise RuntimeError("aiohttp required for HTTP server")
        self.pipeline = pipeline
        self.host = host
        self.port = port
        self.app = None
        self.runner = None
        self.log = adapter("http")

    def make_app(self):
        from aiohttp import web
        app = web.Application()
        app.router.add_get("/status", self.handle_status)
        app.router.add_post("/start", self.handle_start)
        app.router.add_post("/retry", self.handle_retry)
        app.router.add_get("/health", self.handle_health)
        if generate_latest is not None:
            async def metrics(req):
                data = generate_latest()
                return web.Response(body=data, content_type="text/plain; version=0.0.4")
            app.router.add_get("/metrics", metrics)
        self.app = app
        return app

    async def handle_status(self, request):
        from aiohttp import web
        data = {
            "last_discovery": getattr(self.pipeline, "last_discovery_ts", None),
            "retry_count": len(self.pipeline.retry_mgr.data.get("failures", []))
        }
        return web.json_response(data)

    async def handle_start(self, request):
        # schedule an async run in the background
        asyncio.create_task(self.pipeline.run_once_async(download=True, extract=True, postprocess=False))
        from aiohttp import web
        return web.json_response({"status": "started"})

    async def handle_retry(self, request):
        asyncio.create_task(self.pipeline.retry_failed_async())
        from aiohttp import web
        return web.json_response({"status": "retry_started"})

    async def handle_health(self, request):
        from aiohttp import web
        return web.Response(text="ok")

    async def start(self):
        from aiohttp import web
        app = self.make_app()
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()
        self.log.info("HTTP server started at http://%s:%d", self.host, self.port)

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
            self.log.info("HTTP server stopped")

# -----------------------------------------------------------------------------
# Pipeline: orchestration - discovery -> validate -> download -> extract -> parse -> ingest
# -----------------------------------------------------------------------------
class Pipeline:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        ensure_dirs(cfg.outdir, DEFAULT_LOG_DIR)
        self.discovery = DiscoveryManager(cfg)
        self.validator = Validator()
        self.downloader = DownloadManager(cfg.outdir, cfg.concurrency, cfg.retries)
        self.extractor = Extractor()
        self.parser = ParserNormalizer()
        self.dbmgr = DBManager(cfg.db_url) if cfg.db_url else None
        self.retry_mgr = RetryManager(cfg.retry_json)
        self.last_discovery_ts = None
        self.http_server = None
        # Prometheus metrics
        if Counter is not None:
            self.m_downloads = Counter("cbw_downloads_total", "Successful downloads")
            self.m_download_fails = Counter("cbw_download_failures_total", "Failed downloads")
            self.m_discovered = Gauge("cbw_discovered_urls", "Discovered aggregate URLs")
            self.m_last_run = Gauge("cbw_last_run_ts", "Last discovery epoch")
        else:
            self.m_downloads = self.m_download_fails = self.m_discovered = self.m_last_run = None
        self.log = adapter("pipeline")

    @labeled("pipeline_discover")
    def discover(self) -> Dict[str, Any]:
        data = self.discovery.build()
        save_json_atomic(self.cfg.bulk_json, data)
        self.last_discovery_ts = datetime.utcnow().isoformat()
        if self.m_discovered is not None:
            self.m_discovered.set(len(data.get("aggregate_urls", [])))
            self.m_last_run.set(time.time())
        self.log.info("Discovery written to %s", self.cfg.bulk_json)
        return data

    def validate(self, urls: List[str]) -> List[str]:
        return self.validator.filter_list(urls)

    @labeled("pipeline_download")
    def download(self, urls: List[str]) -> List[Dict[str, Any]]:
        results = self.downloader.download_all(urls)
        for r in results:
            if r.get("ok"):
                if self.m_downloads is not None:
                    self.m_downloads.inc()
            else:
                self.retry_mgr.add_failure(r.get("url", "unknown"), r.get("error", "download failed"))
                if self.m_download_fails is not None:
                    self.m_download_fails.inc()
        return results

    @labeled("pipeline_extract")
    def extract_all(self, results: List[Dict[str, Any]], remove_archive: bool = False) -> List[Dict[str, Any]]:
        extracted = []
        for r in results:
            if not r.get("ok"):
                continue
            p = r.get("path")
            if not p:
                continue
            if re.search(r'\.(zip|tar\.gz|tgz|tar)$', p, re.IGNORECASE):
                res = self.extractor.extract(p, remove_archive)
                extracted.append(res)
        self.log.info("Extraction complete: %d", len(extracted))
        return extracted

    @labeled("pipeline_postprocess")
    def postprocess(self, limit_per_file: int = 0):
        """
        Walk the outdir and parse/ingest known file types.
        - OpenStates (JSON) ingestion
        - OpenLegislation (JSON/XML) ingestion
        - govinfo XML ingestion
        """
        if self.dbmgr is None:
            self.log.warning("No DB configured; skipping postprocess")
            return
        self.dbmgr.connect()
        self.dbmgr.run_migrations(MIGRATIONS)
        counts = {"openstates":0, "openleg":0, "govinfo":0}
        for root, _, files in os.walk(self.cfg.outdir):
            for fname in files:
                lower = fname.lower()
                full = os.path.join(root, fname)
                try:
                    if lower.endswith(".json") and "openstates" in full or "openstates" in fname:
                        self._ingest_openstates_file(full, limit_per_file)
                        counts["openstates"] += 1
                    elif lower.endswith((".json", ".xml")) and "openleg" in fname:
                        self._ingest_openleg_file(full, limit_per_file)
                        counts["openleg"] += 1
                    elif lower.endswith(".xml") and ("govinfo" in full or "billstatus" in fname.lower() or "rollcall" in fname.lower()):
                        self._ingest_govinfo_xml(full, limit_per_file)
                        counts["govinfo"] += 1
                except Exception as e:
                    self.log.exception("Postprocess error for %s: %s", full, e)
        self.dbmgr.close()
        self.log.info("Postprocess complete: %s", counts)

    # The ingestion helpers below call parser/mapping functions and DB upserts.
    @labeled("pipeline_ingest_openstates_file")
    def _ingest_openstates_file(self, path: str, limit: int = 0):
        """
        Read OpenStates JSON (array or newline-delimited) and ingest mapped bills and people.
        Conservative mapping. Extend mapping functions if you provide sample dumps.
        """
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        try:
            data = json.loads(text)
            # OpenStates dump could be list or dict with results
            if isinstance(data, dict) and "results" in data:
                records = data["results"]
            elif isinstance(data, list):
                records = data
            else:
                records = [data]
        except Exception:
            # newline-delimited fallback
            records = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
        parsed = 0
        for rec in records:
            if limit and parsed >= limit:
                break
            mapped = self.parser.map_openstates_bill(rec)
            j_name = mapped.get("jurisdiction") or "unknown"
            j_type = "state" if j_name and len(str(j_name)) == 2 else "state" if j_name else "federal"
            j_code = j_name if j_type == "state" else None
            jid = self.dbmgr.upsert_jurisdiction(j_name, j_type, j_code)
            session_id = None
            if mapped.get("session"):
                session_id = self.dbmgr.upsert_session(jid, mapped.get("session"))
            bill_id = self.dbmgr.upsert_bill(mapped.get("source"), mapped.get("source_id"), jid, session_id, mapped.get("bill_number"), mapped.get("chamber"), mapped.get("title"), mapped.get("summary"), mapped.get("status"), mapped.get("introduced_date"))
            # sponsors mapping: try to find rec.get("sponsors")
            for i, s in enumerate(rec.get("sponsors", []) if isinstance(rec.get("sponsors", []), list) else []):
                name = s.get("name") if isinstance(s, dict) else str(s)
                person_id = None
                if isinstance(s, dict) and s.get("person_id"):
                    person_id = self.dbmgr.upsert_person("openstates", s.get("person_id"), name)
                self.dbmgr.insert_sponsor(bill_id, person_id, name, s.get("classification") or s.get("role") or "sponsor", i+1)
            # actions
            for a in rec.get("actions", []) if isinstance(rec.get("actions", []), list) else []:
                self.dbmgr.insert_action(bill_id, a.get("date"), a.get("description") or a.get("note"), a.get("classification"))
            parsed += 1
        self.log.info("Ingested %d OpenStates records from %s", parsed, path)

    @labeled("pipeline_ingest_openleg")
    def _ingest_openleg_file(self, path: str, limit: int = 0):
        """
        Generic OpenLegislation ingestion: supports JSON or XML (best-effort).
        """
        parsed = 0
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            data = json.loads(text)
            records = data if isinstance(data, list) else (data.get("bills") or data.get("results") or [data])
            for rec in records:
                if limit and parsed >= limit:
                    break
                mapped = self.parser.map_openleg_bill(rec)
                j_name = mapped.get("jurisdiction") or "unknown"
                j_type = "state" if j_name and len(str(j_name)) == 2 else "federal"
                jid = self.dbmgr.upsert_jurisdiction(j_name, j_type, j_name if j_type == "state" else None)
                sid = None
                if mapped.get("session"):
                    sid = self.dbmgr.upsert_session(jid, mapped.get("session"))
                bill_id = self.dbmgr.upsert_bill(mapped.get("source"), mapped.get("source_id"), jid, sid, mapped.get("bill_number"), mapped.get("chamber"), mapped.get("title"), mapped.get("summary"), mapped.get("status"), mapped.get("introduced_date"))
                # sponsors, actions etc - best-effort
                for i, s in enumerate(rec.get("sponsors", []) if isinstance(rec.get("sponsors", []), list) else []):
                    name = s.get("name") if isinstance(s, dict) else str(s)
                    person_id = None
                    if isinstance(s, dict) and s.get("person_id"):
                        person_id = self.dbmgr.upsert_person("openlegislation", s.get("person_id"), name)
                    self.dbmgr.insert_sponsor(bill_id, person_id, name, s.get("role") or "sponsor", i+1)
                parsed += 1
            self.log.info("Ingested %d OpenLeg records from %s", parsed, path)
            return
        except Exception:
            # Try XML fallback (if lxml available)
            if etree is None:
                self.log.exception("Failed to parse OpenLeg JSON and lxml not available for XML: %s", path)
                return
            try:
                tree = etree.parse(path)
                # Basic mapping for each <bill> or similar element
                elements = tree.findall(".//bill") or tree.findall(".//legislativeDocument")
                for el in elements:
                    if limit and parsed >= limit:
                        break
                    rec = {child.tag: child.text for child in el}
                    mapped = self.parser.map_openleg_bill(rec)
                    j_name = mapped.get("jurisdiction") or "unknown"
                    j_type = "state" if j_name and len(str(j_name))==2 else "federal"
                    jid = self.dbmgr.upsert_jurisdiction(j_name, j_type, j_name if j_type=="state" else None)
                    sid = None
                    if mapped.get("session"):
                        sid = self.dbmgr.upsert_session(jid, mapped.get("session"))
                    bill_id = self.dbmgr.upsert_bill(mapped.get("source"), mapped.get("source_id"), jid, sid, mapped.get("bill_number"), mapped.get("chamber"), mapped.get("title"), mapped.get("summary"), mapped.get("status"), mapped.get("introduced_date"))
                    parsed += 1
                self.log.info("Ingested %d OpenLeg XML records from %s", parsed, path)
            except Exception as e:
                self.log.exception("OpenLeg parsing failed for %s: %s", path, e)

    @labeled("pipeline_ingest_govinfo")
    def _ingest_govinfo_xml(self, path: str, limit: int = 0):
        """
        Ingest govinfo XMLs (billstatus, rollcall). Scans XMLs found under path if it's a directory.
        """
        # If path is a directory, walk xml files
        files = []
        if os.path.isdir(path):
            for root, _, files_ in os.walk(path):
                for fn in files_:
                    if fn.lower().endswith(".xml"):
                        files.append(os.path.join(root, fn))
        else:
            files = [path]
        parsed = 0
        for p in files:
            if limit and parsed >= limit:
                break
            mapped = self.parser.map_govinfo_bill_from_xml(p)
            jid = self.dbmgr.upsert_jurisdiction("United States", "federal", None)
            sid = None
            bill_id = self.dbmgr.upsert_bill(mapped.get("source"), mapped.get("source_id"), jid, sid, mapped.get("bill_number"), mapped.get("chamber"), mapped.get("title"), mapped.get("summary"), mapped.get("status"), mapped.get("introduced_date"))
            parsed += 1
        self.log.info("Ingested %d govinfo XML bills from %s", parsed, path)

    # Async helpers invoked by HTTP endpoints
    async def run_once_async(self, download: bool=False, extract: bool=False, postprocess: bool=False, validate: bool=False):
        """
        Asynchronously run discover -> (validate) -> download -> (extract) -> (postprocess).
        Useful for HTTP control API background tasks.
        """
        try:
            data = self.discover()
            urls = data.get("aggregate_urls", [])
            if validate:
                urls = self.validate(urls)
            if download and urls:
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(None, self.download, urls)
                if extract:
                    await loop.run_in_executor(None, self.extract_all, results, False)
                if postprocess:
                    await loop.run_in_executor(None, self.postprocess, 0)
        except Exception:
            self.log.exception("run_once_async failed")

    async def retry_failed_async(self, max_attempts: int = 5):
        try:
            urls = self.retry_mgr.list_to_retry(max_attempts)
            if not urls:
                self.log.info("No failed URLs to retry")
                return
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, self.download, urls)
            for r in results:
                if r.get("ok"):
                    self.retry_mgr.remove(r.get("url"))
        except Exception:
            self.log.exception("retry_failed_async failed")

# -----------------------------------------------------------------------------
# Simple interactive console (non-curses) for quick local control when run locally
# -----------------------------------------------------------------------------
def interactive_console(pipeline: Pipeline):
    """
    Simple command loop: discover, status, start, retry, postprocess, exit.
    Useful for manual testing and debugging.
    """
    print("cbw universal pipeline interactive console")
    print("commands: discover | status | start | retry | postprocess | exit")
    while True:
        try:
            cmd = input("cbw> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if cmd in ("exit", "quit"):
            break
        elif cmd == "discover":
            d = pipeline.discover()
            print("Discovered", len(d.get("aggregate_urls", [])), "URLs")
        elif cmd == "status":
            print("Last discovery:", pipeline.last_discovery_ts)
            failures = pipeline.retry_mgr.data.get("failures", [])
            print("Retry failures:", len(failures))
        elif cmd == "start":
            print("Starting discovery+download+extract (blocking)...")
            asyncio.run(pipeline.run_once_async(download=True, extract=True, postprocess=False))
            print("Done")
        elif cmd == "retry":
            print("Retrying failed URLs...")
            asyncio.run(pipeline.retry_failed_async())
            print("Retry started")
        elif cmd == "postprocess":
            print("Running postprocess (DB ingestion)...")
            pipeline.postprocess()
            print("Postprocess finished")
        else:
            print("Unknown command:", cmd)

# -----------------------------------------------------------------------------
# CLI entrypoint
# -----------------------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="cbw Universal Legislative Ingest Pipeline")
    p.add_argument("--start-congress", type=int, default=93)
    p.add_argument("--end-congress", type=int, default=None)
    p.add_argument("--outdir", type=str, default=DEFAULT_OUTDIR)
    p.add_argument("--bulk-json", type=str, default=DEFAULT_BULK_JSON)
    p.add_argument("--retry-json", type=str, default=DEFAULT_RETRY_JSON)
    p.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    p.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    p.add_argument("--collections", type=str, default="", help="Comma-separated filters: bills,rollcall,plaw,crec")
    p.add_argument("--no-discovery", dest="do_discovery", action="store_false")
    p.add_argument("--validate", dest="do_validate", action="store_true")
    p.add_argument("--download", dest="do_download", action="store_true")
    p.add_argument("--extract", dest="do_extract", action="store_true")
    p.add_argument("--postprocess", dest="do_postprocess", action="store_true")
    p.add_argument("--db", dest="db", type=str, default=os.getenv("DATABASE_URL",""), help="Postgres connection string")
    p.add_argument("--serve", dest="serve", action="store_true", help="Start HTTP control server")
    p.add_argument("--serve-port", dest="serve_port", type=int, default=8080)
    p.add_argument("--metrics-port", dest="metrics_port", type=int, default=8000)
    p.add_argument("--schedule", dest="schedule", type=int, default=0, help="Minutes between scheduled runs")
    p.add_argument("--retry-interval", dest="retry_interval", type=int, default=60)
    p.add_argument("--retry-max-attempts", dest="retry_max_attempts", type=int, default=5)
    p.add_argument("--limit", dest="limit", type=int, default=0)
    p.add_argument("--dry-run", dest="dry_run", action="store_true")
    p.add_argument("--interactive", dest="interactive", action="store_true")
    p.add_argument("--log-level", dest="log_level", default="INFO")
    return p.parse_args()

def main():
    args = parse_args()
    level = getattr(logging, args.log_level.upper(), logging.INFO)
    configure_logger(level=level)
    collections = [c.strip().lower() for c in args.collections.split(",") if c.strip()] if args.collections else None
    cfg = Config(start_congress=args.start_congress, end_congress=args.end_congress, outdir=args.outdir, bulk_json=args.bulk_json, retry_json=args.retry_json, concurrency=args.concurrency, retries=args.retries, collections=collections, do_discovery=args.do_discovery, db_url=args.db, metrics_port=args.metrics_port, http_port=args.serve_port)
    pipeline = Pipeline(cfg)

    # Start Prometheus metrics HTTP server if available
    if generate_latest is not None and start_http_server is not None:
        try:
            start_http_server(args.metrics_port)
            adapter("metrics").info("Prometheus metrics exposed on :%d", args.metrics_port)
        except Exception:
            adapter("metrics").warning("Could not start Prometheus metrics server")

    # Dry-run: discover only
    if args.dry_run:
        data = pipeline.discover()
        sample = data.get("aggregate_urls", [])[:20]
        print("DRY RUN - first 20 aggregate URLs:")
        for s in sample:
            print(" -", s)
        if args.interactive:
            interactive_console(pipeline)
        return

    # Optionally start HTTP control server
    if args.serve:
        pipeline.start_http_server(host="0.0.0.0", port=args.serve_port)

    # Single run flow
    data = pipeline.discover()
    urls = data.get("aggregate_urls", [])
    if args.limit and args.limit > 0:
        urls = urls[:args.limit]
    if args.do_validate:
        urls = pipeline.validate(urls)
    results = []
    if args.do_download and urls:
        results = pipeline.download(urls)
    if args.do_extract and results:
        pipeline.extract_all(results, remove_archive=False)
    if args.do_postprocess and args.db:
        pipeline.postprocess(limit_per_file=args.limit)

    # Schedule loop if requested
    if args.schedule and args.schedule > 0:
        pipeline.schedule_loop(interval_minutes=args.schedule, retry_interval=args.retry_interval, max_attempts=args.retry_max_attempts)

    if args.interactive:
        interactive_console(pipeline)

if __name__ == "__main__":
    main()