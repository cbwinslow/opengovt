###############################################################################
# Name:        Universal Legislative Ingest & Normalizer
# Date:        2025-10-02
# Script Name: universal_ingest.py
# Version:     1.0
# Log Summary: Single-file OOP pipeline to ingest OpenStates, OpenLegislation,
#              govinfo/congress.gov and normalize into a unified PostgreSQL schema
# Description:
#   - Compares OpenStates vs OpenLegislation at a conceptual level, implements
#     mapping and ingestion for both where possible, and provides a universal
#     DB schema that holds federal and state legislative data together.
#   - This single script discovers/parses provided files (OpenStates JSON dumps,
#     OpenLegislation exports or JSON/XML, govinfo BillStatus/rollcall XML), maps
#     them to a common schema, and upserts into PostgreSQL.
# Change Summary:
#   - 1.0: Initial unify-and-ingest engine: DB migrations, parsers for OpenStates
#          JSON and a generic OpenLegislation JSON/XML handler, mapping utilities,
#          and ingestion pipeline with logging/decorators.
# Inputs:
#   - Files: OpenStates bulk JSON (or per-state JSON), OpenLegislation JSON/XML,
#            govinfo XMLs, theunitedstates legislator JSONs.
#   - CLI flags: --openstates FILE/DIR, --openleg FILE/DIR, --govinfo FILE/DIR,
#                --db DB_URL, --dry-run, --limit, --log-level.
# Outputs:
#   - Writes to PostgreSQL tables (universal normalized schema)
#   - Writes bulk_urls.json on discovery if used, and logs to ./logs
# Notes:
#   - This script is intended to run locally where the data files are available.
#   - For production use extend parsers (XPaths, JSON paths) to match exact dataset samples.
###############################################################################

import os
import sys
import json
import gzip
import zipfile
import shutil
import logging
import argparse
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Iterable
from contextlib import contextmanager

# Optional external libs
try:
    import psycopg2
    import psycopg2.extras
except Exception:
    psycopg2 = None

try:
    from lxml import etree
except Exception:
    etree = None

# ----------------------------- Logging utils --------------------------------
LOG_DIR = os.getenv("CONGRESS_LOG_DIR", "./logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"universal_ingest_{datetime.utcnow().strftime('%Y%m%d')}.log")

def configure_logger(level=logging.INFO):
    logger = logging.getLogger("universal_ingest")
    logger.setLevel(level)
    if not getattr(logger, "_configured", False):
        fmt = "%(asctime)s %(levelname)s [%(label)s] %(message)s"
        formatter = logging.Formatter(fmt)
        fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=7)
        fh.setFormatter(formatter)
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        logger.addHandler(fh)
        logger.addHandler(ch)
        logger._configured = True
    return logger

def adapter(label: str):
    return logging.LoggerAdapter(configure_logger(), {"label": label})

# simple decorator for labeled logging
def labeled(label: str):
    def deco(fn):
        def wrapper(*args, **kwargs):
            log = adapter(label)
            log.info(f"ENTER {fn.__name__} args={len(args)} kwargs={list(kwargs.keys())}")
            start = datetime.utcnow()
            try:
                res = fn(*args, **kwargs)
                dur = (datetime.utcnow() - start).total_seconds()
                log.info(f"EXIT {fn.__name__} duration={dur:.3f}s")
                return res
            except Exception as e:
                log.exception(f"EXCEPTION {fn.__name__}: {e}\n{traceback.format_exc()}")
                raise
        return wrapper
    return deco

