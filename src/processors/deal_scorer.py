"""
DivcoWest innovation economy deal scoring engine — 8 criteria, 100 points.
"""
from dataclasses import dataclass
from typing import Optional

TREASURY_10Y_REF: float = 4.30

MARKET_DATA: dict[str, dict] = {
    "San Francisco Bay Area, CA": {
        "tier": 1, "dw_presence": 95, "supply_risk": "Low",
        "market_vacancy": 21.0, "asking_rent_psf": 73.0, "rent_growth": -3.0,
        "dw_note": "DivcoWest home market; Mission Bay campus is flagship; overall office vacancy 21%+ but lab/life science submarkets outperform — Class A asking rent $73/SF (IPG Q1 2026)",
    },
    "Boston / Cambridge, MA": {
        "tier": 1, "dw_presence": 90, "supply_risk": "Moderate",
        "market_vacancy": 12.5, "asking_rent_psf": 85.0, "rent_growth": 0.0,
        "dw_note": "Kendall Square — tightest lab market in the US; MIT and Broad Institute anchor demand; Kendall Square lab $85–120/SF vs. downtown Boston Class A $78/SF (CommercialCafe Q1 2026)",
    },
    "Los Angeles, CA": {
        "tier": 1, "dw_presence": 80, "supply_risk": "Low",
        "market_vacancy": 18.0, "asking_rent_psf": 52.0, "rent_growth": -2.0,
        "dw_note": "Silicon Beach (Playa Vista, Culver City); Google, Amazon, Snap anchor demand; Class A asking rent $52/SF (CommercialCafe Q1 2026)",
    },
    "San Diego, CA": {
        "tier": 1, "dw_presence": 75, "supply_risk": "Low",
        "market_vacancy": 15.0, "asking_rent_psf": 52.0, "rent_growth": -1.0,
        "dw_note": "Torrey Pines / UTC life science cluster; Illumina, Qualcomm, biotech pipeline anchor; Class A asking rent $52/SF (CommercialCafe Q1 2026)",
    },
    "Seattle, WA": {
        "tier": 2, "dw_presence": 70, "supply_risk": "Moderate",
        "market_vacancy": 23.0, "asking_rent_psf": 38.0, "rent_growth": -4.0,
        "dw_note": "South Lake Union / Bellevue; Amazon and Microsoft HQs create durable tech tenant demand; Class A asking rent $38–41/SF (CommercialCafe Q1 2026); vacancy elevated at 23%+",
    },
    "Austin, TX": {
        "tier": 2, "dw_presence": 65, "supply_risk": "High",
        "market_vacancy": 26.0, "asking_rent_psf": 46.0, "rent_growth": -1.0,
        "dw_note": "Strategic priority market — Domain NORTHSIDE corridor, UT Dell Medical School life science build-out, Apple/Oracle/Tesla anchors; trough acquisition window open 2025–26; Class A asking rent $46/SF (CommercialCafe 2026)",
    },
    "Washington DC / Bethesda, MD": {
        "tier": 2, "dw_presence": 65, "supply_risk": "Low",
        "market_vacancy": 10.5, "asking_rent_psf": 60.0, "rent_growth": 0.0,
        "dw_note": "NIH campus and Bethesda BioPark; government R&D funding provides recession-resistant demand; Class A asking rent $60/SF (CommercialCafe Q1 2026)",
    },
    "New York, NY": {
        "tier": 2, "dw_presence": 55, "supply_risk": "Low",
        "market_vacancy": 13.0, "asking_rent_psf": 83.0, "rent_growth": 1.0,
        "dw_note": "Midtown South / Hudson Yards; life science emerging in Kip's Bay and Alexandria Center; Manhattan Class A $83/SF (Cushman & Wakefield Q1 2026); trophy Midtown South tightening",
    },
    "Raleigh-Durham, NC": {
        "tier": 2, "dw_presence": 45, "supply_risk": "Moderate",
        "market_vacancy": 11.0, "asking_rent_psf": 38.0, "rent_growth": 0.0,
        "dw_note": "Research Triangle Park (300+ companies, 65K+ employees); Apple and Google expanding; Class A asking rent $38/SF (CommercialCafe Q1 2026); vacancy improved to 11%",
    },
    "Nashville, TN": {
        "tier": 2, "dw_presence": 35, "supply_risk": "Moderate",
        "market_vacancy": 20.0, "asking_rent_psf": 35.0, "rent_growth": -2.5,
        "dw_note": "Oracle HQ, Amazon HQ2 expansion; healthcare economy (HCA, Vanderbilt) creates life science opportunity; Class A asking rent $35/SF (CommercialCafe Q1 2026)",
    },
    "Denver, CO": {
        "tier": 3, "dw_presence": 25, "supply_risk": "Moderate",
        "market_vacancy": 21.0, "asking_rent_psf": 36.0, "rent_growth": -3.0,
        "dw_note": "Fitzsimons life science campus; aerospace and energy sector expanding; Class A asking rent $36/SF (Q1 2026)",
    },
    "Miami, FL": {
        "tier": 3, "dw_presence": 20, "supply_risk": "Low",
        "market_vacancy": 13.0, "asking_rent_psf": 60.0, "rent_growth": 4.0,
        "dw_note": "Wynwood tech corridor and Brickell financial cluster; Miami Tech Week validating migration; strongest YoY rent growth in the US at +4.0% (JLL Q1 2026); Class A asking rent $60/SF",
    },
    "Chicago, IL": {
        "tier": 3, "dw_presence": 20, "supply_risk": "Low",
        "market_vacancy": 22.0, "asking_rent_psf": 44.0, "rent_growth": -1.5,
        "dw_note": "Fulton Market tech hub and Goose Island life science corridor; Chicago Quantum Exchange anchor; Class A asking rent $44/SF (CommercialCafe Q1 2026)",
    },
}


