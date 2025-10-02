###############################################################################
# Name:        cbw_config.py
# Date:        2025-10-02
# Script Name: cbw_config.py
# Version:     1.0
# Log Summary: Central configuration and defaults used by the cbw application.
# Description: Encapsulates CLI-to-object mapping and default values for the
#              pipeline (congress ranges, directories, concurrency, database).
# Change Summary:
#   - 1.0 initial configuration object
# Inputs:
#   - CLI args or explicit parameters when constructing Config
# Outputs:
#   - Config instance used across modules
###############################################################################

import os
import logging
from datetime import datetime
from typing import Optional, List

DEFAULT_LOG_DIR = os.getenv("CONGRESS_LOG_DIR", "./logs")
DEFAULT_OUTDIR = os.getenv("CONGRESS_OUTDIR", "./bulk_data")
DEFAULT_BULK_JSON = os.getenv("CONGRESS_BULK_JSON", "bulk_urls.json")
DEFAULT_RETRY_JSON = os.getenv("CONGRESS_RETRY_JSON", "retry_report.json")

def now_congress() -> int:
    dt = datetime.utcnow()
    return 1 + (dt.year - 1789) // 2

class Config:
    def __init__(self,
                 start_congress: int = 93,
                 end_congress: Optional[int] = None,
                 outdir: str = DEFAULT_OUTDIR,
                 bulk_json: str = DEFAULT_BULK_JSON,
                 retry_json: str = DEFAULT_RETRY_JSON,
                 concurrency: int = 6,
                 retries: int = 5,
                 collections: Optional[List[str]] = None,
                 do_discovery: bool = True,
                 db_url: str = "",
                 log_level: int = logging.INFO):
        current = now_congress()
        self.start_congress = start_congress
        self.end_congress = end_congress if end_congress is not None else max(current + 1, 119)
        self.outdir = outdir
        self.bulk_json = bulk_json
        self.retry_json = retry_json
        self.concurrency = concurrency
        self.retries = retries
        self.collections = [c.lower() for c in collections] if collections else None
        self.do_discovery = do_discovery
        self.db_url = db_url
        self.log_level = log_level