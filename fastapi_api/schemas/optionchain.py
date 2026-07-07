"""Pydantic models mirroring restx_api OptionChainSchema."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OptionChainRequest(BaseModel):
    apikey: str = Field(..., min_length=1, max_length=256)
    underlying: str
    exchange: str
    expiry_date: str
    strike_count: int | None = Field(default=10, ge=1, le=100)