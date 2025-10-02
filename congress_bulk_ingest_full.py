###############################################################################
# Name:        Congress Bulk Ingest & Downloader (All-in-One)
# Date:        2025-10-01
# Script Name: congress_bulk_ingest_full.py
# Version:     1.2
# Log Summary: Discover authoritative bulk legislative datasets and optionally
#              download and extract them with concurrency, resume, retries,
#              progress bars, and collection-level filtering.
# Description: Single-file CLI that:
#    - builds a comprehensive list of bulk-data URL candidates (govinfo, GovTrack,
#      theunitedstates, OpenStates, Data.gov pointers),
#    - expands templates across a configurable Congress range (defaults to include 119+),
#    - optionally crawls index pages to discover exact filenames,
#    - validates candidates (HEAD) and writes bulk_urls.json,
#    - optionally concurrently downloads files with resume/retry and progress bars,
#    - automatically extracts archives (zip, tar, tar.gz, tgz) into outdir,
#    - supports filtering by collection and sources, and outputs JSON map.
# Change Summary:
#   - 1.0: initial discovery + templates + govinfo/govtrack index crawling.
#   - 1.1: added concurrent downloader with resume/retry, expanded congress range,
#          OpenStates per-state discovery candidates, and optional extraction.
#   - 1.2: added per-file tqdm progress bars, HEAD validation step, collection filtering,
#          and CLI flags for extraction and keeping/removing archives.
# Inputs:
#   - CLI arguments (see --help). Typical inputs:
#       --start-congress N, --end-congress N
#       --collections comma-separated (e.g., bills,rollcall,legislators,openstates,plaw,crec)
#       --download, --extract, --keep-archives
# Outputs:
#   - bulk_urls.json (by default) containing discovered/generated URLs
#   - (optional) downloaded archives and extracted files under OUTDIR
#   - console logs and summary of successes/failures
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
import zipfile
import tarfile
import requests
from html import unescape
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin

# Optional progress bars
try:
    from tqdm import tqdm
    TQDM = True
except Exception:
    TQDM = False

# ------------------------- CONFIG / KNOWN SOURCES -------------------------- #
REQUESTS_TIMEOUT = 20
DEFAULT_OUTPUT_FILE = "bulk_urls.json"
DEFAULT_OUTDIR = "./bulk_data"
DEFAULT_CONCURRENCY = 6
DEFAULT_RETRIES = 5
DEFAULT_START_CONGRESS = 93

