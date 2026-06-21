"""
Portfolio Analysis API routes
"""

import threading
from datetime import datetime, timezone
from flask import request, jsonify

from . import portfolio_bp
from ..models.portfolio import PortfolioManager, Portfolio, Holding
from ..services.news_aggregator import fetch_portfolio_news
from ..services.filing_fetcher import fetch_all_filings
from ..services.portfolio_analyzer import analyze_portfolio
from ..services.recommendation_engine import generate_recommendations
from ..utils.llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger('mirofish.api.portfolio')


def _holding_from_request(data: dict) -> Holding:
    return Holding(
        ticker=data.get('ticker', '').upper().strip(),
        name=data.get('name', data.get('ticker', '')),
        shares=float(data.get('shares', 0)),
        cost_basis=float(data.get('cost_basis', 0)),
        currency=data.get('currency', 'USD'),
        exchange=data.get('exchange', 'NYSE'),
        holding_type=data.get('holding_type', 'stock'),
        sector=data.get('sector', ''),
        industry=data.get('industry', ''),
    )


# ──────────────────────── Portfolio CRUD ────────────────────────

@portfolio_bp.route('/', methods=['POST'])
def create_portfolio():
    """Create a new portfolio."""
    body = request.get_json(silent=True) or {}
    name          = body.get('name', 'My Portfolio')
    base_currency = body.get('base_currency', 'USD')
    portfolio = PortfolioManager.create(name=name, base_currency=base_currency)
    return jsonify({"success": True, "data": portfolio.to_dict()}), 201


@portfolio_bp.route('/', methods=['GET'])
def list_portfolios():
    """List all portfolios."""
    portfolios = PortfolioManager.list_all()
    return jsonify({"success": True, "data": [p.to_dict() for p in portfolios]})


@portfolio_bp.route('/<portfolio_id>', methods=['GET'])
def get_portfolio(portfolio_id: str):
    """Get a portfolio by ID."""
    p = PortfolioManager.get(portfolio_id)
    if not p:
        return jsonify({"success": False, "error": f"Portfolio {portfolio_id} not found"}), 404
    return jsonify({"success": True, "data": p.to_dict()})


@portfolio_bp.route('/<portfolio_id>', methods=['PUT'])
def update_portfolio(portfolio_id: str):
    """Update portfolio metadata (name, base_currency, notes, target_allocations)."""
    p = PortfolioManager.get(portfolio_id)
    if not p:
        return jsonify({"success": False, "error": f"Portfolio {portfolio_id} not found"}), 404

    body = request.get_json(silent=True) or {}
    if 'name' in body:
        p.name = body['name']
    if 'base_currency' in body:
        p.base_currency = body['base_currency']
    if 'notes' in body:
        p.notes = body['notes']
    if 'target_allocations' in body:
        p.target_allocations = body['target_allocations']

    PortfolioManager.save(p)
    return jsonify({"success": True, "data": p.to_dict()})


@portfolio_bp.route('/<portfolio_id>', methods=['DELETE'])
def delete_portfolio(portfolio_id: str):
    """Delete a portfolio and its analysis data."""
    deleted = PortfolioManager.delete(portfolio_id)
    if not deleted:
        return jsonify({"success": False, "error": f"Portfolio {portfolio_id} not found"}), 404
    return jsonify({"success": True, "message": f"Portfolio {portfolio_id} deleted"})


# ──────────────────────── Holdings ────────────────────────

@portfolio_bp.route('/<portfolio_id>/holdings', methods=['PUT'])
def set_holdings(portfolio_id: str):
    """Replace all holdings in a portfolio."""
    p = PortfolioManager.get(portfolio_id)
    if not p:
        return jsonify({"success": False, "error": f"Portfolio {portfolio_id} not found"}), 404

    body = request.get_json(silent=True) or {}
    holdings_data = body.get('holdings', [])

    try:
        p.holdings = [_holding_from_request(h) for h in holdings_data]
    except (ValueError, KeyError) as e:
        return jsonify({"success": False, "error": f"Invalid holding data: {e}"}), 400

    PortfolioManager.save(p)
    return jsonify({"success": True, "data": p.to_dict()})


