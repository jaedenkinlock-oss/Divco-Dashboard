"""
yfinance fundamentals fetcher.

FFO note: True FFO requires SEC 10-K/10-Q filings (Phase 2 via edgar_fetcher).
Phase 1 proxy:  FFO_proxy = Net Income (TTM) + D&A (TTM)
All proxy metrics are tagged [est.] in downstream display.
"""

import time
from datetime import datetime, timezone
from typing import Optional
import numpy as np
import pandas as pd
import yfinance as yf

from config import ALL_REITS, REIT_CATEGORIES
from utils.cache import read_cache, write_cache
from utils.logger import get_logger

logger = get_logger(__name__)

CACHE_KEY = "reit_fundamentals"
FETCH_DELAY = 0.5   # seconds between tickers (rate limit courtesy)
MAX_RETRIES = 3
RETRY_DELAY = 2.0   # seconds


# ── Low-level helpers ──────────────────────────────────────────────────────────

def _retry(fn, *args, ticker: str, **kwargs):
    """Call fn(*args, **kwargs) with exponential back-off; return None on failure."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            wait = RETRY_DELAY * (2 ** (attempt - 1))
            logger.warning(
                '{"ticker": "%s", "attempt": %d, "error": "%s", "retry_in": %.1f}',
                ticker, attempt, exc, wait,
            )
            if attempt < MAX_RETRIES:
                time.sleep(wait)
    logger.error('{"ticker": "%s", "msg": "all retries exhausted"}', ticker)
    return None


def _safe_get(info: dict, *keys, default=None):
    for k in keys:
        v = info.get(k)
        if v is not None and v == v:  # not NaN
            return v
    return default


# ── TTM financial calculation ──────────────────────────────────────────────────

def _ttm_sum(df: Optional[pd.DataFrame], label: str) -> Optional[float]:
    """Sum the 4 most recent quarterly periods for a given line item."""
    if df is None or df.empty:
        return None
    row = None
    for candidate in [label, label.replace(" ", ""), label.lower()]:
        if candidate in df.index:
            row = df.loc[candidate]
            break
    if row is None:
        for idx in df.index:
            if label.lower() in str(idx).lower():
                row = df.loc[idx]
                break
    if row is None:
        return None
    vals = pd.to_numeric(row, errors="coerce").dropna()
    recent = vals.iloc[:4]
    return float(recent.sum()) if len(recent) > 0 else None


def _fetch_quarterly_data(ticker_obj: yf.Ticker, ticker: str) -> tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Return (quarterly_income_stmt, quarterly_cashflow) or (None, None) on failure."""
    income_q = _retry(lambda: ticker_obj.quarterly_income_stmt, ticker=ticker)
    cashflow_q = _retry(lambda: ticker_obj.quarterly_cashflow, ticker=ticker)
    return income_q, cashflow_q


# ── Per-ticker metric assembly ─────────────────────────────────────────────────