SOURCES = {
    "govinfo": {
        "index_url": "https://www.govinfo.gov/bulkdata",
        "templates": {
            # note keys correspond to collections; used for filtering
            "billstatus": "https://www.govinfo.gov/bulkdata/BILLSTATUS/{congress}/{chamber}/BILLSTATUS-{congress}{chamber}.zip",
            "rollcall": "https://www.govinfo.gov/bulkdata/ROLLCALLVOTE/{congress}/{chamber}/ROLLCALLVOTE-{congress}-{chamber}.zip",
            "bills": "https://www.govinfo.gov/bulkdata/BILLS/{congress}/{chamber}/BILLS-{congress}{chamber}.zip",
            "plaw": "https://www.govinfo.gov/bulkdata/PLAW/{congress}/PLAW-{congress}.zip",
            "crec": "https://www.govinfo.gov/bulkdata/CREC/{congress}/CREC-{congress}.zip",
            "statute": "https://www.govinfo.gov/bulkdata/STATUTE/{year}/STATUTE-{year}.zip",
        },
        "chambers": ["hr", "house", "h", "senate", "s"],
    },
    "congress_legislators": {
        "collection": "legislators",
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

# US states list for OpenStates per-state candidate generation
US_STATES = [
 'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
 'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
 'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC','PR'
]

# ----------------------------- LOGGING SETUP ------------------------------- #
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("congress_bulk")

# --------------------------- HELPER UTILITIES ------------------------------ #
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
        logger.warning("GET %s -> status %s", url, r.status_code)
    except Exception as e:
        logger.warning("GET %s failed: %s", url, e)
    return None

def is_likely_archive(url: str) -> bool:
    return bool(re.search(r'\.(zip|tar\.gz|tgz|tar|json|xml|csv)$', url, re.IGNORECASE))

# ---------------------------- DISCOVERY HELPERS ---------------------------- #
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
    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            out.append(u)
            seen.add(u)
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
            candidate = urljoin(base_dir_url, href)
        else:
            candidate = base_dir_url.rstrip("/") + "/" + href
        if is_likely_archive(candidate):
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

def discover_openstates(do_discovery=True) -> Dict[str, Any]:
    result = {"downloads_page": SOURCES["openstates"]["downloads_page"], "plural_mirror": SOURCES["openstates"]["plural_mirror"], "discovered": []}
    if not do_discovery:
        return result
    # OpenStates downloads page
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
    # Plural mirror directory scan
    plural_html = http_get_text(SOURCES["openstates"]["plural_mirror"])
    if plural_html:
        for match in re.finditer(r'href=["\']([^"\']+)["\']', plural_html, re.IGNORECASE):
            href = unescape(match.group(1))
            candidate = href if href.startswith("http") else SOURCES["openstates"]["plural_mirror"].rstrip("/") + "/" + href
            if re.search(r'\.(zip|json|csv|tar\.gz|tgz)$', candidate, re.IGNORECASE):
                result["discovered"].append(candidate)
    # Add state-by-state guessed patterns on plural mirror (candidates only)
    mirror_base = SOURCES["openstates"]["plural_mirror"].rstrip("/") + "/"
    for st in US_STATES:
        patterns = [
            f"openstates-{st.lower()}.zip",
            f"{st.lower()}.zip",
            f"openstates_{st.lower()}.zip",
            f"openstates-{st.lower()}.json.zip",
            f"{st.lower()}.json.zip",
            f"openstates-{st.lower()}-latest.json.zip",
        ]
        for p in patterns:
            candidate = mirror_base + p
            result["discovered"].append(candidate)
    result["discovered"] = list(dict.fromkeys([u for u in result["discovered"] if u]))
    return result

def discover_data_gov_ckan() -> Dict[str, str]:
    return {"ckan_search_api": SOURCES["data_gov"]["ckan_search_api"], "notes": "Use CKAN API to find datasets; inspect package->resources for file URLs."}

# ------------------------- ASSEMBLE URL DICTIONARY ------------------------- #
def assemble_bulk_url_dict(start_congress: int, end_congress: int, do_discovery=True, collections: Optional[List[str]] = None) -> Dict[str, Any]:
    logger.info("Expanding govinfo templates for congress range %d..%d", start_congress, end_congress)
    result = {}
    result["govinfo_templates_expanded"] = expand_govinfo_templates(start_congress, end_congress, collections)
    if do_discovery:
        logger.info("Discovering exact files from govinfo index...")
        result["govinfo_index_discovered"] = discover_govinfo_index()
    else:
        result["govinfo_index_discovered"] = []
    # theunitedstates legislator files
    if not collections or "legislators" in collections:
        result["congress_legislators"] = SOURCES["congress_legislators"]["urls"]
    else:
        result["congress_legislators"] = []
    # govtrack discovered files
    if do_discovery:
        result["govtrack"] = discover_govtrack(range(start_congress, end_congress + 1))
    else:
        result["govtrack"] = []
    # openstates discovery
    result["openstates"] = discover_openstates(do_discovery)
    # data.gov pointer
    result["data_gov"] = discover_data_gov_ckan()
    result["other_relevant"] = SOURCES["other"]["examples"]
    # Flatten aggregate list for downloads
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
    # filter by collections keywords (simple heuristic)
    if collections:
        filtered = []
        coll_set = set(collections)
        for u in aggregate:
            lowered = u.lower()
            keep = False
            if "openstates" in coll_set and ("openstates" in lowered or "pluralpolicy" in lowered):
                keep = True
            if "legislators" in coll_set and ("congress-legislators" in lowered or "legislators" in lowered):
                keep = True
            # govinfo collection names in path
            for c in coll_set:
                if c in lowered:
                    keep = True
            # if user asked "rollcall" check rollcall or vote indicators
            if "rollcall" in coll_set and ("rollcall" in lowered or "rollcallvote" in lowered or "vote" in lowered):
                keep = True
            if keep:
                filtered.append(u)
        # if filtering removed everything, keep aggregate as fallback
        if filtered:
            aggregate = filtered
    # Deduplicate preserve order
    result["aggregate_urls"] = list(dict.fromkeys(aggregate))
    logger.info("Assembled %d aggregate candidate URLs", len(result["aggregate_urls"]))
    return result

# --------------------------- VALIDATION (HEAD) ----------------------------- #
def validate_urls_head(urls: List[str], timeout: int = 20) -> List[str]:
    """
    Filter the urls by performing HEAD (or GET if HEAD fails) to detect 200/2xx.
    Returns only URLs that appear to exist (status < 400).
    """
    valid = []
    session = requests.Session()
    for u in urls:
        try:
            r = session.head(u, timeout=timeout, allow_redirects=True)
            if r.status_code >= 400:
                # try a GET small request
                r2 = session.get(u, timeout=timeout, stream=True)
                status = r2.status_code
                r2.close()
            else:
                status = r.status_code
            if status < 400:
                valid.append(u)
            else:
                logger.debug("HEAD/GET %s returned %d", u, status)
        except Exception as e:
            logger.debug("HEAD failed for %s: %s", u, e)
    session.close()
    return valid

# ------------------------- ASYNC DOWNLOAD HELPERS -------------------------- #
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
        # fallback: not critical
        pass
    return result

async def stream_download(session: aiohttp.ClientSession, url: str, dest: str, sem: asyncio.Semaphore,
                          retries: int = DEFAULT_RETRIES, show_progress: bool = True) -> Dict[str, Any]:
    """
    Downloads a single file with resume (Range header) if supported.
    Returns dict with url,path,ok,bytes,error
    """
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    attempt = 0
    result = {"url": url, "path": dest, "ok": False, "bytes": 0, "error": None}
    while attempt <= retries:
        attempt += 1
        try:
            async with sem:
                # HEAD to determine size/resume capability
                size = None
                resumable = False
                try:
                    head = await head_info(session, url)
                    size = head.get("size")
                    resumable = head.get("resumable", False)
                except Exception:
                    pass
                # Determine resume offset
                existing = 0
                if os.path.exists(dest):
                    existing = os.path.getsize(dest)
                headers = {}
                mode = "wb"
                if existing and resumable:
                    headers["Range"] = f"bytes={existing}-"
                    mode = "ab"
                # GET stream
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=None)) as resp:
                    if resp.status in (416,):  # range not satisfiable -> file complete
                        result["ok"] = True
                        result["bytes"] = existing
                        return result
                    if resp.status >= 400:
                        raise aiohttp.ClientResponseError(resp.request_info, resp.history, status=resp.status, message=await resp.text())
                    # Determine total for progress
                    total = None
                    cl = resp.headers.get("Content-Length")
                    if cl and cl.isdigit():
                        total = int(cl)
                        # if we used Range, total may be remaining bytes
                        total = total + (existing if mode == "ab" else 0)
                    # Write to file and show progress
                    chunk = 1 << 16
                    written = existing
                    if TQDM and show_progress:
                        # tqdm description
                        desc = os.path.basename(dest)
                        with open(dest, mode) as fh, tqdm(total=total, unit="B", unit_scale=True, unit_divisor=1024,
                                                         initial=existing, desc=desc[:40], leave=False) as pbar:
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
                    return result
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
        # gather with progress
        if TQDM:
            results = []
            for f in asyncio.as_completed(tasks):
                r = await f
                results.append(r)
            return results
        else:
            return await asyncio.gather(*tasks)

