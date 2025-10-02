###############################################################################
# Name:        Congress Bulk URLs and Discovery Script
# Date:        2025-10-01
# Script Name: congress_bulk_urls.py
# Version:     1.0
# Log Summary: Provide an exhaustive (practical and discoverable) array/dictionary
#              of bulk-data URL templates, examples, and discovery helpers so a
#              single script can generate the full set of downloadable endpoints
#              for legislative data (bills, votes, sessions, members, comments).
# Description: Builds a comprehensive dictionary of known authoritative bulk-data
#              sources (govinfo, theunitedstates, govtrack, OpenStates, data.gov,
#              etc.), expands common filename patterns across congress ranges
#              and chambers, and includes simple index-crawling helpers to
#              discover exact files available on govinfo and similar index pages.
# Change Summary:
#   - 1.0: Initial version. Includes:
#       * Pre-built templates + examples for govinfo bulkdata and other sources
#       * Expansion utilities to enumerate congress numbers and chambers
#       * Simple HTML index discovery for govinfo bulkdata
#       * Outputs a JSON file with all discovered/generated URLs
# Inputs:
#   - Optional: user-specified range of congress numbers to expand (defaults 93..118)
# Outputs:
#   - bulk_urls (dictionary) printed and saved as ./bulk_urls.json
#   - Summary printed to stdout with counts per source
###############################################################################

import os
import re
import json
import time
import requests
from typing import List, Dict, Any
from html import unescape

# ---------------------- CONFIG / KNOWN SOURCES ----------------------------- #
# NOTE: This script aims to be exhaustive across well-known authoritative
# sources by giving patterns and discovery helpers. True exhaustiveness (every
# mirror, every congress, every state dataset) requires iterating ranges and
# optionally crawling index pages; helpers below do that programmatically.

OUTPUT_FILE = "bulk_urls.json"
DEFAULT_CONGRESS_RANGE = range(93, 119)  # 93..118 inclusive (update as needed)
REQUESTS_TIMEOUT = 20

