"""
CRE news RSS aggregator + TRD full-text scraper + Google News.
DivcoWest edition: life science, tech office, innovation economy focus.
1-hour parquet cache.
"""
from datetime import datetime, timezone
import re
import feedparser
import requests
from bs4 import BeautifulSoup

from utils.cache import read_cache, write_cache
from utils.logger import get_logger

logger = get_logger(__name__)

_TTL = 1

_DW_KEYWORDS = ["DivcoWest", "Divco West", "divcowest", "Divco west"]

_KEYWORD_WEIGHTS: dict[str, int] = {
    # Tier 1 — DivcoWest identity
    "DivcoWest":             100,
    "Divco West":            100,
    "Stuart Shiff":           80,   # DivcoWest CEO/Founder

    # Tier 2 — deal signals
    "value-add":              18,
    "mark-to-market":         16,
    "lab conversion":         20,
    "lab-to-office":          18,
    "acquired":               12,
    "acquisition":            12,
    "joint venture":          10,
    "ground-up":              10,
    "lease-up":               10,
    "development":             8,
    "disposition":             8,
    "refinancing":             7,
    "recapitalization":        7,
    "transaction":             6,
    "closed":                  5,
    "portfolio":               5,
    "per square foot":         8,
    "per sq ft":               8,
    "WALT":                   10,
    "weighted average lease":  9,

    # Tier 3 — asset types
    "life science":           18,
    "lab":                    15,
    "biotech":                12,
    "innovation economy":     14,
    "tech office":            12,
    "creative office":         8,
    "R&D":                    10,
    "research and development": 9,
    "science park":           10,
    "office":                  5,
    "mixed-use":               4,
    "campus":                  7,

    # Tier 4 — innovation economy markets
    "San Francisco":          10,
    "Mission Bay":            12,
    "Bay Area":                9,
    "Silicon Valley":          9,
    "Boston":                  9,
    "Cambridge":               9,
    "Kendall Square":         14,
    "Los Angeles":             8,
    "Culver City":             9,
    "Playa Vista":             9,
    "San Diego":               9,
    "Torrey Pines":           10,
    "Sorrento Valley":         9,
    "Seattle":                 8,
    "South Lake Union":       10,
    # Austin — elevated weighting (DivcoWest strategic priority market)
    "Austin":                 14,
    "The Domain":             12,
    "Domain NORTHSIDE":       13,
    "Domain North":           11,
    "UT Austin":              10,
    "Dell Medical":           11,
    "Pickle Research":        10,
    "Apple Austin":           11,
    "Oracle Austin":          10,
    "Tesla Austin":            9,
    "Round Rock":              8,
    "Cedar Park":              7,
    "Raleigh":                 7,
    "Research Triangle":      10,
    "Washington DC":           7,
    "Bethesda":                9,
    "NIH":                     9,
    "New York":                6,
    "Denver":                  6,
    "Miami":                   6,
    "Chicago":                 5,

    # Tier 5 — financial / performance
    "cap rate":               10,
    "NOI":                     8,
    "rent growth":            10,
    "rent spread":             9,
    "vacancy":                 7,
    "occupancy":               6,
    "absorption":              8,
    "net absorption":          9,
    "supply":                  5,
    "pipeline":                6,
    "deliveries":              6,
    "asking rent":             7,
    "interest rate":           5,
    "SOFR":                    5,
    "cost basis":              7,
    "cap rate spread":         9,

    # Tier 6 — ecosystem
    "REIT":                    7,
    "Alexandria":              9,   # ARE — top comp
    "Boston Properties":       7,   # BXP
    "Kilroy":                  8,   # KRC
    "CBRE":                    4,
    "JLL":                     4,
    "Newmark":                 4,
    "Biomed Realty":           9,
    "Ventas":                  7,
    "HealthPeak":              7,
    "NAREIT":                  6,
    "CoStar":                  5,
    "Bisnow":                  5,

    # Tier 7 — general CRE
    "commercial real estate":  4,
    "office market":           5,
    "lab market":              8,
    "innovation":              5,
}

