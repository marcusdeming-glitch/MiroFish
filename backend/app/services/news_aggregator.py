"""
News aggregator for portfolio analysis.
Fetches from RSS feeds (Reuters, CNBC, MarketWatch, Yahoo Finance, etc.)
and filters articles relevant to portfolio holdings and their related industries.
"""

import re
import html
import time
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET

from ..utils.logger import get_logger

logger = get_logger('mirofish.portfolio.news')

# Cross-industry ripple relationships: news in industry X affects these sectors
INDUSTRY_RIPPLE = {
    "energy": ["utilities", "chemicals", "transportation", "materials", "industrials", "airlines"],
    "oil & gas": ["energy", "petrochemicals", "transportation", "plastics", "airlines"],
    "semiconductors": ["technology", "electronics", "automotive", "consumer electronics", "AI", "cloud"],
    "banking": ["finance", "real estate", "insurance", "credit", "fintech"],
    "real estate": ["construction", "banking", "materials", "retail", "reits"],
    "airlines": ["oil & gas", "energy", "tourism", "aerospace", "hospitality"],
    "retail": ["consumer discretionary", "logistics", "e-commerce", "real estate"],
    "healthcare": ["pharmaceuticals", "biotech", "insurance", "medical devices"],
    "technology": ["semiconductors", "software", "cloud", "AI", "cybersecurity", "telecom"],
    "automotive": ["semiconductors", "energy", "steel", "manufacturing", "ev"],
    "utilities": ["energy", "infrastructure", "government", "renewables"],
    "consumer staples": ["food", "agriculture", "retail", "packaging"],
    "materials": ["mining", "construction", "industrials", "chemicals"],
    "telecommunications": ["technology", "infrastructure", "media", "5g"],
    "industrials": ["manufacturing", "logistics", "defense", "aerospace"],
    "financials": ["banking", "insurance", "real estate", "fintech"],
    "consumer discretionary": ["retail", "automotive", "leisure", "hospitality"],
    "communication services": ["media", "telecom", "technology", "advertising"],
}

RSS_FEEDS = [
    {"name": "Reuters Business",   "url": "https://feeds.reuters.com/reuters/businessNews",    "source": "Reuters"},
    {"name": "Reuters Finance",    "url": "https://feeds.reuters.com/reuters/financialNews",   "source": "Reuters"},
    {"name": "CNBC Business",      "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html", "source": "CNBC"},
    {"name": "CNBC Finance",       "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html",  "source": "CNBC"},
    {"name": "MarketWatch",        "url": "https://feeds.marketwatch.com/marketwatch/topstories/", "source": "MarketWatch"},
    {"name": "Yahoo Finance",      "url": "https://finance.yahoo.com/rss/topstories",              "source": "Yahoo Finance"},
    {"name": "Investing.com",      "url": "https://www.investing.com/rss/news_25.rss",             "source": "Investing.com"},
    {"name": "FT Markets",         "url": "https://www.ft.com/rss/home/us",                        "source": "Financial Times"},
    {"name": "Bloomberg Markets",  "url": "https://feeds.bloomberg.com/markets/news.rss",          "source": "Bloomberg"},
    {"name": "WSJ Markets",        "url": "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines", "source": "WSJ"},
]

_NAMESPACE_MAP = {
    "media": "http://search.yahoo.com/mrss/",
    "dc":    "http://purl.org/dc/elements/1.1/",
    "atom":  "http://www.w3.org/2005/Atom",
}