# ----------------------------- DB schema ------------------------------------
# Universal schema to capture federal+state data in common tables.
UNIVERSAL_MIGRATIONS = [
("001_universal",
"""
BEGIN;

CREATE TABLE IF NOT EXISTS jurisdictions (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  jurisdiction_type TEXT, -- 'federal' or 'state'
  state_code TEXT,        -- e.g., 'NY', NULL for federal
  UNIQUE(name, state_code)
);

CREATE TABLE IF NOT EXISTS sessions (
  id SERIAL PRIMARY KEY,
  jurisdiction_id INTEGER REFERENCES jurisdictions(id) ON DELETE CASCADE,
  identifier TEXT,        -- e.g., '118', '2021-2022'
  start_date TIMESTAMP,
  end_date TIMESTAMP,
  UNIQUE(jurisdiction_id, identifier)
);

CREATE TABLE IF NOT EXISTS persons (
  id SERIAL PRIMARY KEY,
  source TEXT,            -- e.g., 'openstates', 'theunitedstates', 'govinfo'
  source_id TEXT,         -- original id in source dataset
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
  chamber TEXT, -- 'upper'/'lower' or 'senate'/'house'
  role TEXT,
  term_start TIMESTAMP,
  term_end TIMESTAMP,
  source TEXT,
  source_id TEXT,
  inserted_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bills (
  id SERIAL PRIMARY KEY,
  source TEXT,            -- 'govinfo','openstates','openlegislation'
  source_id TEXT,         -- original id in source
  jurisdiction_id INTEGER REFERENCES jurisdictions(id) ON DELETE CASCADE,
  session_id INTEGER REFERENCES sessions(id) ON DELETE CASCADE,
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
""")]

