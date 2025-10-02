###############################################################################
# Name:        Utilities & Logging Helpers
# Date:        2025-10-02
# Script Name: utils.py
# Version:     1.0
# Log Summary: Logging, decorators, housekeeping, rotation, and diagnostic helpers.
# Description: Provides logging configuration, decorators for entry/exit/exception
#              labeling, and helper functions for file housekeeping.
# Change Summary:
#   - 1.0 initial utilities: logger, entry/exit decorator, error decorator,
#        json save/load helpers, rotating file handler setup.
# Inputs: None (functions accept parameters)
# Outputs: Configured logger, utility functions used by pipeline modules.
###############################################################################

import os
import json
import logging
import functools
import traceback
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Callable, Any, Optional

LOG_DIR = os.getenv("CONGRESS_LOG_DIR", "./logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, f"congress_pipeline_{datetime.utcnow().strftime('%Y%m%d')}.log")

# Configure root logger with rotating file handler
def configure_logger(name: str = "congress", level: int = logging.INFO, json_logs: bool = False) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    # Avoid duplicate handlers on repeated configure
    if not logger.handlers:
        fmt = "%(asctime)s [%(levelname)s] %(label)s %(message)s"
        handler = RotatingFileHandler(LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=10)
        handler.setLevel(level)
        formatter = logging.Formatter(fmt)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        # console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    # add a default adapter so we can attach labels in logs
    return logging.LoggerAdapter(logger, {"label": "[init]"})

# Decorators for function entry/exit and error logging
def labeled(label: str):
    """
    Decorator factory that adds a static label to logs inside the decorated function.
    """

    def deco(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            logger = configure_logger()
            adapter = logging.LoggerAdapter(logger.logger, {"label": f"[{label}]"})
            adapter.info(f"ENTER: {fn.__name__}() args={len(args)} kwargs={list(kwargs.keys())}")
            start = datetime.utcnow()
            try:
                result = fn(*args, **kwargs)
                duration = (datetime.utcnow() - start).total_seconds()
                adapter.info(f"EXIT: {fn.__name__}() duration={duration:.3f}s")
                return result
            except Exception as e:
                adapter.exception(f"EXCEPTION in {fn.__name__}: {e}\n{traceback.format_exc()}")
                raise
        return wrapper
    return deco

def trace_async(label: str):
    """Decorator for async functions to add labeled logging and timing."""
    def deco(fn: Callable):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            logger = configure_logger()
            adapter = logging.LoggerAdapter(logger.logger, {"label": f"[{label}]"})
            adapter.info(f"ENTER async: {fn.__name__}()")
            start = datetime.utcnow()
            try:
                result = await fn(*args, **kwargs)
                dur = (datetime.utcnow() - start).total_seconds()
                adapter.info(f"EXIT async: {fn.__name__}() duration={dur:.3f}s")
                return result
            except Exception as e:
                adapter.exception(f"EXCEPTION async {fn.__name__}: {e}\n{traceback.format_exc()}")
                raise
        return wrapper
    return deco

# Simple JSON helpers with safe write
def save_json_atomic(path: str, data: Any):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def load_json_safe(path: str) -> Optional[Any]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            # Corrupt json: backup and return None
            backup = path + ".corrupt." + datetime.utcnow().strftime("%Y%m%d%H%M%S")
            os.rename(path, backup)
            return None

# Housekeeping helpers
@labeled("housekeeping")
def rotate_logs(keep_days: int = 30):
    """
    Simple housekeeping that removes log files older than keep_days in LOG_DIR.
    """
    now = datetime.utcnow()
    for fname in os.listdir(LOG_DIR):
        path = os.path.join(LOG_DIR, fname)
        try:
            mtime = datetime.utcfromtimestamp(os.path.getmtime(path))
            if (now - mtime).days > keep_days:
                os.remove(path)
        except Exception:
            pass

@labeled("housekeeping")
def ensure_dirs(*dirs):
    for d in dirs:
        os.makedirs(d, exist_ok=True)