_CRE_THRESHOLD = 6

_NEGATIVE_WEIGHTS: dict[str, int] = {
    "multifamily":    -4,
    "apartment":      -4,
    "residential":    -3,
    "self-storage":   -4,
    "data center":    -3,
    "hotel":          -4,
    "retail":         -3,
    "homebuilder":    -5,
    "single-family":  -4,
}

_FEEDS = [
    ("The Real Deal — SF",            "https://therealdeal.com/sanfrancisco/feed/"),
    ("The Real Deal — National",      "https://therealdeal.com/national/feed/"),
    ("The Real Deal — Commercial",    "https://therealdeal.com/category/commercial/feed/"),
    ("Commercial Observer",           "https://commercialobserver.com/feed/"),
    ("REBusiness Online",             "https://rebusinessonline.com/feed/"),
    ("Connect CRE",                   "https://www.connectcre.com/feed/"),
    ("GlobeSt",                       "https://www.globest.com/rss/"),
    ("Bisnow",                        "https://www.bisnow.com/rss"),
    ("Propmodo",                      "https://propmodo.com/feed/"),
    ("NREI",                          "https://www.nreionline.com/rss"),
    ("Nareit",                        "https://www.reit.com/news/rss"),
]

_GOOGLE_NEWS_FEEDS = [
    ("Google News — DivcoWest",
     'https://news.google.com/rss/search?q=%22DivcoWest%22&hl=en-US&gl=US&ceid=US:en',
     True),
    ("Google News — DW Acquisitions",
     'https://news.google.com/rss/search?q=%22DivcoWest%22+acquired+OR+purchased+OR+acquires+OR+sells&hl=en-US&gl=US&ceid=US:en',
     True),
    ("Google News — Life Science CRE",
     'https://news.google.com/rss/search?q=%22life+science%22+%22real+estate%22+office+lab&hl=en-US&gl=US&ceid=US:en',
     False),
    ("Google News — Innovation Office",
     'https://news.google.com/rss/search?q=%22tech+office%22+OR+%22innovation+economy%22+%22real+estate%22&hl=en-US&gl=US&ceid=US:en',
     False),
    ("Google News — Austin CRE",
     'https://news.google.com/rss/search?q=Austin+%22commercial+real+estate%22+OR+%22office%22+OR+%22tech+campus%22&hl=en-US&gl=US&ceid=US:en',
     False),
    ("Google News — Austin Tech",
     'https://news.google.com/rss/search?q=Austin+%22The+Domain%22+OR+%22UT+Austin%22+OR+%22Dell+Medical%22+tech+office&hl=en-US&gl=US&ceid=US:en',
     False),
]

_TRD_DW_SEARCH_URLS = [
    "https://therealdeal.com/sanfrancisco/?s=DivcoWest",
    "https://therealdeal.com/national/?s=DivcoWest",
]
_TRD_BASE = "https://therealdeal.com"

_HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}


def _parse_date(entry) -> datetime:
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)


def _relevance_score(title: str, summary: str) -> int:
    t_lo = title.lower()
    s_lo = summary.lower()
    both = t_lo + " " + s_lo
    score = 0

    for kw, weight in _KEYWORD_WEIGHTS.items():
        kw_l = kw.lower()
        if kw_l in t_lo:
            score += weight * 3
        elif kw_l in s_lo:
            score += weight

    for kw, penalty in _NEGATIVE_WEIGHTS.items():
        if kw.lower() in both:
            score += penalty

    _deal_verbs  = {"acquired", "purchased", "acquires", "buys", "sells", "closed", "traded"}
    _asset_types = {"life science", "lab", "office", "biotech", "innovation", "research"}
    has_deal_verb  = any(v in both for v in _deal_verbs)
    has_asset_type = any(a in both for a in _asset_types)
    if has_deal_verb and has_asset_type:
        score += 15

    if re.search(r"\$\s*\d+\.?\d*\s*[mb]illion|\$\s*\d+[mb]", both, re.IGNORECASE):
        score += 10

    if re.search(r"\b\d{2,4}[\s,]?\d*\s*sq(?:uare)?\s*f(?:eet|t)\b", both, re.IGNORECASE):
        score += 8

    _dw_markets = {"san francisco", "mission bay", "kendall square", "cambridge", "culver city",
                   "playa vista", "torrey pines", "south lake union", "research triangle"}
    if has_deal_verb and any(m in both for m in _dw_markets):
        score += 10

    return max(score, 0)


