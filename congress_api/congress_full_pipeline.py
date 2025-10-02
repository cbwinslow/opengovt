###############################################################################
# Name:        Congress Bulk Legislative Pipeline - Complete Single Script
# Date:        2025-10-02
# Script Name: congress_full_pipeline.py
# Version:     2.0
# Log Summary: Comprehensive single-file OOP pipeline: discovery, validation,
#              concurrent download with resume/retry, extraction, parsing/normalization,
#              PostgreSQL ingestion, retry scheduler, Prometheus metrics, HTTP control API,
#              rotating and structured logging, diagnostic decorators, housekeeping utilities.
# Description:
#    This script implements an end-to-end pipeline to discover and ingest bulk
#    legislative data (bills, rollcalls, legislators, sessions, texts, etc.)
#    from authoritative sources (govinfo, theunitedstates, GovTrack, OpenStates).
#    It is intentionally organized into classes following OOP principles and
#    includes detailed comments, labeled logs, decorators for tracing, and
#    robust error handling to help diagnose runtime issues.
#
# Change Summary:
#   - 2.0: Consolidated multi-module design into a single executable file per
#          user instruction. Added:
#       * Embedded SQL migrations
#       * aiohttp HTTP control server and Prometheus metrics
#       * lxml-based parsing sketches for govinfo billstatus and rollcall
#       * Detailed decorators and rotating logger + JSON-safe atomic writes
#       * Retry manager and scheduler loop
#       * CLI with many options (discovery, download, extract, postprocess, serve)
#
# Inputs:
#   - CLI flags (see --help)
#   - Environment variables (DATABASE_URL, CONGRESS_LOG_DIR)
# Outputs:
#   - bulk_urls.json, retry_report.json
#   - downloaded archives in outdir, extracted files in <archive>_extracted
#   - Postgres tables populated when --db provided
#   - Detailed logs in log directory, Prometheus metrics endpoint (/metrics)
###############################################################################

import os
import re
import sys
import json
import time
import glob
import errno
import signal
import shutil
import tarfile
import zipfile
import asyncio
import logging
import functools
import traceback
import argparse
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urljoin

# Third-party imports may be missing in user's environment; check gracefully.
try:
    import aiohttp
except Exception:
    aiohttp = None

try:
    import requests
except Exception:
    requests = None

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
    from prometheus_client import start_http_server, Counter, Gauge, generate_latest
    from prometheus_client.core import CollectorRegistry
except Exception:
    start_http_server = None
    Counter = None
    Gauge = None
    generate_latest = None
    CollectorRegistry = None

# Optional progress bar
try:
    from tqdm import tqdm
    TQDM_INSTALLED = True
except Exception:
    TQDM_INSTALLED = False

# -----------------------------------------------------------------------------
# Embedded SQL migrations (single-file approach). In real repo these would be
# separate files under migrations/, but embedding keeps single executable as requested.
# -----------------------------------------------------------------------------
MIGRATIONS = [
    (
        "001_init",
        """
BEGIN;
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

CREATE TABLE IF NOT EXISTS sponsors (
  id SERIAL PRIMARY KEY,
  bill_id INTEGER REFERENCES bills(id) ON DELETE CASCADE,
  name TEXT,
  role TEXT
);

CREATE TABLE IF NOT EXISTS bill_actions (
  id SERIAL PRIMARY KEY,
  bill_id INTEGER REFERENCES bills(id) ON DELETE CASCADE,
  action_date TIMESTAMP,
  description TEXT
);

CREATE TABLE IF NOT EXISTS bill_texts (
  id SERIAL PRIMARY KEY,
  bill_id INTEGER REFERENCES bills(id) ON DELETE CASCADE,
  text_type TEXT,
  text_url TEXT,
  inserted_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rollcall_votes (
  id SERIAL PRIMARY KEY,
  vote_id INTEGER REFERENCES votes(id) ON DELETE CASCADE,
  member_bioguide TEXT,
  vote_choice TEXT
);
COMMIT;
"""
    ),
]

