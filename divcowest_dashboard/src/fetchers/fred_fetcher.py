"""
FRED macro data fetcher — live implementation.
Uses fredapi with FRED_API_KEY from .env. 4-hour parquet cache.
"""
from typing import Optional
import pandas as pd
from fredapi import Fred

from config import FRED_API_KEY
from utils.cache import read_cache, write_cache
from utils.logger import get_logger

logger = get_logger(__name__)
_MACRO_TTL = 4  # hours — refresh up to 6× per day


def _fred() -> Fred:
    if not FRED_API_KEY:
        raise ValueError("FRED_API_KEY not set. Add it to .env")
    return Fred(api_key=FRED_API_KEY)


def fetch_series(series_id: str, obs_start: str = "2019-01-01") -> pd.Series:
    """Fetch a FRED series; read from 4-hour parquet cache if fresh."""
    key = f"fred_{series_id.lower()}"
    cached = read_cache(key, ttl_hours=_MACRO_TTL)
    if cached is not None and not cached.empty:
        col = cached.columns[0]
        s = cached[col].dropna()
        s.index = pd.to_datetime(s.index)
        return s

    fred = _fred()
    s = fred.get_series(series_id, observation_start=obs_start).dropna()
    s.name = series_id
    write_cache(key, s.to_frame())
    logger.info("FRED fetched: %s (%d observations)", series_id, len(s))
    return s


def fetch_all_macro() -> dict:
    """
    Fetch all macro series. Returns dict: key -> pd.Series | None.
    Each series fails independently so one bad key never blocks the rest.
    """
    _SERIES = {
        "gs10":        ("GS10",      "2019-01-01"),
        "gs2":         ("GS2",       "2019-01-01"),
        "cpi":         ("CPIAUCSL",  "2019-01-01"),
        "permits":     ("PERMIT",    "2019-01-01"),
        "unemployment":("UNRATE",    "2019-01-01"),
    }
    out = {}
    for key, (sid, start) in _SERIES.items():
        try:
            out[key] = fetch_series(sid, obs_start=start)
        except Exception as exc:
            logger.error("FRED fetch failed — %s (%s): %s", key, sid, exc)
            out[key] = None
    return out