def _fetch_article_text(url: str) -> str:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=12)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, "html.parser")
        for sel in ["article", ".article-body", ".post-content", ".entry-content", "main"]:
            body = soup.select_one(sel)
            if body:
                text = body.get_text(separator=" ", strip=True)
                if len(text) > 150:
                    return text[:2000]
    except Exception:
        pass
    return ""


def _make_article(source: str, title: str, summary: str, link: str,
                  date: datetime, full_text: str = "") -> dict:
    combined = title + " " + summary + " " + full_text
    is_dw    = any(kw.lower() in combined.lower() for kw in _DW_KEYWORDS)
    score    = _relevance_score(title, summary + " " + full_text[:600])
    is_cre   = is_dw or score >= _CRE_THRESHOLD
    return {
        "source":    source,
        "title":     title,
        "summary":   summary[:400] if summary else full_text[:400],
        "link":      link,
        "date":      date,
        "is_dw":     is_dw,
        "is_cre":    is_cre,
        "relevance": score + (1000 if is_dw else 0),
    }


def _fetch_feed(source_name: str, url: str) -> list[dict]:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=10)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
    except Exception as exc:
        logger.error("RSS fetch failed — %s: %s", source_name, exc)
        return []

    is_trd = "Real Deal" in source_name
    articles = []
    for entry in feed.entries:
        title   = getattr(entry, "title",   "").strip()
        summary = getattr(entry, "summary", "").strip()
        link    = getattr(entry, "link",    "").strip()
        if not title or not link:
            continue
        full_text = _fetch_article_text(link) if is_trd else ""
        articles.append(_make_article(source_name, title, summary, link, _parse_date(entry), full_text))
    return articles


def _fetch_google_news(label: str, url: str, force_dw: bool = False) -> list[dict]:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=12)
        r.raise_for_status()
        feed = feedparser.parse(r.content)
    except Exception as exc:
        logger.error("Google News fetch failed — %s: %s", label, exc)
        return []

    articles = []
    for entry in feed.entries:
        raw_title = getattr(entry, "title", "").strip()
        link      = getattr(entry, "link",  "").strip()
        summary   = getattr(entry, "summary", "").strip()
        if not raw_title or not link:
            continue

        parts = re.split(r"\s+[-–]\s+", raw_title)
        if len(parts) >= 2:
            title  = " - ".join(parts[:-1]).strip()
            pub    = parts[-1].strip()
            source = f"{label} / {pub}"
        else:
            title  = raw_title
            source = label

        if "<" in summary:
            summary = BeautifulSoup(summary, "html.parser").get_text(strip=True)

        art = _make_article(source, title, summary[:400], link, _parse_date(entry))
        if force_dw:
            art["is_dw"]     = True
            art["is_cre"]    = True
            art["relevance"] = max(art["relevance"], 1000)
        articles.append(art)

    logger.info("Google News fetched — %s: %d articles", label, len(articles))
    return articles


