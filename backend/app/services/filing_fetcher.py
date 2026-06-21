"""
Filing fetcher for portfolio analysis.
Pulls recent filings from SEC EDGAR (10-K, 10-Q, 8-K) and SGX announcements.
No API keys required — uses public endpoints.
"""

import json
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from ..utils.logger import get_logger

logger = get_logger('mirofish.portfolio.filings')

EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_SEARCH_URL       = "https://efts.sec.gov/LATEST/search-index?q=%22{query}%22&forms={forms}&dateRange=custom&startdt={start_date}&enddt={end_date}"
EDGAR_CIK_LOOKUP_URL   = "https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={ticker}&type=&dateb=&owner=include&count=10&search_text=&action=getcompany&output=atom"
EDGAR_FILING_BASE      = "https://www.sec.gov/Archives/edgar/full-index/"
EDGAR_VIEWER_BASE      = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form_type}&dateb=&owner=include&count=5&output=atom"

SGX_ANNOUNCEMENTS_URL  = "https://api.sgx.com/securities/v1.1/announcements?params=%7B%22marketType%22%3A%22securities%22%2C%22securities%22%3A%5B%7B%22code%22%3A%22{code}%22%7D%5D%7D"
SGX_SEARCH_URL         = "https://api2.sgx.com/sites/default/files/feeds/securities-announcements.json"

_HEADERS = {
    "User-Agent": "MiroFish-PortfolioAnalyzer/1.0 (research; contact@mirofish.io)",
    "Accept": "application/json",
}


def _get(url: str, timeout: int = 15) -> Optional[Any]:
    """GET JSON from a URL, return parsed dict/list or None on failure."""
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        return json.loads(raw)
    except urllib.error.HTTPError as e:
        logger.warning(f"HTTP {e.code} fetching {url}")
    except urllib.error.URLError as e:
        logger.warning(f"URL error fetching {url}: {e}")
    except json.JSONDecodeError as e:
        logger.warning(f"JSON decode error fetching {url}: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error fetching {url}: {e}")
    return None


def _get_xml_text(url: str, timeout: int = 15) -> Optional[str]:
    """GET raw XML/text from a URL."""
    try:
        req = urllib.request.Request(url, headers={**_HEADERS, "Accept": "application/xml,text/xml,*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        logger.warning(f"Text fetch failed {url}: {e}")
    return None


# ─────────────────────────── SEC EDGAR ───────────────────────────

def _resolve_cik(ticker: str) -> Optional[str]:
    """Resolve a US ticker to an SEC CIK number using EDGAR's company search."""
    data = _get(f"https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={ticker}&type=10-K&dateb=&owner=include&count=5&search_text=&action=getcompany&output=atom")
    # Fallback: use the company_tickers.json mapping maintained by EDGAR
    tickers_data = _get("https://www.sec.gov/files/company_tickers.json")
    if tickers_data:
        for _, entry in tickers_data.items():
            if entry.get('ticker', '').upper() == ticker.upper():
                return str(entry['cik_str']).zfill(10)
    return None


def _parse_recent_filings(submissions: Dict[str, Any], form_types: List[str],
                           days_back: int = 90) -> List[Dict[str, Any]]:
    """Extract recent filings of given types from an EDGAR submissions response."""
    filings = []
    recent = submissions.get('filings', {}).get('recent', {})
    if not recent:
        return filings

    forms       = recent.get('form', [])
    dates       = recent.get('filingDate', [])
    accessions  = recent.get('accessionNumber', [])
    descriptions = recent.get('primaryDocument', [])

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days_back)).date()

    for i, form in enumerate(forms):
        if form not in form_types:
            continue
        date_str = dates[i] if i < len(dates) else ""
        try:
            filing_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if filing_date < cutoff:
                continue
        except ValueError:
            continue

        accession = accessions[i] if i < len(accessions) else ""
        cik = submissions.get('cik', '')
        acc_clean = accession.replace('-', '')
        link = f"https://www.sec.gov/Archives/edgar/full-index/{date_str[:4]}/QTR{(int(date_str[5:7])-1)//3+1}/"
        viewer_link = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form}&dateb=&owner=include&count=5"

        filings.append({
            "form_type":    form,
            "filed_date":   date_str,
            "accession":    accession,
            "link":         viewer_link,
            "source":       "SEC EDGAR",
            "description":  f"{form} filing",
        })

    return filings