# ---------------------------- EXTRACTION HELPERS --------------------------- #
def extract_archive(path: str, dest_dir: str) -> Dict[str, Any]:
    """
    Extracts zip/tar/tar.gz/tgz to dest_dir (creates dest_dir). Returns dict with status.
    """
    res = {"path": path, "extracted_to": None, "ok": False, "error": None}
    try:
        os.makedirs(dest_dir, exist_ok=True)
        lower = path.lower()
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path, 'r') as z:
                z.extractall(dest_dir)
            res["extracted_to"] = dest_dir
            res["ok"] = True
            return res
        # tar or gz
        try:
            with tarfile.open(path, 'r:*') as t:
                t.extractall(dest_dir)
            res["extracted_to"] = dest_dir
            res["ok"] = True
            return res
        except tarfile.ReadError:
            # not a tar
            pass
        # Not an archive
        res["error"] = "Not a supported archive format"
    except Exception as e:
        res["error"] = str(e)
    return res

# ------------------------------- MAIN CLI --------------------------------- #
def parse_args():
    parser = argparse.ArgumentParser(description="Discover and download bulk legislative data (govinfo, OpenStates, GovTrack, etc.)")
    now = datetime.utcnow()
    current_cong = now_congress()
    parser.add_argument("--start-congress", type=int, default=DEFAULT_START_CONGRESS, help="Start congress number (default 93)")
    parser.add_argument("--end-congress", type=int, default=max(current_cong + 1, 119), help=f"End congress number (default current+1 -> {max(current_cong + 1, 119)})")
    parser.add_argument("--no-discovery", dest="do_discovery", action="store_false", help="Skip index discovery and only use templates/patterns")
    parser.add_argument("--download", dest="do_download", action="store_true", help="Download all discovered/generated URLs")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_FILE, help="Output JSON file for URL dictionary")
    parser.add_argument("--outdir", type=str, default=DEFAULT_OUTDIR, help="Directory to save downloads/extracted files")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Concurrent download tasks")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help="Per-file retry attempts")
    parser.add_argument("--limit", type=int, default=0, help="(Optional) limit number of aggregate URLs to process/download (0 = no limit)")
    parser.add_argument("--collections", type=str, default="", help="Comma-separated collection filters (e.g., bills,rollcall,legislators,openstates,plaw,crec)")
    parser.add_argument("--extract", dest="do_extract", action="store_true", help="Automatically extract downloaded archives after download")
    parser.add_argument("--keep-archives", dest="keep_archives", action="store_true", help="Keep original archive files after extraction")
    parser.add_argument("--validate", dest="do_validate", action="store_true", help="Validate candidate URLs with HEAD before download")
    return parser.parse_args()