def _build_row(ticker: str, name: str, category: str) -> Optional[dict]:
    """Fetch all available fundamentals for one ticker. Returns None on hard failure."""
    t = yf.Ticker(ticker)

    info = _retry(lambda: t.info, ticker=ticker)
    if not info:
        logger.error('{"ticker": "%s", "msg": "info fetch failed, skipping"}', ticker)
        return None

    income_q, cashflow_q = _fetch_quarterly_data(t, ticker)

    # ── Price & market data ────────────────────────────────────────────────────
    price = _safe_get(info, "currentPrice", "regularMarketPrice", "previousClose")
    market_cap = _safe_get(info, "marketCap")
    shares_out = _safe_get(info, "sharesOutstanding")

    week52_high = _safe_get(info, "fiftyTwoWeekHigh")
    week52_low = _safe_get(info, "fiftyTwoWeekLow")
    pct_from_52w_high = (price / week52_high - 1) if (price and week52_high) else None

    # ── Dividend ───────────────────────────────────────────────────────────────
    div_yield = _safe_get(info, "dividendYield")       # decimal (e.g. 0.035)
    div_rate = _safe_get(info, "dividendRate")         # annual $ per share
    payout_ratio = _safe_get(info, "payoutRatio")      # vs EPS (proxy for AFFO payout)

    # ── Valuation ──────────────────────────────────────────────────────────────
    trailing_pe = _safe_get(info, "trailingPE")
    forward_pe = _safe_get(info, "forwardPE")
    trailing_eps = _safe_get(info, "trailingEps")
    forward_eps = _safe_get(info, "forwardEps")
    price_to_book = _safe_get(info, "priceToBook")
    book_value = _safe_get(info, "bookValue")

    # ── Balance sheet / leverage ───────────────────────────────────────────────
    total_debt = _safe_get(info, "totalDebt")
    total_cash = _safe_get(info, "totalCash")
    ebitda = _safe_get(info, "ebitda")
    net_debt = (total_debt - total_cash) if (total_debt and total_cash) else None
    net_debt_ebitda = (net_debt / ebitda) if (net_debt and ebitda and ebitda != 0) else None

    # ── Revenue ────────────────────────────────────────────────────────────────
    revenue_ttm = _safe_get(info, "totalRevenue")

    # ── FFO proxy (Phase 1 estimate from quarterly filings) ────────────────────
    net_income_ttm = _ttm_sum(income_q, "Net Income")
    da_ttm = _ttm_sum(cashflow_q, "Depreciation And Amortization")

    if da_ttm is None:
        da_ttm = _ttm_sum(cashflow_q, "Depreciation")

    ffo_proxy = None
    ffo_per_share = None
    p_ffo = None

    if net_income_ttm is not None and da_ttm is not None:
        ffo_proxy = net_income_ttm + da_ttm
        if shares_out and shares_out > 0:
            ffo_per_share = ffo_proxy / shares_out
            if price and ffo_per_share and ffo_per_share > 0:
                p_ffo = price / ffo_per_share

    row = {
        # Identity
        "ticker":           ticker,
        "name":             name,
        "category":         category,
        "fetched_at_utc":   datetime.now(timezone.utc).isoformat(timespec="seconds"),
        # Price & size
        "price":            price,
        "market_cap":       market_cap,
        "shares_out":       shares_out,
        "week52_high":      week52_high,
        "week52_low":       week52_low,
        "pct_from_52w_high": pct_from_52w_high,
        # Dividend
        "div_yield":        div_yield,
        "div_rate":         div_rate,
        "payout_ratio":     payout_ratio,
        # Valuation
        "trailing_pe":      trailing_pe,
        "forward_pe":       forward_pe,
        "trailing_eps":     trailing_eps,
        "forward_eps":      forward_eps,
        "price_to_book":    price_to_book,
        "book_value":       book_value,
        # Leverage
        "total_debt":       total_debt,
        "total_cash":       total_cash,
        "net_debt":         net_debt,
        "ebitda":           ebitda,
        "net_debt_ebitda":  net_debt_ebitda,
        # Revenue
        "revenue_ttm":      revenue_ttm,
        # FFO proxy (Phase 1 est.)
        "net_income_ttm":   net_income_ttm,
        "da_ttm":           da_ttm,
        "ffo_proxy":        ffo_proxy,       # Net Income + D&A
        "ffo_per_share":    ffo_per_share,   # [est.]
        "p_ffo":            p_ffo,           # [est.] — ground truth from EDGAR Phase 2
    }

    return row


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_all_fundamentals(
    tickers: Optional[dict[str, str]] = None,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Fetch fundamentals for all REIT tickers with daily parquet caching.

    Args:
        tickers: {ticker: name} dict. Defaults to config.ALL_REITS.
        force_refresh: skip cache and fetch fresh data.

    Returns:
        DataFrame indexed by ticker with all fundamental columns.
    """
    if tickers is None:
        tickers = ALL_REITS

    if not force_refresh:
        cached = read_cache(CACHE_KEY)
        if cached is not None:
            return cached

    logger.info("Fetching fundamentals for %d tickers…", len(tickers))
    rows = []
    errors = []

    for i, (ticker, name) in enumerate(tickers.items(), 1):
        logger.info("[%d/%d] %s — %s", i, len(tickers), ticker, name)
        category = REIT_CATEGORIES.get(ticker, "Other")

        try:
            row = _build_row(ticker, name, category)
            if row is not None:
                rows.append(row)
            else:
                errors.append(ticker)
        except Exception as exc:
            logger.error(
                '{"ticker": "%s", "msg": "unhandled error", "error": "%s"}',
                ticker, exc,
            )
            errors.append(ticker)

        if i < len(tickers):
            time.sleep(FETCH_DELAY)

    if errors:
        logger.warning(
            '{"msg": "tickers with fetch errors", "count": %d, "tickers": %s}',
            len(errors), errors,
        )

    if not rows:
        logger.error("No data fetched — returning empty DataFrame")
        return pd.DataFrame()

    df = pd.DataFrame(rows).set_index("ticker")
    write_cache(CACHE_KEY, df)

    logger.info("Fetch complete: %d/%d tickers succeeded", len(rows), len(tickers))
    return df


# ── CLI entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    df = fetch_all_fundamentals(force_refresh=True)
    cols = ["name", "price", "market_cap", "div_yield", "ffo_per_share", "p_ffo", "payout_ratio"]
    print(df[[c for c in cols if c in df.columns]].to_string())
    print(f"\n✓ {len(df)} tickers cached to data/cache/")
