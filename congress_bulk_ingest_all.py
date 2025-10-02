###############################################################################
# Name:        Congress Bulk Ingest & Downloader
# Date:        2025-10-01
# Script Name: congress_bulk_ingest_all.py
# Version:     1.1
# Log Summary: Single-file tool to discover authoritative bulk legislative data
#              URLs (govinfo, GovTrack, theunitedstates, OpenStates, Data.gov)
#              and optionally download every discovered file with concurrent
#              resume/retry support.
# Description: Builds a comprehensive dictionary of bulk-data URLs (templates
#              expanded across a configurable Congress range and state list),
#              discovers exact archive filenames from index pages, writes
#              bulk_urls.json, and can concurrently download all discovered
#              artifacts with retry and resume support.
# Change Summary:
#   - 1.0: Initial discovery + templates + govinfo/govtrack index crawling.
#   - 1.1: Added concurrent downloader with resume/retry, expanded default
#          Congress range (auto-computed including recent Congresses) and
#          added state-by-state OpenStates discovery via OpenStates downloads
#          page and PluralPolicy mirror.
# Inputs:
#   - CLI flags:
#       --start-congress N  (default computed, typically 93)
#       --end-congress N    (default auto-computed to current congress + 1)
#       --do-discovery / --no-discovery (default do discovery)
#       --download / --no-download (default no download)
#       --output FILE (default bulk_urls.json)
#       --outdir DIR (where downloads/extractions go; default ./bulk_data)
#       --concurrency N (parallel downloads; default 6)
#       --retries N (per-file retries; default 5)
# Outputs:
#   - bulk_urls.json file containing discovered/generated URLs
#   - (optional) downloaded archives and files under OUTDIR
#   - console logs and a short summary
###############################################################################

import os
import re
import sys
import json
import time
import math
import asyncio
import aiohttp
import argparse
import shutil
import logging
from datetime import datetime
from html import unescape
from typing import List, Dict, Any, Optional
import requests

# Optional: progress bars (pip install tqdm)
try:
    from tqdm.asyncio import tqdm as atqdm
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except Exception:
    TQDM_AVAILABLE = False

# ------------------------- CONFIG / KNOWN SOURCES -------------------------- #
REQUESTS_TIMEOUT = 20
DEFAULT_OUTPUT_FILE = "bulk_urls.json"
DEFAULT_OUTDIR = "./bulk_data"
DEFAULT_CONCURRENCY = 6
DEFAULT_RETRIES = 5

SOURCES = {
    "govinfo": {
        "index_url": "https://www.govinfo.gov/bulkdata",
        "templates": {
            # Patterns seen on govinfo — chamber token placeholders vary so we try several tokens
            "BILLSTATUS": "https://www.govinfo.gov/bulkdata/BILLSTATUS/{congress}/{chamber}/BILLSTATUS-{congress}{chamber}.zip",
            "ROLLCALLVOTE": "https://www.govinfo.gov/bulkdata/ROLLCALLVOTE/{congress}/{chamber}/ROLLCALLVOTE-{congress}-{chamber}.zip",
            "BILLS": "https://www.govinfo.gov/bulkdata/BILLS/{congress}/{chamber}/BILLS-{congress}{chamber}.zip",
            "PLAW": "https://www.govinfo.gov/bulkdata/PLAW/{congress}/PLAW-{congress}.zip",
            "CREC": "https://www.govinfo.gov/bulkdata/CREC/{congress}/CREC-{congress}.zip",
            "STATUTE": "https://www.govinfo.gov/bulkdata/STATUTE/{year}/STATUTE-{year}.zip",
        },
        "chambers": ["hr", "house", "h", "senate", "s"],
    },
    "congress_legislators": {
        "urls": [
            "https://theunitedstates.io/congress-legislators/legislators-current.json",
            "https://theunitedstates.io/congress-legislators/legislators-historical.json",
            "https://theunitedstates.io/congress-legislators/legislators-social-media.csv",
            "https://theunitedstates.io/congress-legislators/office.json",
        ]
    },
    "govtrack": {
        "base": "https://www.govtrack.us/data",
        "templates": {
            "per_congress_dir": "https://www.govtrack.us/data/us/{congress}/",
            "bulk_export_example": "https://www.govtrack.us/data/us/bills/bills.csv",
        }
    },
    "openstates": {
        "downloads_page": "https://openstates.org/downloads/",
        "plural_mirror": "https://open.pluralpolicy.com/data/",
        # We'll attempt to scrape downloads_page and the plural mirror; also attempt
        # per-state inferred filenames if present on mirror.
    },
    "data_gov": {
        "ckan_search_api": "https://catalog.data.gov/api/3/action/package_search?q=congress OR congressional OR legislative"
    },
    "other": {
        "examples": [
            "https://www.loc.gov/apis/additional-apis/congress-dot-gov-api/",
            "https://www.govtrack.us/developers/data",
            "https://www.govinfo.gov/bulkdata"
        ]
    }
}

