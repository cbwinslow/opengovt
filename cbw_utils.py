###############################################################################
# Name:        cbw_utils.py
# Date:        2025-10-02
# Script Name: cbw_utils.py
# Version:     1.0
# Log Summary: Logging, decorators, JSON helpers, housekeeping utilities.
# Description: Centralized logging configuration, diagnostic decorators (entry/exit/exception),
#              safe JSON read/write, directory helpers, rotating logfiles, and small helpers
#              used across the cbw_* modules.
# Change Summary:
#   - 1.0 initial split-out from earlier monolith; adds labeled logging, async trace,
#         atomic JSON writes, and housekeeping utilities.
# Inputs:
#   - Environment variables: CONGRESS_LOG_DIR (optional)
#   - Called by other cbw_ modules
# Outputs:
#   - Configured logger and decorator utilities for diagnostic logging
###############################################################################

import os
import sys
import json
import shutil
import functools
import traceback
import logging
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from typing import Any, Callable, Optional

# Locate or create log directory
LOG_DIR = os.getenv("CONGRESS_LOG_DIR", "./logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"cbw_congress_{datetime.utcnow().strftime('%Y%m%d')}.log")

def configure_logger(name: str = "cbw_congress", level: int = logging.INFO) -> logging.Logger:
    """
    Configure and return a logger with rotating file handler and console handler.
    The logger is safe to call multiple times; handlers are added once.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not getattr(logger, "_cbw_configured", False):
        fmt = "%(asctime)s %(levelname)s %(label)s %(message)s"
        formatter = logging.Formatter(fmt)
        fh = RotatingFileHandler(LOG_FILE, maxBytes=20 * 1024 * 1024, backupCount=7)
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        logger._cbw_configured = True
    return logger

def adapter_for(logger: logging.Logger, label: str = "init") -> logging.LoggerAdapter:
    """
    Return a LoggerAdapter that injects a 'label' key into log records so
    formatters can include it. Example: adapter_for(logger, "discovery")
    """
    return logging.LoggerAdapter(logger, {"label": f"[{label}]"})

def save_json_atomic(path: str, data: Any):
    """
    Atomically write JSON to disk (write tmp file then move). Raises on failure.
    """
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def load_json_safe(path: str) -> Optional[Any]:
    """
    Load JSON from disk. If corrupted, move corrupt file aside and return None.
    """
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        bkp = f"{path}.corrupt.{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        shutil.move(path, bkp)
        logger = configure_logger()
        adapter_for(logger, "utils").warning("Corrupt JSON moved from %s to %s", path, bkp)
        return None

def ensure_dirs(*paths: str):
    """
    Ensure directories exist; create them if they don't.
    """
    for p in paths:
        os.makedirs(p, exist_ok=True)

def labeled(label: str):
    """
    Decorator that logs function entry, exit, duration, and exceptions for sync functions.

    Example:
      @labeled("discovery")
      def run(...): ...
    """
    def deco(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            logger = configure_logger()
            adap = adapter_for(logger, label)
            adap.info("ENTER %s args=%d kwargs=%s", fn.__name__, len(args), list(kwargs.keys()))
            start = datetime.utcnow()
            try:
                res = fn(*args, **kwargs)
                dur = (datetime.utcnow() - start).total_seconds()
                adap.info("EXIT %s duration=%.3fs", fn.__name__, dur)
                return res
            except Exception as e:
                adap.exception("EXCEPTION %s: %s\n%s", fn.__name__, e, traceback.format_exc())
                raise
        return wrapper
    return deco

def trace_async(label: str):
    """
    Decorator for async functions to add labeled entry/exit and exception logging.
    """
    def deco(fn: Callable):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            logger = configure_logger()
            adap = adapter_for(logger, label)
            adap.info("ENTER async %s", fn.__name__)
            start = datetime.utcnow()
            try:
                res = await fn(*args, **kwargs)
                dur = (datetime.utcnow() - start).total_seconds()
                adap.info("EXIT async %s duration=%.3fs", fn.__name__, dur)
                return res
            except Exception as e:
                adap.exception("EXCEPTION async %s: %s\n%s", fn.__name__, e, traceback.format_exc())
                raise
        return wrapper
    return deco