@portfolio_bp.route('/<portfolio_id>/holdings', methods=['POST'])
def add_holding(portfolio_id: str):
    """Add or update a single holding (matched by ticker)."""
    p = PortfolioManager.get(portfolio_id)
    if not p:
        return jsonify({"success": False, "error": f"Portfolio {portfolio_id} not found"}), 404

    body = request.get_json(silent=True) or {}
    try:
        new_holding = _holding_from_request(body)
    except (ValueError, KeyError) as e:
        return jsonify({"success": False, "error": f"Invalid holding data: {e}"}), 400

    if not new_holding.ticker:
        return jsonify({"success": False, "error": "ticker is required"}), 400

    # Update existing or append
    existing = next((h for h in p.holdings if h.ticker == new_holding.ticker), None)
    if existing:
        p.holdings = [new_holding if h.ticker == new_holding.ticker else h for h in p.holdings]
    else:
        p.holdings.append(new_holding)

    PortfolioManager.save(p)
    return jsonify({"success": True, "data": p.to_dict()})


@portfolio_bp.route('/<portfolio_id>/holdings/<ticker>', methods=['DELETE'])
def remove_holding(portfolio_id: str, ticker: str):
    """Remove a holding by ticker."""
    p = PortfolioManager.get(portfolio_id)
    if not p:
        return jsonify({"success": False, "error": f"Portfolio {portfolio_id} not found"}), 404

    ticker = ticker.upper()
    original_count = len(p.holdings)
    p.holdings = [h for h in p.holdings if h.ticker != ticker]

    if len(p.holdings) == original_count:
        return jsonify({"success": False, "error": f"Ticker {ticker} not found in portfolio"}), 404

    PortfolioManager.save(p)
    return jsonify({"success": True, "data": p.to_dict()})


# ──────────────────────── News & Filings ────────────────────────