def save_json(data: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("Wrote %s", path)

def main():
    args = parse_args()
    collections = [c.strip().lower() for c in args.collections.split(",") if c.strip()] if args.collections else None
    logger.info("Discovery: start_congress=%d end_congress=%d discovery=%s collections=%s",
                args.start_congress, args.end_congress, args.do_discovery, collections)
    data = assemble_bulk_url_dict(args.start_congress, args.end_congress, do_discovery=args.do_discovery, collections=collections)
    # Save initial JSON
    save_json(data, args.output)
    agg = data.get("aggregate_urls", [])
    if args.limit and args.limit > 0:
        agg = agg[:args.limit]
        logger.info("Limiting aggregate URL list to first %d entries", args.limit)
    # Optional validation
    if args.do_validate and agg:
        logger.info("Validating %d candidate URLs via HEAD/GET...", len(agg))
        valid = validate_urls_head(agg)
        logger.info("Validation: %d URLs appear reachable", len(valid))
        agg = valid
    # If download requested, start asynchronous downloader
    if args.do_download:
        if not agg:
            logger.warning("No aggregate URLs to download.")
            return
        logger.info("Starting download of %d files to %s (concurrency=%d retries=%d)", len(agg), args.outdir, args.concurrency, args.retries)
        start = time.time()
        results = asyncio.run(download_all_async(agg, args.outdir, concurrency=args.concurrency, retries=args.retries))
        elapsed = time.time() - start
        ok = sum(1 for r in results if r.get("ok"))
        failed = [r for r in results if not r.get("ok")]
        logger.info("Download complete: %d succeeded, %d failed in %.1fs", ok, len(failed), elapsed)
        if failed:
            logger.warning("Failed downloads (first 10 shown):")
            for f in failed[:10]:
                logger.warning("%s -> %s", f.get("url"), f.get("error"))
        # Auto-extract archives if requested
        if args.do_extract:
            logger.info("Extracting downloaded archives under %s ...", args.outdir)
            extracted = []
            for r in results:
                if not r.get("ok"):
                    continue
                p = r.get("path")
                if not p:
                    continue
                # only attempt for archive-like names or known extensions
                if re.search(r'\.(zip|tar\.gz|tgz|tar)$', p, re.IGNORECASE):
                    dest_dir = os.path.splitext(p)[0] + "_extracted"
                    res = extract_archive(p, dest_dir)
                    if res.get("ok"):
                        extracted.append(res)
                        if not args.keep_archives:
                            try:
                                os.remove(p)
                            except Exception:
                                pass
            logger.info("Extraction complete: %d archives extracted", len(extracted))
    else:
        logger.info("Discovery complete. bulk_urls.json written. Use --download to fetch files.")

if __name__ == "__main__":
    main()