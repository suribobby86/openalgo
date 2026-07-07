"""
Gzip compression + ETag for large JSON API responses (option chain first).

Stdlib only — no flask-compress dependency.
"""

from __future__ import annotations

import gzip
import hashlib
import os
from flask import Request, Response, request

from utils.logging import get_logger

logger = get_logger(__name__)

MIN_BYTES = int(os.getenv("API_COMPRESS_MIN_BYTES", "1024"))
COMPRESS_LEVEL = int(os.getenv("API_GZIP_LEVEL", "6"))
_DEFAULT_PREFIXES = "/api/v1/optionchain,/api/v1/"
_PREFIXES = tuple(
    p.strip()
    for p in os.getenv("API_COMPRESS_PATHS", _DEFAULT_PREFIXES).split(",")
    if p.strip()
)


def _path_matches(path: str) -> bool:
    normalized = path.rstrip("/") + "/"
    for prefix in _PREFIXES:
        p = prefix if prefix.endswith("/") else prefix + "/"
        if normalized.startswith(p) or path.rstrip("/") == prefix.rstrip("/"):
            return True
    return False


def _accepts_gzip(req: Request) -> bool:
    return "gzip" in (req.headers.get("Accept-Encoding") or "").lower()


def init_api_compression(app) -> None:
    """Register after_request hook for gzip + ETag on configured API paths."""

    @app.after_request
    def compress_api_response(response: Response) -> Response:
        if request.method not in ("GET", "POST"):
            return response
        if not _path_matches(request.path):
            return response
        if response.status_code != 200:
            return response
        if response.headers.get("Content-Encoding"):
            return response
        if response.mimetype not in ("application/json", "application/json; charset=utf-8", None):
            if not str(response.content_type or "").startswith("application/json"):
                return response

        raw = response.get_data()
        if len(raw) < MIN_BYTES:
            return response

        etag = f'"{hashlib.md5(raw, usedforsecurity=False).hexdigest()}"'
        response.headers["ETag"] = etag
        if_none = request.headers.get("If-None-Match")
        if if_none and if_none == etag:
            return Response(status=304, headers={"ETag": etag, "Vary": "Accept-Encoding"})

        if not _accepts_gzip(request):
            return response

        compressed = gzip.compress(raw, compresslevel=COMPRESS_LEVEL)
        if len(compressed) >= len(raw):
            return response

        response.set_data(compressed)
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Content-Length"] = str(len(compressed))
        response.headers["Vary"] = "Accept-Encoding"
        logger.debug(
            "Compressed %s %s: %d -> %d bytes",
            request.method,
            request.path,
            len(raw),
            len(compressed),
        )
        return response

    logger.info("API response compression enabled for prefixes: %s", _PREFIXES)