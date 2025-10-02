###############################################################################
# Name:        cbw_downloader.py
# Date:        2025-10-02
# Script Name: cbw_downloader.py
# Version:     1.0
# Log Summary: Async DownloadManager with resume/retry and tqdm progress bars.
# Description: Uses aiohttp to download concurrently; first attempts HEAD to
#              detect Accept-Ranges and resumes partially downloaded files.
# Change Summary:
#   - 1.0 initial implementation with per-file result dicts and logging integration.
# Inputs:
#   - list of URLs, output directory, concurrency, retry policy
# Outputs:
#   - list of dicts {url, path, ok, bytes, error}
###############################################################################

import os
import asyncio
from typing import List, Dict, Any
from urllib.parse import urlparse

from cbw_utils import labeled, trace_async, configure_logger, adapter_for, ensure_dirs

logger = configure_logger()
ad = adapter_for(logger, "downloader")

try:
    import aiohttp
except Exception:
    aiohttp = None
    ad.warning("aiohttp not installed; downloader will not function without it")

try:
    from tqdm import tqdm
    TQDM = True
except Exception:
    TQDM = False

class DownloadManager:
    def __init__(self, outdir: str = "./bulk_data", concurrency: int = 6, retries: int = 5):
        ensure_dirs(outdir)
        self.outdir = outdir
        self.concurrency = concurrency
        self.retries = retries
        self.logger = ad

    async def _head_info(self, session: "aiohttp.ClientSession", url: str) -> Dict[str, Any]:
        try:
            async with session.head(url, timeout=aiohttp.ClientTimeout(total=30), allow_redirects=True) as resp:
                cl = resp.headers.get("Content-Length")
                ar = resp.headers.get("Accept-Ranges", "")
                return {"status": resp.status, "size": int(cl) if cl and cl.isdigit() else None, "resumable": "bytes" in ar.lower()}
        except Exception:
            return {"status": None, "size": None, "resumable": False}

    async def _download_single(self, session: "aiohttp.ClientSession", url: str, dest: str) -> Dict[str, Any]:
        attempts = 0
        res = {"url": url, "path": dest, "ok": False, "bytes": 0, "error": None}
        while attempts <= self.retries:
            attempts += 1
            try:
                info = await self._head_info(session, url)
                resumable = info.get("resumable", False)
                existing = os.path.getsize(dest) if os.path.exists(dest) else 0
                headers = {}
                mode = "wb"
                if existing and resumable:
                    headers["Range"] = f"bytes={existing}-"
                    mode = "ab"
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=None)) as resp:
                    if resp.status >= 400:
                        raise Exception(f"HTTP {resp.status}")
                    cl = resp.headers.get("Content-Length")
                    total = int(cl) + (existing if mode == "ab" else 0) if cl and cl.isdigit() else None
                    written = existing
                    chunk = 1 << 16
                    if TQDM:
                        desc = os.path.basename(dest)
                        with open(dest, mode) as fh, tqdm(total=total, initial=existing, unit="B", unit_scale=True, unit_divisor=1024, desc=desc[:40], leave=False) as pbar:
                            async for data in resp.content.iter_chunked(chunk):
                                if not data:
                                    break
                                fh.write(data)
                                written += len(data)
                                pbar.update(len(data))
                    else:
                        with open(dest, mode) as fh:
                            async for data in resp.content.iter_chunked(chunk):
                                if not data:
                                    break
                                fh.write(data)
                                written += len(data)
                    res["ok"] = True
                    res["bytes"] = written
                    self.logger.info("Downloaded %s -> %s (%d bytes)", url, dest, written)
                    return res
            except Exception as e:
                res["error"] = str(e)
                self.logger.warning("Download attempt %d/%d failed for %s: %s", attempts, self.retries, url, e)
                await asyncio.sleep(min(30, 2 ** attempts))
        return res

    @labeled("downloader_download_all")
    def download_all(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Synchronous facade which runs the async downloader and returns a list of results.
        """
        if aiohttp is None:
            raise RuntimeError("aiohttp not installed: pip install aiohttp")
        async def runner():
            sem = asyncio.Semaphore(self.concurrency)
            connector = aiohttp.TCPConnector(limit_per_host=self.concurrency, limit=0)
            results = []
            async with aiohttp.ClientSession(connector=connector) as session:
                tasks = []
                for i, u in enumerate(urls):
                    filename = u.split("?")[0].rstrip("/").split("/")[-1] or f"file_{i}"
                    domain = urlparse(u).netloc.replace(":", "_")
                    dest_dir = os.path.join(self.outdir, domain)
                    ensure_dirs(dest_dir)
                    dest = os.path.join(dest_dir, filename)
                    async def sem_task(u=u, dest=dest):
                        async with sem:
                            return await self._download_single(session, u, dest)
                    tasks.append(asyncio.create_task(sem_task()))
                for fut in asyncio.as_completed(tasks):
                    r = await fut
                    results.append(r)
            return results
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(runner())