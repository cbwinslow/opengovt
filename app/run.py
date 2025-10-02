###############################################################################
# Name:        CLI entrypoint
# Date:        2025-10-02
# Script Name: run.py
# Version:     1.0
# Log Summary: CLI wrapper that constructs Config and calls Pipeline.
# Description: Single entrypoint to run discovery, validation, download, extract,
#              postprocessing, scheduling, and optionally start HTTP control server.
# Change Summary:
#   - 1.0 initial CLI binding and argument parsing
# Inputs: CLI options
# Outputs: triggers pipeline operations and writes bulk_urls.json and retry_report.json
###############################################################################

import argparse
import os
from app.pipeline import Pipeline
from app.pipeline import DiscoveryManager
from app.utils import configure_logger, ensure_dirs

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-congress", type=int, default=93)
    parser.add_argument("--end-congress", type=int, default=None)
    parser.add_argument("--outdir", type=str, default="./bulk_data")
    parser.add_argument("--output", type=str, default="bulk_urls.json")
    parser.add_argument("--retry-report", type=str, default="retry_report.json")
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--retries", type=int, default=5)
    parser.add_argument("--collections", type=str, default="")
    parser.add_argument("--no-discovery", dest="do_discovery", action="store_false")
    parser.add_argument("--validate", dest="do_validate", action="store_true")
    parser.add_argument("--download", dest="do_download", action="store_true")
    parser.add_argument("--extract", dest="do_extract", action="store_true")
    parser.add_argument("--postprocess", dest="do_postprocess", action="store_true")
    parser.add_argument("--db", type=str, default="", help="Postgres connection string")
    parser.add_argument("--schedule-interval", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", dest="dry_run", action="store_true")
    parser.add_argument("--log-level", type=str, default="INFO")
    return parser.parse_args()

def main():
    args = parse_args()
    collections = [c.strip().lower() for c in args.collections.split(",") if c.strip()] if args.collections else None
    from app.pipeline import Config
    cfg = Config(start_congress=args.start_congress, end_congress=args.end_congress, outdir=args.outdir, output_file=args.output, retry_report=args.retry_report, concurrency=args.concurrency, retries=args.retries, collections=collections, do_discovery=args.do_discovery)
    ensure_dirs(args.outdir)
    pipeline = Pipeline(cfg, db_conn=args.db if args.db else None)
    if args.dry_run:
        data = pipeline.discover()
        sample = data.get("aggregate_urls", [])[:20]
        print("DRY RUN SAMPLE URLs:")
        for s in sample:
            print(" -", s)
        return
    pipeline.run_once(validate=args.do_validate, download=args.do_download, extract=args.do_extract, postprocess=args.do_postprocess)
    if args.schedule_interval and args.schedule_interval > 0:
        pipeline.schedule_loop(interval_minutes=args.schedule_interval, retry_interval=60, max_attempts=5, do_validate=args.do_validate, do_download=args.do_download, do_extract=args.do_extract, do_postprocess=args.do_postprocess)

if __name__ == "__main__":
    main()