# ----------------------------- LOGGING SETUP ------------------------------- #
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("congress_bulk")

# --------------------------- UTILITY FUNCTIONS ----------------------------- #
def current_congress_from_date(dt: datetime) -> int:
    # First Congress started 1789, each congress lasts 2 years
    return 1 + (dt.year - 1789) // 2

def congress_first_year(congress: int) -> int:
    return 1789 + 2 * (congress - 1)

def http_get_text(url: str, timeout=REQUESTS_TIMEOUT) -> Optional[str]:
    try:
        r = requests.get(url, timeout=timeout)
        if r.status_code == 200:
            return r.text
        logger.warning("GET %s -> status %s", url, r.status_code)
    except Exception as e:
        logger.warning("GET %s failed: %s", url, e)
    return None

# ---------------------------- DISCOVERY HELPERS ---------------------------- #
def expand_govinfo_templates(start: int, end: int) -> List[str]:
    urls = []
    templates = SOURCES["govinfo"]["templates"]
    chambers = SOURCES["govinfo"]["chambers"]
    for c in range(start, end + 1):
        for name, tpl in templates.items():
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
    seen = set()
    dedup = []
    for u in urls:
        if u not in seen:
            dedup.append(u)
            seen.add(u)
    return dedup

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
        if re.search(r'\.(zip|tar\.gz|tgz|json|xml|csv)$', full, re.IGNORECASE):
            links.append(full)
    # dedupe preserve order
    return list(dict.fromkeys(links))

def discover_directory_links(base_dir_url: str) -> List[str]:
    html = http_get_text(base_dir_url)
    links = []
    if not html:
        return links
    for match in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
        href = unescape(match.group(1))
        if href.startswith("http"):
            candidate = href
        elif href.startswith("/"):
            from urllib.parse import urljoin
            candidate = urljoin(base_dir_url, href)
        else:
            candidate = base_dir_url.rstrip("/") + "/" + href
        if re.search(r'\.(zip|tar\.gz|tgz|json|xml|csv)$', candidate, re.IGNORECASE):
            links.append(candidate)
    return list(dict.fromkeys(links))

def discover_govtrack(congress_range: range) -> List[str]:
    urls = []
    urls.append(SOURCES["govtrack"]["templates"]["bulk_export_example"])
    for c in congress_range:
        dir_url = SOURCES["govtrack"]["templates"]["per_congress_dir"].format(congress=c)
        found = discover_directory_links(dir_url)
        if found:
            logger.info("govtrack discovered %d files in %s", len(found), dir_url)
        urls.extend(found)
    return list(dict.fromkeys(urls))

# OpenStates discovery: scrape downloads page and plural mirror; attempt per-state mirror
US_STATES = [
 'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
 'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
 'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','PR'
]