# -----------------------------------------------------------------------------
# Basic configuration and constants
# -----------------------------------------------------------------------------
DEFAULT_LOG_DIR = os.getenv("CONGRESS_LOG_DIR", "./logs")
os.makedirs(DEFAULT_LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(DEFAULT_LOG_DIR, f"congress_pipeline_{datetime.utcnow().strftime('%Y%m%d')}.log")

DEFAULT_OUTDIR = "./bulk_data"
DEFAULT_BULK_JSON = "bulk_urls.json"
DEFAULT_RETRY_JSON = "retry_report.json"
DEFAULT_CONCURRENCY = 6
DEFAULT_RETRIES = 5
DEFAULT_START_CONGRESS = 93

# Prometheus metrics placeholders (will be set if prometheus_client is installed)
MET_DOWNLOADS = None
MET_DOWNLOAD_FAILS = None
MET_DISCOVERED_URLS = None
MET_LAST_RUN_TS = None

# -----------------------------------------------------------------------------
# Logging configuration and decorator utilities
# -----------------------------------------------------------------------------
def configure_logger(name: str = "congress", level: int = logging.INFO) -> logging.Logger:
    """
    Configure a root logger with rotating file handler and console handler.
    Returns a Logger instance (not adapter). Uses LOG_FILE at top-level.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    # Avoid adding handlers multiple times in interactive runs
    if not getattr(logger, "_configured", False):
        fmt = "%(asctime)s %(levelname)s %(label)s %(message)s"
        formatter = logging.Formatter(fmt)
        # Rotating file handler
        fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=20 * 1024 * 1024, backupCount=10)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        logger._configured = True
    return logger

# A helper to create LoggerAdapter so we can attach label metadata dynamically.
def adapter_for(logger: logging.Logger, label: str = "[init]") -> logging.LoggerAdapter:
    return logging.LoggerAdapter(logger, {"label": f"[{label}] "})

# Decorator to label functions with entry/exit/exception logs
def labeled(label: str):
    """
    Decorator to add labeled entry/exit and exception logs with timing.
    Use: @labeled("mylabel")
    """
    def deco(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            logger = configure_logger()
            adap = adapter_for(logger, label)
            adap.info(f"ENTER {fn.__name__} args={len(args)} kwargs={list(kwargs.keys())}")
            start = datetime.utcnow()
            try:
                result = fn(*args, **kwargs)
                dur = (datetime.utcnow() - start).total_seconds()
                adap.info(f"EXIT {fn.__name__} duration={dur:.3f}s")
                return result
            except Exception as e:
                adap.exception(f"EXCEPTION in {fn.__name__}: {e}\n{traceback.format_exc()}")
                raise
        return wrapper
    return deco

# Async variant
def trace_async(label: str):
    def deco(fn: Callable):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            logger = configure_logger()
            adap = adapter_for(logger, label)
            adap.info(f"ENTER async {fn.__name__}")
            start = datetime.utcnow()
            try:
                result = await fn(*args, **kwargs)
                dur = (datetime.utcnow() - start).total_seconds()
                adap.info(f"EXIT async {fn.__name__} duration={dur:.3f}s")
                return result
            except Exception as e:
                adap.exception(f"EXCEPTION async {fn.__name__}: {e}\n{traceback.format_exc()}")
                raise
        return wrapper
    return deco

# -----------------------------------------------------------------------------
# Utility functions (file atomic write, housekeeping)
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
        # back up corrupt file and return None
        bkp = f"{path}.corrupt.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        shutil.move(path, bkp)
        configure_logger(); adapter_for(logging.getLogger(), "utils").warning("Corrupt JSON at %s moved to %s", path, bkp)
        return None

@labeled("utils_ensure_dirs")
def ensure_dirs(*dirs: str):
    for d in dirs:
        os.makedirs(d, exist_ok=True)

@labeled("utils_rotate_logs")
def rotate_logs(keep_days: int = 30):
    now = datetime.utcnow()
    for fname in os.listdir(DEFAULT_LOG_DIR):
        path = os.path.join(DEFAULT_LOG_DIR, fname)
        try:
            mtime = datetime.utcfromtimestamp(os.path.getmtime(path))
            if (now - mtime).days > keep_days:
                os.remove(path)
        except Exception:
            pass

# -----------------------------------------------------------------------------
# Config object for CLI and defaults
# -----------------------------------------------------------------------------
class Config:
    def __init__(self,
                 start_congress: int = DEFAULT_START_CONGRESS,
                 end_congress: Optional[int] = None,
                 outdir: str = DEFAULT_OUTDIR,
                 bulk_json: str = DEFAULT_BULK_JSON,
                 retry_json: str = DEFAULT_RETRY_JSON,
                 concurrency: int = DEFAULT_CONCURRENCY,
                 retries: int = DEFAULT_RETRIES,
                 collections: Optional[List[str]] = None,
                 do_discovery: bool = True,
                 db_url: Optional[str] = None,
                 log_level: int = logging.INFO):
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
        self.log_level = log_level

# -----------------------------------------------------------------------------
# DiscoveryManager - build candidate URLs (templates + index crawl)
# -----------------------------------------------------------------------------
class DiscoveryManager:
    """
    Builds a comprehensive dictionary of candidate bulk-data URLs:
      - govinfo template expansion (BILLSTATUS, ROLLCALLVOTE, BILLS, PLAW, CREC)
      - govinfo index crawl to discover exact filenames
      - GovTrack per-congress discovery
      - OpenStates downloads + plural mirror heuristics + per-state guesses
      - theunitedstates legislator links
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
        "https://theunitedstates.io/congress-legislators/legislators-historical.json",
    ]
    GOVTRACK_BASE = "https://www.govtrack.us/data"

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.logger = adapter_for(configure_logger(), "discovery")

    def _http_get(self, url: str, timeout: int = 20) -> Optional[str]:
        if requests is None:
            self.logger.warning("requests not installed; cannot http_get %s", url)
            return None
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200:
                return r.text
            self.logger.debug("GET %s -> %d", url, r.status_code)
        except Exception as e:
            self.logger.debug("GET failed %s: %s", url, e)
        return None

    @labeled("discovery_expand_templates")
    def expand_templates(self) -> List[str]:
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
        # dedupe preserve order
        seen = set(); out = []
        for u in urls:
            if u not in seen:
                out.append(u); seen.add(u)
        self.logger.info("Expanded %d template URLs", len(out))
        return out

    @labeled("discovery_govinfo_index")
    def discover_govinfo_index(self) -> List[str]:
        html = self._http_get(self.GOVINFO_INDEX)
        links = []
        if not html:
            return links
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
        self.logger.info("Discovered %d govinfo index links", len(links))
        return list(dict.fromkeys(links))

    @labeled("discovery_govtrack")
    def discover_govtrack(self) -> List[str]:
        results = []
        # include a known govtrack export pointer
        results.append("https://www.govtrack.us/data/us/bills/bills.csv")
        for c in range(self.cfg.start_congress, self.cfg.end_congress + 1):
            dir_url = f"https://www.govtrack.us/data/us/{c}/"
            html = self._http_get(dir_url)
            if not html:
                continue
            for m in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
                href = m.group(1)
                candidate = href if href.startswith("http") else urljoin(dir_url, href)
                if re.search(r'\.(zip|tar\.gz|tgz|json|xml|csv)$', candidate, re.IGNORECASE):
                    results.append(candidate)
        self.logger.info("Discovered %d govtrack links", len(results))
        return list(dict.fromkeys(results))

    @labeled("discovery_openstates")
    def discover_openstates(self) -> List[str]:
        discovered = []
        html = self._http_get(self.OPENSTATES_DOWNLOADS)
        if html:
            for m in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
                href = m.group(1)
                if href.startswith("http"):
                    candidate = href
                elif href.startswith("/"):
                    candidate = "https://openstates.org" + href
                else:
                    continue
                if re.search(r'\.(zip|json|csv|tgz|tar\.gz)$', candidate, re.IGNORECASE):
                    discovered.append(candidate)
        # scan plural mirror
        mirror_html = self._http_get(self.OPENSTATES_MIRROR)
        if mirror_html:
            for m in re.finditer(r'href=["\']([^"\']+)["\']', mirror_html, re.IGNORECASE):
                href = m.group(1)
                candidate = href if href.startswith("http") else self.OPENSTATES_MIRROR.rstrip("/") + "/" + href
                if re.search(r'\.(zip|json|csv|tgz|tar\.gz)$', candidate, re.IGNORECASE):
                    discovered.append(candidate)
        # guessed per-state patterns
        base = self.OPENSTATES_MIRROR.rstrip("/") + "/"
        for st in ("al","ak","az","ar","ca","co","ct","de","fl","ga","hi","id","il","in","ia","ks","ky","la","me","md","ma","mi","mn","ms","mo","mt","ne","nv","nh","nj","nm","ny","nc","nd","oh","ok","or","pa","ri","sc","sd","tn","tx","ut","vt","va","wa","wv","wi","wy","dc","pr"):
            for p in (f"openstates-{st}.zip", f"{st}.zip", f"openstates-{st}.json.zip"):
                discovered.append(base + p)
        self.logger.info("Discovered %d openstates candidate links", len(discovered))
        return list(dict.fromkeys(discovered))

    @labeled("discovery_build")
    def build(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        data["govinfo_templates_expanded"] = self.expand_templates()
        if self.cfg.do_discovery:
            data["govinfo_index_discovered"] = self.discover_govinfo_index()
            data["govtrack"] = self.discover_govtrack()
            data["openstates"] = self.discover_openstates()
        else:
            data["govinfo_index_discovered"] = []
            data["govtrack"] = []
            data["openstates"] = []
        data["congress_legislators"] = self.THEUNITEDSTATES_LEGISLATORS
        # flatten aggregate
        agg: List[str] = []
        for v in data.values():
            if isinstance(v, list):
                agg.extend(v)
            elif isinstance(v, dict):
                for iv in v.values():
                    if isinstance(iv, list):
                        agg.extend(iv)
        data["aggregate_urls"] = list(dict.fromkeys([u for u in agg if isinstance(u, str)]))
        # Metrics
        global MET_DISCOVERED_URLS
        if MET_DISCOVERED_URLS is not None:
            MET_DISCOVERED_URLS.set(len(data["aggregate_urls"]))
        self.logger.info("Built discovery data with %d aggregate URLs", len(data["aggregate_urls"]))
        return data

# -----------------------------------------------------------------------------
# Validator class: lightweight HEAD checks
# -----------------------------------------------------------------------------
class Validator:
    def __init__(self):
        self.logger = adapter_for(configure_logger(), "validator")

    @labeled("validator_head_ok")
    def head_ok(self, url: str, timeout: int = 20) -> bool:
        if requests is None:
            self.logger.warning("requests not installed; cannot validate HEAD for %s", url)
            return False
        try:
            r = requests.head(url, timeout=timeout, allow_redirects=True)
            if r.status_code >= 400:
                # sometimes HEAD blocked: try small GET
                r2 = requests.get(url, timeout=timeout, stream=True)
                ok = r2.status_code < 400
                r2.close()
                return ok
            return True
        except Exception as e:
            self.logger.debug("HEAD check failed for %s: %s", url, e)
            return False

# -----------------------------------------------------------------------------
# DownloadManager: async downloads with resume (Range) and retries + progress
# -----------------------------------------------------------------------------
class DownloadManager:
    def __init__(self, outdir: str, concurrency: int = DEFAULT_CONCURRENCY, retries: int = DEFAULT_RETRIES):
        ensure_dirs(outdir, DEFAULT_LOG_DIR)
        self.outdir = outdir
        self.concurrency = concurrency
        self.retries = retries
        self.logger = adapter_for(configure_logger(), "downloader")

    async def _head_info(self, session: aiohttp.ClientSession, url: str) -> Dict[str, Any]:
        """Attempt HEAD; return dict with status, size, resumable boolean."""
        try:
            async with session.head(url, timeout=aiohttp.ClientTimeout(total=30), allow_redirects=True) as resp:
                status = resp.status
                cl = resp.headers.get("Content-Length")
                ar = resp.headers.get("Accept-Ranges", "")
                return {"status": status, "size": int(cl) if cl and cl.isdigit() else None, "resumable": "bytes" in ar.lower()}
        except Exception:
            return {"status": None, "size": None, "resumable": False}

    async def _download_single(self, session: aiohttp.ClientSession, url: str, dest: str) -> Dict[str, Any]:
        """Download a single URL with resume support and retries."""
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
                    total = None
                    cl = resp.headers.get("Content-Length")
                    if cl and cl.isdigit():
                        total = int(cl) + (existing if mode == "ab" else 0)
                    written = existing
                    chunk = 1 << 16
                    # streaming write with optional tqdm progress bar
                    if TQDM_INSTALLED:
                        desc = os.path.basename(dest)
                        with open(dest, mode) as fh, tqdm(total=total, initial=existing, unit="B", unit_scale=True, unit_divisor=1024, desc=desc[:40], leave=False) as pbar:
                            async for chunk_data in resp.content.iter_chunked(chunk):
                                if not chunk_data:
                                    break
                                fh.write(chunk_data)
                                written += len(chunk_data)
                                pbar.update(len(chunk_data))
                    else:
                        with open(dest, mode) as fh:
                            async for chunk_data in resp.content.iter_chunked(chunk):
                                if not chunk_data:
                                    break
                                fh.write(chunk_data)
                                written += len(chunk_data)
                    result["ok"] = True
                    result["bytes"] = written
                    if MET_DOWNLOADS is not None:
                        MET_DOWNLOADS.inc()
                    self.logger.info("Downloaded %s -> %s bytes=%d", url, dest, written)
                    return result
            except Exception as e:
                result["error"] = str(e)
                self.logger.warning("Attempt %d/%d failed for %s: %s", attempts, self.retries, url, e)
                await asyncio.sleep(min(30, 2 ** attempts))
        if MET_DOWNLOAD_FAILS is not None:
            MET_DOWNLOAD_FAILS.inc()
        return result

    @labeled("downloader_run")
    def download_all(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Entry point to download a list of URLs concurrently. Returns list of dicts
        with per-URL result info. This uses asyncio and aiohttp.
        """
        if aiohttp is None:
            raise RuntimeError("aiohttp is required for downloads; pip install aiohttp")
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
# Extractor: automatically extract zip, tar, tgz, tar.gz
# -----------------------------------------------------------------------------
class Extractor:
    def __init__(self):
        self.logger = adapter_for(configure_logger(), "extractor")

    @labeled("extractor_extract")
    def extract(self, archive_path: str, remove_archive: bool = False) -> Dict[str, Any]:
        """
        Extract archive to <archive_path>_extracted and optionally remove archive file.
        Returns dict with ok/dest/error.
        """
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
            self.logger.info("Extracted %s -> %s", archive_path, dest)
            return {"ok": True, "dest": dest}
        except Exception as e:
            self.logger.exception("Extraction error for %s", archive_path)
            return {"ok": False, "error": str(e)}

# -----------------------------------------------------------------------------
# ParserNormalizer: parse billstatus and rollcall XMLs (sketch using lxml),
# plus legislators JSON. These parsers are extendable to exact govinfo schemas.
# -----------------------------------------------------------------------------
class ParserNormalizer:
    def __init__(self):
        self.logger = adapter_for(configure_logger(), "parser")
        if etree is None:
            self.logger.warning("lxml not installed; XML parsing may be limited. pip install lxml")

    @labeled("parser_parse_billstatus")
    def parse_billstatus(self, xml_path: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to parse key bill fields from govinfo billstatus XML.
        This is conservative: it uses common element names and falls back gracefully.
        """
        if etree is None:
            self.logger.warning("Skipping XML parse (lxml missing) for %s", xml_path)
            return None
        try:
            tree = etree.parse(xml_path)
            root = tree.getroot()
            # Try common XPath locations - real govinfo uses namespaces; we try local-name matching
            def first_text(xpath_list):
                for xp in xpath_list:
                    found = root.xpath(xp, namespaces=root.nsmap)
                    if found:
                        # element or string
                        if isinstance(found[0], etree._Element):
                            text = found[0].text
                        else:
                            text = str(found[0])
                        if text:
                            return text.strip()
                return None
            bill_no = first_text([".//billNumber", ".//*[local-name() = 'billNumber']"])
            title = first_text([".//title", ".//*[local-name() = 'title']"])
            sponsor = first_text([".//sponsor//*[local-name() = 'name']", ".//sponsor//*[local-name() = 'fullName']"])
            introduced = first_text([".//introducedDate", ".//*[local-name() = 'introducedDate']"])
            return {"source_file": xml_path, "bill_number": bill_no, "title": title, "sponsor": sponsor, "introduced_date": introduced}
        except Exception as e:
            self.logger.debug("Bill parse failed for %s: %s", xml_path, e)
            return None

    @labeled("parser_parse_rollcall")
    def parse_rollcall(self, xml_path: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to parse basic rollcall vote info. Detailed member votes parsing
        would require schema-specific code.
        """
        if etree is None:
            self.logger.warning("Skipping rollcall parse (lxml missing) for %s", xml_path)
            return None
        try:
            tree = etree.parse(xml_path)
            root = tree.getroot()
            def first_text(xpath_list):
                for xp in xpath_list:
                    found = root.xpath(xp, namespaces=root.nsmap)
                    if found:
                        if isinstance(found[0], etree._Element):
                            text = found[0].text
                        else:
                            text = str(found[0])
                        if text:
                            return text.strip()
                return None
            vote_id = first_text([".//vote_id", ".//*[local-name() = 'voteNumber']"])
            result = first_text([".//result", ".//*[local-name() = 'result']"])
            date = first_text([".//voteDate", ".//*[local-name() = 'voteDate']"])
            # member breakdown parsing placeholder: real implementation iterates member elements
            return {"source_file": xml_path, "vote_id": vote_id, "result": result, "date": date}
        except Exception as e:
            self.logger.debug("Rollcall parse failed for %s: %s", xml_path, e)
            return None

    @labeled("parser_parse_legislator_json")
    def parse_legislators_json(self, json_path: str) -> List[Dict[str, Any]]:
        result = []
        try:
            with open(json_path, "r", encoding="utf-8") as fh:
                j = json.load(fh)
            for item in j:
                name = None
                bioguide = None
                if isinstance(item, dict):
                    name = item.get("name", {}).get("official_full") or item.get("name")
                    bioguide = item.get("id", {}).get("bioguide") or item.get("id")
                    terms = item.get("terms", [])
                    current = terms[-1] if terms else {}
                    result.append({"name": name, "bioguide": bioguide, "current_party": current.get("party"), "state": current.get("state"), "source_file": json_path})
            return result
        except Exception as e:
            self.logger.debug("Legislators JSON parse failed for %s: %s", json_path, e)
            return []

# -----------------------------------------------------------------------------
# DB Manager: runs embedded migrations and upserts parsed records into Postgres
# -----------------------------------------------------------------------------
class DBManager:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str
        self.conn = None
        self.logger = adapter_for(configure_logger(), "dbmgr")

    @labeled("db_connect")
    def connect(self):
        if psycopg2 is None:
            raise RuntimeError("psycopg2 not installed; pip install psycopg2-binary")
        self.conn = psycopg2.connect(self.conn_str)
        self.conn.autocommit = False
        self.logger.info("Connected to Postgres")

    @labeled("db_run_migrations")
    def run_migrations(self):
        if not self.conn:
            self.connect()
        cur = self.conn.cursor()
        try:
            for name, sql in MIGRATIONS:
                self.logger.info("Applying migration %s", name)
                cur.execute(sql)
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            self.logger.exception("Migration error: %s", e)
            raise

    @labeled("db_upsert_bill")
    def upsert_bill(self, rec: Dict[str, Any], congress: Optional[int] = None, chamber: Optional[str] = None):
        if not self.conn:
            self.connect()
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bills (source_file, congress, chamber, bill_number, title, sponsor, introduced_date)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (congress,chamber,bill_number) DO UPDATE
                SET title = EXCLUDED.title, sponsor = EXCLUDED.sponsor, introduced_date = EXCLUDED.introduced_date
                RETURNING id
            """, (rec.get("source_file"), congress, chamber, rec.get("bill_number"), rec.get("title"), rec.get("sponsor"), rec.get("introduced_date")))
            row = cur.fetchone()
        self.conn.commit()
        return row[0] if row else None

    @labeled("db_upsert_vote")
    def upsert_vote(self, rec: Dict[str, Any], congress: Optional[int] = None, chamber: Optional[str] = None):
        if not self.conn:
            self.connect()
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO votes (source_file, congress, chamber, vote_id, vote_date, result)
                VALUES (%s,%s,%s,%s,%s,%s)
                ON CONFLICT (congress,chamber,vote_id) DO UPDATE
                SET result = EXCLUDED.result, vote_date = EXCLUDED.vote_date
                RETURNING id
            """, (rec.get("source_file"), congress, chamber, rec.get("vote_id"), rec.get("date"), rec.get("result")))
            row = cur.fetchone()
        self.conn.commit()
        return row[0] if row else None

    @labeled("db_upsert_legislator")
    def upsert_legislator(self, rec: Dict[str, Any]):
        if not self.conn:
            self.connect()
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO legislators (name, bioguide, current_party, state)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT (bioguide) DO UPDATE
                SET name = EXCLUDED.name, current_party = EXCLUDED.current_party, state = EXCLUDED.state
                RETURNING id
            """, (rec.get("name"), rec.get("bioguide"), rec.get("current_party"), rec.get("state")))
            row = cur.fetchone()
        self.conn.commit()
        return row[0] if row else None

    @labeled("db_close")
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.logger.info("Postgres connection closed")

# -----------------------------------------------------------------------------
# Retry Manager: tracks failed downloads and retains attempt counts
# -----------------------------------------------------------------------------
class RetryManager:
    def __init__(self, path: str):
        self.path = path
        self.logger = adapter_for(configure_logger(), "retry")
        self._load()

    def _load(self):
        data = load_json_safe(self.path)
        if not data:
            self.data = {"failures": []}
        else:
            self.data = data

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
        self.logger.info("Recorded failure for %s", url)

    @labeled("retry_list")
    def list_to_retry(self, max_attempts: int = 5) -> List[str]:
        return [r["url"] for r in self.data["failures"] if r.get("attempts", 0) < max_attempts]

    @labeled("retry_remove")
    def remove(self, url: str):
        self.data["failures"] = [r for r in self.data["failures"] if r["url"] != url]
        save_json_atomic(self.path, self.data)

# -----------------------------------------------------------------------------
# HTTP Control Server and Prometheus metrics exposure
# -----------------------------------------------------------------------------
class HTTPControlServer:
    """
    Lightweight aiohttp server exposing:
      - /metrics (Prometheus)
      - /status : json status of last discovery and queued failures
      - /start : trigger a discovery+download run (POST)
      - /retry : trigger retry of failed downloads
    This is optional; the pipeline can also be controlled through CLI and file outputs.
    """
    def __init__(self, pipeline, host: str = "0.0.0.0", port: int = 8080):
        self.pipeline = pipeline
        self.host = host
        self.port = port
        self.app = None
        self.runner = None
        self.logger = adapter_for(configure_logger(), "http")

    def make_app(self):
        from aiohttp import web
        app = web.Application()
        app.router.add_get("/status", self.handle_status)
        app.router.add_post("/start", self.handle_start)
        app.router.add_post("/retry", self.handle_retry)
        # metrics endpoint: use prometheus_client if available
        if generate_latest is not None:
            async def metrics(req):
                data = generate_latest()
                return web.Response(body=data, content_type="text/plain; version=0.0.4")
            app.router.add_get("/metrics", metrics)
        app.router.add_get("/health", lambda req: web.Response(text="ok"))
        self.app = app
        return app

    async def handle_status(self, request):
        data = {"last_discovery": getattr(self.pipeline, "last_discovery_ts", None), "retry_count": len(self.pipeline.retry_mgr.data.get("failures", []))}
        return aiohttp.web.json_response(data)

    async def handle_start(self, request):
        # run discovery+download in background
        asyncio.create_task(self.pipeline.run_once_async(download=True, extract=True, postprocess=False))
        return aiohttp.web.json_response({"status": "started"})

    async def handle_retry(self, request):
        asyncio.create_task(self.pipeline.retry_failed_async())
        return aiohttp.web.json_response({"status": "retry_started"})

    async def start(self):
        if aiohttp is None:
            raise RuntimeError("aiohttp is required to run HTTP control server")
        app = self.make_app()
        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, self.host, self.port)
        await site.start()
        self.logger.info("HTTP control server started at http://%s:%d", self.host, self.port)
        self.runner = runner

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
            self.logger.info("HTTP control server stopped")

