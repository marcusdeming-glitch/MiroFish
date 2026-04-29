"""
Portfolio data model and manager
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from ..config import Config


@dataclass
class Holding:
    """A single portfolio holding (stock or ETF)"""
    ticker: str
    name: str
    shares: float
    cost_basis: float        # cost per share
    currency: str = "USD"
    exchange: str = "NYSE"   # NYSE, NASDAQ, SGX, LSE, etc.
    holding_type: str = "stock"  # stock | etf
    sector: str = ""
    industry: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "shares": self.shares,
            "cost_basis": self.cost_basis,
            "currency": self.currency,
            "exchange": self.exchange,
            "holding_type": self.holding_type,
            "sector": self.sector,
            "industry": self.industry,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Holding':
        return cls(
            ticker=data['ticker'],
            name=data.get('name', data['ticker']),
            shares=float(data.get('shares', 0)),
            cost_basis=float(data.get('cost_basis', 0)),
            currency=data.get('currency', 'USD'),
            exchange=data.get('exchange', 'NYSE'),
            holding_type=data.get('holding_type', 'stock'),
            sector=data.get('sector', ''),
            industry=data.get('industry', ''),
        )


@dataclass
class Portfolio:
    """Portfolio data model"""
    portfolio_id: str
    name: str
    created_at: str
    updated_at: str
    holdings: List[Holding] = field(default_factory=list)
    target_allocations: Dict[str, float] = field(default_factory=dict)
    base_currency: str = "USD"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "holdings": [h.to_dict() for h in self.holdings],
            "target_allocations": self.target_allocations,
            "base_currency": self.base_currency,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Portfolio':
        holdings = [Holding.from_dict(h) for h in data.get('holdings', [])]
        return cls(
            portfolio_id=data['portfolio_id'],
            name=data.get('name', 'My Portfolio'),
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
            holdings=holdings,
            target_allocations=data.get('target_allocations', {}),
            base_currency=data.get('base_currency', 'USD'),
            notes=data.get('notes', ''),
        )


class PortfolioManager:
    """Manages portfolio persistence via JSON files"""

    PORTFOLIOS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'portfolios')

    @classmethod
    def _ensure_dir(cls):
        os.makedirs(cls.PORTFOLIOS_DIR, exist_ok=True)

    @classmethod
    def _get_path(cls, portfolio_id: str) -> str:
        return os.path.join(cls.PORTFOLIOS_DIR, f"{portfolio_id}.json")

    @classmethod
    def _get_analysis_path(cls, portfolio_id: str) -> str:
        return os.path.join(cls.PORTFOLIOS_DIR, f"analysis_{portfolio_id}.json")

    @classmethod
    def create(cls, name: str = "My Portfolio", base_currency: str = "USD") -> Portfolio:
        cls._ensure_dir()
        portfolio_id = f"port_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()
        portfolio = Portfolio(
            portfolio_id=portfolio_id,
            name=name,
            created_at=now,
            updated_at=now,
            base_currency=base_currency,
        )
        cls.save(portfolio)
        return portfolio

    @classmethod
    def save(cls, portfolio: Portfolio) -> None:
        cls._ensure_dir()
        portfolio.updated_at = datetime.now().isoformat()
        with open(cls._get_path(portfolio.portfolio_id), 'w', encoding='utf-8') as f:
            json.dump(portfolio.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def get(cls, portfolio_id: str) -> Optional[Portfolio]:
        path = cls._get_path(portfolio_id)
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return Portfolio.from_dict(json.load(f))

    @classmethod
    def list_all(cls) -> List[Portfolio]:
        cls._ensure_dir()
        portfolios = []
        for fname in os.listdir(cls.PORTFOLIOS_DIR):
            if fname.endswith('.json') and not fname.startswith('analysis_'):
                p = cls.get(fname[:-5])
                if p:
                    portfolios.append(p)
        portfolios.sort(key=lambda p: p.created_at, reverse=True)
        return portfolios

    @classmethod
    def delete(cls, portfolio_id: str) -> bool:
        path = cls._get_path(portfolio_id)
        if not os.path.exists(path):
            return False
        os.remove(path)
        analysis_path = cls._get_analysis_path(portfolio_id)
        if os.path.exists(analysis_path):
            os.remove(analysis_path)
        return True

    @classmethod
    def save_analysis(cls, portfolio_id: str, analysis: Dict[str, Any]) -> None:
        cls._ensure_dir()
        with open(cls._get_analysis_path(portfolio_id), 'w', encoding='utf-8') as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)

    @classmethod
    def get_analysis(cls, portfolio_id: str) -> Optional[Dict[str, Any]]:
        path = cls._get_analysis_path(portfolio_id)
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
