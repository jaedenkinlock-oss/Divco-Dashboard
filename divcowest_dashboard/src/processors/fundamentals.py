"""
Apply business logic and flag rules to raw fundamentals DataFrame.
Moghadam layer: AFFO payout thresholds, P/FFO context, leverage flags.
"""

import pandas as pd
from config import AFFO_PAYOUT_YELLOW, AFFO_PAYOUT_RED


def build_fundamentals_table(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich raw fundamentals DataFrame with flag columns and display-ready fields.

    Flag columns (values: "ok", "yellow", "red"):
      - payout_flag   — AFFO payout ratio thresholds
      - leverage_flag — Net Debt/EBITDA > 7x = yellow, > 9x = red
    """
    out = df.copy()

    # ── Payout ratio flags ─────────────────────────────────────────────────────
    def _payout_flag(ratio):
        if pd.isna(ratio):
            return "na"
        if ratio > AFFO_PAYOUT_RED:
            return "red"
        if ratio > AFFO_PAYOUT_YELLOW:
            return "yellow"
        return "ok"

    out["payout_flag"] = out["payout_ratio"].apply(_payout_flag)

    # ── Leverage flags ─────────────────────────────────────────────────────────
    def _leverage_flag(nd_ebitda):
        if pd.isna(nd_ebitda):
            return "na"
        if nd_ebitda > 9:
            return "red"
        if nd_ebitda > 7:
            return "yellow"
        return "ok"

    out["leverage_flag"] = out["net_debt_ebitda"].apply(_leverage_flag)

    # ── P/FFO context (placeholder — 5Y average from EDGAR in Phase 2) ────────
    out["p_ffo_vs_avg"] = None   # will be: (p_ffo / 5y_avg_p_ffo) - 1

    # ── Sort: life science first, then by market cap desc ────────────────────
    cat_order = {"Life Science": 0, "Premier Office": 1, "West Coast Office": 2, "Sun Belt / Gov Office": 3}
    out["_cat_ord"] = out["category"].map(cat_order).fillna(3)
    out = out.sort_values(["_cat_ord", "market_cap"], ascending=[True, False])
    out = out.drop(columns=["_cat_ord"])

    return out
