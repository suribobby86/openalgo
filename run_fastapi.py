#!/usr/bin/env python3
"""Launch OpenAlgo FastAPI v2 sidecar (default port 5001)."""

from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    host = os.getenv("FASTAPI_HOST", "127.0.0.1")
    port = int(os.getenv("FASTAPI_PORT", "5001"))
    reload = os.getenv("FASTAPI_RELOAD", "false").lower() in ("1", "true", "yes")
    uvicorn.run("fastapi_api.app:app", host=host, port=port, reload=reload, log_level="info")