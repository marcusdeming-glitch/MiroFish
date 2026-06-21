"""
Conservative recommendation engine.
Takes portfolio analysis output and produces passive-investor-friendly adjustment suggestions.
"""

import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger('mirofish.portfolio.recommendations')

SYSTEM_PROMPT = """You are a conservative financial advisor focused on long-term passive investing.
Your recommendations are:
- Conservative: you prefer small, deliberate adjustments over dramatic moves
- Risk-aware: you always quantify the reason for a suggestion
- Passive-friendly: your default is to hold; you only suggest action when evidence is compelling
- Clear: each recommendation explains the what, why, and how much
- Diversification-focused: you consider sector concentration and correlation risks

You never recommend more than a 5-10% portfolio weight shift in a single action.
You always distinguish between "watch" (monitor, no action) and "act" (make a small adjustment)."""


def _format_analysis_for_prompt(analysis: Dict[str, Any]) -> str:
    sentiment = analysis.get('overall_sentiment', 'neutral')
    summary   = analysis.get('market_summary', '')

    impacts_text = []
    for imp in analysis.get('holding_impacts', []):
        impacts_text.append(
            f"- {imp.get('ticker')}: {imp.get('sentiment')} impact ({imp.get('impact_level')})\n"
            f"  Drivers: {', '.join(imp.get('key_drivers', []))}\n"
            f"  {imp.get('analysis', '')}"
        )

    risks_text = []
    for risk in analysis.get('risk_flags', []):
        risks_text.append(f"- [{risk.get('severity').upper()}] {risk.get('ticker')}: {risk.get('flag')} — {risk.get('detail')}")

    cross_text = []
    for ci in analysis.get('cross_industry_insights', []):
        cross_text.append(f"- {ci.get('trigger')} → affects {', '.join(ci.get('affected_tickers', []))}: {ci.get('insight')}")

    return f"""OVERALL SENTIMENT: {sentiment}
MARKET SUMMARY: {summary}

HOLDING-LEVEL IMPACTS:
{chr(10).join(impacts_text) or 'None identified.'}

RISK FLAGS:
{chr(10).join(risks_text) or 'No material risks flagged.'}

CROSS-INDUSTRY EFFECTS:
{chr(10).join(cross_text) or 'None identified.'}

MACRO THEMES: {', '.join(analysis.get('macro_themes', []))}"""


def _format_holdings_for_prompt(holdings: List[Dict[str, Any]]) -> str:
    total_cost = sum(h.get('shares', 0) * h.get('cost_basis', 0) for h in holdings)
    lines = []
    for h in holdings:
        ticker  = h.get('ticker', '')
        shares  = h.get('shares', 0)
        cost    = h.get('cost_basis', 0)
        value   = shares * cost
        weight  = (value / total_cost * 100) if total_cost > 0 else 0
        sector  = h.get('sector', 'Unknown')
        htype   = h.get('holding_type', 'stock').upper()
        target  = h.get('target_allocation', None)
        target_str = f", target {target:.1f}%" if target is not None else ""
        lines.append(f"- {ticker} | {htype} | {sector} | weight {weight:.1f}%{target_str}")
    return '\n'.join(lines)


def generate_recommendations(
    portfolio: Dict[str, Any],
    analysis: Dict[str, Any],
    llm_client: Optional[LLMClient] = None,
) -> Dict[str, Any]:
    """
    Generate conservative portfolio adjustment recommendations.

    Returns a dict with:
    - summary: overall recommendation stance
    - recommendations: list of specific action items
    - watchlist: items to monitor without acting yet
    - rebalancing: drift alerts vs. target allocations
    - generated_at: ISO timestamp
    """
    if llm_client is None:
        llm_client = LLMClient()

    holdings = portfolio.get('holdings', [])
    targets  = portfolio.get('target_allocations', {})

    # Compute drift vs. targets
    total_cost = sum(h.get('shares', 0) * h.get('cost_basis', 0) for h in holdings)
    drift_alerts = []
    for h in holdings:
        ticker = h.get('ticker', '')
        if ticker not in targets:
            continue
        value  = h.get('shares', 0) * h.get('cost_basis', 0)
        actual = (value / total_cost * 100) if total_cost > 0 else 0
        target = targets[ticker]
        drift  = actual - target
        if abs(drift) >= 3.0:
            drift_alerts.append({
                "ticker":        ticker,
                "actual_weight": round(actual, 1),
                "target_weight": round(target, 1),
                "drift":         round(drift, 1),
                "direction":     "overweight" if drift > 0 else "underweight",
            })

    analysis_text   = _format_analysis_for_prompt(analysis)
    holdings_text   = _format_holdings_for_prompt(holdings)
    drift_text      = json.dumps(drift_alerts, indent=2) if drift_alerts else "No significant drift detected."
    tickers         = [h.get('ticker', '') for h in holdings]

    prompt = f"""Based on the portfolio analysis below, generate conservative adjustment recommendations.

## Current Portfolio
{holdings_text}

## Analysis Results
{analysis_text}

## Drift vs. Targets
{drift_text}

## Task
You are advising a passive, long-term investor who makes only small, infrequent adjustments.
Return a JSON object with this exact structure:

{{
  "summary": "1-2 sentence overall stance (e.g. 'Portfolio is well-positioned; minor risk monitoring recommended')",
  "recommendations": [
    {{
      "action": "HOLD|TRIM|ADD|REBALANCE|REVIEW",
      "ticker": "TICKER or ALL",
      "priority": "high|medium|low",
      "rationale": "Why this action is recommended, citing specific news/risk",
      "suggested_adjustment": "e.g. Reduce by 2-3% of portfolio weight, or 'No immediate action'",
      "time_horizon": "immediate|1-3 months|3-6 months|long-term"
    }}
  ],
  "watchlist": [
    {{
      "ticker": "TICKER",
      "watch_reason": "What to monitor and why",
      "trigger": "What event/signal would escalate this to an action"
    }}
  ],
  "rebalancing_alerts": {json.dumps(drift_alerts)},
  "key_risks_to_monitor": ["risk1", "risk2"],
  "positive_catalysts": ["catalyst1", "catalyst2"],
  "next_review_suggestion": "When to re-run this analysis (e.g. 'After Q2 earnings season')"
}}

Tickers in portfolio: {tickers}
Only reference portfolio tickers. Default bias is HOLD — only recommend action when the evidence clearly warrants it."""

    try:
        result = llm_client.chat_json(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.3,
            max_tokens=3000,
        )
    except Exception as e:
        logger.error(f"Recommendation generation failed: {e}")
        result = {
            "summary": "Recommendation generation encountered an error.",
            "recommendations": [],
            "watchlist": [],
            "rebalancing_alerts": drift_alerts,
            "key_risks_to_monitor": [],
            "positive_catalysts": [],
            "next_review_suggestion": "Please retry the analysis.",
            "error": str(e),
        }

    result["generated_at"]    = datetime.now(timezone.utc).isoformat()
    result["portfolio_id"]    = portfolio.get('portfolio_id', '')
    result["overall_sentiment"] = analysis.get('overall_sentiment', 'neutral')
    return result