def _clean_html(text: str) -> str:
    """Strip HTML tags and unescape entities."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def _parse_date(date_str: str) -> Optional[str]:
    """Parse an RFC 2822 or ISO date string into ISO format."""
    if not date_str:
        return None
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.isoformat()
    except Exception:
        return None


def _fetch_rss(url: str, timeout: int = 10) -> Optional[ET.Element]:
    """Fetch and parse an RSS XML document."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "MiroFish-PortfolioAnalyzer/1.0 (+https://github.com/666ghj/MiroFish)"
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return ET.fromstring(raw)
    except urllib.error.URLError as e:
        logger.warning(f"RSS fetch failed ({url}): {e}")
    except ET.ParseError as e:
        logger.warning(f"RSS parse failed ({url}): {e}")
    return None


def _extract_items(root: ET.Element, source_name: str) -> List[Dict[str, Any]]:
    """Extract news items from an RSS or Atom feed root element."""
    items = []
    ns = ""
    # Atom feeds wrap in {http://www.w3.org/2005/Atom}feed
    if root.tag.endswith('}feed'):
        ns = root.tag.split('}')[0] + '}'
        for entry in root.findall(f"{ns}entry"):
            title_el = entry.find(f"{ns}title")
            link_el  = entry.find(f"{ns}link")
            summary_el = entry.find(f"{ns}summary") or entry.find(f"{ns}content")
            date_el  = entry.find(f"{ns}updated") or entry.find(f"{ns}published")
            title   = _clean_html(title_el.text if title_el is not None else "")
            link    = (link_el.get('href') if link_el is not None else "") or ""
            summary = _clean_html(summary_el.text if summary_el is not None else "")
            pub_date = _parse_date(date_el.text if date_el is not None else "")
            if title:
                items.append({"title": title, "link": link, "summary": summary,
                              "published_at": pub_date, "source": source_name})
    else:
        # RSS 2.0
        channel = root.find('channel')
        if channel is None:
            return items
        for item in channel.findall('item'):
            def get(tag):
                el = item.find(tag)
                return el.text if el is not None else ""
            title   = _clean_html(get('title'))
            link    = get('link') or get('guid') or ""
            summary = _clean_html(get('description') or get('summary') or "")
            pub_date = _parse_date(get('pubDate') or get('dc:date'))
            if title:
                items.append({"title": title, "link": link, "summary": summary,
                              "published_at": pub_date, "source": source_name})
    return items


def _article_id(article: Dict[str, Any]) -> str:
    key = (article.get('link') or article.get('title', ''))
    return hashlib.md5(key.encode()).hexdigest()


def _matches(text: str, keywords: List[str]) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def _build_keywords(holdings: List[Dict[str, Any]]) -> List[str]:
    """Build keyword list from portfolio holdings: tickers, names, sectors, and related industries."""
    keywords = set()
    sectors_seen = set()

    for h in holdings:
        ticker = h.get('ticker', '')
        name   = h.get('name', '')
        sector = h.get('sector', '').lower()
        industry = h.get('industry', '').lower()

        if ticker:
            keywords.add(ticker.upper())
        if name and len(name) > 3:
            keywords.add(name)
        if sector:
            keywords.add(sector)
            sectors_seen.add(sector)
        if industry:
            keywords.add(industry)

    # Add related/ripple industries
    for sector in list(sectors_seen):
        for ripple_sector, related in INDUSTRY_RIPPLE.items():
            if sector in ripple_sector or ripple_sector in sector:
                keywords.update(related)
            for rel in related:
                if sector in rel or rel in sector:
                    keywords.add(ripple_sector)

    return [k for k in keywords if k]


def _tag_holdings(article: Dict[str, Any], holdings: List[Dict[str, Any]]) -> List[str]:
    """Return list of tickers whose company/sector appears in the article."""
    text = (article.get('title', '') + ' ' + article.get('summary', '')).lower()
    matched = []
    for h in holdings:
        ticker  = h.get('ticker', '').upper()
        name    = h.get('name', '').lower()
        sector  = h.get('sector', '').lower()
        industry = h.get('industry', '').lower()
        if (ticker.lower() in text
                or (name and len(name) > 3 and name in text)
                or (sector and sector in text)
                or (industry and industry in text)):
            matched.append(ticker)
    return matched


def _tag_cross_industry(article: Dict[str, Any], holdings: List[Dict[str, Any]]) -> List[str]:
    """Return tickers that may be indirectly impacted via cross-industry ripple."""
    text = (article.get('title', '') + ' ' + article.get('summary', '')).lower()
    affected = []
    for h in holdings:
        ticker = h.get('ticker', '').upper()
        sector = h.get('sector', '').lower()
        if not sector:
            continue
        for ripple_sector, related_list in INDUSTRY_RIPPLE.items():
            # Check if article mentions a sector that ripples into this holding's sector
            if any(r in text for r in related_list) and (sector in ripple_sector or ripple_sector in sector):
                if ticker not in affected:
                    affected.append(ticker)
    return affected


def fetch_portfolio_news(holdings: List[Dict[str, Any]], max_articles: int = 60,
                         days_back: int = 7) -> List[Dict[str, Any]]:
    """
    Fetch and filter news relevant to the given portfolio holdings.

    Returns a deduplicated list of articles sorted newest-first, each tagged
    with directly and indirectly affected tickers.
    """
    if not holdings:
        return []

    keywords = _build_keywords(holdings)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    seen_ids: set = set()
    articles: List[Dict[str, Any]] = []

    for feed in RSS_FEEDS:
        try:
            root = _fetch_rss(feed['url'])
            if root is None:
                continue
            raw_items = _extract_items(root, feed['source'])
            for item in raw_items:
                art_id = _article_id(item)
                if art_id in seen_ids:
                    continue
                # Date filter
                if item.get('published_at'):
                    try:
                        pub_dt = datetime.fromisoformat(item['published_at'])
                        if pub_dt.tzinfo is None:
                            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                        if pub_dt < cutoff:
                            continue
                    except Exception:
                        pass
                # Relevance filter
                full_text = item.get('title', '') + ' ' + item.get('summary', '')
                if not _matches(full_text, keywords):
                    continue
                seen_ids.add(art_id)
                item['id']              = art_id
                item['direct_tickers']  = _tag_holdings(item, holdings)
                item['ripple_tickers']  = _tag_cross_industry(item, holdings)
                item['affected_tickers'] = list(set(item['direct_tickers'] + item['ripple_tickers']))
                articles.append(item)
        except Exception as e:
            logger.error(f"Error processing feed {feed['name']}: {e}")
        time.sleep(0.3)  # polite crawl delay

    # Sort newest-first
    def sort_key(a):
        try:
            return datetime.fromisoformat(a.get('published_at') or '2000-01-01T00:00:00+00:00')
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    articles.sort(key=sort_key, reverse=True)
    return articles[:max_articles]