def discover_openstates(do_discovery=True) -> Dict[str, Any]:
    result = {"downloads_page": SOURCES["openstates"]["downloads_page"], "plural_mirror": SOURCES["openstates"]["plural_mirror"], "discovered": []}
    if not do_discovery:
        return result
    # try OpenStates downloads page
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
            if re.search(r'\.(zip|json|csv|tar\.gz|tgz)$', candidate, re.IGNORECASE):
                result["discovered"].append(candidate)
    # try plural mirror directory listing
    plural_html = http_get_text(SOURCES["openstates"]["plural_mirror"])
    if plural_html:
        for match in re.finditer(r'href=["\']([^"\']+)["\']', plural_html, re.IGNORECASE):
            href = unescape(match.group(1))
            candidate = href if href.startswith("http") else SOURCES["openstates"]["plural_mirror"].rstrip("/") + "/" + href
            if re.search(r'\.(zip|json|csv|tar\.gz|tgz)$', candidate, re.IGNORECASE):
                result["discovered"].append(candidate)
    # attempt state-by-state pattern on plural mirror (common naming: openstates-<state>-YYYY.json.zip or similar)
    mirror_base = SOURCES["openstates"]["plural_mirror"].rstrip("/") + "/"
    for st in US_STATES:
        # try a few common patterns
        patterns = [
            f"openstates-{st.lower()}.zip",
            f"{st.lower()}.zip",
            f"openstates_{st.lower()}.zip",
            f"openstates-{st.lower()}.json.zip",
            f"{st.lower()}.json.zip",
        ]
        for p in patterns:
            candidate = mirror_base + p
            # don't assume existence, but include as candidate for downloader (HEAD)
            result["discovered"].append(candidate)
    # dedupe
    result["discovered"] = list(dict.fromkeys([u for u in result["discovered"] if u]))
    return result

def discover_data_gov_ckan() -> Dict[str, str]:
    return {"ckan_search_api": SOURCES["data_gov"]["ckan_search_api"], "notes": "Use CKAN API to find datasets; inspect package->resources for file URLs."}

# ------------------------- ASSEMBLE URL DICTIONARY ------------------------- #
def assemble_bulk_url_dict(start_congress: int, end_congress: int, do_discovery=True) -> Dict[str, Any]:
    logger.info("Expanding govinfo templates for congress range %d..%d", start_congress, end_congress)
    result = {}
    result["govinfo_templates_expanded"] = expand_govinfo_templates(start_congress, end_congress)
    if do_discovery:
        logger.info("Discovering exact files from govinfo index (this may take a few seconds)...")
        result["govinfo_index_discovered"] = discover_govinfo_index()
    else:
        result["govinfo_index_discovered"] = []
    # theunitedstates legislator files
    result["congress_legislators"] = SOURCES["congress_legislators"]["urls"]
    # govtrack discovered files
    result["govtrack"] = discover_govtrack(range(start_congress, end_congress + 1)) if do_discovery else []
    # openstates discovery
    result["openstates"] = discover_openstates(do_discovery)
    # data.gov pointer
    result["data_gov"] = discover_data_gov_ckan()
    # other pointers
    result["other_relevant"] = SOURCES["other"]["examples"]
    # flattened aggregate list for download convenience
    aggregate = []
    for k, v in result.items():
        if isinstance(v, list):
            aggregate.extend(v)
        elif isinstance(v, dict):
            # collect inner lists and values that look like URLs
            for iv in v.values():
                if isinstance(iv, list):
                    aggregate.extend(iv)
                elif isinstance(iv, str) and iv.startswith("http"):
                    aggregate.append(iv)
    # dedupe aggregate
    result["aggregate_urls"] = list(dict.fromkeys([u for u in aggregate if isinstance(u, str) and u.startswith("http")]))
    logger.info("Assembled %d aggregate candidate URLs", len(result["aggregate_urls"]))
    return result