def _scrape_trd_dw_search() -> list[dict]:
    seen:     set[str]   = set()
    articles: list[dict] = []

    for search_url in _TRD_DW_SEARCH_URLS:
        try:
            r = requests.get(search_url, headers=_HEADERS, timeout=12)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "html.parser")
        except Exception as exc:
            logger.error("TRD search scrape failed — %s: %s", search_url, exc)
            continue

        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href", "")
            if not any(f"/{y}/" in href for y in ["2024", "2025", "2026", "2023"]):
                continue
            if not anchor.find("article"):
                continue

            link = (_TRD_BASE + href) if href.startswith("/") else href
            if link in seen:
                continue

            article_el = anchor.find("article")
            title_el   = article_el.select_one("h2, h3, [class*='title']") if article_el else None
            date_el    = article_el.select_one("[class*='date'] span, time") if article_el else None

            title = title_el.get_text(strip=True) if title_el else anchor.get_text(strip=True)[:120]
            if not title:
                continue

            date_str = date_el.get_text(strip=True) if date_el else ""
            try:
                date = datetime.strptime(date_str, "%B %d, %Y").replace(tzinfo=timezone.utc) if date_str else datetime.now(timezone.utc)
            except Exception:
                date = datetime.now(timezone.utc)

            seen.add(link)
            full_text = _fetch_article_text(link)
            summary   = full_text[:400] if full_text else ""

            art = _make_article("The Real Deal — SF", title, summary, link, date, full_text)
            if "divcowest" in link.lower() or "divco" in link.lower():
                art["is_dw"]     = True
                art["relevance"] = max(art["relevance"], 1000)
            art["is_cre"] = True
            articles.append(art)

    logger.info("TRD DW search: %d articles found", len(articles))
    return articles


def fetch_ticker_news(tickers: list[str], max_per_ticker: int = 3) -> dict[str, list[dict]]:
    """
    Fetch recent headlines for a list of REIT tickers via Yahoo Finance RSS.
    Returns {ticker: [article_dict, ...]} — empty list on any failure.
    """
    import requests
    import feedparser
    from datetime import datetime, timezone

    results: dict[str, list[dict]] = {}
    headers = {"User-Agent": "Mozilla/5.0"}

    for ticker in tickers:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
        try:
            r = requests.get(url, headers=headers, timeout=8)
            r.raise_for_status()
            feed = feedparser.parse(r.content)
            articles = []
            for entry in feed.entries[:max_per_ticker]:
                title = getattr(entry, "title", "").strip()
                link  = getattr(entry, "link",  "").strip()
                if not title or not link:
                    continue
                articles.append({
                    "title":  title,
                    "link":   link,
                    "date":   _parse_date(entry),
                    "source": "Yahoo Finance",
                })
            results[ticker] = articles
        except Exception as exc:
            logger.warning("fetch_ticker_news failed — %s: %s", ticker, exc)
            results[ticker] = []

    return results


def fetch_news(force: bool = False) -> list[dict]:
    """Return combined, deduplicated article list; 1-hour parquet cache."""
    import pandas as pd

    key = "dw_news_feed"
    if not force:
        cached = read_cache(key, ttl_hours=_TTL)
        if cached is not None and not cached.empty:
            records = cached.to_dict("records")
            for rec in records:
                if isinstance(rec.get("date"), str):
                    try:
                        rec["date"] = datetime.fromisoformat(rec["date"])
                    except Exception:
                        rec["date"] = datetime.now(timezone.utc)
                rec["is_dw"]     = bool(rec.get("is_dw"))
                rec["is_cre"]    = bool(rec.get("is_cre"))
                rec["relevance"] = int(rec.get("relevance", 0))
            return records

    all_articles: list[dict] = []
    seen_links:   set[str]   = set()

    def _add(arts: list[dict]):
        for art in arts:
            if art["link"] not in seen_links:
                seen_links.add(art["link"])
                all_articles.append(art)

    for label, url, force_dw in _GOOGLE_NEWS_FEEDS:
        _add(_fetch_google_news(label, url, force_dw=force_dw))

    _add(_scrape_trd_dw_search())

    for source_name, url in _FEEDS:
        _add(_fetch_feed(source_name, url))

    if not all_articles:
        return []

    df = pd.DataFrame(all_articles)
    df["date"] = df["date"].astype(str)
    write_cache(key, df)
    return all_articles