# -----------------------------------------------------------------------------
# Orchestrator Pipeline - ties everything together and provides sync & async run
# -----------------------------------------------------------------------------
class Pipeline:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        ensure_dirs(cfg.outdir, DEFAULT_LOG_DIR)
        self.logger = adapter_for(configure_logger(), "pipeline")
        self.discovery_mgr = DiscoveryManager(cfg)
        self.validator = Validator()
        self.downloader = DownloadManager(cfg.outdir, concurrency=cfg.concurrency, retries=cfg.retries)
        self.extractor = Extractor()
        self.parser = ParserNormalizer()
        self.dbmgr = DBManager(cfg.db_url) if cfg.db_url else None
        self.retry_mgr = RetryManager(cfg.retry_json)
        self.http_server = None
        self.last_discovery_ts: Optional[str] = None

    @labeled("pipeline_discover")
    def discover(self) -> Dict[str, Any]:
        data = self.discovery_mgr.build()
        save_json_atomic(self.cfg.bulk_json, data)
        self.last_discovery_ts = datetime.utcnow().isoformat()
        global MET_LAST_RUN_TS
        if MET_LAST_RUN_TS is not None:
            MET_LAST_RUN_TS.set(time.time())
        self.logger.info("Discovery saved to %s", self.cfg.bulk_json)
        return data

    def validate(self, urls: List[str]) -> List[str]:
        out = []
        for u in urls:
            if self.validator.head_ok(u):
                out.append(u)
            else:
                self.logger.debug("Validation failed for %s", u)
        self.logger.info("Validation: %d/%d URLs OK", len(out), len(urls))
        return out

    @labeled("pipeline_download")
    def download(self, urls: List[str]) -> List[Dict[str, Any]]:
        results = self.downloader.download_all(urls)
        # record failures
        for r in results:
            if not r.get("ok"):
                self.retry_mgr.add_failure(r.get("url", "unknown"), r.get("error", "download failed"))
        return results

    @labeled("pipeline_extract")
    def extract_all(self, download_results: List[Dict[str, Any]], remove_archive: bool = False) -> List[Dict[str, Any]]:
        extracted = []
        for r in download_results:
            if not r.get("ok"):
                continue
            path = r.get("path")
            if not path:
                continue
            if re.search(r'\.(zip|tar\.gz|tgz|tar)$', path, re.IGNORECASE):
                res = self.extractor.extract(path, remove_archive)
                extracted.append(res)
        self.logger.info("Extraction run complete (%d extracted)", len(extracted))
        return extracted

    @labeled("pipeline_postprocess")
    def postprocess(self, collections: Optional[List[str]] = None):
        if not self.dbmgr:
            self.logger.warning("DB URL not configured; skipping postprocess/ingestion")
            return
        self.dbmgr.connect()
        self.dbmgr.run_migrations()
        # Walk outdir and ingest parsed files
        count = {"bills":0, "votes":0, "legislators":0}
        for root, dirs, files in os.walk(self.cfg.outdir):
            for fname in files:
                full = os.path.join(root, fname)
                lower = fname.lower()
                try:
                    if lower.endswith(".json") and "legislators" in fname.lower():
                        rows = self.parser.parse_legislators_json(full)
                        for r in rows:
                            self.dbmgr.upsert_legislator(r)
                            count["legislators"] += 1
                    elif lower.endswith(".xml") and ("bill" in lower or "billstatus" in lower):
                        rec = self.parser.parse_billstatus(full)
                        if rec:
                            self.dbmgr.upsert_bill(rec)
                            count["bills"] += 1
                    elif lower.endswith(".xml") and ("vote" in lower or "rollcall" in lower):
                        rec = self.parser.parse_rollcall(full)
                        if rec:
                            self.dbmgr.upsert_vote(rec)
                            count["votes"] += 1
                except Exception as e:
                    self.logger.exception("Postprocess error for %s: %s", full, e)
        self.dbmgr.close()
        self.logger.info("Postprocess ingestion complete: %s", count)

    # Async wrappers for HTTP server background tasks
    async def run_once_async(self, download: bool = False, extract: bool = False, postprocess: bool = False, validate: bool = False):
        loop_logger = adapter_for(configure_logger(), "pipeline_async")
        try:
            data = self.discover()
            agg = data.get("aggregate_urls", [])
            if validate:
                agg = self.validate(agg)
            if download and agg:
                results = await asyncio.get_event_loop().run_in_executor(None, self.download, agg)
                if extract:
                    await asyncio.get_event_loop().run_in_executor(None, self.extract_all, results, False)
                if postprocess:
                    await asyncio.get_event_loop().run_in_executor(None, self.postprocess, None)
            loop_logger.info("Async run_once completed")
        except Exception as e:
            loop_logger.exception("Async run_once failed: %s", e)

    async def retry_failed_async(self, max_attempts: int = 5):
        to_retry = self.retry_mgr.list_to_retry(max_attempts)
        if not to_retry:
            self.logger.info("No failures to retry")
            return
        self.logger.info("Retrying %d failed URLs", len(to_retry))
        results = await asyncio.get_event_loop().run_in_executor(None, self.download, to_retry)
        for r in results:
            if r.get("ok"):
                self.retry_mgr.remove(r.get("url"))
        self.logger.info("Retry round complete")

    def start_http_server(self, host: str = "0.0.0.0", port: int = 8080):
        if aiohttp is None:
            raise RuntimeError("aiohttp required to start HTTP server")
        self.http_server = HTTPControlServer(self, host=host, port=port)
        loop = asyncio.get_event_loop()
        loop.create_task(self.http_server.start())
        self.logger.info("HTTP server scheduled to start")

    def schedule_loop(self, interval_minutes: int = 60, retry_interval: int = 60, max_attempts: int = 5):
        """
        Blocking schedule loop that runs discovery+download+extract+postprocess repeatedly.
        Also attempts automatic retries for failed downloads at retry_interval.
        """
        self.logger.info("Entering schedule loop: run every %d minutes; retry every %d minutes", interval_minutes, retry_interval)
        next_retry = datetime.utcnow() + timedelta(minutes=retry_interval)
        try:
            while True:
                self.logger.info("Scheduled run started at %s", datetime.utcnow().isoformat())
                self.discover()
                urls = load_json_safe(self.cfg.bulk_json).get("aggregate_urls", [])
                if urls:
                    valid_urls = self.validate(urls)
                    results = self.download(valid_urls)
                    self.extract_all(results, remove_archive=False)
                    if self.dbmgr:
                        self.postprocess()
                # retry failed if time
                if datetime.utcnow() >= next_retry:
                    self.logger.info("Scheduled retry round")
                    retry_list = self.retry_mgr.list_to_retry(max_attempts)
                    if retry_list:
                        results = self.download(retry_list)
                        for r in results:
                            if r.get("ok"):
                                self.retry_mgr.remove(r.get("url"))
                    next_retry = datetime.utcnow() + timedelta(minutes=retry_interval)
                self.logger.info("Scheduled run complete; sleeping %d minutes", interval_minutes)
                time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            self.logger.info("Schedule loop interrupted by user")