# ----------------------------- DB manager -----------------------------------
class DBManager:
    """
    Minimal DB manager for running migrations and upserting normalized entities.
    Uses simple upsert logic for persons and jurisdictions; assumes unique source ids.
    """
    def __init__(self, conn_string: str):
        if psycopg2 is None:
            raise RuntimeError("psycopg2 is required; install psycopg2-binary")
        self.conn_string = conn_string
        self.conn = None
        self.log = adapter("db")

    @labeled("db_connect")
    def connect(self):
        self.conn = psycopg2.connect(self.conn_string)
        self.conn.autocommit = False
        self.log.info("Connected to DB")

    @labeled("db_close")
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            self.log.info("DB closed")

    @labeled("db_run_migrations")
    def run_migrations(self, migrations: List[tuple]):
        if not self.conn:
            self.connect()
        cur = self.conn.cursor()
        try:
            for name, sql in migrations:
                self.log.info("Applying migration %s", name)
                cur.execute(sql)
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            self.log.exception("Migration failed")
            raise

    # Upsert helpers
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
    def upsert_session(self, jurisdiction_id:int, identifier:str, start_date:Optional[str]=None, end_date:Optional[str]=None)->int:
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
    def upsert_person(self, source: str, source_id: str, name: str, given_name:Optional[str]=None, family_name:Optional[str]=None) -> int:
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
    def insert_member(self, person_id:int, jurisdiction_id:int, data:Dict[str,Any]):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO members (person_id, jurisdiction_id, current_party, state, district, chamber, role, term_start, term_end, source, source_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (person_id, jurisdiction_id, data.get("current_party"), data.get("state"), data.get("district"), data.get("chamber"), data.get("role"), data.get("term_start"), data.get("term_end"), data.get("source"), data.get("source_id")))
        self.conn.commit()

    @labeled("db_upsert_bill")
    def upsert_bill(self, source:str, source_id:str, jurisdiction_id:int, session_id:Optional[int], bill_number:Optional[str], chamber:Optional[str], title:Optional[str], summary:Optional[str], status:Optional[str], introduced_date:Optional[str]) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO bills (source, source_id, jurisdiction_id, session_id, bill_number, chamber, title, summary, status, introduced_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (source, source_id) DO UPDATE SET title=COALESCE(EXCLUDED.title, bills.title), summary=COALESCE(EXCLUDED.summary, bills.summary), status=COALESCE(EXCLUDED.status, bills.status), updated_at=now()
            RETURNING id
        """, (source, source_id, jurisdiction_id, session_id, bill_number, chamber, title, summary, status, introduced_date))
        row = cur.fetchone()
        self.conn.commit()
        return row[0]

    @labeled("db_insert_sponsor")
    def insert_sponsor(self, bill_id:int, person_id:Optional[int], name:str, role:str, sponsor_order:int):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO sponsors (bill_id, person_id, name, role, sponsor_order) VALUES (%s,%s,%s,%s,%s)
        """, (bill_id, person_id, name, role, sponsor_order))
        self.conn.commit()

    @labeled("db_insert_action")
    def insert_action(self, bill_id:int, action_date:Optional[str], description:str, type_:Optional[str]=None):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO actions (bill_id, action_date, description, type) VALUES (%s,%s,%s,%s)
        """, (bill_id, action_date, description, type_))
        self.conn.commit()

    @labeled("db_insert_vote")
    def insert_vote(self, source:str, source_id:str, bill_id:Optional[int], jurisdiction_id:Optional[int], session_id:Optional[int], chamber:Optional[str], vote_date:Optional[str], result:Optional[str], yeas:Optional[int], nays:Optional[int], others:Optional[int]) -> int:
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO votes (source, source_id, bill_id, jurisdiction_id, session_id, chamber, vote_date, result, yeas, nays, others)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
        """, (source, source_id, bill_id, jurisdiction_id, session_id, chamber, vote_date, result, yeas, nays, others))
        row = cur.fetchone()
        self.conn.commit()
        return row[0]

    @labeled("db_insert_vote_record")
    def insert_vote_record(self, vote_id:int, person_id:Optional[int], member_name:str, vote_choice:str):
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO vote_records (vote_id, person_id, member_name, vote_choice) VALUES (%s,%s,%s,%s)
        """, (vote_id, person_id, member_name, vote_choice))
        self.conn.commit()

# ----------------------------- Parsers & Mappers -----------------------------
# These map source-specific shapes into universal schema dicts consumed by DBManager.

@labeled("map_openstates_bill")
def map_openstates_bill(raw: Dict[str,Any]) -> Dict[str,Any]:
    """
    Map an OpenStates bill JSON dict to a normalized dict used by DBManager.upsert_bill
    Fields in OpenStates vary; this tries to pick the most common ones.
    """
    # Example OpenStates bill keys: id, identifier (list), title, abstract, created_at, updated_at, legislative_session, chamber, from_organization...
    source_id = raw.get("id") or raw.get("openstates_id") or raw.get("identifier")
    session = raw.get("legislative_session")
    jurisdiction = raw.get("jurisdiction")
    chamber = raw.get("from_organization", {}).get("classification") if raw.get("from_organization") else raw.get("chamber")
    bill_number = None
    # find a stable bill number from identifiers
    for ident in raw.get("identifiers", []) if isinstance(raw.get("identifiers", []), list) else []:
        if isinstance(ident, dict):
            if ident.get("identifier"):
                bill_number = ident.get("identifier"); break
            elif isinstance(ident, str):
                bill_number = ident; break
    title = raw.get("title") or raw.get("short_title") or (raw.get("title_without_number") if raw.get("title_without_number") else None)
    summary = raw.get("abstract") or raw.get("summary")
    status = raw.get("status") or (raw.get("classification") and ", ".join(raw.get("classification", [])))
    introduced = raw.get("created_at")
    return {
        "source": "openstates",
        "source_id": source_id,
        "session": session,
        "jurisdiction": jurisdiction,
        "bill_number": bill_number,
        "chamber": chamber,
        "title": title,
        "summary": summary,
        "status": status,
        "introduced_date": introduced,
        "raw": raw
    }

@labeled("map_openleg_bill")
def map_openlegislation_bill(raw: Dict[str,Any]) -> Dict[str,Any]:
    """
    Map an OpenLegislation bill object to the universal shape.
    OpenLegislation schemas vary; attempt to find common keys: id, bill_number, title, summary, jurisdiction, session.
    """
    source_id = raw.get("id") or raw.get("bill_id") or raw.get("leg_id")
    bill_number = raw.get("bill_number") or raw.get("number") or raw.get("official_number")
    title = raw.get("title") or raw.get("short_title") or raw.get("official_title")
    summary = raw.get("summary") or raw.get("description")
    jurisdiction = raw.get("jurisdiction") or raw.get("state") or raw.get("jurisdiction_name")
    session = raw.get("session") or raw.get("legislative_session")
    chamber = raw.get("chamber")
    introduced = raw.get("introduced_at") or raw.get("introduced_date")
    status = raw.get("status")
    return {
        "source": "openlegislation",
        "source_id": source_id,
        "session": session,
        "jurisdiction": jurisdiction,
        "bill_number": bill_number,
        "chamber": chamber,
        "title": title,
        "summary": summary,
        "status": status,
        "introduced_date": introduced,
        "raw": raw
    }

@labeled("map_govinfo_bill_xml")
def map_govinfo_bill_from_xml(xml_path: str) -> Dict[str,Any]:
    """
    Conservative mapping from govinfo billstatus XML to universal shape.
    Uses lxml if present, else returns minimal info.
    """
    if etree is None:
        return {"source":"govinfo","source_id":os.path.basename(xml_path),"title":None,"raw":None}
    try:
        tree = etree.parse(xml_path); root = tree.getroot()
        def first_x(paths):
            for p in paths:
                got = root.xpath(p, namespaces=root.nsmap)
                if got:
                    val = got[0]
                    if hasattr(val, "text") and val.text:
                        return val.text.strip()
                    else:
                        return str(val).strip()
            return None
        source_id = first_x([".//*[local-name()='billId']",".//*[local-name()='bill_number']"]) or os.path.basename(xml_path)
        bill_no = first_x([".//*[local-name()='billNumber']"])
        title = first_x([".//*[local-name()='officialTitle']", ".//*[local-name()='title']"])
        sponsor = first_x([".//*[local-name()='sponsor']//*[local-name()='person']", ".//*[local-name()='sponsor']"])
        introduced = first_x([".//*[local-name()='introducedDate']"])
        return {
            "source":"govinfo",
            "source_id":source_id,
            "bill_number": bill_no,
            "title": title,
            "summary": None,
            "status": None,
            "introduced_date": introduced,
            "raw": None
        }
    except Exception as e:
        adapter("map_govinfo_bill").exception("Failed map_govinfo_bill_from_xml %s: %s", xml_path, e)
        return {"source":"govinfo","source_id":os.path.basename(xml_path)}

# ------------------------ Ingestion worker functions ------------------------
@labeled("ingest_openstates_file")
def ingest_openstates_file(db: DBManager, filepath: str, cfg: Config, limit:int=0):
    """
    Given a path to an OpenStates bulk JSON (or zipped JSON), parse and ingest bills and legislators.
    The function expects the file to be either a JSON array or a JSON per-record newline file.
    """
    log = adapter("ingest_openstates")
    def opener(p):
        if p.endswith(".gz"):
            return gzip.open(p, "rt", encoding="utf-8")
        elif p.endswith(".zip"):
            # look for first .json inside zip
            zf = zipfile.ZipFile(p)
            for name in zf.namelist():
                if name.lower().endswith(".json"):
                    return zf.open(name, "r")
            return None
        else:
            return open(p, "r", encoding="utf-8")
    f = opener(filepath)
    if f is None:
        log.warning("Unable to open %s", filepath); return
    count = 0
    # Try to load entire JSON first (most OpenStates dumps are arrays)
    try:
        if hasattr(f, "read"):
            text = f.read() if not isinstance(f, zipfile.ZipExtFile) else f.read().decode("utf-8")
            data = json.loads(text)
            # data could be dict with 'results' or a list
            if isinstance(data, dict) and "results" in data:
                records = data["results"]
            elif isinstance(data, list):
                records = data
            else:
                # fallback: single record
                records = [data]
        else:
            records = []
    except Exception:
        # fallback to newline-delimited JSON
        try:
            f.seek(0)
            records = []
            for line in f:
                line = line.strip()
                if not line: continue
                records.append(json.loads(line))
        except Exception as e:
            log.exception("Failed to parse JSON from %s: %s", filepath, e)
            return
    for rec in records:
        if limit and count >= limit:
            break
        # ingest legislator files if detected by filename heuristics
        if "legislators" in os.path.basename(filepath).lower() or rec.get("role_type") == "legislator":
            # normalize person
            source = "openstates"
            source_id = rec.get("id") or rec.get("openstates_id")
            name = rec.get("name") or rec.get("full_name") or rec.get("given_name")
            person_id = db.upsert_person(source, source_id, name, rec.get("given_name"), rec.get("family_name"))
            # members: terms exist in OpenStates as 'memberships' maybe
            # attempt to ingest current membership
            for term in rec.get("terms", []) if isinstance(rec.get("terms", []), list) else []:
                jurisdiction_name = term.get("jurisdiction") or term.get("state")
                if jurisdiction_name:
                    j_id = db.upsert_jurisdiction(jurisdiction_name, "state", term.get("state"))
                else:
                    j_id = db.upsert_jurisdiction("unknown", "state", term.get("state"))
                member_data = {
                    "current_party": term.get("party"),
                    "state": term.get("state"),
                    "district": term.get("district"),
                    "chamber": term.get("type"),
                    "role": term.get("role"),
                    "term_start": term.get("start_date"),
                    "term_end": term.get("end_date"),
                    "source": source,
                    "source_id": source_id
                }
                db.insert_member(person_id, j_id, member_data)
            count += 1
            continue
        # Otherwise treat as bill-like
        mapped = map_openstates_bill(rec)
        # resolve jurisdiction/session
        j_name = mapped.get("jurisdiction") or "federal"
        j_type = "state" if j_name and len(str(j_name))==2 else "federal"
        jurisdiction_id = db.upsert_jurisdiction(j_name or "federal", j_type, j_name if j_type=="state" else None)
        session_identifier = mapped.get("session")
        session_id = None
        if session_identifier:
            session_id = db.upsert_session(jurisdiction_id, session_identifier)
        # upsert bill
        bill_id = db.upsert_bill(mapped["source"], mapped["source_id"], jurisdiction_id, session_id, mapped.get("bill_number"), mapped.get("chamber"), mapped.get("title"), mapped.get("summary"), mapped.get("status"), mapped.get("introduced_date"))
        # sponsors
        for i, s in enumerate(rec.get("sponsors", []) if isinstance(rec.get("sponsors", []), list) else []):
            # sponsor object may have name and person_id
            pname = s.get("name") or s.get("person") or s.get("person_name")
            psource = s.get("source") or "openstates"
            psource_id = s.get("person_id") or s.get("id")
            person_id = None
            if psource_id:
                person_id = db.upsert_person(psource, psource_id, pname)
            db.insert_sponsor(bill_id, person_id, pname, s.get("classification") or s.get("role") or "sponsor", i+1)
        # actions
        for a in rec.get("actions", []) if isinstance(rec.get("actions", []), list) else []:
            db.insert_action(bill_id, a.get("date"), a.get("description"), a.get("classification"))
        count += 1
    log.info("Ingested %d records from %s", count, filepath)
    try:
        f.close()
    except Exception:
        pass

@labeled("ingest_openleg_file")
def ingest_openleg_file(db: DBManager, filepath: str, cfg: Config, limit:int=0):
    """
    Ingest OpenLegislation formatted files. OpenLegislation comes in a few forms (JSON, XML).
    This function tries to be generic: if JSON, load and map; if XML, try to parse per-element.
    """
    log = adapter("ingest_openleg")
    def open_maybe(p):
        if p.endswith(".gz"):
            import gzip
            return gzip.open(p, "rt", encoding="utf-8")
        elif p.endswith(".zip"):
            z = zipfile.ZipFile(p)
            for name in z.namelist():
                if name.lower().endswith(".json"):
                    return z.open(name, "r")
            return None
        else:
            return open(p, "r", encoding="utf-8")
    handle = open_maybe(filepath)
    if handle is None:
        log.warning("Cannot open %s", filepath); return
    count = 0
    # Try to parse JSON array
    try:
        text = handle.read() if not isinstance(handle, zipfile.ZipExtFile) else handle.read().decode("utf-8")
        data = json.loads(text)
        records = data if isinstance(data, list) else (data.get("bills") or data.get("results") or [data])
    except Exception:
        # fallback to XML
        if etree is None:
            log.exception("XML parsing requires lxml; skipping %s", filepath)
            return
        try:
            tree = etree.parse(filepath)
            root = tree.getroot()
            # attempt to find bill elements
            bills = root.findall(".//bill")
            if not bills:
                bills = root.findall(".//legislativeDocument")
            records = []
            for b in bills:
                # convert element to dict naive
                rec = {child.tag: child.text for child in b}
                records.append(rec)
        except Exception as e:
            log.exception("Failed to parse OpenLeg XML %s: %s", filepath, e)
            return
    for rec in records:
        if limit and count >= limit:
            break
        mapped = map_openlegislation_bill(rec) if isinstance(rec, dict) else {}
        j_name = mapped.get("jurisdiction") or "federal"
        j_type = "state" if mapped.get("jurisdiction") and len(str(mapped.get("jurisdiction")) )==2 else "federal"
        jurisdiction_id = db.upsert_jurisdiction(j_name, j_type, j_name if j_type=="state" else None)
        session_id = None
        if mapped.get("session"):
            session_id = db.upsert_session(jurisdiction_id, mapped.get("session"))
        bill_id = db.upsert_bill(mapped.get("source"), mapped.get("source_id"), jurisdiction_id, session_id, mapped.get("bill_number"), mapped.get("chamber"), mapped.get("title"), mapped.get("summary"), mapped.get("status"), mapped.get("introduced_date"))
        # sponsors if present
        for i, s in enumerate(rec.get("sponsors", []) if isinstance(rec.get("sponsors", []), list) else []):
            name = s.get("name") if isinstance(s, dict) else str(s)
            person_id = None
            if isinstance(s, dict) and s.get("person_id"):
                person_id = db.upsert_person("openlegislation", s.get("person_id"), name)
            db.insert_sponsor(bill_id, person_id, name, s.get("role") if isinstance(s, dict) else "sponsor", i+1)
        count += 1
    log.info("Ingested %d OpenLeg records from %s", count, filepath)
    try:
        handle.close()
    except Exception:
        pass

@labeled("ingest_govinfo_dir")
def ingest_govinfo_dir(db: DBManager, dirpath: str, cfg: Config, limit:int=0):
    """
    Scan a directory for govinfo XML billstatus files and ingest them using XML mapper.
    """
    log = adapter("ingest_govinfo")
    files = []
    for root, _, filenames in os.walk(dirpath):
        for fn in filenames:
            if fn.lower().endswith(".xml"):
                files.append(os.path.join(root, fn))
    files = sorted(files)
    count = 0
    for p in files:
        if limit and count >= limit:
            break
        mapped = map_govinfo_bill_from_xml(p)
        j_name = "federal"
        j_id = db.upsert_jurisdiction(j_name, "federal", None)
        session_id = None
        bill_id = db.upsert_bill(mapped.get("source"), mapped.get("source_id"), j_id, session_id, mapped.get("bill_number"), mapped.get("chamber"), mapped.get("title"), mapped.get("summary"), mapped.get("status"), mapped.get("introduced_date"))
        count += 1
    log.info("Ingested %d govinfo XML bills from %s", count, dirpath)

# ---------------------------- Comparative notes -----------------------------
# Short conceptual comparison of OpenStates vs OpenLegislation and how we unify:
# - OpenStates: state-focused, JSON-first, well-documented entity shapes (bills, votes,
#   people, organizations). Good bulk dumps per state. Identifiers often include `openstates_id`.
# - OpenLegislation: a more generic term / some projects called OpenLegislation publish
#   legislative data, sometimes in XML or JSON, schemas vary by implementation; may
#   include more normalized canonical bill models across jurisdictions.
# - govinfo / congress.gov: federal authoritative XML collections (BillStatus, RollCall)
# To unify:
# - Use `jurisdictions` table to separate states vs federal.
# - Use `persons` and `members` for human identities across sources; prefer source+source_id uniqueness.
# - Use `bills` as canonical container with source/source_id and optional session/jurisdiction relations.
# - Sponsors/actions/votes normalized into dedicated tables with foreign keys.
#
# This script maps key fields from each source to the universal schema; for production
# extend mapping functions to handle all fields and provide more complete member linking.

# ----------------------------- CLI & Usage ----------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="Universal ingest for OpenStates, OpenLegislation, govinfo")
    p.add_argument("--openstates", nargs="*", help="OpenStates JSON files or directories to ingest")
    p.add_argument("--openleg", nargs="*", help="OpenLegislation files (JSON/XML) or directories")
    p.add_argument("--govinfo", nargs="*", help="Directories containing govinfo XML files")
    p.add_argument("--db", required=True, help="Postgres connection string, psycopg2 format")
    p.add_argument("--dry-run", action="store_true", help="Do discovery and mapping but not write to DB")
    p.add_argument("--limit", type=int, default=0, help="Limit records per file (0 = no limit)")
    p.add_argument("--log-level", default="INFO")
    return p.parse_args()

@labeled("main")
def main():
    args = parse_args()
    level = getattr(logging, args.log_level.upper(), logging.INFO)
    configure_logger(level=level)
    log = adapter("main")
    cfg = Config()
    db = DBManager(args.db)
    db.connect()
    db.run_migrations(UNIVERSAL_MIGRATIONS)
    # iterate OpenStates inputs
    if args.openstates:
        for path in args.openstates:
            if os.path.isdir(path):
                # find files ending with .json or .json.gz or .zip
                for root, _, files in os.walk(path):
                    for fn in files:
                        if fn.lower().endswith((".json", ".json.gz", ".zip")):
                            fp = os.path.join(root, fn)
                            if args.dry_run:
                                log.info("DRY RUN would ingest OpenStates file %s", fp)
                            else:
                                ingest_openstates_file(db, fp, cfg, limit=args.limit)
            elif os.path.isfile(path):
                if args.dry_run:
                    log.info("DRY RUN would ingest OpenStates file %s", path)
                else:
                    ingest_openstates_file(db, path, cfg, limit=args.limit)
    # iterate OpenLeg inputs
    if args.openleg:
        for path in args.openleg:
            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for fn in files:
                        if fn.lower().endswith((".json", ".xml", ".zip", ".gz")):
                            fp = os.path.join(root, fn)
                            if args.dry_run:
                                log.info("DRY RUN would ingest OpenLeg file %s", fp)
                            else:
                                ingest_openleg_file(db, fp, cfg, limit=args.limit)
            elif os.path.isfile(path):
                if args.dry_run:
                    log.info("DRY RUN would ingest OpenLeg file %s", path)
                else:
                    ingest_openleg_file(db, path, cfg, limit=args.limit)
    # iterate govinfo directories
    if args.govinfo:
        for path in args.govinfo:
            if os.path.isdir(path):
                if args.dry_run:
                    log.info("DRY RUN would scan govinfo dir %s", path)
                else:
                    ingest_govinfo_dir(db, path, cfg, limit=args.limit)
            else:
                log.warning("govinfo path %s is not a directory; skipping", path)
    log.info("Ingestion runs complete")
    db.close()

if __name__ == "__main__":
    main()