def fetch_sec_filings(ticker: str, form_types: Optional[List[str]] = None,
                      days_back: int = 90) -> List[Dict[str, Any]]:
    """
    Fetch recent SEC filings for a US ticker.
    Defaults to 8-K (material events), 10-Q (quarterly), 10-K (annual).
    """
    if form_types is None:
        form_types = ["8-K", "10-Q", "10-K"]

    cik = _resolve_cik(ticker)
    if not cik:
        logger.info(f"Could not resolve CIK for {ticker}")
        return []

    url = EDGAR_SUBMISSIONS_URL.format(cik=cik)
    data = _get(url)
    if not data:
        return []

    filings = _parse_recent_filings(data, form_types, days_back)

    entity_name = data.get('name', ticker)
    for f in filings:
        f['ticker']      = ticker.upper()
        f['entity_name'] = entity_name

    return filings


def fetch_sec_search(query: str, form_types: Optional[List[str]] = None,
                     days_back: int = 30) -> List[Dict[str, Any]]:
    """Search EDGAR full-text for a query string across recent filings."""
    if form_types is None:
        form_types = ["8-K", "10-K", "10-Q"]
    forms_str = ",".join(form_types)

    end_date   = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    url = EDGAR_SEARCH_URL.format(
        query=urllib.parse.quote(query),
        forms=forms_str,
        start_date=start_date,
        end_date=end_date,
    )
    data = _get(url)
    if not data:
        return []

    results = []
    for hit in data.get('hits', {}).get('hits', [])[:10]:
        src = hit.get('_source', {})
        results.append({
            "ticker":      query.upper(),
            "form_type":   src.get('form_type', ''),
            "filed_date":  src.get('file_date', ''),
            "entity_name": src.get('entity_name', query),
            "description": src.get('form_type', '') + " — " + src.get('entity_name', ''),
            "link":        f"https://www.sec.gov/Archives/edgar/data/{src.get('entity_id', '')}/{src.get('file_num', '')}",
            "source":      "SEC EDGAR",
        })
    return results


# ─────────────────────────── SGX ───────────────────────────

def fetch_sgx_filings(ticker_or_code: str, days_back: int = 30) -> List[Dict[str, Any]]:
    """
    Fetch recent SGX announcements for a stock code.
    SGX codes are typically 4-character alphanumeric (e.g. D05, Z74, ES3).
    """
    code = ticker_or_code.upper().strip()
    url  = SGX_ANNOUNCEMENTS_URL.format(code=urllib.parse.quote(code))
    data = _get(url)
    if not data:
        return []

    filings = []
    cutoff  = datetime.now(timezone.utc) - timedelta(days=days_back)

    announcements = data if isinstance(data, list) else data.get('data', data.get('announcements', []))
    if not isinstance(announcements, list):
        return []

    for ann in announcements[:20]:
        date_str = ann.get('date', ann.get('announcementDate', ann.get('dateTime', '')))
        try:
            if 'T' in date_str:
                ann_dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                ann_dt = datetime.strptime(date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if ann_dt < cutoff:
                continue
        except Exception:
            pass

        title = ann.get('title', ann.get('headline', ann.get('announcement', '')))
        link  = ann.get('url', ann.get('link', f"https://www.sgx.com/securities/announcements"))

        filings.append({
            "ticker":      code,
            "form_type":   ann.get('category', ann.get('type', 'Announcement')),
            "filed_date":  date_str[:10] if date_str else '',
            "entity_name": ann.get('companyName', ann.get('name', code)),
            "description": title,
            "link":        link,
            "source":      "SGX",
        })

    return filings


# ─────────────────────────── Combined ───────────────────────────

def fetch_all_filings(holdings: List[Dict[str, Any]], days_back: int = 30) -> List[Dict[str, Any]]:
    """
    Fetch filings for all holdings in a portfolio.
    Automatically routes US tickers to SEC EDGAR and SGX codes to SGX.
    """
    all_filings: List[Dict[str, Any]] = []

    for holding in holdings:
        ticker   = holding.get('ticker', '').upper()
        exchange = holding.get('exchange', 'NYSE').upper()

        if not ticker:
            continue

        try:
            if 'SGX' in exchange or exchange in ('SGX', 'SI'):
                filings = fetch_sgx_filings(ticker, days_back=days_back)
            else:
                # US exchanges: NYSE, NASDAQ, AMEX, etc.
                filings = fetch_sec_filings(ticker, days_back=days_back)
                # Also do a text search for the company name to catch related filings
                if not filings and holding.get('name'):
                    filings = fetch_sec_search(ticker, days_back=days_back)

            all_filings.extend(filings)
        except Exception as e:
            logger.error(f"Error fetching filings for {ticker}: {e}")

        time.sleep(0.5)  # Respect rate limits

    # Sort by filed date descending
    def sort_key(f):
        try:
            return datetime.strptime(f.get('filed_date', '2000-01-01')[:10], "%Y-%m-%d")
        except Exception:
            return datetime.min
    all_filings.sort(key=sort_key, reverse=True)
    return all_filings