# -----------------------------------------------------------------------------
# Prometheus metrics initialization helper
# -----------------------------------------------------------------------------
def init_metrics():
    global MET_DOWNLOADS, MET_DOWNLOAD_FAILS, MET_DISCOVERED_URLS, MET_LAST_RUN_TS
    if Counter is None:
        return
    MET_DOWNLOADS = Counter("congress_downloads_total", "Total successful downloads")
    MET_DOWNLOAD_FAILS = Counter("congress_download_failures_total", "Total failed downloads")
    MET_DISCOVERED_URLS = Gauge("congress_discovered_urls", "Number of discovered aggregate URLs")
    MET_LAST_RUN_TS = Gauge("congress_last_run_timestamp", "Timestamp of last discovery run")

# -----------------------------------------------------------------------------
# CLI parsing and main
# -----------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="Congress Bulk Legislative Pipeline - single script")
    parser.add_argument("--start-congress", type=int, default=DEFAULT_START_CONGRESS)
    parser.add_argument("--end-congress", type=int, default=None)
    parser.add_argument("--outdir", type=str, default=DEFAULT_OUTDIR)
    parser.add_argument("--bulk-json", type=str, default=DEFAULT_BULK_JSON)
    parser.add_argument("--retry-json", type=str, default=DEFAULT_RETRY_JSON)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    parser.add_argument("--collections", type=str, default="", help="Comma-separated (bills,rollcall,plaw,crec,legislators)")
    parser.add_argument("--no-discovery", dest="do_discovery", action="store_false")
    parser.add_argument("--validate", dest="do_validate", action="store_true")
    parser.add_argument("--download", dest="do_download", action="store_true")
    parser.add_argument("--extract", dest="do_extract", action="store_true")
    parser.add_argument("--postprocess", dest="do_postprocess", action="store_true")
    parser.add_argument("--db", type=str, default=os.getenv("DATABASE_URL", ""), help="Postgres connection string")
    parser.add_argument("--serve", dest="serve", action="store_true", help="Start HTTP control server")
    parser.add_argument("--serve-host", type=str, default="0.0.0.0")
    parser.add_argument("--serve-port", type=int, default=8080)
    parser.add_argument("--schedule", type=int, default=0, help="Run schedule loop every N minutes (0 disables)")
    parser.add_argument("--retry-interval", type=int, default=60, help="Retry failed downloads every N minutes")
    parser.add_argument("--retry-max-attempts", type=int, default=5)
    parser.add_argument("--limit", type=int, default=0, help="Limit number of aggregate URLs processed (0 all)")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Only discovery and print sample")
    parser.add_argument("--log-level", type=str, default="INFO")
    return parser.parse_args()