# --------------------------- DOWNLOAD HELPERS ------------------------------ #
# Async downloader with resume (Range) and retries; uses aiohttp
async def download_with_resume(session: aiohttp.ClientSession, url: str, dest_path: str,
                               retries: int = DEFAULT_RETRIES, semaphore: asyncio.Semaphore = None,
                               idx: int = 0, total: int = 0, show_progress: bool = True) -> Dict[str, Any]:
    """
    Downloads url to dest_path. If server supports Accept-Ranges, resumes existing file.
    Returns dict with status and bytes_written.
    """
    if semaphore is None:
        semaphore = asyncio.Semaphore(DEFAULT_CONCURRENCY)
    result = {"url": url, "path": dest_path, "ok": False, "bytes": 0, "error": None}
    os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
    attempt = 0
    while attempt <= retries:
        attempt += 1
        try:
            async with semaphore:
                # First, try HEAD to see if resumable and to get total size
                headers = {}
                try:
                    async with session.head(url, timeout=aiohttp.ClientTimeout(total=60)) as head:
                        status = head.status
                        if status >= 400:
                            # some servers don't allow HEAD; we will attempt GET
                            total_size = None
                        else:
                            total_size = head.headers.get("Content-Length")
                            accept_ranges = head.headers.get("Accept-Ranges", "")
                            resumable = "bytes" in accept_ranges.lower()
                except Exception:
                    total_size = None
                    resumable = False
                # current file size
                mode = "wb"
                existing = 0
                if os.path.exists(dest_path):
                    existing = os.path.getsize(dest_path)
                    if existing > 0 and resumable:
                        headers["Range"] = f"bytes={existing}-"
                        mode = "ab"
                # Perform GET with appropriate headers
                chunk_size = 1 << 16
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=None)) as resp:
                    if resp.status in (416,):  # Range not satisfiable (file already complete)
                        result["ok"] = True
                        result["bytes"] = existing
                        return result
                    if resp.status >= 400:
                        raise aiohttp.ClientResponseError(resp.request_info, resp.history, status=resp.status, message=await resp.text())
                    # If we appended, bytes_written starts at existing
                    written = existing
                    # Stream and write
                    with open(dest_path, mode + "b") as fh:
                        async for chunk in resp.content.iter_chunked(chunk_size):
                            if not chunk:
                                break
                            fh.write(chunk)
                            written += len(chunk)
                    result["ok"] = True
                    result["bytes"] = written
                    return result
        except Exception as e:
            logger.warning("Attempt %d/%d failed for %s: %s", attempt, retries, url, e)
            result["error"] = str(e)
            # exponential backoff with jitter
            backoff = min(30, (2 ** attempt) + (0.1 * (attempt)))
            await asyncio.sleep(backoff)
            continue
    return result

async def download_all(urls: List[str], outdir: str, concurrency: int = DEFAULT_CONCURRENCY, retries: int = DEFAULT_RETRIES):
    os.makedirs(outdir, exist_ok=True)
    sem = asyncio.Semaphore(concurrency)
    connector = aiohttp.TCPConnector(limit_per_host=concurrency, limit=0)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for i, u in enumerate(urls):
            # sanitize filename
            filename = u.split("?")[0].rstrip("/").split("/")[-1] or f"file_{i}"
            # store in outdir, preserve some structure (by domain)
            from urllib.parse import urlparse
            p = urlparse(u)
            domain = p.netloc.replace(":", "_")
            dest_dir = os.path.join(outdir, domain)
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, filename)
            tasks.append(download_with_resume(session, u, dest, retries=retries, semaphore=sem, idx=i, total=len(urls)))
        if TQDM_AVAILABLE:
            results = []
            for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Downloading"):
                r = await f
                results.append(r)
        else:
            results = await asyncio.gather(*tasks)
    return results