# Authoritative source definitions and templates
SOURCES = {
    "govinfo": {
        "description": (
            "Official bulk data (govinfo) produced by GPO/Library of Congress and others. "
            "Common collections include BILLSTATUS and ROLLCALLVOTE. Files are typically "
            "zipped and organized by congress and chamber."
        ),
        # base index to crawl for available files if you want to discover exact names
        "index_url": "https://www.govinfo.gov/bulkdata",
        # template patterns (format placeholders will be replaced by code)
        # Examples:
        #   https://www.govinfo.gov/bulkdata/BILLSTATUS/118/hr/BILLSTATUS-118hr.zip
        #   https://www.govinfo.gov/bulkdata/ROLLCALLVOTE/118/senate/ROLLCALLVOTE-118-senate.zip
        "templates": {
            "BILLSTATUS": "https://www.govinfo.gov/bulkdata/BILLSTATUS/{congress}/{chamber}/BILLSTATUS-{congress}{chamber}.zip",
            "ROLLCALLVOTE": "https://www.govinfo.gov/bulkdata/ROLLCALLVOTE/{congress}/{chamber}/ROLLCALLVOTE-{congress}-{chamber}.zip",
            # common collections (may require discovery for exact filenames):
            "BILLS": "https://www.govinfo.gov/bulkdata/BILLS/{congress}/{chamber}/BILLS-{congress}{chamber}.zip",
            "PLAW": "https://www.govinfo.gov/bulkdata/PLAW/{congress}/PLAW-{congress}.zip",
            "CONGRESSIONALRECORD": "https://www.govinfo.gov/bulkdata/CREC/{congress}/CREC-{congress}.zip",
            "STATUTE": "https://www.govinfo.gov/bulkdata/STATUTE/{year}/STATUTE-{year}.zip",
        },
        # valid chamber tokens to try when expanding templates
        "chambers": ["hr", "house", "senate", "s"],
    },

    "congress_legislators": {
        "description": "Legislators data and related files hosted by 'theunitedstates.io' (the UnitedStates project).",
        "urls": [
            "https://theunitedstates.io/congress-legislators/legislators-current.json",
            "https://theunitedstates.io/congress-legislators/legislators-historical.json",
            "https://theunitedstates.io/congress-legislators/legislators-social-media.csv",
            "https://theunitedstates.io/congress-legislators/office.json",
        ],
    },

    "govtrack": {
        "description": "GovTrack bulk data and derived datasets. GovTrack provides several downloadable datasets and per-congress directories.",
        "base": "https://www.govtrack.us/data",
        # Typical per-congress patterns (example):
        #  https://www.govtrack.us/data/us/118/bills/bills-118.xml  (note: exact filenames need discovery)
        "templates": {
            "per_congress_dir": "https://www.govtrack.us/data/us/{congress}/",
            # Known higher-level dataset:
            "bulk_export": "https://www.govtrack.us/data/us/bills/bills.csv",  # example single CSV export
        },
    },

    "openstates": {
        "description": "OpenStates provides comprehensive state legislative data. Bulk downloads are available; use the OpenStates downloads page or their data API.",
        "downloads_page": "https://openstates.org/downloads/",
        # PluralPolicy mirror (useful pointer):
        "plural_mirror": "https://open.pluralpolicy.com/data/",
        # Note: OpenStates may require API tokens for some endpoints; bulk dumps are usually provided as direct downloads.
    },

    "data_gov": {
        "description": "Data.gov is a catalog of datasets; many legislative datasets are cataloged there. Use the CKAN API to search programmatically.",
        "ckan_search_api": "https://catalog.data.gov/api/3/action/package_search?q=congress OR 'congressional' OR 'legislative'",
        "ckan_package_show": "https://catalog.data.gov/api/3/action/package_show?id={package_id}",
    },

    "unitedstates_congress_repo": {
        "description": "The unitedstates/congress GitHub repo contains scripts and references for collecting public domain congressional data.",
        "repo": "https://github.com/unitedstates/congress",
        "notes": "This repository includes scrapers, converters, and pointers to authoritative bulk downloads. Use it as an orchestration reference.",
    },

    "other_relevant": {
        "description": "Other useful endpoints and datasets (examples).",
        "examples": [
            # Library of Congress (Congress.gov) API
            "https://api.congress.gov/",
            # Library of Congress has a docs page for the Congress.gov API:
            "https://www.loc.gov/apis/additional-apis/congress-dot-gov-api/",
            # GovInfo bulkdata landing (index)
            "https://www.govinfo.gov/bulkdata",
            # GovTrack developer data landing
            "https://www.govtrack.us/developers/data",
        ],
    },
}

# ---------------------- HELPERS TO BUILD/EXPAND URLs ----------------------- #
def expand_govinfo_templates(congress_range=DEFAULT_CONGRESS_RANGE) -> List[str]:
    """
    Expand the govinfo templates across the provided congress range and chambers.
    Returns a deduplicated list of candidate URLs (these are the typical filenames;
    sometimes exact file names differ—the index crawler below can discover exact names).
    """
    urls = []
    templates = SOURCES["govinfo"]["templates"]
    chambers = SOURCES["govinfo"]["chambers"]

    for c in congress_range:
        for name, tpl in templates.items():
            # If template requires chamber, expand across chamber tokens
            if "{chamber}" in tpl:
                for ch in set(chambers):
                    try:
                        url = tpl.format(congress=c, chamber=ch)
                        urls.append(url)
                    except Exception:
                        pass
            else:
                try:
                    # Year-based templates: try to infer years from congress number roughly:
                    year = congress_to_first_year(c)
                    url = tpl.format(congress=c, year=year)
                    urls.append(url)
                except Exception:
                    try:
                        url = tpl.format(congress=c)
                        urls.append(url)
                    except Exception:
                        pass
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for u in urls:
        if u not in seen:
            deduped.append(u)
            seen.add(u)
    return deduped

def congress_to_first_year(congress_number: int) -> int:
    """
    Heuristic: The 1st US Congress began in 1789. Each Congress lasts 2 years.
    So first year = 1789 + 2*(congress_number - 1)
    """
    return 1789 + 2 * (congress_number - 1)

