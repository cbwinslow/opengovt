###############################################################################
# Name:        cbw_retry.py
# Date:        2025-10-02
# Script Name: cbw_retry.py
# Version:     1.0
# Log Summary: RetryManager records failed downloads and exposes retry lists.
# Description: Keeps a JSON file of failed URLs with attempt counts and timestamps.
# Change Summary:
#   - 1.0 initial implementation
# Inputs:
#   - path to JSON retry report
# Outputs:
#   - updates retry JSON and provides list/removal utilities
###############################################################################

from datetime import datetime
from typing import List
from cbw_utils import labeled, save_json_atomic, load_json_safe, configure_logger, adapter_for

logger = configure_logger()
ad = adapter_for(logger, "retry")

class RetryManager:
    def __init__(self, path: str = "retry_report.json"):
        self.path = path
        self._load()

    def _load(self):
        data = load_json_safe(self.path)
        self.data = data if data else {"failures": []}

    @labeled("retry_add")
    def add(self, url: str, error: str):
        now = datetime.utcnow().isoformat()
        rec = next((r for r in self.data["failures"] if r["url"] == url), None)
        if rec:
            rec["attempts"] = rec.get("attempts", 0) + 1
            rec["last_error"] = error
            rec["last_attempted"] = now
        else:
            self.data["failures"].append({"url": url, "attempts": 1, "first_failed": now, "last_attempted": now, "last_error": error})
        save_json_atomic(self.path, self.data)
        ad.info("Added failure: %s", url)

    @labeled("retry_list")
    def list_to_retry(self, max_attempts: int = 5) -> List[str]:
        return [r["url"] for r in self.data["failures"] if r.get("attempts", 0) < max_attempts]

    @labeled("retry_remove")
    def remove(self, url: str):
        self.data["failures"] = [r for r in self.data["failures"] if r["url"] != url]
        save_json_atomic(self.path, self.data)
        ad.info("Removed failure record for %s", url)