###############################################################################
# Name:        cbw_discovery.py
# Date:        2025-10-02
# Script Name: cbw_discovery.py
# Version:     1.0
# Log Summary: DiscoveryManager: generate template URLs and crawl indexes.
# Description: Expand govinfo/GovTrack/OpenStates templates across congress range,
#              crawl govinfo index for exact filenames, and produce a JSON-ready
#              dictionary of candidate URLs to feed the downloader.
# Change Summary:
#   - 1.0 initial split into DiscoveryManager class
# Inputs:
#   - Config object with start_congress, end_congress, collections, do_discovery
# Outputs:
#   - dict containing lists of discovered candidate URLs (aggregate_urls included)
###############################################################################

import re
from typing import List, Dict, Any
from urllib.parse import urljoin
import requests

from cbw_utils import labeled, configure_logger, adapter_for
from cbw_config import Config

logger = configure_logger()
ad = adapter_for(logger, "discovery")

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
        "https://theunitedstates.io/congress-legislators/legislators-historical.json"
    ]

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.logger = ad

    @labeled("discovery_expand")
    def expand_govinfo_templates(self) -> List[str]:
        urls: List[str] = []
        for c in range(self.cfg.start_congress, self.cfg.end_congress + 1):
            for collection, tpl in self.GOVINFO_TEMPLATES.items():
                if self.cfg.collections and collection not in self.cfg.collections:
                    continue
                if "{chamber}" in tpl:
                    for ch in self.GOVINFO_CHAMBERS:
                        urls.append(tpl.format(congress=c, chamber=ch))
                else:
                    urls.append(tpl.format(congress=c))
        # dedupe while preserving order
        seen = set(); out = []
        for u in urls:
            if u not in seen:
                out.append(u); seen.add(u)
        self.logger.info("Expanded govinfo template URLs: %d", len(out))
        return out

    @labeled("discovery_govinfo_index")
    def discover_govinfo_index(self) -> List[str]:
        try:
            r = requests.get(self.GOVINFO_INDEX, timeout=20)
            if r.status_code != 200:
                self.logger.warning("govinfo index returned status %d", r.status_code)
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
            self.logger.info("Discovered %d govinfo index links", len(links))
            return list(dict.fromkeys(links))
        except Exception as e:
            self.logger.exception("discover_govinfo_index failed: %s", e)
            return []

    @labeled("discovery_govtrack")
    def discover_govtrack(self) -> List[str]:
        urls = ["https://www.govtrack.us/data/us/bills/bills.csv"]
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
                self.logger.debug("govtrack crawl failed for %s", dir_url)
        self.logger.info("Discovered govtrack urls: %d", len(urls))
        return list(dict.fromkeys(urls))

    @labeled("discovery_openstates")
    def discover_openstates(self) -> List[str]:
        found: List[str] = []
        try:
            r = requests.get(self.OPENSTATES_DOWNLOADS, timeout=15)
            if r.status_code == 200:
                for m in re.finditer(r'href=["\']([^"\']+)["\']', r.text, re.IGNORECASE):
                    href = m.group(1)
                    candidate = href if href.startswith("http") else "https://openstates.org" + href
                    if re.search(r'\.(zip|json|csv|tgz|tar\.gz)$', candidate, re.IGNORECASE):
                        found.append(candidate)
        except Exception:
            self.logger.debug("openstates downloads page fetch failed")
        try:
            r2 = requests.get(self.OPENSTATES_MIRROR, timeout=10)
            if r2.status_code == 200:
                for m in re.finditer(r'href=["\']([^"\']+)["\']', r2.text, re.IGNORECASE):
                    href = m.group(1)
                    candidate = href if href.startswith("http") else self.OPENSTATES_MIRROR.rstrip("/") + "/" + href
                    if re.search(r'\.(zip|json|csv|tgz|tar\.gz)$', candidate, re.IGNORECASE):
                        found.append(candidate)
        except Exception:
            self.logger.debug("openstates mirror crawl failed")
        # heuristics: per-state guesses on mirror
        base = self.OPENSTATES_MIRROR.rstrip("/") + "/"
        states = ["al","ak","az","ar","ca","co","ct","de","fl","ga","hi","id","il","in","ia","ks","ky","la","me","md","ma","mi","mn","ms","mo","mt","ne","nv","nh","nj","nm","ny","nc","nd","oh","ok","or","pa","ri","sc","sd","tn","tx","ut","vt","va","wa","wv","wi","wy","dc","pr"]
        for st in states:
            for p in (f"openstates-{st}.zip", f"{st}.zip", f"openstates-{st}.json.zip"):
                found.append(base + p)
        self.logger.info("OpenStates candidate count: %d", len(found))
        return list(dict.fromkeys(found))

    @labeled("discovery_build")
    def build(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        data["govinfo_templates_expanded"] = self.expand_govinfo_templates()
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
        self.logger.info("Discovery built, aggregate urls: %d", len(data["aggregate_urls"]))
        return data