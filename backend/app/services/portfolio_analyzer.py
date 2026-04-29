"""
Portfolio analyzer — uses the LLM to evaluate news and filings impact on
each holding, map cross-industry effects, and produce structured analysis.
"""

import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger('mirofish.portfolio.analyzer')

SYSTEM_PROMPT = """You are a senior portfolio analyst and financial advisor with expertise in:
- Equity and ETF analysis across US (NYSE/NASDAQ) and Singapore (SGX) markets
- Cross-industry impact analysis (supply chains, macro linkages, sector correlations)
- Conservative, long-term portfolio management for passive investors
- Risk assessment based on real-world news events and regulatory filings

Your analysis style is:
- Factual and grounded in the provided news/filings
- Conservative — you flag genuine risks, not noise
- Clear about uncertainty — distinguish confirmed facts from potential impacts
- Actionable — each insight has a clear implication for the portfolio

Always structure your JSON responses exactly as specified."""


def _truncate(text: str, max_chars: int = 300) -> str:
    return text[:max_chars] + "..." if len(text) > max_chars else text


def _format_news_for_prompt(articles: List[Dict[str, Any]], max_items: int = 20) -> str:
    lines = []
    for i, art in enumerate(articles[:max_items]):
        src  = art.get('source', '')
        date = (art.get('published_at') or '')[:10]
        title = art.get('title', '')
        summary = _truncate(art.get('summary', ''), 200)
        affected = ', '.join(art.get('affected_tickers', []))
        lines.append(f"{i+1}. [{src} {date}] {title}\n   Summary: {summary}\n   Tickers possibly affected: {affected or 'general market'}")
    return '\n'.join(lines) if lines else "No recent news available."


def _format_filings_for_prompt(filings: List[Dict[str, Any]], max_items: int = 15) -> str:
    lines = []
    for i, f in enumerate(filings[:max_items]):
        ticker = f.get('ticker', '')
        form   = f.get('form_type', '')
        date   = f.get('filed_date', '')[:10]
        desc   = _truncate(f.get('description', ''), 150)
        source = f.get('source', '')
        lines.append(f"{i+1}. [{source}] {ticker} — {form} ({date}): {desc}")
    return '\n'.join(lines) if lines else "No recent filings available."


def _format_holdings_for_prompt(holdings: List[Dict[str, Any]]) -> str:
    lines = []
    total_cost = sum(h.get('shares', 0) * h.get('cost_basis', 0) for h in holdings)
    for h in holdings:
        ticker  = h.get('ticker', '')
        name    = h.get('name', ticker)
        shares  = h.get('shares', 0)
        cost    = h.get('cost_basis', 0)
        value   = shares * cost
        weight  = (value / total_cost * 100) if total_cost > 0 else 0
        sector  = h.get('sector', 'Unknown')
        htype   = h.get('holding_type', 'stock').upper()
        exchange = h.get('exchange', '')
        lines.append(f"- {ticker} ({name}) | {htype} | {exchange} | {sector} | {shares:.2f} shares @ {cost:.2f} | Portfolio weight: {weight:.1f}%")
    return '\n'.join(lines) if lines else "No holdings."


def analyze_portfolio(
    portfolio: Dict[str, Any],
    articles: List[Dict[str, Any]],
    filings: List[Dict[str, Any]],
    llm_client: Optional[LLMClient] = None,
) -> Dict[str, Any]:
    """
    Run LLM-based analysis of portfolio impact from recent news and filings.

    Returns a structured dict with:
    - overall_sentiment: bullish | neutral | cautious | bearish
    - market_summary: brief macro overview
    - holding_impacts: per-ticker impact analysis
    - cross_industry_insights: sector ripple effects observed
    - risk_flags: material risks identified
    - analysis_date: ISO timestamp
    """
    if llm_client is None:
        llm_client = LLMClient()

    holdings = portfolio.get('holdings', [])
    if not holdings:
        return {"error": "No holdings in portfolio", "analysis_date": datetime.now(timezone.utc).isoformat()}

    holdings_text  = _format_holdings_for_prompt(holdings)
    news_text      = _format_news_for_prompt(articles)
    filings_text   = _format_filings_for_prompt(filings)
    tickers        = [h.get('ticker', '') for h in holdings]

    prompt = f"""Analyze the following portfolio in light of the recent news and regulatory filings provided.

## Portfolio Holdings
{holdings_text}

## Recent News (last 7 days)
{news_text}

## Recent Regulatory Filings (last 30 days)
{filings_text}

## Task
Provide a comprehensive portfolio impact analysis. Return a JSON object with this exact structure:

{{
  "overall_sentiment": "bullish|neutral|cautious|bearish",
  "market_summary": "2-3 sentence macro overview relevant to this portfolio",
  "holding_impacts": [
    {{
      "ticker": "TICKER",
      "name": "Company Name",
      "sentiment": "positive|neutral|negative",
      "impact_level": "high|medium|low|none",
      "key_drivers": ["driver 1", "driver 2"],
      "analysis": "2-3 sentence analysis of how current news/filings affect this holding",
      "relevant_news_indices": [1, 3]
    }}
  ],
  "cross_industry_insights": [
    {{
      "trigger": "industry or event that caused the ripple",
      "affected_tickers": ["TICK1", "TICK2"],
      "insight": "How this cross-industry dynamic affects the portfolio"
    }}
  ],
  "risk_flags": [
    {{
      "severity": "high|medium|low",
      "ticker": "TICKER or ALL",
      "flag": "Short risk description",
      "detail": "More detailed explanation",
      "source": "News item or filing reference"
    }}
  ],
  "macro_themes": ["theme1", "theme2", "theme3"]
}}

Only include tickers from this list: {tickers}
Base your analysis strictly on the provided news and filings. If information is limited, say so clearly."""

    try:
        result = llm_client.chat_json(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
    except Exception as e:
        logger.error(f"LLM analysis failed: {e}")
        result = {
            "overall_sentiment": "neutral",
            "market_summary": "Analysis could not be completed due to an error.",
            "holding_impacts": [],
            "cross_industry_insights": [],
            "risk_flags": [],
            "macro_themes": [],
            "error": str(e),
        }

    result["analysis_date"]   = datetime.now(timezone.utc).isoformat()
    result["news_count"]      = len(articles)
    result["filings_count"]   = len(filings)
    result["portfolio_id"]    = portfolio.get('portfolio_id', '')
    result["portfolio_name"]  = portfolio.get('name', '')
    return result
