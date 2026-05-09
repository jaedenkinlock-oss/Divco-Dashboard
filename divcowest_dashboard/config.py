import os
from dotenv import load_dotenv

load_dotenv()

try:
    import streamlit as st
    if not os.getenv("FRED_API_KEY") and "FRED_API_KEY" in st.secrets:
        os.environ["FRED_API_KEY"] = st.secrets["FRED_API_KEY"]
except Exception:
    pass

# ── REIT Universe ──────────────────────────────────────────────────────────────

LIFE_SCIENCE_REITS: dict[str, str] = {
    "ARE":  "Alexandria Real Estate Equities",
}

PREMIER_OFFICE_REITS: dict[str, str] = {
    "BXP":  "Boston Properties",
    "VNO":  "Vornado Realty Trust",
    "SLG":  "SL Green Realty",
    "PGRE": "Paramount Group",
    "EQC":  "Equity Commonwealth",
}

WEST_COAST_OFFICE: dict[str, str] = {
    "KRC":  "Kilroy Realty",
}

SUN_BELT_OFFICE: dict[str, str] = {
    "HIW":  "Highwoods Properties",
    "PDM":  "Piedmont Office Realty",
    "CIO":  "City Office REIT",
    "DEA":  "Easterly Government Properties",
}

ALL_REITS: dict[str, str] = {
    **LIFE_SCIENCE_REITS,
    **PREMIER_OFFICE_REITS,
    **WEST_COAST_OFFICE,
    **SUN_BELT_OFFICE,
}

REIT_CATEGORIES: dict[str, str] = {
    **{t: "Life Science" for t in LIFE_SCIENCE_REITS},
    **{t: "Premier Office" for t in PREMIER_OFFICE_REITS},
    **{t: "West Coast Office" for t in WEST_COAST_OFFICE},
    **{t: "Sun Belt / Gov Office" for t in SUN_BELT_OFFICE},
}

# ── DivcoWest Target Innovation Markets ───────────────────────────────────────

DW_MARKETS: dict[str, list[str]] = {
    "tier_1": [
        "San Francisco Bay Area, CA",
        "Boston / Cambridge, MA",
        "Los Angeles, CA",
        "San Diego, CA",
    ],
    "tier_2": [
        "Seattle, WA",
        "Austin, TX",
        "Washington DC / Bethesda, MD",
        "New York, NY",
        "Raleigh-Durham, NC",
        "Nashville, TN",
    ],
    "tier_3": [
        "Denver, CO",
        "Miami, FL",
        "Chicago, IL",
    ],
}

# ── FRED Series ────────────────────────────────────────────────────────────────

FRED_SERIES: dict[str, str] = {
    "treasury_10y":   "GS10",
    "treasury_2y":    "GS2",
    "cpi_all":        "CPIAUCSL",
    "cpi_rent":       "CUSR0000SEHA",
    "vacancy_rental": "RRVRUSQ156N",
    "permits_nat":    "PERMIT",
    "unemployment":   "UNRATE",
}

# ── API Keys ───────────────────────────────────────────────────────────────────

FRED_API_KEY: str = os.getenv("FRED_API_KEY", "")

# ── Cache / Paths ──────────────────────────────────────────────────────────────

CACHE_DIR: str = "data/cache"
PROCESSED_DIR: str = "data/processed"
LOG_DIR: str = "logs"
CACHE_TTL_HOURS: int = 24

# ── Thresholds ─────────────────────────────────────────────────────────────────

AFFO_PAYOUT_YELLOW: float = 0.90
AFFO_PAYOUT_RED: float = 1.00
CAP_SPREAD_WARN_BPS: int = 150

# ── UI Colors — DivcoWest Institutional Palette ───────────────────────────────

DW_NAVY     = "#0F2040"   # Primary dark — deep navy
DW_DARK     = "#162840"   # Secondary dark
DW_MID      = "#6B7B8D"   # Muted slate
DW_LIGHT    = "#F5F7FA"   # Off-white page background
DW_BORDER   = "#CDD5E0"   # Blue-gray border
DW_STEEL    = "#2D6AA0"   # Accent blue (replaces gold)
DW_STEEL_LT = "#E8F0FA"   # Light accent background
DW_SLATE    = "#3A5A7A"   # Dark slate — secondary accent
DW_SLATE_LT = "#E8EFF7"   # Light slate background
DW_GREEN    = "#1E5C3A"   # Signal green
DW_GREEN_LT = "#E8F2EC"   # Light green
DW_RED      = "#8B2020"   # Signal red
DW_RED_LT   = "#F5E8E8"   # Light red
DW_AMBER    = "#7A5A1A"   # Amber / caution
DW_AMBER_LT = "#F5F0E0"   # Light amber

# Legacy aliases
DARK_BG      = DW_NAVY
CARD_BG      = DW_DARK
ACCENT_BLUE  = DW_STEEL
SIGNAL_GREEN = DW_GREEN
SIGNAL_RED   = DW_RED
TEXT_MUTED   = DW_MID
