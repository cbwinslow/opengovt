###############################################################################
# Name:        cbw_extractor.py
# Date:        2025-10-02
# Script Name: cbw_extractor.py
# Version:     1.0
# Log Summary: Extractor: extract zip, tar, tgz and optionally remove archives.
# Description: Extracts archives into a sibling "_extracted" directory and logs result.
# Change Summary:
#   - 1.0 initial extraction helper with safety and logging
# Inputs:
#   - path to archive
# Outputs:
#   - dict {ok, dest, error}
###############################################################################

import os
import tarfile
import zipfile
from cbw_utils import labeled, configure_logger, adapter_for, ensure_dirs

logger = configure_logger()
ad = adapter_for(logger, "extractor")

class Extractor:
    def __init__(self, base_out: str = "./bulk_data"):
        self.base_out = base_out
        ensure_dirs(self.base_out)

    @labeled("extractor_extract")
    def extract(self, archive_path: str, remove_archive: bool = False) -> dict:
        dest = archive_path + "_extracted"
        ensure_dirs(dest)
        try:
            if zipfile.is_zipfile(archive_path):
                with zipfile.ZipFile(archive_path, 'r') as z:
                    z.extractall(dest)
            else:
                with tarfile.open(archive_path, 'r:*') as t:
                    t.extractall(dest)
            if remove_archive:
                try:
                    os.remove(archive_path)
                except Exception:
                    pass
            ad.info("Extracted %s -> %s", archive_path, dest)
            return {"ok": True, "dest": dest}
        except Exception as e:
            ad.exception("Extraction failed for %s: %s", archive_path, e)
            return {"ok": False, "error": str(e)}