@dataclass
class Criterion:
    name: str
    points_earned: float
    points_max: float
    note: str
    status: str  # "strength" | "caution" | "neutral"


def score_deal(
    market: str,
    asset_class: str,
    sqft: int,
    year_built: int,
    asking_price_m: float,
    noi_k: Optional[float],
    cap_rate_pct: float,
    inplace_rent_psf: float,
    market_rent_psf: float,
    vacancy_pct: float,
    walt_years: float,
    treasury_rate: float = TREASURY_10Y_REF,
) -> tuple[float, list[Criterion], str, str]:

    md = MARKET_DATA.get(market, {})
    criteria: list[Criterion] = []
    total = 0.0

    # ── 1. Innovation Cluster Fit — 20 pts ────────────────────────────────────
    tier = md.get("tier", 0)
    tier_pts = {1: 20, 2: 14, 3: 7}.get(tier, 0)
    tier_note = {
        1: f"Tier 1 Innovation Core — maximum cluster fit",
        2: f"Tier 2 Growth Market — solid but below core cluster density",
        3: f"Tier 3 Expansion Watch — early-stage positioning",
        0: "Outside DivcoWest target markets — no cluster premium",
    }[tier if tier in (1, 2, 3) else 0]
    criteria.append(Criterion("Innovation Cluster Fit", tier_pts, 20, tier_note,
                               "strength" if tier_pts >= 14 else "caution" if tier_pts >= 7 else "caution"))
    total += tier_pts

    # ── 2. DivcoWest Market Presence — 15 pts ────────────────────────────────
    pres = md.get("dw_presence", 0)
    pres_pts = round(pres / 100 * 15, 1)
    criteria.append(Criterion(
        "DivcoWest Market Presence", pres_pts, 15,
        f"{pres}/100 operational footprint — {md.get('dw_note', '—')}",
        "strength" if pres >= 70 else "neutral" if pres >= 40 else "caution",
    ))
    total += pres_pts

    # ── 3. Cap Rate vs. 10Y Treasury — 15 pts ───────────────────────────────
    spread_bps = (cap_rate_pct - treasury_rate) * 100
    if spread_bps >= 175:
        cap_pts, cap_note, cap_st = 15, f"{spread_bps:.0f}bps spread — compelling premium over risk-free", "strength"
    elif spread_bps >= 100:
        cap_pts, cap_note, cap_st = 10, f"{spread_bps:.0f}bps spread — adequate; discipline required at current rates", "neutral"
    elif spread_bps >= 0:
        cap_pts, cap_note, cap_st = 5, f"{spread_bps:.0f}bps spread — thin; limited cushion against rate volatility", "caution"
    else:
        cap_pts, cap_note, cap_st = 0, f"Negative spread ({spread_bps:.0f}bps) — cap rate below risk-free rate", "caution"
    criteria.append(Criterion("Cap Rate vs. 10Y Treasury", cap_pts, 15, cap_note, cap_st))
    total += cap_pts

    # ── 4. Mark-to-Market / Lease Rollover — 15 pts ─────────────────────────
    if inplace_rent_psf > 0:
        mtm = (market_rent_psf - inplace_rent_psf) / inplace_rent_psf * 100
    else:
        mtm = 0.0
    if mtm >= 15:
        mtm_pts, mtm_note, mtm_st = 15, f"{mtm:.1f}% below-market in-place rents — strong rollover upside at expiry", "strength"
    elif mtm >= 8:
        mtm_pts, mtm_note, mtm_st = 10, f"{mtm:.1f}% mark-to-market gap — meaningful but moderate rollover opportunity", "strength"
    elif mtm >= 0:
        mtm_pts, mtm_note, mtm_st = 5, f"{mtm:.1f}% gap — limited near-term lease rollover upside", "neutral"
    else:
        mtm_pts, mtm_note, mtm_st = 0, f"In-place rents above market ({mtm:.1f}%) — rollover risk on next expiry", "caution"
    criteria.append(Criterion("Mark-to-Market / Rollover", mtm_pts, 15, mtm_note, mtm_st))
    total += mtm_pts

    # ── 5. Occupancy vs. Market — 10 pts ────────────────────────────────────
    mkt_vac = md.get("market_vacancy", 15.0)
    occ_pct = 100.0 - vacancy_pct
    delta = vacancy_pct - mkt_vac
    if delta >= 5:
        occ_pts, occ_note, occ_st = 10, f"Property {vacancy_pct:.1f}% vacant vs. {mkt_vac:.1f}% market — deep occupancy recovery opportunity", "strength"
    elif delta >= 0:
        occ_pts, occ_note, occ_st = 7, f"Property {vacancy_pct:.1f}% vacant vs. {mkt_vac:.1f}% market — modest recovery upside", "neutral"
    elif delta >= -3:
        occ_pts, occ_note, occ_st = 4, f"Property in line with market ({vacancy_pct:.1f}% vs {mkt_vac:.1f}%) — limited occupancy upside", "neutral"
    else:
        occ_pts, occ_note, occ_st = 1, f"Property outperforming market ({vacancy_pct:.1f}% vs {mkt_vac:.1f}%) — fully stabilized, less operational upside", "caution"
    criteria.append(Criterion("Occupancy vs. Market", occ_pts, 10, occ_note, occ_st))
    total += occ_pts

    # ── 6. Asset Vintage / Lab Conversion Potential — 10 pts ────────────────
    if 1985 <= year_built <= 2010:
        vint_pts, vint_note, vint_st = 10, f"{year_built} vintage — ideal conversion window; structural floor-to-floor height and column spacing typically supports lab conversion", "strength"
    elif 2011 <= year_built <= 2018:
        vint_pts, vint_note, vint_st = 7, f"{year_built} vintage — modern but conversion depends on mechanical/HVAC capacity; spec suite work more likely than full lab", "neutral"
    elif year_built > 2018:
        vint_pts, vint_note, vint_st = 4, f"{year_built} vintage — newer asset; value-add limited to leasing strategy and amenity repositioning", "neutral"
    else:
        vint_pts, vint_note, vint_st = 5, f"Pre-1985 vintage ({year_built}) — deep value; conversion feasibility requires structural assessment", "caution"
    criteria.append(Criterion("Vintage / Conversion Potential", vint_pts, 10, vint_note, vint_st))
    total += vint_pts

    # ── 7. Supply Pipeline Risk — 10 pts ─────────────────────────────────────
    supply_risk = md.get("supply_risk", "Moderate")
    supply_pts = {"Low": 10, "Moderate": 6, "High": 2}.get(supply_risk, 6)
    supply_note = {
        "Low":      "Low pipeline risk — limited new competitive supply in this submarket",
        "Moderate": "Moderate pipeline risk — manageable new supply; underwrite conservative lease-up",
        "High":     "Elevated pipeline risk — significant new supply competing for same tenant base",
    }.get(supply_risk, "—")
    criteria.append(Criterion("Supply Pipeline Risk", supply_pts, 10, supply_note,
                               "strength" if supply_pts >= 8 else "neutral" if supply_pts >= 5 else "caution"))
    total += supply_pts

    # ── 8. Asset Scale / WALT — 5 pts ───────────────────────────────────────
    if walt_years >= 7:
        walt_pts, walt_note = 5, f"{walt_years:.1f}yr WALT — long-term income security; strong tenant commitment"
    elif walt_years >= 4:
        walt_pts, walt_note = 3, f"{walt_years:.1f}yr WALT — adequate; near-term rollover manageable"
    elif walt_years >= 2:
        walt_pts, walt_note = 2, f"{walt_years:.1f}yr WALT — short; rollover risk elevated, lease-up assumption required in underwriting"
    else:
        walt_pts, walt_note = 0, f"{walt_years:.1f}yr WALT — very short; significant near-term leasing risk"
    walt_st = "strength" if walt_pts >= 4 else "neutral" if walt_pts >= 2 else "caution"

    scale_pts = min(walt_pts, 5)
    criteria.append(Criterion("WALT / Tenant Commitment", scale_pts, 5, walt_note, walt_st))
    total += scale_pts

    # ── Recommendation ────────────────────────────────────────────────────────
    total = round(total, 1)
    if total >= 75:
        rec = "Advance to Due Diligence"
        rec_detail = "Strong cluster fit and financial fundamentals. Recommend full underwriting, tenant roll schedule review, and physical due diligence."
    elif total >= 55:
        rec = "Conditional Review"
        rec_detail = "Mixed signals — worth advancing with specific conditions addressed. Key sensitivities should be stress-tested before IC submission."
    elif total >= 35:
        rec = "Monitor — Do Not Pursue Now"
        rec_detail = "Below DivcoWest acquisition threshold at current terms. Re-evaluate if pricing adjusts or market conditions improve."
    else:
        rec = "Pass"
        rec_detail = "Does not meet DivcoWest innovation economy acquisition criteria. Pass at current market, pricing, and asset profile."

    return total, criteria, rec, rec_detail
