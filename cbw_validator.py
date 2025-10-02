###############################################################################
# Name:        cbw_validator.py
# Date:        2025-10-02
# Script Name: cbw_validator.py
# Version:     1.0
# Log Summary: Validator class performs HEAD/GET checks and filters unreachable URLs.
# Description: Small utility to verify candidate URLs before large downloads to save bandwidth.
# Change Summary:
#   - 1.0 initial implementation
# Inputs:
#   - list of candidate URLs
# Outputs:
#   - filtered list of reachable URLs
###############################################################################

import requests
from typing import List
from cbw_utils import labeled, configure_logger, adapter_for

logger = configure_logger()
ad = adapter_for(logger, "validator")

class Validator:
    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.logger = ad

    @labeled("validator_head")
    def head_ok(self, url: str) -> bool:
        """
        Return True if HEAD indicates 2xx/3xx. Fallback to small GET if HEAD fails.
        """
        try:
            r = requests.head(url, timeout=self.timeout, allow_redirects=True)
            if r.status_code < 400:
                return True
            # fallback to GET if HEAD blocked
            r2 = requests.get(url, timeout=self.timeout, stream=True)
            ok = r2.status_code < 400
            r2.close()
            self.logger.debug("Fallback GET for %s returned %d", url, r2.status_code)
            return ok
        except Exception as e:
            self.logger.debug("HEAD/GET check failed for %s: %s", url, e)
            return False

    @labeled("validator_filter_list")
    def filter_list(self, urls: List[str]) -> List[str]:
        return [u for u in urls if self.head_ok(u)]