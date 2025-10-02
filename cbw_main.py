###############################################################################
# Name:        cbw_main.py
# Date:        2025-10-02
# Script Name: cbw_main.py
# Version:     1.0
# Log Summary: Main entrypoint that wires cbw_* modules into a runnable app.
# Description: CLI that runs discovery, optional validation, download, extract,
#              postprocessing (DB ingestion), HTTP server, and scheduled runs.
# Change Summary:
#   - 1.0 orchestrator that ties modules together and provides a simple CLI
# Inputs:
#   - CLI flags: --download --extract --postprocess --serve --dry-run etc.
# Outputs:
#   - bulk_urls.json, retry_report.json, logs, DB tables if configured
###############################################################################

import argparse
import time
import asyncio
import os
from cbw_utils import configure_logger, adapter_for, ensure_dirs, save_json_atomic
from cbw_config import Config
from cbw_discovery import DiscoveryManager
from cbw_validator import Validator
from cbw_downloader import DownloadManager
from cbw_extractor import Extractor
from cbw_parser import ParserNormalizer
from cbw_db import DBManager
from cbw_retry import RetryManager
from cbw_http import HTTPControlServer

# Embedded minimal migration to create core tables (can be expanded)
MIGRATIONS = [
    ("001_init", """
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
COMMIT;
""")
]

logger = configure_logger()
ad = adapter_for(logger, "main")

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--start-congress", type=int, default=93)
    p.add_argument("--end-congress", type=int, default=None)
    p.add_argument("--outdir", type=str, default="./bulk_data")
    p.add_argument("--bulk-json", type=str, default="bulk_urls.json")
    p.add_argument("--retry-json", type=str, default="retry_report.json")
    p.add_argument("--concurrency", type=int, default=6)
    p.add_argument("--retries", type=int, default=5)
    p.add_argument("--collections", type=str, default="")
    p.add_argument("--no-discovery", dest="do_discovery", action="store_false")
    p.add_argument("--validate", dest="do_validate", action="store_true")
    p.add_argument("--download", dest="do_download", action="store_true")
    p.add_argument("--extract", dest="do_extract", action="store_true")
    p.add_argument("--postprocess", dest="do_postprocess", action="store_true")
    p.add_argument("--db", type=str, default="")
    p.add_argument("--serve", action="store_true")
    p.add_argument("--serve-port", type=int, default=8080)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=0)
    return p.parse_args()

def main():
    args = parse_args()
    collections = [c.strip().lower() for c in args.collections.split(",") if c.strip()] if args.collections else None
    cfg = Config(start_congress=args.start_congress, end_congress=args.end_congress, outdir=args.outdir,
                 bulk_json=args.bulk_json, retry_json=args.retry_json, concurrency=args.concurrency,
                 retries=args.retries, collections=collections, do_discovery=args.do_discovery, db_url=args.db)
    ensure_dirs(cfg.outdir, "./logs")
    discovery = DiscoveryManager(cfg)
    validator = Validator()
    downloader = DownloadManager(cfg.outdir, concurrency=cfg.concurrency, retries=cfg.retries)
    extractor = Extractor(cfg.outdir)
    parser = ParserNormalizer()
    retry_mgr = RetryManager(cfg.retry_json)
    dbmgr = DBManager(cfg.db_url, migrations=MIGRATIONS) if cfg.db_url else None

    ad.info("Starting cbw pipeline: start=%s end=%s collections=%s", cfg.start_congress, cfg.end_congress, cfg.collections)

    # Discovery
    discovered = discovery.build()
    save_json_atomic(cfg.bulk_json, discovered)
    ad.info("Discovery saved to %s", cfg.bulk_json)

    if args.dry_run:
        sample = discovered.get("aggregate_urls", [])[:20]
        print("DRY RUN SAMPLE (first 20):")
        for s in sample:
            print(" -", s)
        return

    urls = discovered.get("aggregate_urls", [])
    if args.limit and args.limit > 0:
        urls = urls[:args.limit]

    if args.do_validate:
        urls = validator.filter_list(urls)
        ad.info("After validation, %d URLs remain", len(urls))

    download_results = []
    if args.do_download and urls:
        download_results = downloader.download_all(urls)
        # record failures
        for r in download_results:
            if not r.get("ok"):
                retry_mgr.add(r.get("url", "unknown"), r.get("error", "download failed"))

    if args.do_extract and download_results:
        for r in download_results:
            if not r.get("ok"):
                continue
            path = r.get("path")
            if path and any(path.lower().endswith(ext) for ext in (".zip", ".tar.gz", ".tgz", ".tar")):
                extractor.extract(path, remove_archive=False)

    if args.do_postprocess and dbmgr:
        dbmgr.connect()
        dbmgr.run_migrations()
        counts = {"bills":0,"votes":0,"legislators":0}
        # Walk outdir for extracted files
        for root, _, files in os.walk(cfg.outdir):
            for fname in files:
                full = os.path.join(root, fname)
                if fname.lower().endswith(".json") and "legislators" in fname.lower():
                    rows = parser.parse_legislators(full)
                    for r in rows:
                        dbmgr.upsert_legislator(r); counts["legislators"] += 1
                elif fname.lower().endswith(".xml") and ("bill" in fname.lower() or "billstatus" in fname.lower()):
                    rec = parser.parse_billstatus(full)
                    if rec:
                        dbmgr.upsert_bill(rec); counts["bills"] += 1
                elif fname.lower().endswith(".xml") and ("vote" in fname.lower() or "rollcall" in fname.lower()):
                    rec = parser.parse_rollcall(full)
                    if rec:
                        dbmgr.upsert_vote(rec); counts["votes"] += 1
        ad.info("Postprocess counts: %s", counts)
        dbmgr.close()

    # Optional HTTP control server for TUI integration
    if args.serve:
        pipeline = None  # lightweight; for richer integration create Pipeline class with run_once_async
        server = HTTPControlServer(pipeline=None, host="0.0.0.0", port=args.serve_port)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(server.start())
        ad.info("HTTP server running on port %d; press Ctrl-C to stop", args.serve_port)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            loop.run_until_complete(server.stop())

if __name__ == "__main__":
    main()