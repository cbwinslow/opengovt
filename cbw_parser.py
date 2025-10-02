###############################################################################
# Name:        cbw_parser.py
# Date:        2025-10-02
# Script Name: cbw_parser.py
# Version:     1.0
# Log Summary: Parsers for billstatus, rollcall, and legislators JSON.
# Description: Conservative parsers that extract common fields and return
#              flattened dictionaries suitable for DB upserts. Uses lxml when available.
# Change Summary:
#   - 1.0 initial parsing utilities; extend with more detailed XPaths when sample files present.
# Inputs:
#   - file paths (XML or JSON)
# Outputs:
#   - dicts or lists of dicts representing parsed entities
###############################################################################

import json
from typing import List, Dict, Any, Optional
from cbw_utils import labeled, configure_logger, adapter_for

logger = configure_logger()
ad = adapter_for(logger, "parser")

try:
    from lxml import etree
except Exception:
    etree = None
    ad.warning("lxml not installed; XML parsing will be limited. Install via pip install lxml")

class ParserNormalizer:
    def __init__(self):
        self.logger = ad

    @labeled("parser_parse_billstatus")
    def parse_billstatus(self, xml_path: str) -> Optional[Dict[str, Any]]:
        if etree is None:
            self.logger.debug("Skipping parse_billstatus: lxml missing")
            return None
        try:
            tree = etree.parse(xml_path)
            root = tree.getroot()
            def first(xpath_list):
                for xp in xpath_list:
                    found = root.xpath(xp, namespaces=root.nsmap)
                    if found:
                        v = found[0]
                        if hasattr(v, "text"):
                            return v.text.strip() if v.text else None
                        else:
                            return str(v).strip()
                return None
            bill_no = first([".//*[local-name()='billNumber']", ".//billNumber"])
            title = first([".//*[local-name()='title']", ".//title"])
            sponsor = first([".//*[local-name()='sponsor']//*[local-name()='name']", ".//*[local-name()='sponsor']"])
            introduced = first([".//*[local-name()='introducedDate']", ".//introducedDate"])
            return {"source_file": xml_path, "bill_number": bill_no, "title": title, "sponsor": sponsor, "introduced_date": introduced}
        except Exception as e:
            self.logger.exception("parse_billstatus failed for %s: %s", xml_path, e)
            return None

    @labeled("parser_parse_rollcall")
    def parse_rollcall(self, xml_path: str) -> Optional[Dict[str, Any]]:
        if etree is None:
            self.logger.debug("Skipping parse_rollcall: lxml missing")
            return None
        try:
            tree = etree.parse(xml_path)
            root = tree.getroot()
            def first(xpath_list):
                for xp in xpath_list:
                    found = root.xpath(xp, namespaces=root.nsmap)
                    if found:
                        v = found[0]
                        if hasattr(v, "text"):
                            return v.text.strip() if v.text else None
                        else:
                            return str(v).strip()
                return None
            vote_id = first([".//*[local-name()='voteNumber']", ".//*[local-name()='vote_id']"])
            result = first([".//*[local-name()='result']", ".//result"])
            date = first([".//*[local-name()='voteDate']", ".//voteDate"])
            return {"source_file": xml_path, "vote_id": vote_id, "result": result, "date": date}
        except Exception as e:
            self.logger.exception("parse_rollcall failed for %s: %s", xml_path, e)
            return None

    @labeled("parser_parse_legislators")
    def parse_legislators(self, json_path: str) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        try:
            with open(json_path, "r", encoding="utf-8") as fh:
                j = json.load(fh)
            for m in j:
                if not isinstance(m, dict):
                    continue
                name = m.get("name", {}).get("official_full") or m.get("name")
                bioguide = m.get("id", {}).get("bioguide") or None
                terms = m.get("terms", [])
                current = terms[-1] if terms else {}
                out.append({"name": name, "bioguide": bioguide, "current_party": current.get("party"), "state": current.get("state"), "source_file": json_path})
            return out
        except Exception as e:
            self.logger.exception("parse_legislators failed for %s: %s", json_path, e)
            return []