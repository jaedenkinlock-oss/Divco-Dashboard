import sys, os
_root = os.path.dirname(os.path.abspath(__file__))
for _p in (_root, os.path.join(_root, "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import streamlit as st
from datetime import datetime, timezone
import pandas as pd
import plotly.graph_objects as go

from config import (
    DW_NAVY, DW_DARK, DW_STEEL, DW_STEEL_LT, DW_LIGHT, DW_BORDER,
    DW_MID, DW_SLATE, DW_SLATE_LT, DW_GREEN, DW_RED, DW_GREEN_LT,
    DW_RED_LT, DW_AMBER, DW_AMBER_LT, CAP_SPREAD_WARN_BPS,
)
from fetchers.yfinance_fetcher import fetch_all_fundamentals
from fetchers.rss_fetcher import fetch_news
try:
    from fetchers.rss_fetcher import fetch_ticker_news
except ImportError:
    def fetch_ticker_news(tickers, max_per_ticker=3):
        return {t: [] for t in tickers}
from processors.fundamentals import build_fundamentals_table
from processors.deal_scorer import score_deal, MARKET_DATA, TREASURY_10Y_REF
from utils.cache import cache_timestamp
from utils.formatters import fmt_large, fmt_pct, fmt_multiple

st.set_page_config(
    page_title="DivcoWest Dashboard — Innovation Economy Intelligence · Jaeden Kinlock",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Social preview / OG image ──────────────────────────────────────────────────
_OG_IMAGE = "https://raw.githubusercontent.com/jaedenkinlock-oss/divco-dashboard/main/assets/preview.png"
_OG_TITLE = "DivcoWest Dashboard — Innovation Economy Intelligence"
_OG_DESC  = "61M+ SF acquired · 58 properties · 13 core markets · Office & Lab · by Jaeden Kinlock"

st.markdown(f"""
<meta property="og:type"        content="website">
<meta property="og:title"       content="{_OG_TITLE}">
<meta property="og:description" content="{_OG_DESC}">
<meta property="og:image"       content="{_OG_IMAGE}">
<meta name="twitter:card"        content="summary_large_image">
<meta name="twitter:title"       content="{_OG_TITLE}">
<meta name="twitter:description" content="{_OG_DESC}">
<meta name="twitter:image"       content="{_OG_IMAGE}">
<script>
(function(){{
  var img = "{_OG_IMAGE}";
  var ttl = "{_OG_TITLE}";
  var dsc = "{_OG_DESC}";
  [
    ['property','og:type',        'website'],
    ['property','og:title',       ttl],
    ['property','og:description', dsc],
    ['property','og:image',       img],
    ['name','twitter:card',        'summary_large_image'],
    ['name','twitter:title',       ttl],
    ['name','twitter:description', dsc],
    ['name','twitter:image',       img],
  ].forEach(function(m){{
    var el = document.createElement('meta');
    el.setAttribute(m[0], m[1]);
    el.setAttribute('content', m[2]);
    document.head.appendChild(el);
  }});
}})();
</script>
""", unsafe_allow_html=True)

st.markdown(f"""
<style>
[data-testid="stHeader"] {{ display: none !important; }}
[data-testid="stSidebarNav"] {{ display: none !important; }}
[data-testid="collapsedControl"] {{ display: none !important; }}
.stMainBlockContainer {{ padding: 0 !important; max-width: 100% !important; }}
section[data-testid="stMain"] > div {{ padding: 0 !important; }}
.block-container {{ padding: 0 !important; }}

:root {{
  --dw-navy:     {DW_NAVY};
  --dw-dark:     {DW_DARK};
  --dw-steel:    {DW_STEEL};
  --dw-steel-lt: {DW_STEEL_LT};
  --dw-light:    {DW_LIGHT};
  --dw-border:   {DW_BORDER};
  --dw-mid:      {DW_MID};
  --dw-slate:    {DW_SLATE};
  --dw-slate-lt: {DW_SLATE_LT};
  --dw-green:    {DW_GREEN};
  --dw-green-lt: {DW_GREEN_LT};
  --dw-red:      {DW_RED};
  --dw-red-lt:   {DW_RED_LT};
  --dw-amber:    {DW_AMBER};
  --dw-amber-lt: {DW_AMBER_LT};
}}

.dw-header {{
  background: var(--dw-navy); padding: 16px 24px;
  display: flex; align-items: center; justify-content: space-between;
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}}
.dw-wordmark {{ font-size: 15px; font-weight: 300; letter-spacing: 0.20em; color: #fff; text-transform: uppercase; }}
.dw-wordmark strong {{ font-weight: 700; }}
.dw-tagline {{ font-size: 9px; letter-spacing: 0.14em; color: #7a9bbf; text-transform: uppercase; margin-top: 3px; }}
.dw-header-right {{ text-align: right; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }}
.dw-header-right p {{ font-size: 11px; color: #7a9bbf; margin: 0 0 2px 0; }}
.dw-header-right strong {{ color: #a8c8f0; }}
.dw-byline {{ font-size: 9px; color: #4a6a8a; letter-spacing: 0.06em; font-style: italic; margin-top: 3px; }}

.dw-sub {{
  background: var(--dw-dark); padding: 9px 24px;
  display: flex; gap: 20px; align-items: center;
  border-bottom: 1px solid #1e3a5a; flex-wrap: wrap;
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}}
.dw-stat-val {{ font-size: 17px; font-weight: 300; color: #fff; line-height: 1.1; }}
.dw-stat-lbl {{ font-size: 9px; letter-spacing: 0.09em; color: #6a8aaa; text-transform: uppercase; margin-top: 2px; }}
.dw-sub-divider {{ width: 1px; height: 28px; background: #2a4a6a; flex-shrink: 0; }}

.stTabs [data-baseweb="tab-list"] {{
  background: var(--dw-light) !important;
  border-bottom: 1px solid var(--dw-border) !important;
  gap: 0 !important; padding: 0 24px !important;
}}
.stTabs [data-baseweb="tab"] {{
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
  font-size: 11px !important; letter-spacing: 0.08em !important;
  text-transform: uppercase !important; padding: 10px 16px !important;
  color: var(--dw-mid) !important; border-bottom: 2px solid transparent !important;
  background: transparent !important;
}}
.stTabs [aria-selected="true"] {{
  color: var(--dw-navy) !important;
  border-bottom-color: var(--dw-steel) !important;
  font-weight: 600 !important;
}}
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {{ display: none !important; }}
.stTabs [data-baseweb="tab-panel"] {{
  padding: 20px 24px !important;
  background: var(--dw-light) !important;
}}

.sec-lbl {{
  font-size: 9px; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--dw-mid); font-weight: 600; margin-bottom: 10px;
  padding-bottom: 5px; border-bottom: 1px solid var(--dw-border);
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}}

.thesis-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px; }}
.tc {{ background: #fff; border: 0.5px solid var(--dw-border); padding: 14px 15px; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }}
.tc h4 {{ font-size: 9px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--dw-steel); font-weight: 600; margin-bottom: 8px; }}
.tc p, .tc li {{ font-size: 12px; color: var(--dw-mid); line-height: 1.7; margin-bottom: 4px; }}
.tc li strong, .tc p strong {{ color: var(--dw-navy); }}
.tc ul {{ padding-left: 14px; }}

.mi-header {{
  background: var(--dw-navy); padding: 12px 16px;
  display: flex; align-items: flex-start; justify-content: space-between;
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}}
.mi-title {{ font-size: 13px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: #fff; }}
.mi-sub {{ font-size: 10px; color: #7a9bbf; margin-top: 2px; letter-spacing: 0.04em; }}
.mi-data-note {{ font-size: 10px; color: #4a6a8a; text-align: right; }}
.mi-stats {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1px; background: var(--dw-border); margin-bottom: 1px;
}}
.mi-stat {{ background: var(--dw-dark); padding: 10px 14px; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }}
.mi-stat-val {{ font-size: 18px; font-weight: 300; color: var(--dw-steel); }}
.mi-stat-val.pos {{ color: #5a9e70; }}
.mi-stat-val.neg {{ color: #c47070; }}
.mi-stat-lbl {{ font-size: 9px; letter-spacing: 0.08em; text-transform: uppercase; color: #7a9bbf; margin-top: 1px; }}
.mi-stat-src {{ font-size: 9px; color: #4a6a8a; margin-top: 2px; font-style: italic; }}
.insight-box {{
  background: var(--dw-steel-lt); border-left: 3px solid var(--dw-steel);
  padding: 12px 14px; margin-bottom: 1px;
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}}
.insight-box h5 {{
  font-size: 9px; letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--dw-slate); font-weight: 600; margin-bottom: 6px;
}}
.insight-box ul {{ padding-left: 14px; }}
.insight-box li {{ font-size: 12px; color: var(--dw-navy); line-height: 1.75; margin-bottom: 3px; }}
.insight-box li strong {{ color: var(--dw-navy); }}
.src-bar {{
  font-size: 10px; color: var(--dw-mid); padding-top: 8px;
  border-top: 1px solid var(--dw-border);
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}}

[data-testid="stMetric"] {{
  background: #fff; border: 0.5px solid var(--dw-border); padding: 14px 18px; border-radius: 0;
}}
[data-testid="stMetricLabel"] {{
  font-size: 9px !important; letter-spacing: 0.1em !important; text-transform: uppercase !important;
  color: var(--dw-mid) !important; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
}}
[data-testid="stMetricValue"] {{
  font-size: 1.5rem !important; font-weight: 300 !important; color: var(--dw-navy) !important;
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
}}

.badge-red    {{ display:inline-block; background: var(--dw-red-lt);   color: var(--dw-red);   font-size:10px; padding:2px 8px; font-weight:600; letter-spacing:0.04em; font-family:'Helvetica Neue',Arial,sans-serif; }}
.badge-yellow {{ display:inline-block; background: var(--dw-amber-lt); color: var(--dw-amber); font-size:10px; padding:2px 8px; font-weight:600; letter-spacing:0.04em; font-family:'Helvetica Neue',Arial,sans-serif; }}
.badge-ok     {{ display:inline-block; background: var(--dw-green-lt); color: var(--dw-green); font-size:10px; padding:2px 8px; font-weight:600; letter-spacing:0.04em; font-family:'Helvetica Neue',Arial,sans-serif; }}
.badge-na     {{ display:inline-block; background: #eee; color: #999; font-size:10px; padding:2px 8px; font-weight:600; font-family:'Helvetica Neue',Arial,sans-serif; }}

.reit-detail {{
  background: #fff; border: 0.5px solid var(--dw-border); padding: 18px 20px;
  margin-top: 10px; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}}
.reit-detail-title {{
  font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--dw-steel); font-weight: 600; margin-bottom: 12px;
  padding-bottom: 6px; border-bottom: 1px solid var(--dw-border);
}}
.reit-kv-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }}
.reit-kv {{ background: var(--dw-light); padding: 10px 12px; }}
.reit-kv-lbl {{ font-size: 9px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--dw-mid); margin-bottom: 3px; }}
.reit-kv-val {{ font-size: 15px; font-weight: 300; color: var(--dw-navy); }}
.reit-kv-note {{ font-size: 10px; color: var(--dw-mid); margin-top: 2px; font-style: italic; }}

.deal-form-card {{
  background: #fff; border: 0.5px solid var(--dw-border); padding: 18px 20px;
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}}
.deal-form-title {{
  font-size: 9px; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--dw-navy); font-weight: 600; margin-bottom: 14px;
  padding-bottom: 8px; border-bottom: 1px solid var(--dw-border);
}}
.score-hero {{
  text-align: center; padding: 24px 20px 16px 20px;
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}}
.score-num {{ font-size: 64px; font-weight: 200; line-height: 1; }}
.score-denom {{ font-size: 18px; color: var(--dw-mid); font-weight: 300; }}
.score-label {{ font-size: 9px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--dw-mid); margin-top: 6px; }}
.rec-box {{
  padding: 12px 14px; margin-bottom: 12px;
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}}
.rec-box.advance      {{ background: var(--dw-green-lt);  border-left: 3px solid var(--dw-green); }}
.rec-box.conditional  {{ background: var(--dw-steel-lt);  border-left: 3px solid var(--dw-steel); }}
.rec-box.monitor      {{ background: var(--dw-amber-lt);  border-left: 3px solid var(--dw-amber); }}
.rec-box.pass-box     {{ background: var(--dw-red-lt);    border-left: 3px solid var(--dw-red); }}
.rec-box h5 {{
  font-size: 9px; letter-spacing: 0.1em; text-transform: uppercase; font-weight: 600; margin-bottom: 5px;
}}
.rec-box.advance h5   {{ color: var(--dw-green); }}
.rec-box.conditional h5 {{ color: var(--dw-slate); }}
.rec-box.monitor h5   {{ color: var(--dw-amber); }}
.rec-box.pass-box h5  {{ color: var(--dw-red); }}
.rec-box p {{ font-size: 12px; color: var(--dw-navy); line-height: 1.65; margin: 0; }}
.criterion-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }}
.criterion-card {{
  background: var(--dw-light); padding: 10px 12px;
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}}
.criterion-card.strength {{ border-left: 3px solid var(--dw-green); }}
.criterion-card.caution  {{ border-left: 3px solid var(--dw-red); }}
.criterion-card.neutral  {{ border-left: 3px solid var(--dw-border); }}
.criterion-name {{ font-size: 9px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--dw-mid); margin-bottom: 3px; }}
.criterion-pts  {{ font-size: 14px; font-weight: 600; color: var(--dw-navy); }}
.criterion-note {{ font-size: 11px; color: var(--dw-mid); line-height: 1.5; margin-top: 4px; }}
.disclaimer {{
  font-size: 10px; color: var(--dw-mid); padding: 10px 14px;
  border-top: 1px solid var(--dw-border); line-height: 1.6;
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  background: #fff;
}}

.phase-placeholder {{
  background: #fff; border: 0.5px solid var(--dw-border); padding: 40px 24px; text-align: center;
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}}
.phase-placeholder h3 {{ font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase; color: var(--dw-mid); font-weight: 600; margin-bottom: 10px; }}
.phase-placeholder p {{ font-size: 12px; color: var(--dw-mid); line-height: 1.7; }}

[data-testid="stPills"] {{
  background: var(--dw-light) !important;
  border: 0.5px solid var(--dw-border) !important;
  padding: 10px 16px 12px 16px !important;
  margin-bottom: 0 !important;
  gap: 8px !important;
}}
[data-testid="stPills"] > label {{
  font-size: 9px !important; letter-spacing: 0.12em !important;
  text-transform: uppercase !important; font-weight: 600 !important;
  color: var(--dw-mid) !important;
  font-family: 'Helvetica Neue', Arial, sans-serif !important;
  margin-bottom: 6px !important;
}}
[data-testid="stPills"] button {{
  font-family: 'Helvetica Neue', Arial, sans-serif !important;
  font-size: 10px !important; letter-spacing: 0.06em !important;
  border-radius: 0 !important; border: 1px solid #bbb !important;
  color: var(--dw-navy) !important; background: #fff !important;
  padding: 3px 10px !important;
}}
[data-testid="stPills"] button:hover {{
  border-color: var(--dw-steel) !important; color: var(--dw-steel) !important;
  background: var(--dw-steel-lt) !important;
}}
[data-testid="stPills"] button[kind="pillsActive"] {{
  border-color: var(--dw-steel) !important;
  color: var(--dw-steel) !important;
  background: var(--dw-steel-lt) !important;
}}

.pillar-detail {{
  background: #fff; border: 0.5px solid var(--dw-border);
  border-left: 3px solid var(--dw-steel);
  padding: 18px 20px; margin-top: 0; margin-bottom: 16px;
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}}
.pillar-detail h4 {{
  font-size: 9px; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--dw-slate); font-weight: 600; margin-bottom: 10px;
  padding-bottom: 6px; border-bottom: 1px solid var(--dw-border);
}}
.pillar-detail p {{ color: var(--dw-navy); font-size: 13px; line-height: 1.75; margin-bottom: 10px; }}
.pillar-detail ul {{ padding-left: 16px; margin-top: 0; }}
.pillar-detail li {{ color: var(--dw-navy); font-size: 12.5px; line-height: 1.75; margin-bottom: 4px; }}
.pillar-detail li strong, .pillar-detail p strong {{ color: var(--dw-navy); font-weight: 600; }}

.news-dw-banner {{
  background: var(--dw-navy); border-left: 4px solid var(--dw-steel);
  padding: 10px 16px; margin-bottom: 12px;
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase;
  color: #a8c8f0; font-weight: 700;
}}
.news-card {{
  border: 0.5px solid var(--dw-border); padding: 14px 16px;
  margin-bottom: 8px; background: #fff;
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}}
.news-card.dw-hit {{
  border-left: 3px solid var(--dw-steel); background: var(--dw-steel-lt);
}}
.news-card-headline {{ font-size: 13px; font-weight: 600; color: #111; margin-bottom: 4px; line-height: 1.4; }}
.news-card-headline a {{ color: #111; text-decoration: none; }}
.news-card-headline a:hover {{ text-decoration: underline; color: var(--dw-steel); }}
.news-card-meta {{ font-size: 10px; color: #888; letter-spacing: 0.06em; margin-bottom: 6px; }}
.news-card-summary {{ font-size: 11.5px; color: #444; line-height: 1.55; }}
.news-badge-dw {{
  display: inline-block; font-size: 9px; letter-spacing: 0.1em;
  text-transform: uppercase; background: var(--dw-steel); color: #fff;
  padding: 2px 7px; font-weight: 700; margin-right: 6px;
}}
.news-badge-src {{
  display: inline-block; font-size: 9px; letter-spacing: 0.08em;
  text-transform: uppercase; background: #eee; color: #555;
  padding: 2px 7px; font-weight: 600; margin-right: 4px;
}}
.news-empty {{ color: #888; font-size: 12px; padding: 24px 0; text-align: center; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }}
</style>
""", unsafe_allow_html=True)


# ── Header ─────────────────────────────────────────────────────────────────────

ts = cache_timestamp("reit_fundamentals") or datetime.now(timezone.utc).strftime("%B %d, %Y")

st.markdown(f"""
<div class="dw-header">
  <div>
    <div class="dw-wordmark"><strong>DivcoWest</strong>&nbsp;&nbsp;·&nbsp;&nbsp;Jaeden Kinlock</div>
    <div class="dw-tagline">Innovation Economy · Value-Add · Lab / Life Sciences · 13 Core Markets</div>
  </div>
  <div class="dw-header-right">
    <p><strong>61M+</strong> SF acquired &nbsp;·&nbsp; <strong>58</strong> current properties &nbsp;·&nbsp; <strong>$2.25B</strong> Fund VI &nbsp;·&nbsp; Fund VII open</p>
    <p>LPs: <strong>CalPERS &nbsp;·&nbsp; CalSTRS &nbsp;·&nbsp; Mass PRIM</strong> &nbsp;·&nbsp; REIT data: {ts}</p>
    <div class="dw-byline">by Jaeden Kinlock</div>
  </div>
</div>
<div class="dw-sub">
  <div><div class="dw-stat-val">61M+</div><div class="dw-stat-lbl">SF Acquired</div></div>
  <div class="dw-sub-divider"></div>
  <div><div class="dw-stat-val">58</div><div class="dw-stat-lbl">Current Properties</div></div>
  <div class="dw-sub-divider"></div>
  <div><div class="dw-stat-val">$2.25B</div><div class="dw-stat-lbl">Fund VI</div></div>
  <div class="dw-sub-divider"></div>
  <div><div class="dw-stat-val" style="font-size:13px;letter-spacing:0.02em;">Fund VII &nbsp;<span style="font-size:9px;color:#5a9e70;letter-spacing:0.08em;text-transform:uppercase;font-weight:600;">Open</span></div><div class="dw-stat-lbl">Mass PRIM LP</div></div>
  <div class="dw-sub-divider"></div>
  <div><div class="dw-stat-val" style="font-size:11px;letter-spacing:0.01em;">CalPERS &nbsp;·&nbsp; CalSTRS &nbsp;·&nbsp; Mass PRIM</div><div class="dw-stat-lbl">Key LPs</div></div>
  <div class="dw-sub-divider"></div>
  <div><div class="dw-stat-val">Est. 1993</div><div class="dw-stat-lbl">San Francisco, CA</div></div>
</div>
""", unsafe_allow_html=True)


# ── Data load ──────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_data():
    try:
        raw = fetch_all_fundamentals()
        if raw is None or raw.empty:
            return pd.DataFrame()
        return build_fundamentals_table(raw)
    except Exception:
        return pd.DataFrame()

with st.spinner(""):
    df = load_data()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _flag_badge(flag: str) -> str:
    return {
        "red":    '<span class="badge-red">HIGH RISK</span>',
        "yellow": '<span class="badge-yellow">MODERATE</span>',
        "ok":     '<span class="badge-ok">LOW RISK</span>',
        "na":     '<span class="badge-na">N/A</span>',
    }.get(flag, '<span class="badge-na">N/A</span>')


def _flag_text(flag: str) -> str:
    return {"red": "HIGH RISK", "yellow": "MODERATE", "ok": "LOW RISK", "na": "N/A"}.get(flag, "N/A")


def render_market_block(title, subtitle, data_note, stats, insights, sources):
    stats_html = "".join([f"""
      <div class="mi-stat">
        <div class="mi-stat-val {s.get('cls','')}">{s['val']}</div>
        <div class="mi-stat-lbl">{s['label']}</div>
        <div class="mi-stat-src">{s['src']}</div>
      </div>""" for s in stats])
    insights_html = "".join([f"<li><strong>{i[0]}</strong> {i[1]}</li>" for i in insights])
    st.markdown(f"""
    <div class="mi-header">
      <div><div class="mi-title">{title}</div><div class="mi-sub">{subtitle}</div></div>
      <div class="mi-data-note">{data_note}</div>
    </div>
    <div class="mi-stats">{stats_html}</div>
    <div class="insight-box">
      <h5>DivcoWest Thesis Signal — Acquisition Intelligence</h5>
      <ul>{insights_html}</ul>
    </div>
    <div class="src-bar">{sources}</div>
    """, unsafe_allow_html=True)


# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_thesis, tab_reits, tab_markets, tab_macro, tab_news, tab_deal = st.tabs([
    "Investment Thesis",
    "REIT Comparables",
    "Market Intelligence",
    "Macro Overlay",
    "News Tracker",
    "Deal Analyzer",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Investment Thesis
# ══════════════════════════════════════════════════════════════════════════════

with tab_thesis:
    PILLAR_DETAIL = {
        "Innovation Economy Demand": """<p>DivcoWest invests in buildings occupied by the companies building the future — biotech, software, AI, and research institutions. Unlike traditional office tenants, these tenants grow their footprints over time, sign long leases, and have real estate needs that general office product cannot serve.</p>
<ul>
  <li><strong>Why it is structural:</strong> The US life science sector has more than doubled in employment since 2010, adding over 400,000 jobs. Tech sector employment is now 10M+ workers nationally — the renter base for DivcoWest's core markets.</li>
  <li><strong>Why it differs from commodity office:</strong> Lab-enabled and R&D space requires purpose-built infrastructure (HVAC capacity, floor-to-floor height, power) — creating natural barriers to supply and switching costs for tenants.</li>
  <li><strong>The demand floor:</strong> NIH funding ($50B+ annually), university research budgets, and venture capital deployment into life science ($20B+ in 2024) all feed directly into lab space demand regardless of broader economic cycles.</li>
</ul>""",

        "Lab / Life Sciences Convergence": """<p>The line between office and laboratory is dissolving. Biotech and pharma companies now occupy buildings that blend traditional office with wet lab, dry lab, clean room, and R&D flex space — creating a new asset class that neither pure office nor pure lab captures. DivcoWest is positioned at this intersection.</p>
<ul>
  <li><strong>The conversion opportunity:</strong> Office buildings built between 1985 and 2010 in innovation clusters often have the floor-to-floor height (13–15 ft), column spacing, and structural loading to support lab conversion — at a fraction of the cost of ground-up lab development.</li>
  <li><strong>The rent premium:</strong> Lab space commands $80–$140/sqft/yr in Tier 1 markets (Boston/Cambridge, SF Bay Area) versus $40–$70/sqft/yr for comparable traditional office — a 40–100% premium that underwrites conversion economics.</li>
  <li><strong>Market leaders validating the thesis:</strong> Alexandria Real Estate Equities (ARE) — the largest public life science REIT — trades at a premium to all other office REITs precisely because of this positioning.</li>
</ul>""",

        "Supply Constraint in Core Clusters": """<p>Lab and innovation-economy office space is highly concentrated in a small number of submarkets where land is scarce, entitlements are slow, and construction costs are high. New supply is structurally limited — protecting existing owners from competition for longer than in conventional office markets.</p>
<ul>
  <li><strong>Kendall Square, Boston:</strong> Consistently runs 5–9% vacancy with nearly zero new available land — MIT's master plan and Cambridge zoning constrain any meaningful supply addition.</li>
  <li><strong>Mission Bay, San Francisco:</strong> UC San Francisco's research campus has absorbed nearly all developable parcels; the remaining sites face 5–7 year entitlement timelines.</li>
  <li><strong>Torrey Pines / UTC, San Diego:</strong> The biotech cluster's physical expansion is bounded by the Torrey Pines State Reserve — geographic constraint is permanent.</li>
  <li><strong>The national picture:</strong> Life science construction starts are down 35%+ from the 2022 peak as capital markets tightened, even as tenant demand has remained firm.</li>
</ul>""",

        "Value-Add Repositioning": """<p>DivcoWest acquires office and lab buildings where current rents, occupancy, or physical condition are below what the market supports — then creates value by improving the building and its tenancy. The innovation economy thesis provides the demand confidence to underwrite this repositioning work.</p>
<ul>
  <li><strong>The playbook:</strong> Acquire below replacement cost in a supply-constrained submarket, invest $20–$60/sqft in amenity upgrades and systems improvements, re-lease at market rents to tech or life science tenants.</li>
  <li><strong>The current entry window:</strong> Office-to-lab conversions are being acquired at significant discounts to lab replacement cost ($500–$700/sqft to build new vs. $300–$450/sqft to acquire and convert) in several Tier 1 and Tier 2 markets.</li>
  <li><strong>Execution edge:</strong> DivcoWest's 30+ years in innovation economy markets gives it proprietary relationships with biotech and tech tenants before they go to brokers — a sourcing advantage that translates directly into lease-up timing.</li>
</ul>""",

        "Mark-to-Market / Rollover Upside": """<p>In markets where rents have risen since a lease was signed, in-place rents are below what the market now supports. When leases expire, rents reset to market — this gap is contractual income growth that requires no market improvement, just time and normal lease rollover.</p>
<ul>
  <li><strong>Where the gap is widest:</strong> Boston/Cambridge lab rents are 15–25% above 2018–2020 in-place rents for life science tenants; San Francisco Bay Area office tenants on 10+ year leases signed pre-2020 are significantly below current sub-5% vacancy submarkets.</li>
  <li><strong>What it means in practice:</strong> A 100,000 sq ft building with in-place rents at $65/sqft vs. a $78/sqft market = $1.3M in incremental annual NOI on full rollover — with no capex required beyond standard TI/LC.</li>
  <li><strong>WALT as a dual signal:</strong> Long WALT provides income security; short WALT on below-market leases provides near-term upside capture. DivcoWest underwrites both scenarios explicitly.</li>
</ul>""",

        "Development Pipeline": """<p>DivcoWest develops ground-up lab and innovation office buildings in its core markets — controlling cost basis, building specifications, and timing in ways that acquisitions cannot. Development also creates the highest-quality product in each submarket, attracting anchor tenants that validate the investment and set rent comps.</p>
<ul>
  <li><strong>Why develop in a constrained market:</strong> When land is scarce and entitlements slow, the developer who controls sites controls the supply — and can time deliveries to demand rather than competing with a wave of spec product.</li>
  <li><strong>Mission Bay as the model:</strong> DivcoWest's Mission Bay campus in San Francisco established the rent benchmark for the submarket; lab tenants anchoring the campus drove secondary demand for the surrounding blocks.</li>
  <li><strong>The return profile:</strong> Ground-up lab development in Tier 1 markets targets 7–9% stabilized yield on cost vs. 5–6% going-in cap rates on stabilized acquisitions — a 150–300bps development premium for execution risk.</li>
</ul>""",

        "Tenant Credit Quality": """<p>Innovation economy tenants are a fundamentally different credit profile than traditional office tenants. Biotech and pharma companies funded by NIH grants, venture capital, or public capital markets maintain lease obligations even through business volatility — and anchor tenants (hospitals, universities, government agencies) represent some of the most durable credits in commercial real estate.</p>
<ul>
  <li><strong>Anchor institution demand:</strong> MIT, UCSF, Harvard, NIH-affiliated research institutions all require permanent, mission-critical space — these leases are structurally more secure than corporate office leases that can be shed in a downturn.</li>
  <li><strong>Tech tenant credit:</strong> FAANG and hyperscaler tenants (Google, Amazon, Microsoft) signing long-term leases represent investment-grade or near-investment-grade credit with balance sheets that dwarf their landlords.</li>
  <li><strong>Biotech credit nuance:</strong> Pre-revenue biotech requires careful underwriting — but funded companies with 3–5 years of runway on multiyear leases provide adequate security, especially in cluster locations where subleasing is viable if the company pivots.</li>
</ul>""",

        "Institutional Capital Velocity": """<p>Global institutional capital continues to flow toward innovation economy real estate as a distinct asset class — separate from commodity office and separate from traditional core. This capital formation expands the buyer pool for DivcoWest's assets, compresses cap rates over the long term, and validates the strategy to pension funds, sovereign wealth funds, and family offices.</p>
<ul>
  <li><strong>Sector allocation growth:</strong> Life science real estate allocations by institutional investors grew from near-zero in 2010 to a dedicated sub-category in most large pension and endowment real estate programs by 2022.</li>
  <li><strong>M&A validation:</strong> Blackstone's $14.6B acquisition of Biomed Realty (2016) and its multiple subsequent life science platform investments validate the thesis at the highest institutional level.</li>
  <li><strong>DivcoWest's position:</strong> 400+ investor relationships spanning pension funds, sovereign wealth funds, foundations, and family offices — pre-committed capital means DivcoWest can close in 30–60 days on complex transactions where speed is a differentiator.</li>
</ul>""",
    }

    selected_pillar = st.pills(
        "Thesis Pillars — Select to expand",
        list(PILLAR_DETAIL.keys()),
        selection_mode="single",
        default=None,
    )

    if selected_pillar:
        st.markdown(
            f'<div class="pillar-detail"><h4>{selected_pillar}</h4>{PILLAR_DETAIL[selected_pillar]}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("""
    <div class="sec-lbl">Investment Thesis — divcowest.com · public statements · CBRE Life Science Report Q1 2026 · JLL Office &amp; Lab Analytics Q1 2026</div>
    <div class="thesis-grid">
      <div class="tc">
        <h4>Investment Mandate</h4>
        <ul>
          <li><strong>Platform:</strong> Innovation economy specialist — office, lab, R&D, and life science properties in the highest-density knowledge-worker clusters in the US</li>
          <li><strong>AUM:</strong> $16B+ across 13 target markets; 50M+ sq ft; 400+ institutional, family office, and HNW investors</li>
          <li><strong>Edge:</strong> 30+ years of relationships with biotech, pharma, and tech tenants — before they engage brokers</li>
        </ul>
      </div>
      <div class="tc">
        <h4>Strategy — Ranked by Preference</h4>
        <ul>
          <li><strong>1. Value-add repositioning</strong> — below-market rents or occupancy; upgrade to lab/life science spec; re-lease at market to innovation tenants</li>
          <li><strong>2. Lab conversion</strong> — 1985–2010 vintage office; structural assessment → convert to wet lab / R&D flex; 40–100% rent premium over base office</li>
          <li><strong>3. Development</strong> — ground-up lab campus in supply-constrained core clusters; 150–300bps development premium over acquisition yield</li>
          <li><strong>4. Distressed / special situations</strong> — vacant post-COVID office in Tier 1 innovation cores at below-replacement cost basis</li>
        </ul>
      </div>
      <div class="tc">
        <h4>Target Markets by Tier</h4>
        <ul>
          <li><strong>Tier 1 — Innovation Core (4):</strong> SF Bay Area · Boston/Cambridge · Los Angeles · San Diego</li>
          <li><strong>Tier 2 — Growth (6):</strong> Seattle · Austin · Washington DC/Bethesda · New York · Raleigh-Durham · Nashville</li>
          <li><strong>Tier 3 — Expansion Watch (3):</strong> Denver · Miami · Chicago</li>
          <li>Selection driven by NIH funding concentration + university research density + venture capital deployment + existing DivcoWest footprint</li>
        </ul>
      </div>
      <div class="tc">
        <h4>Acquisition Criteria</h4>
        <ul>
          <li><strong>Mark-to-market &gt; 8%</strong> — contractual rent upside on rollover; no reliance on market rent growth</li>
          <li><strong>Vintage: 1985–2010</strong> — structural conversion window; floor-to-floor height ≥ 13 ft; adequate column spacing</li>
          <li><strong>Occupancy: 70–90%</strong> — cash flow to carry capex; vacancy recovers via DivcoWest leasing relationships</li>
          <li><strong>Size: 50,000–500,000 sqft</strong> — sufficient for institutional tenant requirements</li>
          <li><strong>Capital stack:</strong> 50–65% LTV; institutional JV or fund equity; 5–10 year hold</li>
        </ul>
      </div>
      <div class="tc">
        <h4>Platform Edge</h4>
        <ul>
          <li><strong>Tenant network:</strong> 30+ years of direct relationships with biotech, pharma, and tech space users — off-market lease sourcing before broker campaigns</li>
          <li><strong>Lab expertise:</strong> In-house team for conversion feasibility, MEP design standards, and lab TI negotiation — reduces conversion cost basis 10–15% vs. non-specialist owners</li>
          <li><strong>Capital relationships:</strong> 400+ investors; flexible structures across core+, value-add, and development risk profiles</li>
          <li><strong>Data advantage:</strong> Proprietary rent and vacancy data across 50M+ sq ft of managed space in innovation clusters</li>
        </ul>
      </div>
      <div class="tc">
        <h4>Active Thesis — 2025–26</h4>
        <ul>
          <li><strong>Post-COVID office recalibration:</strong> Distressed vacancy in Tier 1 innovation cores creates below-replacement-cost entry; life science demand has not receded — mismatched supply/demand is the opportunity</li>
          <li><strong>Lab conversion economics compelling:</strong> $300–$450/sqft convert-and-reposition vs. $600–$800/sqft ground-up lab; 40–100% rent premium justifies the spread</li>
          <li><strong>Austin — contrarian Tier 2 priority:</strong> 22% vacancy is supply-driven, not demand-driven; Apple, Oracle, Tesla, and Dell have permanently anchored Austin as a top-5 US tech market. DivcoWest acquires now at 40–50% below replacement cost, repositions for tech/life science, and holds into the 2026–27 recovery — the Mission Bay playbook applied to Texas</li>
          <li><strong>Rate trajectory tailwind:</strong> Each 25bps cut on a $100M office asset at 5× leverage adds ~$1.6M in value via cap rate compression; DivcoWest's stabilized assets benefit immediately</li>
          <li><strong>Boston/Cambridge tightest in the US:</strong> Kendall Square lab vacancy at 5–9%; rent growth returned to positive territory; supply pipeline is structurally limited by MIT land control</li>
        </ul>
      </div>
    </div>
    <div class="src-bar">Sources: divcowest.com &nbsp;&middot;&nbsp; CBRE Life Science Real Estate Outlook Q1 2026 &nbsp;&middot;&nbsp; JLL Life Sciences Office &amp; Lab Report Q1 2026 &nbsp;&middot;&nbsp; CommercialCafe Office Analytics Q1 2026 &nbsp;&middot;&nbsp; NIH Budget FY2025</div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — REIT Comparables
# ══════════════════════════════════════════════════════════════════════════════

with tab_reits:
    if df.empty:
        st.warning("REIT data unavailable — yfinance fetch failed or timed out. Data will refresh automatically on next load.")
    else:
      st.markdown(
        '<div class="sec-lbl">REIT universe &nbsp;&middot;&nbsp; life science · office · innovation economy &nbsp;&middot;&nbsp; live yfinance data</div>',
        unsafe_allow_html=True,
      )

      _n_total   = len(df)
      _mc_total  = df["market_cap"].dropna().sum()
      _dy_avg    = df["div_yield"].dropna().mean()
      _pffo_med  = df["p_ffo"].dropna().median()
      _ndeb_med  = df["net_debt_ebitda"].dropna().median()
      _hr        = int((df["payout_flag"] == "red").sum())
      _mod       = int((df["payout_flag"] == "yellow").sum())

      st.markdown(f"""
      <div class="mi-stats" style="margin-bottom:16px;">
        <div class="mi-stat">
          <div class="mi-stat-val">{_n_total}</div>
          <div class="mi-stat-lbl">REITs in Universe</div>
          <div class="mi-stat-src">Office &amp; Life Science</div>
        </div>
        <div class="mi-stat">
          <div class="mi-stat-val">{fmt_large(_mc_total)}</div>
          <div class="mi-stat-lbl">Combined Market Cap</div>
          <div class="mi-stat-src">Full universe</div>
        </div>
        <div class="mi-stat">
          <div class="mi-stat-val" style="color:var(--dw-steel);">{fmt_pct(_dy_avg) if _dy_avg == _dy_avg else '—'}</div>
          <div class="mi-stat-lbl">Avg Dividend Yield</div>
          <div class="mi-stat-src">Universe average</div>
        </div>
        <div class="mi-stat">
          <div class="mi-stat-val" style="color:var(--dw-steel);">{fmt_multiple(_pffo_med) if _pffo_med == _pffo_med else '—'}</div>
          <div class="mi-stat-lbl">Median P / FFO [est.]</div>
          <div class="mi-stat-src">Net Income + D&amp;A proxy</div>
        </div>
        <div class="mi-stat">
          <div class="mi-stat-val" style="color:var(--dw-steel);">{f'{_ndeb_med:.1f}x' if _ndeb_med == _ndeb_med else '—'}</div>
          <div class="mi-stat-lbl">Median ND / EBITDA</div>
          <div class="mi-stat-src">Leverage — full universe</div>
        </div>
        <div class="mi-stat">
          <div class="mi-stat-val {'neg' if _hr > 0 else ''}" style="font-size:18px;font-weight:300;">
            {_hr} High · {_mod} Mod
          </div>
          <div class="mi-stat-lbl">Payout Risk Flags</div>
          <div class="mi-stat-src">Full universe</div>
        </div>
      </div>
      """, unsafe_allow_html=True)

      _all_cats = sorted(df["category"].unique().tolist())
      _preferred = ["Life Science", "Premier Office", "West Coast Office"]
      _default_cats = [c for c in _preferred if c in _all_cats] or _all_cats
      _cat_sel = st.pills(
          "Category",
          _all_cats,
          selection_mode="multi",
          default=_default_cats,
          key="reit_cats",
      )

      _RISK_OPTS = ["Low Risk", "Moderate", "High Risk", "N/A"]
      _RISK_MAP  = {"Low Risk": "ok", "Moderate": "yellow", "High Risk": "red", "N/A": "na"}
      _risk_sel = st.pills(
          "Payout Risk",
          _RISK_OPTS,
          selection_mode="multi",
          default=_RISK_OPTS,
          key="reit_risk",
      )

      _SORT_MAP = {
          "Market Cap":        "market_cap",
          "Dividend Yield":    "div_yield",
          "P/FFO [est.]":      "p_ffo",
          "Payout Ratio":      "payout_ratio",
          "Net Debt / EBITDA": "net_debt_ebitda",
      }
      _sf1, _sf2 = st.columns([1, 2])
      with _sf1:
          _sort_label = st.selectbox("Sort By", list(_SORT_MAP.keys()), key="reit_sort")
      with _sf2:
          _tick_sel = st.selectbox(
              "Ticker detail",
              options=["— select ticker —"] + sorted(df.index.tolist()),
              key="reit_ticker",
          )

      _cats_active = _cat_sel if _cat_sel else _all_cats
      _risk_active = [_RISK_MAP[l] for l in (_risk_sel if _risk_sel else _RISK_OPTS)]
      _sort_col    = _SORT_MAP[_sort_label]

      filtered = df[df["category"].isin(_cats_active) & df["payout_flag"].isin(_risk_active)]
      if _sort_col in filtered.columns:
          filtered = filtered.sort_values(_sort_col, ascending=False)

      st.markdown(
          f'<div class="sec-lbl" style="margin-top:4px;">{len(filtered)} tickers shown &nbsp;&middot;&nbsp; '
          'FFO [est.] = Net Income TTM + D&amp;A TTM &nbsp;&middot;&nbsp; EDGAR ground truth: Phase 2</div>',
          unsafe_allow_html=True,
      )

      display = pd.DataFrame({
          "Company":       filtered["name"],
          "Category":      filtered["category"],
          "Price":         filtered["price"].map(lambda x: f"${x:.2f}" if x == x else "—"),
          "Market Cap":    filtered["market_cap"].map(fmt_large),
          "Div Yield":     filtered["div_yield"].map(lambda x: fmt_pct(x) if x == x else "—"),
          "Annual Div":    filtered["div_rate"].map(lambda x: f"${x:.2f}" if x == x else "—"),
          "Payout Ratio":  filtered["payout_ratio"].map(lambda x: fmt_pct(x) if x == x else "—"),
          "Payout Risk":   filtered["payout_flag"].map(_flag_text),
          "FFO/Sh [est.]": filtered["ffo_per_share"].map(lambda x: f"${x:.2f}" if x == x else "—"),
          "P/FFO [est.]":  filtered["p_ffo"].map(lambda x: fmt_multiple(x) if x == x else "—"),
          "ND/EBITDA":     filtered["net_debt_ebitda"].map(lambda x: f"{x:.1f}x" if x == x else "—"),
          "Lev Risk":      filtered["leverage_flag"].map(_flag_text),
          "52W High":      filtered["week52_high"].map(lambda x: f"${x:.2f}" if x == x else "—"),
          "vs 52W High":   filtered["pct_from_52w_high"].map(lambda x: fmt_pct(x) if x == x else "—"),
      }, index=filtered.index)

      st.dataframe(display, use_container_width=True, height=440)

      st.markdown(
          f'<div class="src-bar">Source: yfinance &nbsp;&middot;&nbsp; {ts} &nbsp;&middot;&nbsp; '
          'Moderate = payout &gt;90% &nbsp;&middot;&nbsp; High Risk = payout &gt;100% &nbsp;&middot;&nbsp; '
          'Leverage moderate = ND/EBITDA &gt;7x &nbsp;&middot;&nbsp; High Risk = &gt;9x</div>',
          unsafe_allow_html=True,
      )

      st.markdown("""
      <div class="insight-box" style="margin-top:10px;">
        <h5>How to Read This Table</h5>
        <ul>
          <li><strong>Price / Funds From Operations (P/FFO) [est.]</strong> — REITs use FFO instead of earnings because traditional earnings subtract depreciation, which makes real estate look less profitable than it actually is. FFO adds depreciation back, giving a clearer picture of cash generated by the properties. P/FFO is therefore the standard REIT valuation multiple — think of it like a P/E ratio for real estate. Lower P/FFO = cheaper valuation relative to cash flow. <em>Note: This estimate uses Net Income + Depreciation &amp; Amortization as a proxy; the precise FFO figure from SEC filings will be incorporated in a future update.</em></li>
          <li><strong>Dividend Payout Ratio</strong> — What percentage of earnings is paid out as dividends. REITs are required by law to pay out at least 90% of taxable income, so high payout ratios are normal. A ratio above 90% (yellow flag) means the company is paying nearly everything it earns — manageable, but leaves little buffer. Above 100% (red flag) means the company is paying out more than it earns, which is only sustainable short-term. For DivcoWest comparables, this measures income stability.</li>
          <li><strong>Net Debt / EBITDA (Leverage Ratio)</strong> — How many years of operating profit it would take to pay off all debt (total debt minus cash). Below 7x is healthy for office/lab REITs. Above 7x (yellow) signals elevated leverage that constrains acquisition capacity. Above 9x (red) is a stress signal — the company has limited flexibility in a rising-rate environment, which is directly relevant to DivcoWest's underwriting of comparable capital structures.</li>
          <li><strong>Why Alexandria Real Estate (ARE) is the benchmark</strong> — Alexandria is the largest publicly traded pure-play life science REIT in the US. Its portfolio — Kendall Square, Mission Bay, Research Triangle — overlaps almost exactly with DivcoWest's Tier 1 markets and tenant base (biotech, pharma, research institutions). ARE's cap rates, occupancy, and P/FFO serve as the closest public-market reference for what DivcoWest's private assets should trade at.</li>
        </ul>
      </div>
      """, unsafe_allow_html=True)

      if _tick_sel != "— select ticker —" and _tick_sel in df.index:
          row = df.loc[_tick_sel]
          cat = row.get("category", "—")

          def _v(x, fmt=None):
              if x is None or (isinstance(x, float) and x != x): return "—"
              return fmt(x) if fmt else str(x)

          pb = row.get("payout_flag", "na")
          lb = row.get("leverage_flag", "na")

          st.markdown(f"""
          <div class="reit-detail">
            <div class="reit-detail-title">{_tick_sel} — {row.get('name','—')} &nbsp;&middot;&nbsp; {cat}</div>
            <div class="reit-kv-grid">
              <div class="reit-kv"><div class="reit-kv-lbl">Current Price</div><div class="reit-kv-val">{_v(row.get('price'), lambda x: f'${x:.2f}')}</div></div>
              <div class="reit-kv"><div class="reit-kv-lbl">Market Cap</div><div class="reit-kv-val">{_v(row.get('market_cap'), fmt_large)}</div></div>
              <div class="reit-kv"><div class="reit-kv-lbl">Dividend Yield</div><div class="reit-kv-val">{_v(row.get('div_yield'), fmt_pct)}</div><div class="reit-kv-note">Annual: {_v(row.get('div_rate'), lambda x: f'${x:.2f}')}/sh</div></div>
              <div class="reit-kv"><div class="reit-kv-lbl">Payout Ratio</div><div class="reit-kv-val">{_v(row.get('payout_ratio'), fmt_pct)}</div><div class="reit-kv-note">{_flag_badge(pb)}</div></div>
              <div class="reit-kv"><div class="reit-kv-lbl">FFO / Share [est.]</div><div class="reit-kv-val">{_v(row.get('ffo_per_share'), lambda x: f'${x:.2f}')}</div><div class="reit-kv-note">Net Income + D&amp;A proxy</div></div>
              <div class="reit-kv"><div class="reit-kv-lbl">P / FFO [est.]</div><div class="reit-kv-val">{_v(row.get('p_ffo'), fmt_multiple)}</div><div class="reit-kv-note">EDGAR ground truth: Phase 2</div></div>
              <div class="reit-kv"><div class="reit-kv-lbl">Forward EPS</div><div class="reit-kv-val">{_v(row.get('forward_eps'), lambda x: f'${x:.2f}')}</div><div class="reit-kv-note">Fwd P/E: {_v(row.get('forward_pe'), lambda x: f'{x:.1f}x')}</div></div>
              <div class="reit-kv"><div class="reit-kv-lbl">Net Debt / EBITDA</div><div class="reit-kv-val">{_v(row.get('net_debt_ebitda'), lambda x: f'{x:.1f}x')}</div><div class="reit-kv-note">{_flag_badge(lb)}</div></div>
              <div class="reit-kv"><div class="reit-kv-lbl">Revenue (TTM)</div><div class="reit-kv-val">{_v(row.get('revenue_ttm'), fmt_large)}</div></div>
              <div class="reit-kv"><div class="reit-kv-lbl">EBITDA (TTM)</div><div class="reit-kv-val">{_v(row.get('ebitda'), fmt_large)}</div></div>
              <div class="reit-kv"><div class="reit-kv-lbl">52-Week High</div><div class="reit-kv-val">{_v(row.get('week52_high'), lambda x: f'${x:.2f}')}</div></div>
              <div class="reit-kv"><div class="reit-kv-lbl">52-Week Low</div><div class="reit-kv-val">{_v(row.get('week52_low'), lambda x: f'${x:.2f}')}</div></div>
            </div>
          </div>
          <div class="src-bar" style="margin-top:6px;">Source: yfinance &nbsp;&middot;&nbsp; {ts} &nbsp;&middot;&nbsp; FFO [est.] = Net Income TTM + D&amp;A TTM &nbsp;&middot;&nbsp; EDGAR 10-K/10-Q FFO in Phase 2.</div>
          """, unsafe_allow_html=True)

          _ticker_news = fetch_ticker_news([_tick_sel], max_per_ticker=4).get(_tick_sel, [])
          if _ticker_news:
              _news_age = (datetime.now(timezone.utc) - _ticker_news[0]["date"]).total_seconds()
              _freshness = "LIVE" if _news_age < 3600 else f"{int(_news_age/3600)}h ago"
              st.markdown(
                  f'<div class="sec-lbl" style="margin-top:14px;">'
                  f'Recent Headlines — {_tick_sel} &nbsp;&middot;&nbsp; Yahoo Finance &nbsp;&middot;&nbsp; '
                  f'<span style="color:var(--dw-steel);font-weight:600;">{_freshness}</span></div>',
                  unsafe_allow_html=True,
              )
              for art in _ticker_news:
                  _art_date = art["date"].strftime("%b %d") if hasattr(art["date"], "strftime") else ""
                  st.markdown(
                      f'<div style="padding:6px 0;border-bottom:1px solid #e8e6e0;">'
                      f'<a href="{art["link"]}" target="_blank" style="color:var(--dw-navy);font-weight:600;text-decoration:none;">'
                      f'{art["title"]}</a>'
                      f'<span style="color:#999;font-size:11px;margin-left:8px;">{_art_date}</span>'
                      f'</div>',
                      unsafe_allow_html=True,
                  )

      with st.expander("Raw data — all columns"):
          st.dataframe(filtered, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Market Intelligence
# ══════════════════════════════════════════════════════════════════════════════

with tab_markets:
    st.markdown('<div class="sec-lbl">DivcoWest target markets &nbsp;&middot;&nbsp; office &amp; lab fundamentals &nbsp;&middot;&nbsp; data as of Q1 2026 &nbsp;&middot;&nbsp; live FRED integration Phase 2</div>', unsafe_allow_html=True)

    _MARKET_COORDS = {
        "San Francisco Bay Area, CA":   (37.75, -122.42, 1),
        "Boston / Cambridge, MA":       (42.37, -71.05,  1),
        "Los Angeles, CA":              (34.05, -118.24, 1),
        "San Diego, CA":                (32.72, -117.16, 1),
        "Seattle, WA":                  (47.61, -122.33, 2),
        "Austin, TX":                   (30.27, -97.74,  2),
        "Washington DC / Bethesda, MD": (38.89, -77.03,  2),
        "New York, NY":                 (40.71, -74.01,  2),
        "Raleigh-Durham, NC":           (35.78, -78.64,  2),
        "Nashville, TN":                (36.16, -86.78,  2),
        "Denver, CO":                   (39.74, -104.99, 3),
        "Miami, FL":                    (25.76, -80.19,  3),
        "Chicago, IL":                  (41.88, -87.63,  3),
    }

    _T3_DATA = {
        "Denver, CO":  "Fitzsimons life science campus; aerospace and energy sector driving R&D demand. 25/100 DivcoWest presence. Full intelligence module in Phase 3.",
        "Miami, FL":   "Wynwood tech corridor and Brickell financial cluster; Miami Tech Week validating tech migration. 20/100 presence. Full module Phase 3.",
        "Chicago, IL": "Fulton Market tech hub and Goose Island life science corridor; Chicago Quantum Exchange anchor. 20/100 presence. Full module Phase 3.",
    }
    _T3_NAMES = list(_T3_DATA.keys())

    T1_MARKETS = [
        {
            "name": "San Francisco Bay Area, CA",
            "expander": "San Francisco Bay Area, CA  —  Tier 1 Innovation Core  ·  21.0% Office Vacancy  ·  −3.0% Rent Growth YOY",
            "subtitle": "DivcoWest Home Market · Mission Bay Flagship Campus · Lab Outperforming General Office",
            "stats": [
                {"val": "21.0%",  "label": "Office Vacancy (Overall)",     "src": "IPG SF Q1 2026 — lab/life science submarkets materially tighter", "cls": "neg"},
                {"val": "$73",    "label": "Asking Rent ($/sqft/yr)",      "src": "IPG SF Q1 2026 — Class A; Mission Bay lab commands premium above this"},
                {"val": "−3.0%",  "label": "Rent Growth YOY",              "src": "IPG SF Q1 2026 — softening continues; lab product more resilient", "cls": "neg"},
                {"val": "95/100", "label": "DivcoWest Presence Score",     "src": "DivcoWest internal — Mission Bay campus is flagship asset"},
                {"val": "Low",    "label": "Supply Pipeline Risk",          "src": "JLL Q1 2026 — no meaningful new lab deliveries 2025–26"},
                {"val": "UCSF",   "label": "Anchor Institution",            "src": "UCSF Mission Bay — world-class research campus; largest SF employer"},
                {"val": "1.2M+",  "label": "Lab Sq Ft Under Construction",  "src": "JLL Q1 2026 — concentrated in Mission Bay and Oyster Point"},
            ],
            "insights": [
                ("Lab vs. office bifurcation — the core thesis:", "Overall SF office vacancy is 21%+, but Mission Bay and Oyster Point lab space remains materially tighter. Acquirers are buying lab-adjacent or convertible product at office-equivalent cap rates — the pricing gap is the opportunity."),
                ("Mission Bay / Oyster Point corridor:", "UCSF presence (6,000+ researchers) and the biotech cluster along the Bay creates permanent tenant demand; DivcoWest's 95/100 presence score reflects deep submarket knowledge and tenant relationships unavailable to outside capital."),
            ],
            "sources": "IPG San Francisco Q1 2026 · JLL Life Sciences Bay Area Q1 2026 · UCSF Mission Bay Research Campus · BLS San Francisco Metro Employment 2025",
        },
        {
            "name": "Boston / Cambridge, MA",
            "expander": "Boston / Cambridge, MA  —  Tier 1 Innovation Core  ·  12.5% Vacancy  ·  Flat Rent Growth YOY",
            "subtitle": "Tightest Lab Market in the US · MIT and Broad Institute Anchor · Kendall Square Rent Premium",
            "stats": [
                {"val": "12.5%",  "label": "Lab / Life Science Vacancy",  "src": "CommercialCafe Q1 2026 — Kendall Square lab tighter than broader market"},
                {"val": "$85",    "label": "Asking Rent ($/sqft/yr)",      "src": "Kendall Square lab submarket Q1 2026; downtown Boston Class A at $78/SF (CommercialCafe)", "cls": "pos"},
                {"val": "Flat",   "label": "Rent Growth YOY",              "src": "CommercialCafe Q1 2026 — lab product stable; general office softening"},
                {"val": "90/100", "label": "DivcoWest Presence Score",     "src": "DivcoWest internal — significant Cambridge/Somerville exposure"},
                {"val": "Moderate","label": "Supply Pipeline Risk",         "src": "JLL Q1 2026 — some spec deliveries in Somerville/Watertown; Cambridge constrained"},
                {"val": "MIT",    "label": "Anchor Institution",            "src": "MIT · Broad Institute · Harvard Medical School — highest research density globally"},
                {"val": "3.5M+",  "label": "Lab Sq Ft Under Construction",  "src": "JLL Q1 2026 — concentrated in Watertown, Somerville, Alewife"},
            ],
            "insights": [
                ("Kendall Square — structurally supply-constrained:", "MIT's master plan controls nearly all developable parcels; Cambridge zoning further constrains supply; vacancy has risen from 9% but remains significantly below national averages — the supply-demand structure is durable."),
                ("Watertown and Somerville emerging at a discount:", "Next-tier lab submarkets at 20–30% discounts to Kendall Square rents — acquisition window before they reprice as the primary cluster reaches stabilization."),
            ],
            "sources": "CommercialCafe Boston Q1 2026 · JLL Life Sciences Boston Q1 2026 · MIT Investment Management Company Annual Report · BLS Boston Metro Employment 2025",
        },
        {
            "name": "Los Angeles, CA",
            "expander": "Los Angeles, CA  —  Tier 1 Innovation Core  ·  18.0% Office Vacancy  ·  −2.0% Rent Growth YOY",
            "subtitle": "Silicon Beach (Playa Vista, Culver City) · Google, Amazon, Snap Anchor · Life Science Emerging in Torrance",
            "stats": [
                {"val": "18.0%",  "label": "Office / Creative Vacancy",    "src": "CommercialCafe Q1 2026 — elevated; Silicon Beach submarket tighter at ~12%"},
                {"val": "$52",    "label": "Asking Rent ($/sqft/yr)",       "src": "CommercialCafe Q1 2026 — Class A; lab commands $65–80 in El Segundo/Torrance"},
                {"val": "−2.0%",  "label": "Rent Growth YOY",              "src": "CommercialCafe Q1 2026 — general office declining", "cls": "neg"},
                {"val": "80/100", "label": "DivcoWest Presence Score",      "src": "DivcoWest internal — significant Playa Vista and Culver City exposure"},
                {"val": "Low",    "label": "Supply Pipeline Risk",           "src": "CoStar — limited new product in core Silicon Beach submarkets"},
                {"val": "Google", "label": "Silicon Beach Anchor",           "src": "Google Playa Vista (3M+ sqft), Amazon Culver City, Snap HQ"},
                {"val": "800K+",  "label": "Life Science Sq Ft Emerging",   "src": "JLL LA Life Sciences Q1 2026 — Torrance / El Segundo bioscience corridor forming"},
            ],
            "insights": [
                ("Silicon Beach creative/tech office tighter than overall market:", "Playa Vista and Culver City vacancy runs 10–14% vs. 18%+ for greater LA — DivcoWest's 80/100 presence means access to tenant roll data and sub-market comps before they are published."),
                ("Life science emerging thesis:", "Torrance/El Segundo bioscience corridor is early-stage but gaining velocity; below-market entry points available before the submarket gets a CoStar label and institutional pricing follows."),
            ],
            "sources": "CommercialCafe LA Q1 2026 · JLL LA Life Sciences Q1 2026 · BLS Los Angeles Metro Employment 2025 · CBRE Silicon Beach Report Q1 2026",
        },
        {
            "name": "San Diego, CA",
            "expander": "San Diego, CA  —  Tier 1 Innovation Core  ·  15.0% Vacancy  ·  −1.0% Rent Growth YOY",
            "subtitle": "Torrey Pines / UTC Life Science Cluster · Illumina, Qualcomm, Biotech Pipeline Anchor",
            "stats": [
                {"val": "15.0%",  "label": "Lab / R&D Vacancy",            "src": "CommercialCafe Q1 2026 — elevated vs. cycle lows; Torrey Pines tighter"},
                {"val": "$52",    "label": "Asking Rent ($/sqft/yr)",       "src": "CommercialCafe Q1 2026 — Class A; Torrey Pines lab commands premium"},
                {"val": "−1.0%",  "label": "Rent Growth YOY",              "src": "CommercialCafe Q1 2026 — softening from 2022–23 highs", "cls": "neg"},
                {"val": "75/100", "label": "DivcoWest Presence Score",      "src": "DivcoWest internal — Torrey Pines / UTC exposure"},
                {"val": "Low",    "label": "Supply Pipeline Risk",           "src": "JLL Q1 2026 — Torrey Pines State Reserve bounds expansion permanently"},
                {"val": "Illumina","label": "Genomics Anchor",               "src": "Illumina HQ (UTC); Qualcomm HQ; 600+ biotech and pharma companies"},
                {"val": "1.0M+",  "label": "Lab Sq Ft Under Construction",  "src": "JLL Q1 2026 — concentrated in Sorrento Valley and Miramar"},
            ],
            "insights": [
                ("Geographic constraint is permanent:", "The Torrey Pines State Reserve and Pacific Ocean physically bound the core cluster — no new land supply is possible, which is why this submarket has maintained below-average vacancy despite national office softening."),
                ("Biotech pipeline creates structural demand:", "San Diego is the #3 US biotech hub (after Boston/Cambridge and SF Bay Area) with 600+ companies; the pipeline of pre-revenue to revenue-stage companies provides a continuous leasing cycle for lab space."),
            ],
            "sources": "CommercialCafe San Diego Q1 2026 · JLL Life Sciences San Diego Q1 2026 · San Diego Regional EDC 2025 · BLS San Diego Metro Employment 2025",
        },
    ]

    T2_MARKETS = [
        {
            "name": "Seattle, WA",
            "expander": "Seattle, WA  —  Tier 2 Growth  ·  23.0% Office Vacancy  ·  −4.0% Rent Growth YOY",
            "subtitle": "South Lake Union / Bellevue · Amazon and Microsoft HQ Anchor · Life Science Emerging",
            "stats": [
                {"val": "23.0%",  "label": "Office Vacancy",               "src": "CommercialCafe Q1 2026 — among highest of major US markets; SLU tighter", "cls": "neg"},
                {"val": "$38",    "label": "Asking Rent ($/sqft/yr)",       "src": "CommercialCafe Q1 2026 — Class A; $38–41/SF range"},
                {"val": "−4.0%",  "label": "Rent Growth YOY",              "src": "CommercialCafe Q1 2026", "cls": "neg"},
                {"val": "70/100", "label": "DivcoWest Presence Score",      "src": "DivcoWest internal — South Lake Union exposure"},
                {"val": "Moderate","label": "Supply Pipeline Risk",          "src": "JLL Q1 2026 — Amazon sublease overhang still clearing"},
                {"val": "Amazon", "label": "Anchor Tenant",                  "src": "Amazon World HQ (SLU); Microsoft Bellevue; Google; Meta"},
                {"val": "850K+",  "label": "Lab Sq Ft Under Construction",  "src": "JLL Q1 2026 — South Lake Union biotech emerging"},
            ],
            "insights": [
                ("Deepest discount in Tier 2 — selective opportunity:", "23%+ vacancy and $38/SF asking rent represent the widest bid-ask spread in the DivcoWest universe. Amazon sublease overhang is still clearing; patient capital acquiring today at 2015-level pricing positions for the tech re-entry when sublease depth normalizes."),
                ("Life science emerging in SLU:", "Allen Institute, Fred Hutchinson Cancer Center, and UW Medicine are anchoring a biotech cluster in South Lake Union; DivcoWest's 70/100 presence positions it to benefit before the submarket reprices."),
            ],
            "sources": "CommercialCafe Seattle Q1 2026 · JLL Seattle Life Sciences Q1 2026 · BLS Seattle Metro Employment 2025",
        },
        {
            "name": "Austin, TX",
            "expander": "Austin, TX  —  Tier 2 Strategic Priority  ·  26.0% Office Vacancy  ·  DivcoWest Active — Domain + UT Corridor",
            "subtitle": "DivcoWest Strategic Expansion Market · Domain NORTHSIDE Anchor · UT Life Science $3B Build-Out · Trough Acquisition Window Open",
            "stats": [
                {"val": "26.0%",  "label": "Office Vacancy",                "src": "CommercialCafe Q1 2026 — peak; new deliveries absorbed through 2026; pipeline thinning sharply", "cls": "neg"},
                {"val": "$46",    "label": "Asking Rent ($/sqft/yr)",        "src": "CommercialCafe Q1 2026 — most affordable innovation market in DivcoWest universe"},
                {"val": "−1.0%",  "label": "Rent Growth YOY",               "src": "CommercialCafe Q1 2026 — trough signal narrowing; recovery modeled 2026–27", "cls": "neg"},
                {"val": "65/100", "label": "DivcoWest Presence Score",       "src": "DivcoWest internal — Domain North, The Triangle, UT corridor exposure; active leasing relationships"},
                {"val": "High",   "label": "Supply Pipeline Risk",            "src": "CommercialCafe Q1 2026 — pipeline moderating; bulk of deliveries cleared by mid-2026"},
                {"val": "Apple",  "label": "Flagship Tech Anchor",            "src": "Apple Campus 2 Austin (~3M sqft, 5,000+ employees); Oracle HQ (8,500 jobs); Tesla Giga Texas; Dell HQ"},
                {"val": "350K+",  "label": "Life Science Sq Ft in Pipeline", "src": "JLL Austin Life Sciences Q1 2026 — UT Dell Medical School and Pickle Research Campus driving demand"},
                {"val": "$3B+",   "label": "UT Life Science Infrastructure", "src": "UT Austin — Dell Medical School, Moody Center for the Arts of Science, Pickle Research Campus 10-yr plan"},
                {"val": "+3.2%",  "label": "Tech Employment Growth YOY",     "src": "BLS Q1 2026 — Austin ranks #2 nationally for tech job growth behind only Miami", "cls": "pos"},
            ],
            "insights": [
                ("DivcoWest's contrarian Austin thesis — trough entry, long hold:", "26% vacancy is a cyclical phenomenon driven by 2021–23 overbuilding, not a structural demand failure. Apple, Oracle, Tesla, and Dell have permanently relocated HQ or major operations to Austin — creating a tech tenant base that will absorb the supply overhang by 2026–27. DivcoWest's 65/100 presence score means active relationships with these tenants before they engage brokers."),
                ("The Domain / Domain NORTHSIDE — Austin's innovation campus anchor:", "The Domain is a 300-acre mixed-use innovation campus in north Austin housing Amazon, Meta, Indeed, Visa, and 60+ tech tenants. Domain NORTHSIDE (Phase II expansion) adds 500K+ sqft of office and lab product through 2026–27; DivcoWest has established relationships in this corridor that create off-market acquisition access."),
                ("UT life science build-out is a 10-year structural demand driver:", "University of Texas's $3B+ life science infrastructure plan — Dell Medical School, Pickle Research Campus, and the new Moody Center for the Arts of Science — is creating a permanent life science cluster adjacent to downtown Austin. Early-stage biotech and medtech companies seeding out of UT will need purpose-built lab space; no existing institutional lab product serves this demand today."),
                ("Below-replacement-cost entry window open now:", "Class A office at $46/sqft/yr asking rent represents 35–45% below replacement cost in this market. The supply absorption cycle is underway through 2026; DivcoWest's model calls for acquisition at distressed pricing, repositioning to tech/life science spec, and re-leasing into a recovering market — the same playbook executed in Mission Bay SF in the 2010s."),
            ],
            "sources": "CommercialCafe Austin Office Q1 2026 · JLL Austin Life Sciences Report Q1 2026 · BLS Austin–Round Rock–Georgetown Metro Employment Q1 2026 · UT Austin Dell Medical School 2025 · Austin Chamber of Commerce Innovation Economy Report 2025 · CBRE Austin Tech Tenant Survey Q4 2025",
        },
        {
            "name": "Washington DC / Bethesda, MD",
            "expander": "Washington DC / Bethesda, MD  —  Tier 2 Growth  ·  10.5% Lab Vacancy  ·  Flat Rent Growth YOY",
            "subtitle": "NIH Campus · Bethesda BioPark · Government R&D Funding Provides Recession-Resistant Demand",
            "stats": [
                {"val": "10.5%",  "label": "Lab / Government Office Vacancy","src": "CommercialCafe Q1 2026 — tightest in DivcoWest Tier 2"},
                {"val": "$60",    "label": "Asking Rent ($/sqft/yr)",         "src": "CommercialCafe Q1 2026 — Class A government office and Bethesda BioPark"},
                {"val": "Flat",   "label": "Rent Growth YOY",                "src": "CommercialCafe Q1 2026 — stable; government demand floors the market"},
                {"val": "65/100", "label": "DivcoWest Presence Score",        "src": "DivcoWest internal — Bethesda and Rockville exposure"},
                {"val": "Low",    "label": "Supply Pipeline Risk",             "src": "JLL Q1 2026 — limited spec development; government pre-leasing dominates"},
                {"val": "NIH",    "label": "Government Anchor",                "src": "NIH Bethesda Campus (22,000+ employees; $50B+ annual research budget)"},
                {"val": "600K+",  "label": "Lab Sq Ft Under Construction",    "src": "JLL Q1 2026 — Bethesda BioPark and Rockville Pike corridor"},
            ],
            "insights": [
                ("NIH funding is recession-proof demand:", "NIH's $50B+ annual budget — largely independent of economic cycles — funds thousands of researchers who need lab and office space; the Bethesda cluster is structurally different from commercial office markets."),
                ("Lowest supply risk in Tier 2:", "Government pre-leasing and the NIH campus footprint limit speculative development; 10.5% vacancy is the tightest in the DivcoWest Tier 2 universe, supported by a demand floor that does not require private sector health."),
            ],
            "sources": "CommercialCafe DC/Bethesda Q1 2026 · JLL DC Metro Life Sciences Q1 2026 · NIH Campus &amp; Research 2025 · BLS Washington DC Metro Employment Q1 2026",
        },
        {
            "name": "New York, NY",
            "expander": "New York, NY  —  Tier 2 Growth  ·  13.0% Office Vacancy  ·  +1.0% Rent Growth YOY",
            "subtitle": "Midtown South / Hudson Yards · Life Science Emerging in Kip's Bay and Alexandria Center",
            "stats": [
                {"val": "13.0%",  "label": "Office Vacancy",               "src": "Cushman & Wakefield Q1 2026 — improving; trophy Midtown South and Hudson Yards tightening"},
                {"val": "$83",    "label": "Asking Rent ($/sqft/yr)",       "src": "Cushman & Wakefield Q1 2026 — Manhattan Class A; Midtown South tech premium above this"},
                {"val": "+1.0%",  "label": "Rent Growth YOY",              "src": "Cushman & Wakefield Q1 2026", "cls": "pos"},
                {"val": "55/100", "label": "DivcoWest Presence Score",      "src": "DivcoWest internal — Hudson Yards and Midtown South exposure"},
                {"val": "Low",    "label": "Supply Pipeline Risk",           "src": "JLL Q1 2026 — high land costs constrain new development in target submarkets"},
                {"val": "Alexandria","label": "Life Science Anchor REIT",    "src": "Alexandria Center for Life Science — East River cluster validating demand"},
                {"val": "1.5M+",  "label": "Life Science Sq Ft in Pipeline", "src": "JLL NYC Life Sciences Q1 2026 — Kip's Bay, East River, Long Island City corridor"},
            ],
            "insights": [
                ("Life science emerging as a distinct asset class in NYC:", "Alexandria Center for Life Science (East River) has validated the NYC lab demand thesis; Kip's Bay and Long Island City are the next-tier submarkets where DivcoWest's 55/100 presence provides competitive intelligence ahead of repricing."),
                ("NYC office recovery outperforming national trend:", "Manhattan vacancy improved to 13% as flight-to-quality accelerates — Midtown South (Flatiron/Chelsea) tech office running 10–12% vs. 15%+ for Midtown CBD; positive rent growth (+1.0% YOY) marks the first recovery since 2020."),
            ],
            "sources": "Cushman &amp; Wakefield Manhattan Q1 2026 · JLL NYC Life Sciences Q1 2026 · BLS New York Metro Employment Q1 2026",
        },
        {
            "name": "Raleigh-Durham, NC",
            "expander": "Raleigh-Durham, NC  —  Tier 2 Growth  ·  11.0% Office Vacancy  ·  Flat Rent Growth YOY",
            "subtitle": "Research Triangle Park · Apple and Google Expanding · 300+ Companies, 65K+ Employees",
            "stats": [
                {"val": "11.0%",  "label": "Office / R&D Vacancy",         "src": "CommercialCafe Q1 2026 — improving steadily; RTP submarkets tighter"},
                {"val": "$38",    "label": "Asking Rent ($/sqft/yr)",       "src": "CommercialCafe Q1 2026 — most affordable in DivcoWest Tier 2"},
                {"val": "Flat",   "label": "Rent Growth YOY",              "src": "CommercialCafe Q1 2026 — stabilizing; absorption catching supply"},
                {"val": "45/100", "label": "DivcoWest Presence Score",      "src": "DivcoWest internal — Research Triangle Park exposure"},
                {"val": "Moderate","label": "Supply Pipeline Risk",          "src": "CommercialCafe Q1 2026 — new spec R&D product moderating; RTP master plan product well-leased"},
                {"val": "RTP",    "label": "Research Anchor",                "src": "Research Triangle Park — 300+ companies, 65K+ employees; largest research park in the US"},
                {"val": "750K+",  "label": "R&D Sq Ft Under Construction",  "src": "JLL Raleigh-Durham Q1 2026 — RTP master plan expansion"},
            ],
            "insights": [
                ("Apple and Google are creating a demand step-change:", "Apple's $1B+ campus and Google's data center expansion are adding $150K+ income tech workers through 2026–28 — most affordable innovation market in the DivcoWest universe with a compelling long-term trajectory."),
                ("Vacancy improved to 11%; rent stabilizing:", "From 14% in 2024 to 11% in Q1 2026 — one of the fastest vacancy improvements in the DivcoWest Tier 2 universe; RTP's master plan conversion to mixed-use innovation campus is attracting biotech and pharma tenants ahead of broader market recognition."),
            ],
            "sources": "CommercialCafe Raleigh-Durham Q1 2026 · JLL Raleigh-Durham Life Sciences Q1 2026 · Research Triangle Park 2025 Economic Impact · BLS Raleigh Metro Employment Q1 2026",
        },
        {
            "name": "Nashville, TN",
            "expander": "Nashville, TN  —  Tier 2 Growth  ·  20.0% Office Vacancy  ·  −2.5% Rent Growth YOY",
            "subtitle": "Oracle HQ, Amazon HQ2 Expansion · Healthcare Economy (HCA, Vanderbilt) · Life Science Opportunity",
            "stats": [
                {"val": "20.0%",  "label": "Office Vacancy",               "src": "CommercialCafe Q1 2026 — supply wave absorbing; 2026 deliveries thinning", "cls": "neg"},
                {"val": "$35",    "label": "Asking Rent ($/sqft/yr)",       "src": "CommercialCafe Q1 2026 — lowest in DivcoWest Tier 2"},
                {"val": "−2.5%",  "label": "Rent Growth YOY",              "src": "CommercialCafe Q1 2026", "cls": "neg"},
                {"val": "35/100", "label": "DivcoWest Presence Score",      "src": "DivcoWest internal — early-stage positioning"},
                {"val": "Moderate","label": "Supply Pipeline Risk",          "src": "JLL Q1 2026 — pipeline moderating; 2026 absorption catching up"},
                {"val": "HCA",    "label": "Healthcare Anchor",              "src": "HCA Healthcare HQ (world's largest for-profit hospital); Vanderbilt Medical (25K+ employees)"},
                {"val": "400K+",  "label": "Life Science Sq Ft Emerging",   "src": "JLL Nashville Life Sciences Q1 2026 — Vanderbilt corridor and MetroCenter"},
            ],
            "insights": [
                ("Healthcare economy creates innovation office demand:", "HCA Healthcare (29K+ Nashville employees) and Vanderbilt Medical are generating demand for medical office and R&D flex space that is structurally different from commodity office — this is the early-stage DivcoWest opportunity in Nashville."),
                ("Deepest discount and improving trajectory:", "20% vacancy + Oracle HQ + Amazon HQ2 expansion = trough acquisition window; supply pipeline moderates sharply in 2026 — patient capital acquires today at below-replacement cost."),
            ],
            "sources": "CommercialCafe Nashville Office Q1 2026 · JLL Nashville Market Report Q1 2026 · BLS Nashville Metro Employment Q1 2026 · HCA Healthcare 2025 Annual Report",
        },
    ]

    ALL_MARKETS_DICT = {m["name"]: m for m in T1_MARKETS + T2_MARKETS}

    for _k in ("mkt_t1", "mkt_t2", "mkt_t3"):
        if _k not in st.session_state:
            st.session_state[_k] = None

    def _clr_t2_t3(): st.session_state.mkt_t2 = None; st.session_state.mkt_t3 = None
    def _clr_t1_t3(): st.session_state.mkt_t1 = None; st.session_state.mkt_t3 = None
    def _clr_t1_t2(): st.session_state.mkt_t1 = None; st.session_state.mkt_t2 = None

    sel_t1 = st.pills("Tier 1 — Innovation Core", [m["name"] for m in T1_MARKETS],
                      selection_mode="single", default=None, key="mkt_t1", on_change=_clr_t2_t3)
    sel_t2 = st.pills("Tier 2 — Growth Markets",  [m["name"] for m in T2_MARKETS],
                      selection_mode="single", default=None, key="mkt_t2", on_change=_clr_t1_t3)
    sel_t3 = st.pills("Tier 3 — Expansion Watch", _T3_NAMES,
                      selection_mode="single", default=None, key="mkt_t3", on_change=_clr_t1_t2)
    _sel = sel_t1 or sel_t2 or sel_t3

    # ── Plotly US map ─────────────────────────────────────────────────────────
    _mlats, _mlons, _mtexts, _mcolors, _msizes, _mborders = [], [], [], [], [], []
    for _mname, (_mlat, _mlon, _mtier) in _MARKET_COORDS.items():
        _mlats.append(_mlat); _mlons.append(_mlon)
        if _mname in ALL_MARKETS_DICT:
            _md = ALL_MARKETS_DICT[_mname]
            _ms = _md["stats"]
            _vac = next((x["val"] for x in _ms if "Vacancy" in x["label"]), "—")
            _rg  = next((x["val"] for x in _ms if "Rent Growth" in x["label"]), "—")
            _rnt = next((x["val"] for x in _ms if "Asking Rent" in x["label"]), "—")
            _tlbl = "Tier 1 — Innovation Core" if _mtier == 1 else "Tier 2 — Growth"
            _mtexts.append(f"<b>{_mname}</b><br>{_tlbl}<br>Vacancy: {_vac}<br>Rent Growth: {_rg}<br>Asking Rent: {_rnt}/sqft/yr")
        else:
            _mtexts.append(f"<b>{_mname}</b><br>Tier 3 — Expansion Watch<br>{_T3_DATA.get(_mname,'')}")

        if _mname == _sel:
            _mcolors.append("#2D6AA0"); _msizes.append(20); _mborders.append("#ffffff")
        elif _mtier == 1:
            _mcolors.append("#2D6AA0"); _msizes.append(13); _mborders.append("#0F2040")
        elif _mtier == 2:
            _mcolors.append("#3A5A7A"); _msizes.append(10); _mborders.append("#0F2040")
        else:
            _mcolors.append("#4a6a8a"); _msizes.append(8);  _mborders.append("#0F2040")

    _mfig = go.Figure(go.Scattergeo(
        lat=_mlats, lon=_mlons, text=_mtexts,
        hovertemplate="%{text}<extra></extra>",
        mode="markers",
        marker=dict(size=_msizes, color=_mcolors, line=dict(width=1.5, color=_mborders)),
    ))
    _mfig.update_layout(
        geo=dict(scope="usa", projection_type="albers usa",
                 showland=True, landcolor="#1A2535",
                 showcoastlines=True, coastlinecolor="#2A3A4A",
                 showlakes=True, lakecolor="#0F2040",
                 showframe=False, bgcolor="#0F2040",
                 showsubunits=True, subunitcolor="#2A3A4A"),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#0F2040",
        height=340,
        hoverlabel=dict(bgcolor="#0F2040", bordercolor="#2D6AA0",
                        font=dict(color="#fff", size=11, family="Helvetica Neue, Arial")),
    )
    st.plotly_chart(_mfig, use_container_width=True, config={"displayModeBar": False})

    if _sel and _sel in ALL_MARKETS_DICT:
        _lm = ALL_MARKETS_DICT[_sel]
        render_market_block(_lm["name"], _lm["subtitle"], "Data as of Q1 2026",
                            _lm["stats"], _lm["insights"], _lm["sources"])
    elif _sel and _sel in _T3_DATA:
        st.markdown(f"""
        <div class="mi-header">
          <div><div class="mi-title">{_sel}</div>
          <div class="mi-sub">Tier 3 — Expansion Watch &nbsp;·&nbsp; Full intelligence module in Phase 3</div></div>
          <div class="mi-data-note">Phase 3</div>
        </div>
        <div class="insight-box" style="margin-top:1px;">
          <h5>Market Brief</h5>
          <ul><li>{_T3_DATA[_sel]}</li>
          <li>Full CoStar, JLL, and CBRE data integration in Phase 3.</li></ul>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Macro Overlay
# ══════════════════════════════════════════════════════════════════════════════

with tab_macro:
    from fetchers.fred_fetcher import fetch_all_macro

    _m_lbl, _m_btn = st.columns([5, 1])
    with _m_lbl:
        st.markdown(
            '<div class="sec-lbl">FRED macro overlay &nbsp;&middot;&nbsp; live St. Louis Fed data &nbsp;&middot;&nbsp; '
            '4-hour cache &nbsp;&middot;&nbsp; capital markets → innovation economy office &amp; lab fundamentals</div>',
            unsafe_allow_html=True,
        )
    with _m_btn:
        _macro_refresh = st.button("Refresh Data", key="macro_refresh")

    @st.cache_data(ttl=14400, show_spinner=False)
    def _load_macro():
        return fetch_all_macro()

    if _macro_refresh:
        st.cache_data.clear()
    with st.spinner("Fetching FRED data..."):
        _macro = _load_macro()

    def _latest(s):
        if s is None or len(s) == 0: return None
        return float(s.dropna().iloc[-1])

    def _yoy(s):
        if s is None or len(s) < 13: return None
        v = s.dropna()
        return (float(v.iloc[-1]) / float(v.iloc[-13]) - 1.0) * 100.0

    def _chg(s):
        if s is None or len(s) < 2: return None
        v = s.dropna()
        return float(v.iloc[-1]) - float(v.iloc[-2])

    def _fmt(val, suffix="", dec=2, sign=False):
        if val is None: return "—"
        prefix = "+" if sign and val > 0 else ""
        return f"{prefix}{val:.{dec}f}{suffix}"

    def _fmt_dollar(val):
        if val is None: return "—"
        if val >= 1_000_000: return f"${val/1_000_000:.2f}M"
        if val >= 1_000:     return f"${val/1_000:.1f}K"
        return f"${val:,.0f}"

    gs10  = _macro.get("gs10");  gs2  = _macro.get("gs2")
    cpi   = _macro.get("cpi");   prm  = _macro.get("permits")
    unem  = _macro.get("unemployment")

    gs10_val = _latest(gs10);  gs2_val  = _latest(gs2)
    spread   = (gs10_val - gs2_val) if gs10_val and gs2_val else None
    cpi_yoy  = _yoy(cpi)
    prm_val  = _latest(prm);   unem_val = _latest(unem)

    _BENCH_CAP = 6.0  # innovation economy office/lab cap rate proxy
    cap_spread_bps = int((_BENCH_CAP - gs10_val) * 100) if gs10_val else None
    if cap_spread_bps is not None:
        if cap_spread_bps < 0:
            _spread_cls, _spread_icon, _spread_msg = "high-risk", "NEGATIVE SPREAD", \
                f"Innovation economy cap rates ({_BENCH_CAP:.1f}%) are BELOW the 10Y Treasury ({gs10_val:.2f}%). Acquisition discipline critical — yield premium has evaporated."
        elif cap_spread_bps < CAP_SPREAD_WARN_BPS:
            _spread_cls, _spread_icon, _spread_msg = "moderate", "COMPRESSED — WATCH", \
                f"Cap rate spread at {cap_spread_bps}bps — below the {CAP_SPREAD_WARN_BPS}bps institutional threshold. Value-add conversion premium and below-market rent upside are the required buffers."
        else:
            _spread_cls, _spread_icon, _spread_msg = "ok", f"{cap_spread_bps}bps SPREAD", \
                f"Cap rate spread at {cap_spread_bps}bps above 10Y Treasury. Adequate risk premium for innovation economy office/lab; acquisition window remains open for stabilized assets."
    else:
        _spread_cls, _spread_icon, _spread_msg = "na", "—", "FRED data unavailable."

    _spread_color = {"ok": DW_GREEN, "moderate": DW_AMBER, "high-risk": DW_RED, "na": DW_MID}[_spread_cls]
    _spread_bg    = {"ok": DW_GREEN_LT, "moderate": DW_AMBER_LT, "high-risk": DW_RED_LT, "na": "#eee"}[_spread_cls]

    st.markdown(f"""
    <div style="background:{_spread_bg};border-left:4px solid {_spread_color};
         padding:12px 16px;margin-bottom:14px;
         font-family:'Helvetica Neue',Arial,sans-serif;">
      <div style="font-size:9px;letter-spacing:0.14em;text-transform:uppercase;
           font-weight:600;color:{_spread_color};margin-bottom:4px;">
        Cap Rate Spread Signal &nbsp;·&nbsp; {_spread_icon}
      </div>
      <div style="font-size:12px;color:{DW_NAVY};line-height:1.6;">{_spread_msg}</div>
      <div style="font-size:10px;color:{DW_MID};margin-top:4px;">
        Benchmark cap rate: {_BENCH_CAP:.1f}% (innovation economy office/lab proxy) &nbsp;·&nbsp;
        Live 10Y: {_fmt(gs10_val,'%')} &nbsp;·&nbsp;
        Source: FRED GS10
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sec-lbl" style="margin-bottom:4px;">Capital Markets &amp; Employment</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="mi-stats" style="margin-bottom:12px;">
      <div class="mi-stat"><div class="mi-stat-val">{_fmt(gs10_val,'%')}</div><div class="mi-stat-lbl">10Y Treasury</div><div class="mi-stat-src">FRED GS10 — live</div></div>
      <div class="mi-stat"><div class="mi-stat-val">{_fmt(gs2_val,'%')}</div><div class="mi-stat-lbl">2Y Treasury</div><div class="mi-stat-src">FRED GS2 — live</div></div>
      <div class="mi-stat">
        <div class="mi-stat-val" style="font-size:18px;font-weight:300;color:{'#5a9e70' if spread and spread>=0 else '#c47070'}">
          {_fmt(spread,'%',sign=True)}</div>
        <div class="mi-stat-lbl">Yield Curve (10Y−2Y)</div><div class="mi-stat-src">FRED GS10 − GS2</div>
      </div>
      <div class="mi-stat">
        <div class="mi-stat-val" style="color:{'#c47070' if cpi_yoy and cpi_yoy>3 else '#5a9e70'}">{_fmt(cpi_yoy,'%',sign=True)}</div>
        <div class="mi-stat-lbl">CPI Inflation YOY</div><div class="mi-stat-src">FRED CPIAUCSL</div>
      </div>
      <div class="mi-stat"><div class="mi-stat-val" style="color:var(--dw-steel);">{_fmt(unem_val,'%')}</div><div class="mi-stat-lbl">Unemployment Rate</div><div class="mi-stat-src">FRED UNRATE</div></div>
      <div class="mi-stat"><div class="mi-stat-val" style="color:var(--dw-steel);">{f"{prm_val:.0f}K" if prm_val else "—"}</div><div class="mi-stat-lbl">Building Permits (SAAR)</div><div class="mi-stat-src">FRED PERMIT</div></div>
    </div>
    """, unsafe_allow_html=True)

    def _dark_layout(title, yformat=".2f", height=260):
        return dict(
            paper_bgcolor="#0F2040", plot_bgcolor="#0F2040",
            font=dict(color="#7a9bbf", family="Helvetica Neue, Arial", size=10),
            title=dict(text=title, font=dict(color="#7a9bbf", size=9), x=0, xanchor="left", pad=dict(l=0, t=4)),
            xaxis=dict(gridcolor="#1A2535", linecolor="#2A3A4A", tickfont=dict(size=9)),
            yaxis=dict(gridcolor="#1A2535", linecolor="#2A3A4A", tickfont=dict(size=9), tickformat=yformat),
            margin=dict(l=50, r=16, t=36, b=36),
            height=height,
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9), x=0.01, y=0.99),
            hovermode="x unified",
            hoverlabel=dict(bgcolor="#0F2040", bordercolor="#2D6AA0", font=dict(color="#fff", size=10)),
        )

    def _line(s, name, color="#2D6AA0", dash="solid", width=1.5):
        if s is None or len(s) == 0: return go.Scatter(x=[], y=[], name=name)
        v = s.dropna()
        return go.Scatter(x=v.index, y=v.values, name=name, mode="lines",
                          line=dict(color=color, width=width, dash=dash),
                          hovertemplate=f"%{{y:.2f}} ({name})<extra></extra>")

    def _yoy_series(s):
        if s is None or len(s) < 13: return None
        v = s.dropna()
        return (v / v.shift(12) - 1) * 100

    _cfg = {"displayModeBar": False}

    st.markdown('<div class="sec-lbl" style="margin:8px 0 4px;">Rate Environment — Treasury vs. Cap Rate Proxy</div>', unsafe_allow_html=True)
    _f1 = go.Figure()
    if gs10 is not None: _f1.add_trace(_line(gs10, "10Y Treasury (GS10)", "#2D6AA0"))
    if gs2  is not None: _f1.add_trace(_line(gs2,  "2Y Treasury (GS2)",   "#3A5A7A", dash="dot"))
    _f1.add_hline(y=_BENCH_CAP, line=dict(color="#1E5C3A", width=1, dash="dash"),
                  annotation_text=f"Cap Rate Proxy {_BENCH_CAP}%",
                  annotation_font=dict(color="#1E5C3A", size=9))
    if gs10_val:
        _f1.add_hline(y=1.5 + gs10_val, line=dict(color="#4a6a8a", width=0.5, dash="dot"),
                      annotation_text="150bps spread threshold", annotation_font=dict(color="#4a6a8a", size=8))
    _f1.update_layout(**_dark_layout("10Y &amp; 2Y TREASURY RATES VS. INNOVATION ECONOMY CAP RATE PROXY  (%)"))
    st.plotly_chart(_f1, use_container_width=True, config=_cfg)

    st.markdown('<div class="sec-lbl" style="margin:8px 0 4px;">Inflation &amp; Employment</div>', unsafe_allow_html=True)
    _r2c1, _r2c2 = st.columns(2)
    with _r2c1:
        _f2 = go.Figure()
        _cpi_yoy_s = _yoy_series(cpi)
        if _cpi_yoy_s is not None: _f2.add_trace(_line(_cpi_yoy_s, "CPI All Items YOY", "#2D6AA0"))
        _f2.add_hline(y=2.0, line=dict(color="#1E5C3A", width=1, dash="dash"),
                      annotation_text="Fed Target 2%", annotation_font=dict(color="#1E5C3A", size=9))
        _f2.update_layout(**_dark_layout("CPI INFLATION — ALL ITEMS  (YOY %)", yformat=".1f"))
        st.plotly_chart(_f2, use_container_width=True, config=_cfg)
    with _r2c2:
        _f_unem = go.Figure()
        if unem is not None:
            _uv = unem.dropna()
            _f_unem.add_trace(go.Scatter(x=_uv.index, y=_uv.values, name="Unemployment Rate",
                mode="lines", line=dict(color="#2D6AA0", width=1.5),
                hovertemplate="%{y:.1f}%<extra></extra>",
                fill="tozeroy", fillcolor="rgba(45,106,160,0.08)"))
        _f_unem.update_layout(**_dark_layout("UNEMPLOYMENT RATE  (%)", yformat=".1f"))
        st.plotly_chart(_f_unem, use_container_width=True, config=_cfg)

    st.markdown('<div class="sec-lbl" style="margin:8px 0 4px;">Supply Pipeline — National Building Permits</div>', unsafe_allow_html=True)
    _f4 = go.Figure()
    if prm is not None:
        _pv = prm.dropna()
        _f4.add_trace(go.Bar(x=_pv.index, y=_pv.values, name="Building Permits (K, SAAR)",
            marker_color="#2D6AA0", marker_line_width=0, opacity=0.8,
            hovertemplate="%{y:.0f}K units SAAR<extra></extra>"))
    _f4.update_layout(**_dark_layout("NATIONAL BUILDING PERMITS (SAAR, thousands) — leading indicator for new competitive supply", yformat=".0f"))
    _f4.update_layout(bargap=0.1)
    st.plotly_chart(_f4, use_container_width=True, config=_cfg)

    _all_s = [gs10, gs2, cpi, prm, unem]
    _macro_ts = max(
        (s.index[-1].strftime("%b %Y") for s in _all_s if s is not None and len(s) > 0),
        default="—",
    )
    st.markdown(
        f'<div class="src-bar">Sources: Federal Reserve Bank of St. Louis (FRED) &nbsp;&middot;&nbsp; '
        f'GS10 (10Y Treasury) · GS2 (2Y Treasury) · CPIAUCSL (CPI All Items) · PERMIT (Building Permits) · UNRATE (Unemployment) &nbsp;&middot;&nbsp; '
        f'Latest data: {_macro_ts} &nbsp;&middot;&nbsp; '
        f'Cap rate benchmark: {_BENCH_CAP}% (innovation economy office/lab proxy)</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — News Tracker
# ══════════════════════════════════════════════════════════════════════════════

with tab_news:
    _NEWS_SOURCES = [
        "Google News — DivcoWest", "Google News — DW Acquisitions",
        "Google News — Life Science CRE", "Google News — Innovation Office",
        "Google News — Austin CRE", "Google News — Austin Tech",
        "The Real Deal — SF", "The Real Deal — National", "The Real Deal — Commercial",
        "Commercial Observer", "REBusiness Online", "Connect CRE", "GlobeSt",
        "Bisnow", "Propmodo", "NREI", "Nareit",
    ]
    _NEWS_TOPICS = ["All", "DivcoWest", "Life Science", "Tech Office", "Transactions",
                    "Cap Rate", "Austin", "Boston / Cambridge", "Bay Area", "Lab Conversion"]

    _n_col1, _n_col2 = st.columns([3, 1])
    with _n_col1:
        _src_filter = st.pills("Source", ["All Sources"] + _NEWS_SOURCES,
                               selection_mode="single", default="All Sources", key="news_src")
    with _n_col2:
        _refresh_news = st.button("Refresh Feed", key="news_refresh")

    _topic_filter = st.pills("Topic", _NEWS_TOPICS,
                              selection_mode="single", default="All", key="news_topic")

    _TOPIC_KEYWORDS = {
        "DivcoWest":        ["DivcoWest", "Divco West"],
        "Life Science":     ["life science", "biotech", "lab", "pharmaceutical", "biopharma", "R&D"],
        "Tech Office":      ["tech office", "innovation economy", "creative office", "Silicon Beach", "South Lake Union"],
        "Transactions":     ["acquisition", "transaction", "portfolio", "sale", "sold", "purchased", "acquired"],
        "Cap Rate":         ["cap rate", "capitalization rate", "yield", "spread"],
        "Austin":           ["Austin", "Domain", "Domain NORTHSIDE", "UT Austin", "Dell Medical", "Pickle Research",
                             "Apple Austin", "Oracle Austin", "Tesla Austin", "Round Rock", "Cedar Park"],
        "Boston / Cambridge": ["Boston", "Cambridge", "Kendall Square", "Somerville", "Watertown"],
        "Bay Area":         ["San Francisco", "Mission Bay", "Bay Area", "Silicon Valley", "Oyster Point"],
        "Lab Conversion":   ["lab conversion", "office-to-lab", "lab-to-office", "conversion", "repositioning"],
    }

    @st.cache_data(ttl=3600, show_spinner=False)
    def _load_news():
        return fetch_news()

    with st.spinner("Loading CRE news feed..."):
        _articles = _load_news() if not _refresh_news else fetch_news(force=True)
        if _refresh_news:
            st.cache_data.clear()

    _now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    def _sort_key(a):
        dt = a.get("date")
        if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        days_old = max(0, (_now_utc - dt).days) if dt else 30
        return a.get("relevance", 0) / (1.0 + days_old)

    _dw_hits = sorted([a for a in _articles if a.get("is_dw")], key=_sort_key, reverse=True)
    if _dw_hits:
        st.markdown('<div class="news-dw-banner">DivcoWest — In the News</div>', unsafe_allow_html=True)
        for _a in _dw_hits[:5]:
            _dt = _a["date"].strftime("%b %d, %Y") if hasattr(_a["date"], "strftime") else str(_a["date"])[:10]
            st.markdown(f"""
            <div class="news-card dw-hit">
              <div class="news-card-meta">
                <span class="news-badge-dw">DW</span>
                <span class="news-badge-src">{_a['source']}</span>{_dt}
              </div>
              <div class="news-card-headline"><a href="{_a['link']}" target="_blank">{_a['title']}</a></div>
              {"<div class='news-card-summary'>" + _a['summary'] + "</div>" if _a['summary'] else ""}
            </div>
            """, unsafe_allow_html=True)

    _filtered = _articles
    if _src_filter and _src_filter != "All Sources":
        if _src_filter.startswith("Google News"):
            _filtered = [a for a in _filtered if a["source"].startswith(_src_filter)]
        else:
            _filtered = [a for a in _filtered if a["source"] == _src_filter]
    if _topic_filter and _topic_filter != "All":
        _kws = _TOPIC_KEYWORDS.get(_topic_filter, [])
        _filtered = [
            a for a in _filtered
            if any(kw.lower() in (a["title"] + " " + a["summary"]).lower() for kw in _kws)
        ]
    _filtered_cre = [a for a in _filtered if a.get("is_cre")]

    st.markdown(
        f'<div class="sec-lbl">{len(_filtered_cre)} CRE articles &nbsp;·&nbsp; {len(_dw_hits)} DivcoWest mentions &nbsp;·&nbsp; '
        f'{len(_articles)} total retrieved &nbsp;·&nbsp; Google News (4 queries) + 7 trade feeds &nbsp;·&nbsp; time-decayed relevance sort &nbsp;·&nbsp; 1-hour cache</div>',
        unsafe_allow_html=True,
    )

    if not _filtered_cre:
        st.markdown('<div class="news-empty">No articles match the current filter.</div>', unsafe_allow_html=True)
    else:
        for _a in sorted(_filtered_cre, key=_sort_key, reverse=True):
            _dt = _a["date"].strftime("%b %d, %Y") if hasattr(_a["date"], "strftime") else str(_a["date"])[:10]
            _dw_badge = '<span class="news-badge-dw">DW</span>' if _a.get("is_dw") else ""
            st.markdown(f"""
            <div class="news-card{"  dw-hit" if _a.get("is_dw") else ""}">
              <div class="news-card-meta">
                {_dw_badge}<span class="news-badge-src">{_a['source']}</span>{_dt}
              </div>
              <div class="news-card-headline"><a href="{_a['link']}" target="_blank">{_a['title']}</a></div>
              {"<div class='news-card-summary'>" + _a['summary'] + "</div>" if _a['summary'] else ""}
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — Deal Analyzer
# ══════════════════════════════════════════════════════════════════════════════

with tab_deal:
    st.markdown('<div class="sec-lbl">Innovation economy deal analyzer &nbsp;&middot;&nbsp; score any property against DivcoWest acquisition criteria &nbsp;&middot;&nbsp; 8 weighted criteria &nbsp;&middot;&nbsp; 0&ndash;100 scale</div>', unsafe_allow_html=True)

    with st.expander("Scoring methodology — how this analyzer works"):
        st.markdown(f"""
| Criterion | Weight | Key Driver |
|---|---|---|
| Innovation Cluster Fit | 20 pts | Tier 1 Core = 20, Tier 2 Growth = 14, Tier 3 Expansion = 7, Outside DivcoWest = 0 |
| DivcoWest Market Presence | 15 pts | Operational footprint (0–100) × 15. Higher presence = lower execution risk and shorter lease-up. |
| Cap Rate vs. 10Y Treasury | 15 pts | Spread in bps over {TREASURY_10Y_REF}% 10Y proxy. >175bps = 15 pts; negative = 0 pts. |
| Mark-to-Market / Rollover | 15 pts | (Market rent − In-place rent) / In-place rent. >15% gap = 15 pts; negative = 0 pts. |
| Occupancy vs. Market | 10 pts | Property vacancy vs. submarket benchmark. Underperforming asset = higher score (more operational upside). |
| Vintage / Lab Conversion | 10 pts | 1985–2010 = 10 pts (ideal conversion window). Pre-1985 or post-2018 = lower. |
| Supply Pipeline Risk | 10 pts | Market-level supply risk: Low = 10, Moderate = 6, High = 2. Based on Q1 2026 market data. |
| WALT / Tenant Commitment | 5 pts | ≥7yr WALT = 5 pts; <2yr = 0 pts. |

**Thresholds:** 75–100 = Advance to Due Diligence · 55–74 = Conditional Review · 35–54 = Monitor · 0–34 = Pass

*Market data as of Q1 2026 (CommercialCafe, JLL, Cushman &amp; Wakefield). 10Y Treasury reference: {TREASURY_10Y_REF}% (Phase 2 will pull live from FRED GS10).*
        """)

    col_form, col_result = st.columns([1, 1], gap="large")

    with col_form:
        st.markdown('<div class="deal-form-card"><div class="deal-form-title">Property Details</div>', unsafe_allow_html=True)

        with st.form("deal_form"):
            property_name = st.text_input("Property Name / Address",
                placeholder="e.g. 1 Kendall Square, Cambridge MA — Lab/Office")
            market = st.selectbox("Market", options=list(MARKET_DATA.keys()))
            asset_class = st.selectbox("Asset Class",
                ["Lab / Life Science", "Tech Office", "R&D Flex", "Office-to-Lab Conversion",
                 "Creative Office", "Mixed-Use Campus"])

            st.markdown("**Location & Size**")
            col_a, col_b = st.columns(2)
            with col_a:
                sqft = st.number_input("Rentable Sq Ft", min_value=5_000, max_value=2_000_000,
                                       value=100_000, step=5_000)
                year_built = st.number_input("Year Built", min_value=1960, max_value=2025, value=1998)
            with col_b:
                asking_price_m = st.number_input("Asking Price ($M)", min_value=0.5, max_value=2000.0,
                                                 value=75.0, step=1.0)
                noi_k = st.number_input("Annual NOI ($K)", min_value=0.0, value=4500.0, step=100.0,
                                        help="Net Operating Income before debt service")

            st.markdown("**Financial Metrics**")
            col_c, col_d = st.columns(2)
            with col_c:
                cap_rate = st.number_input("Going-in Cap Rate (%)", min_value=0.5, max_value=12.0,
                                           value=5.8, step=0.05, format="%.2f")
                inplace_rent = st.number_input("In-Place Rent ($/sqft/yr)", min_value=10.0, max_value=300.0,
                                               value=58.0, step=1.0)
            with col_d:
                vacancy = st.number_input("Current Vacancy (%)", min_value=0.0, max_value=70.0,
                                          value=18.0, step=0.5)
                market_rent = st.number_input("Market Rent ($/sqft/yr)", min_value=10.0, max_value=300.0,
                                              value=72.0, step=1.0,
                                              help="Current asking rent for comparable lab/office in this submarket")

            col_e, col_f = st.columns(2)
            with col_e:
                walt = st.number_input("WALT (years)", min_value=0.0, max_value=25.0,
                                       value=5.5, step=0.5, format="%.1f",
                                       help="Weighted average lease term across all tenants")
            with col_f:
                treasury_rate = st.number_input("10Y Treasury Rate (%)", min_value=1.0, max_value=10.0,
                                                value=TREASURY_10Y_REF, step=0.05, format="%.2f",
                                                help=f"Default: {TREASURY_10Y_REF}% (Q1 2026 proxy).")

            submitted = st.form_submit_button("Analyze Deal", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_result:
        if submitted:
            total, criteria, rec, rec_detail = score_deal(
                market=market,
                asset_class=asset_class,
                sqft=int(sqft),
                asking_price_m=float(asking_price_m),
                year_built=int(year_built),
                cap_rate_pct=float(cap_rate),
                inplace_rent_psf=float(inplace_rent),
                market_rent_psf=float(market_rent),
                vacancy_pct=float(vacancy),
                noi_k=float(noi_k) if noi_k else None,
                walt_years=float(walt),
                treasury_rate=float(treasury_rate),
            )

            if total >= 75:   score_color, rec_cls = DW_GREEN, "advance"
            elif total >= 55: score_color, rec_cls = DW_STEEL, "conditional"
            elif total >= 35: score_color, rec_cls = DW_AMBER, "monitor"
            else:             score_color, rec_cls = DW_RED,   "pass-box"

            prop_label = property_name if property_name.strip() else "Unnamed Property"
            price_psf  = asking_price_m * 1_000_000 / sqft if sqft > 0 else 0
            mtm        = (market_rent - inplace_rent) / inplace_rent * 100 if inplace_rent > 0 else 0
            spread_bps = (cap_rate - treasury_rate) * 100

            st.markdown(f"""
            <div class="score-hero">
              <div style="font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:var(--dw-mid);margin-bottom:8px;font-family:'Helvetica Neue',Arial,sans-serif;">{prop_label} &nbsp;&middot;&nbsp; {market}</div>
              <div class="score-num" style="color:{score_color};">{total}<span class="score-denom"> / 100</span></div>
              <div class="score-label">DivcoWest Innovation Economy Score</div>
            </div>
            <div class="rec-box {rec_cls}">
              <h5>Recommendation</h5>
              <p><strong>{rec}</strong> &mdash; {rec_detail}</p>
            </div>
            <div style="font-size:9px;letter-spacing:0.12em;text-transform:uppercase;color:var(--dw-mid);font-weight:600;margin-bottom:8px;font-family:'Helvetica Neue',Arial,sans-serif;">Score Breakdown</div>
            <div class="criterion-grid">
            """, unsafe_allow_html=True)

            for c in criteria:
                st.markdown(f"""
                <div class="criterion-card {c.status}">
                  <div class="criterion-name">{c.name}</div>
                  <div class="criterion-pts">{c.points_earned:.1f} <span style="font-size:11px;color:var(--dw-mid);font-weight:400;">/ {c.points_max}</span></div>
                  <div class="criterion-note">{c.note}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown(f"""
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--dw-border);margin-top:12px;margin-bottom:12px;">
              <div class="mi-stat" style="background:var(--dw-dark);">
                <div class="mi-stat-val" style="font-size:15px;">${price_psf:,.0f}</div>
                <div class="mi-stat-lbl">Price / Sq Ft</div>
              </div>
              <div class="mi-stat" style="background:var(--dw-dark);">
                <div class="mi-stat-val {'pos' if mtm > 0 else 'neg'}" style="font-size:15px;">{mtm:+.1f}%</div>
                <div class="mi-stat-lbl">Mark-to-Market Gap</div>
              </div>
              <div class="mi-stat" style="background:var(--dw-dark);">
                <div class="mi-stat-val {'pos' if spread_bps > 100 else 'neg'}" style="font-size:15px;">{spread_bps:.0f}bps</div>
                <div class="mi-stat-lbl">Cap Rate Spread</div>
              </div>
              <div class="mi-stat" style="background:var(--dw-dark);">
                <div class="mi-stat-val" style="font-size:15px;">{MARKET_DATA.get(market,{{}}).get('dw_presence','—')}/100</div>
                <div class="mi-stat-lbl">DivcoWest Presence</div>
              </div>
            </div>
            <div class="disclaimer">
              Analysis generated by DivcoWest Investment Intelligence v1.0 &nbsp;&middot;&nbsp; Market data as of Q1 2026 (CommercialCafe, JLL, Cushman &amp; Wakefield) &nbsp;&middot;&nbsp;
              10Y Treasury reference rate: {treasury_rate:.2f}% &nbsp;&middot;&nbsp; This tool is for preliminary screening only and does not constitute investment advice.
              All acquisitions subject to DivcoWest's full underwriting, due diligence, and Investment Committee approval process.
            </div>
            """, unsafe_allow_html=True)

        else:
            st.markdown("""
            <div class="phase-placeholder" style="margin-top:40px;">
              <h3>Enter property details to generate score</h3>
              <p>Complete the form to receive a scored analysis across 8 DivcoWest acquisition criteria,<br>
              including DivcoWest's operational presence in the target innovation market as a first-class risk input.</p>
            </div>
            """, unsafe_allow_html=True)