def main():
    args = parse_args()
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logger_main = configure_logger()
    adapter_for(logger_main, "main").info("Starting pipeline script")
    collections = [c.strip().lower() for c in args.collections.split(",") if c.strip()] if args.collections else None
    cfg = Config(start_congress=args.start_congress, end_congress=args.end_congress, outdir=args.outdir,
                 bulk_json=args.bulk_json, retry_json=args.retry_json, concurrency=args.concurrency,
                 retries=args.retries, collections=collections, do_discovery=args.do_discovery, db_url=args.db, log_level=log_level)
    # initialize metrics if available
    init_metrics()
    if generate_latest is not None and start_http_server is not None:
        try:
            # run a Prometheus metrics HTTP server on different port (default 8000)
            start_http_server(8000)
            adapter_for(logger_main, "metrics").info("Prometheus metrics server started on :8000")
        except Exception:
            adapter_for(logger_main, "metrics").warning("Could not start Prometheus metrics server")
    pipeline = Pipeline(cfg)
    # dry-run: do discovery only and print sample
    if args.dry_run:
        data = pipeline.discover()
        sample = data.get("aggregate_urls", [])[:20]
        print("DRY RUN SAMPLE (first 20 aggregate URLs):")
        for s in sample:
            print(" -", s)
        return
    # Optional HTTP server
    if args.serve:
        pipeline.start_http_server(host=args.serve_host, port=args.serve_port)
    # One-off run
    data = pipeline.discover()
    agg = data.get("aggregate_urls", [])
    if args.limit and args.limit > 0:
        agg = agg[:args.limit]
    if args.do_validate:
        agg = pipeline.validate(agg)
    if args.do_download and agg:
        results = pipeline.download(agg)
        if args.do_extract:
            pipeline.extract_all(results, remove_archive=False)
    if args.do_postprocess:
        pipeline.postprocess(collections)
    # schedule loop if requested
    if args.schedule and args.schedule > 0:
        pipeline.schedule_loop(interval_minutes=args.schedule, retry_interval=args.retry_interval, max_attempts=args.retry_max_attempts)
    adapter_for(logger_main, "main").info("Pipeline main finished")

if __name__ == "__main__":
    main()