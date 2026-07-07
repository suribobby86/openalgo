"""POST /api/v2/optionchain — async wrapper around existing service layer."""

from __future__ import annotations

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from fastapi import APIRouter, HTTPException

from fastapi_api.schemas.optionchain import OptionChainRequest
from services.option_chain_service import get_option_chain
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["optionchain"])
_executor = ThreadPoolExecutor(max_workers=int(os.getenv("FASTAPI_CHAIN_WORKERS", "4")))


async def _fetch_chain(payload: OptionChainRequest) -> tuple[bool, dict[str, Any], int]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _executor,
        lambda: get_option_chain(
            underlying=payload.underlying,
            exchange=payload.exchange,
            expiry_date=payload.expiry_date,
            strike_count=payload.strike_count,
            api_key=payload.apikey,
        ),
    )


@router.post("/optionchain")
async def option_chain(body: OptionChainRequest) -> dict[str, Any]:
    logger.info(
        "FastAPI optionchain: underlying=%s exchange=%s expiry=%s strikes=%s",
        body.underlying,
        body.exchange,
        body.expiry_date,
        body.strike_count,
    )
    success, response, status_code = await _fetch_chain(body)
    if not success:
        raise HTTPException(status_code=status_code, detail=response)
    return response