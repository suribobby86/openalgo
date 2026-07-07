"""
OpenAlgo FastAPI application (v2 skeleton).

Run alongside Flask (port 5000) on a separate port:

    uvicorn fastapi_api.app:app --host 127.0.0.1 --port 5001 --reload

Or: python run_fastapi.py
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from fastapi_api.routers import optionchain as optionchain_router
from utils.env_check import load_and_check_env_variables

load_and_check_env_variables()

app = FastAPI(
    title="OpenAlgo API v2",
    version="2.0.0-skeleton",
    description="Async migration path for OpenAlgo REST endpoints.",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(GZipMiddleware, minimum_size=int(os.getenv("API_COMPRESS_MIN_BYTES", "1024")))
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("FASTAPI_CORS_ORIGINS", "http://127.0.0.1:5000,http://localhost:5000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(optionchain_router.router, prefix="/api/v2")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "api": "fastapi-v2-skeleton"}