@portfolio_bp.route('/<portfolio_id>/news', methods=['GET'])
def get_portfolio_news(portfolio_id: str):
    """Fetch relevant news articles for the portfolio's holdings."""
    p = PortfolioManager.get(portfolio_id)
    if not p:
        return jsonify({"success": False, "error": f"Portfolio {portfolio_id} not found"}), 404

    days_back   = request.args.get('days', 7, type=int)
    max_articles = request.args.get('max', 60, type=int)
    holdings_dicts = [h.to_dict() for h in p.holdings]

    try:
        articles = fetch_portfolio_news(holdings_dicts, max_articles=max_articles, days_back=days_back)
    except Exception as e:
        logger.error(f"News fetch error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({"success": True, "data": articles, "count": len(articles)})


@portfolio_bp.route('/<portfolio_id>/filings', methods=['GET'])
def get_portfolio_filings(portfolio_id: str):
    """Fetch recent SEC/SGX filings for the portfolio's holdings."""
    p = PortfolioManager.get(portfolio_id)
    if not p:
        return jsonify({"success": False, "error": f"Portfolio {portfolio_id} not found"}), 404

    days_back = request.args.get('days', 30, type=int)
    holdings_dicts = [h.to_dict() for h in p.holdings]

    try:
        filings = fetch_all_filings(holdings_dicts, days_back=days_back)
    except Exception as e:
        logger.error(f"Filings fetch error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

    return jsonify({"success": True, "data": filings, "count": len(filings)})


# ──────────────────────── Analysis ────────────────────────

# In-memory analysis task tracker (analysis_id -> status/result)
_analysis_tasks: dict = {}
_analysis_lock = threading.Lock()


@portfolio_bp.route('/<portfolio_id>/analyze', methods=['POST'])
def start_analysis(portfolio_id: str):
    """
    Start an async portfolio analysis job.
    Fetches news + filings, runs LLM analysis, generates recommendations.
    Returns an analysis_id to poll for results.
    """
    p = PortfolioManager.get(portfolio_id)
    if not p:
        return jsonify({"success": False, "error": f"Portfolio {portfolio_id} not found"}), 404

    if not p.holdings:
        return jsonify({"success": False, "error": "Portfolio has no holdings to analyze"}), 400

    body      = request.get_json(silent=True) or {}
    days_news = body.get('days_news', 7)
    days_filings = body.get('days_filings', 30)

    import uuid
    analysis_id = f"anlz_{uuid.uuid4().hex[:10]}"

    with _analysis_lock:
        _analysis_tasks[analysis_id] = {
            "status":       "running",
            "portfolio_id": portfolio_id,
            "started_at":   datetime.now(timezone.utc).isoformat(),
        }

    def run_analysis():
        try:
            holdings_dicts = [h.to_dict() for h in p.holdings]

            logger.info(f"[{analysis_id}] Fetching news for {portfolio_id}")
            articles = fetch_portfolio_news(holdings_dicts, days_back=days_news)

            logger.info(f"[{analysis_id}] Fetching filings for {portfolio_id}")
            filings = fetch_all_filings(holdings_dicts, days_back=days_filings)

            logger.info(f"[{analysis_id}] Running LLM analysis")
            llm = LLMClient()
            analysis = analyze_portfolio(p.to_dict(), articles, filings, llm_client=llm)

            logger.info(f"[{analysis_id}] Generating recommendations")
            recommendations = generate_recommendations(p.to_dict(), analysis, llm_client=llm)

            result = {
                "analysis_id":     analysis_id,
                "portfolio_id":    portfolio_id,
                "analysis":        analysis,
                "recommendations": recommendations,
                "news":            articles[:30],  # Store first 30 for display
                "filings":         filings[:20],
                "completed_at":    datetime.now(timezone.utc).isoformat(),
            }

            PortfolioManager.save_analysis(portfolio_id, result)

            with _analysis_lock:
                _analysis_tasks[analysis_id] = {
                    "status":       "completed",
                    "portfolio_id": portfolio_id,
                    "analysis_id":  analysis_id,
                    "completed_at": result["completed_at"],
                }

            logger.info(f"[{analysis_id}] Analysis complete")

        except Exception as e:
            logger.error(f"[{analysis_id}] Analysis failed: {e}")
            with _analysis_lock:
                _analysis_tasks[analysis_id] = {
                    "status":       "failed",
                    "portfolio_id": portfolio_id,
                    "error":        str(e),
                }

    thread = threading.Thread(target=run_analysis, daemon=True)
    thread.start()

    return jsonify({
        "success":     True,
        "analysis_id": analysis_id,
        "status":      "running",
        "message":     "Analysis started. Poll /status for progress.",
    }), 202


@portfolio_bp.route('/<portfolio_id>/analyze/status', methods=['GET'])
def get_analysis_status(portfolio_id: str):
    """Poll the status of the most recent or a specific analysis job."""
    analysis_id = request.args.get('analysis_id')

    if analysis_id:
        with _analysis_lock:
            task = _analysis_tasks.get(analysis_id)
        if not task:
            return jsonify({"success": False, "error": f"Analysis {analysis_id} not found"}), 404
        return jsonify({"success": True, "data": task})

    # Return status of all tasks for this portfolio
    with _analysis_lock:
        tasks = [t for t in _analysis_tasks.values() if t.get('portfolio_id') == portfolio_id]
    tasks.sort(key=lambda t: t.get('started_at', ''), reverse=True)
    return jsonify({"success": True, "data": tasks[:5]})


@portfolio_bp.route('/<portfolio_id>/analysis', methods=['GET'])
def get_analysis_result(portfolio_id: str):
    """Get the latest saved analysis result for a portfolio."""
    p = PortfolioManager.get(portfolio_id)
    if not p:
        return jsonify({"success": False, "error": f"Portfolio {portfolio_id} not found"}), 404

    result = PortfolioManager.get_analysis(portfolio_id)
    if not result:
        return jsonify({"success": False, "error": "No analysis available. Run /analyze first."}), 404

    return jsonify({"success": True, "data": result})