# ----------------------------- MAIN / CLI --------------------------------- #
def parse_args():
    parser = argparse.ArgumentParser(description="Discover and download bulk legislative data (govinfo, OpenStates, GovTrack, etc.)")
    # compute sensible defaults
    now = datetime.utcnow()
    current_cong = current_congress_from_date(now)
    parser.add_argument("--start-congress", type=int, default=93, help="Start congress number (default 93)")
    parser.add_argument("--end-congress", type=int, default=max(current_cong + 1, 119), help=f"End congress number (default current+1 -> {max(current_cong + 1, 119)})")
    parser.add_argument("--no-discovery", dest="do_discovery", action="store_false", help="Skip index discovery and only use templates/patterns")
    parser.add_argument("--download", dest="do_download", action="store_true", help="Download all discovered/generated URLs")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_FILE, help="Output JSON file for URL dictionary")
    parser.add_argument("--outdir", type=str, default=DEFAULT_OUTDIR, help="Directory to save downloads/extracted files")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Concurrent download tasks")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help="Per-file retry attempts")
    parser.add_argument("--limit", type=int, default=0, help="(Optional) limit number of aggregate URLs to process/download (0 = no limit)")
    return parser.parse_args()

def save_json(data: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("Wrote %s", path)

def main():
    args = parse_args()
    logger.info("Running discovery with start_congress=%d end_congress=%d discovery=%s",
                args.start_congress, args.end_congress, args.do_discovery)
    data = assemble_bulk_url_dict(args.start_congress, args.end_congress, do_discovery=args.do_discovery)
    save_json(data, args.output)
    agg = data.get("aggregate_urls", [])
    if args.limit and args.limit > 0:
        agg = agg[:args.limit]
        logger.info("Limiting aggregate URL list to first %d entries", args.limit)
    if args.do_download:
        if not agg:
            logger.warning("No aggregate URLs to download.")
        else:
            logger.info("Starting concurrent download of %d files to %s (concurrency=%d retries=%d)",
                        len(agg), args.outdir, args.concurrency, args.retries)
            start = time.time()
            results = asyncio.run(download_all(agg, args.outdir, concurrency=args.concurrency, retries=args.retries))
            # summarise
            ok = sum(1 for r in results if r.get("ok"))
            failed = [r for r in results if not r.get("ok")]
            elapsed = time.time() - start
            logger.info("Download complete: %d succeeded, %d failed in %.1fs", ok, len(failed), elapsed)
            if failed:
                logger.warning("Failed downloads (first 10 shown):")
                for f in failed[:10]:
                    logger.warning("%s -> %s", f.get("url"), f.get("error"))
    else:
        logger.info("Discovery complete. Use --download to download discovered files.")

if __name__ == "__main__":
    main()

###############################################################################
# USAGE:
# 1) Install dependencies:
#      pip install requests aiohttp tqdm
# 2) Run discovery only:
#      python congress_bulk_ingest_all.py --output bulk_urls.json
# 3) Run discovery and download everything (concurrent, resume/retry enabled):
#      python congress_bulk_ingest_all.py --download --outdir ./bulk_data --concurrency 8
# 4) To limit work for testing:
#      python congress_bulk_ingest_all.py --download --limit 50
#
# NOTES:
# - The script writes bulk_urls.json containing:
#     * govinfo_templates_expanded
#     * govinfo_index_discovered (if discovery on)
#     * congress_legislators (theunitedstates links)
#     * govtrack discovered links (if discovery on)
#     * openstates discovered candidates + plural mirror per-state guesses
#     * data_gov CKAN API pointer
#     * aggregate_urls: deduplicated list of URLs ready for download
# - Resume support depends on server Accept-Ranges support. The downloader will
#   attempt a HEAD first and use Range headers if available. If HEAD is blocked,
#   the downloader will still attempt GET and write until complete.
# - Some candidate URLs (particularly guessed per-state mirror patterns) may 404;
#   downloader will retry with exponential backoff and then record failures in the summary.
# - After downloading, you can extract archives (zip/tar.gz) in the outdir as a
#   post-processing step. I can add auto-extraction if you want.
###############################################################################