def discover_govinfo_index(index_url: str = SOURCES["govinfo"]["index_url"]) -> List[str]:
    """
    Fetches the govinfo bulkdata index page and extracts all href links that point
    to the govinfo bulkdata domain. This helps to discover exact filenames that
    may not exactly match templates.
    """
    links = []
    try:
        resp = requests.get(index_url, timeout=REQUESTS_TIMEOUT)
        if resp.status_code != 200:
            print("[WARN] govinfo index returned status", resp.status_code)
            return links
        html = resp.text
        # crude href extractor: find href="..."
        for match in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
            href = unescape(match.group(1))
            # Normalize relative links
            if href.startswith("/"):
                full = "https://www.govinfo.gov" + href
            elif href.startswith("http"):
                full = href
            else:
                # skip other relative fragments
                continue
            # Only collect links that look like bulkdata zip/tar/json/xml
            if re.search(r'\.(zip|tar\.gz|tgz|json|xml|csv)$', full, re.IGNORECASE):
                links.append(full)
    except Exception as e:
        print("[ERROR] Failed to fetch/parse govinfo index:", e)
    # Deduplicate
    return list(dict.fromkeys(links))

def discover_directory_links(base_dir_url: str) -> List[str]:
    """
    For sites that expose directory listings (like govtrack per-congress directories),
    a simple attempt to fetch the directory URL and extract downloadable links.
    """
    links = []
    try:
        resp = requests.get(base_dir_url, timeout=REQUESTS_TIMEOUT)
        if resp.status_code != 200:
            return links
        html = resp.text
        for match in re.finditer(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
            href = unescape(match.group(1))
            if href.startswith("http"):
                candidate = href
            elif href.startswith("/"):
                # Build absolute on same host
                from urllib.parse import urljoin
                candidate = urljoin(base_dir_url, href)
            else:
                candidate = base_dir_url.rstrip("/") + "/" + href
            if re.search(r'\.(zip|tar\.gz|tgz|json|xml|csv)$', candidate, re.IGNORECASE):
                links.append(candidate)
    except Exception as e:
        print("[WARN] discover_directory_links failed for", base_dir_url, ":", e)
    return list(dict.fromkeys(links))

# ---------------------- ASSEMBLE A COMPREHENSIVE URL DICT ------------------ #
def assemble_bulk_url_dict(congress_range=DEFAULT_CONGRESS_RANGE, do_discovery=True) -> Dict[str, Any]:
    """
    Returns a dictionary keyed by source name containing lists of URLs. If do_discovery
    is True, the script will attempt to fetch index pages for govinfo and govtrack
    per-congress directories to collect exact filenames in addition to templates.
    """
    result = {}

    # 1) govinfo: expand template patterns
    govinfo_candidates = expand_govinfo_templates(congress_range)
    result["govinfo_templates_expanded"] = govinfo_candidates

    # Optionally discover exact files from the govinfo index
    if do_discovery:
        print("[INFO] Discovering exact files from govinfo index page...")
        discovered = discover_govinfo_index()
        print(f"[INFO] govinfo discovery found {len(discovered)} archive links.")
        result["govinfo_index_discovered"] = discovered
    else:
        result["govinfo_index_discovered"] = []

    # 2) theunitedstates.io (legislators & related)
    result["congress_legislators"] = SOURCES["congress_legislators"]["urls"]

    # 3) govtrack: attempt to discover per-congress directories and links
    govtrack_urls = []
    govtrack_base = SOURCES["govtrack"]["base"]
    # Add known higher-level examples
    if "bulk_export" in SOURCES["govtrack"]["templates"]:
        govtrack_urls.append(SOURCES["govtrack"]["templates"]["bulk_export"])
    # Try to enumerate per-congress directories and discover files
    if do_discovery:
        for c in congress_range:
            dir_url = SOURCES["govtrack"]["templates"]["per_congress_dir"].format(congress=c)
            found = discover_directory_links(dir_url)
            if found:
                print(f"[INFO] govtrack discovered {len(found)} files in {dir_url}")
            govtrack_urls.extend(found)
    result["govtrack"] = list(dict.fromkeys(govtrack_urls))

    # 4) OpenStates: include downloads page and plural mirror
    result["openstates"] = {
        "downloads_page": SOURCES["openstates"]["downloads_page"],
        "plural_mirror": SOURCES["openstates"]["plural_mirror"],
    }

    # 5) data.gov: include CKAN search API to find datasets programmatically
    result["data_gov"] = {
        "ckan_search_api": SOURCES["data_gov"]["ckan_search_api"],
        "notes": "Use the CKAN API to search for dataset packages, then inspect 'resources' to get file URLs.",
    }

    # 6) unitedstates/congress repo pointer
    result["unitedstates_congress_repo"] = {
        "repo": SOURCES["unitedstates_congress_repo"]["repo"],
        "notes": SOURCES["unitedstates_congress_repo"]["notes"],
    }

    # 7) other useful links
    result["other_relevant"] = SOURCES["other_relevant"]["examples"]

    return result

# ---------------------- UTILITY: SAVE/PRINT RESULTS ------------------------ #
def save_bulk_urls(d: Dict[str, Any], outfile=OUTPUT_FILE):
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
    print(f"[INFO] Wrote {outfile}")

def print_summary(d: Dict[str, Any]):
    print("\n=== Summary of URL groups ===")
    for k, v in d.items():
        if isinstance(v, list):
            print(f"{k}: {len(v)} entries")
        elif isinstance(v, dict):
            # count inner list-like items
            inner_count = sum(len(x) if isinstance(x, list) else 1 for x in v.values())
            print(f"{k}: {inner_count} referenced items")
        else:
            print(f"{k}: single value")

# ---------------------- CLI / DEFAULT RUN BEHAVIOR ------------------------- #
def main():
    """
    Default run will:
      - Expand govinfo templates for congress range DEFAULT_CONGRESS_RANGE
      - Discover govinfo index archive links
      - Attempt to discover per-congress govtrack files
      - Write bulk_urls.json with all discovered/generated URLs
    """
    start = time.time()
    print("[INFO] Assembling bulk URLs. This may take ~10-30s depending on discovery network calls.")
    data = assemble_bulk_url_dict(congress_range=DEFAULT_CONGRESS_RANGE, do_discovery=True)
    save_bulk_urls(data, OUTPUT_FILE)
    print_summary(data)
    elapsed = time.time() - start
    print(f"[INFO] Done in {elapsed:.1f}s. Inspect {OUTPUT_FILE} for the full JSON dictionary.")

if __name__ == "__main__":
    main()

###############################################################################
# USAGE NOTES & NEXT STEPS:
# - Run this single script: python congress_bulk_urls.py
# - The script writes bulk_urls.json which contains:
#     * govinfo_templates_expanded: candidate URLs constructed from templates
#     * govinfo_index_discovered: exact archive links discovered on the govinfo index
#     * congress_legislators: direct links to theunitedstates.io legislator files
#     * govtrack: discovered govtrack per-congress files (if any)
#     * openstates: pointers to OpenStates download pages
#     * data_gov: CKAN search endpoint to programmatically find additional datasets
#     * unitedstates_congress_repo: pointer to the GitHub repo for scripts/more pointers
#
# - Why templates+discovery? Some collections change exact filenames or use slightly
#   different naming for chambers (hr vs house, s vs senate). Templates produce
#   likely candidates; discovery fetches the authoritative index pages to collect
#   the exact available files.
#
# - To download everything:
#     1) Run this script to produce bulk_urls.json.
#     2) Inspect `bulk_urls.json` and feed the arrays into a downloader script
#        (or re-use your previous downloader) to download and extract each archive.
#     3) For state-level data use the OpenStates downloads page (automated by crawling
#        or manual discovery) and Data.gov via CKAN search for specialized datasets.
#
# - If you want, I can:
#     * Extend this script to perform HEAD checks and optionally download every file.
#     * Add explicit per-congress and per-year iterations to reach any future congress numbers.
#     * Add support for OpenLegislation (if you provide the canonical index URL) and
#       for scraping comments/other non-archive endpoints.
###############################################################################