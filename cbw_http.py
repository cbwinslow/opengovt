###############################################################################
# Name:        cbw_http.py
# Date:        2025-10-02
# Script Name: cbw_http.py
# Version:     1.0
# Log Summary: HTTP control server to expose /status, /start, /retry, /metrics.
# Description: Provides an aiohttp server so the Go TUI can control and query the pipeline.
# Change Summary:
#   - 1.0 initial control server that delegates to Pipeline methods.
# Inputs:
#   - pipeline instance exposing run_once_async and retry_failed_async
# Outputs:
#   - HTTP endpoints for control and metrics
###############################################################################

from typing import Optional
from cbw_utils import labeled, configure_logger, adapter_for

logger = configure_logger()
ad = adapter_for(logger, "http")

try:
    from aiohttp import web
    from prometheus_client import generate_latest
except Exception:
    web = None
    generate_latest = None
    ad.warning("aiohttp or prometheus_client missing; HTTP server or /metrics disabled")

class HTTPControlServer:
    def __init__(self, pipeline, host: str = "0.0.0.0", port: int = 8080):
        self.pipeline = pipeline
        self.host = host
        self.port = port
        self.app = None
        self.runner = None

    @labeled("http_make_app")
    def make_app(self):
        if web is None:
            raise RuntimeError("aiohttp required to run HTTP server")
        app = web.Application()
        app.router.add_get("/status", self.handle_status)
        app.router.add_post("/start", self.handle_start)
        app.router.add_post("/retry", self.handle_retry)
        app.router.add_get("/health", self.handle_health)
        if generate_latest is not None:
            async def metrics(req):
                data = generate_latest()
                return web.Response(body=data, content_type="text/plain; version=0.0.4")
            app.router.add_get("/metrics", metrics)
        self.app = app
        return app

    async def handle_status(self, request):
        data = {"last_discovery": getattr(self.pipeline, "last_discovery_ts", None), "retry_count": len(self.pipeline.retry_mgr.data.get("failures", []))}
        return web.json_response(data)

    async def handle_start(self, request):
        # schedule an async pipeline run (download+extract)
        import asyncio
        asyncio.create_task(self.pipeline.run_once_async(download=True, extract=True, postprocess=False))
        return web.json_response({"status": "started"})

    async def handle_retry(self, request):
        import asyncio
        asyncio.create_task(self.pipeline.retry_failed_async())
        return web.json_response({"status": "retry_started"})

    async def handle_health(self, request):
        return web.Response(text="ok")

    async def start(self):
        if web is None:
            raise RuntimeError("aiohttp required to run HTTP server")
        app = self.make_app()
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()
        ad.info("HTTP server started at http://%s:%d", self.host, self.port)

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
            ad.info("HTTP server stopped")