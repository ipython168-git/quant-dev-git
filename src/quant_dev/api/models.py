# quant_dev/api/models.py
"""
API data models (Pydantic).
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class StrategyInfo(BaseModel):
    """Strategy information"""
    name: str
    display_name: str
    description: str
    default_params: Dict[str, Any]
    required_params: List[str]


class PortfolioBacktestRequest(BaseModel):
    """Portfolio backtest request"""
    tickers: List[str]
    strategy: str
    params: Optional[Dict[str, Any]] = None
    weights: Optional[List[float]] = None
    leverage: float = 1.0
    initial: float = 100000.0
    days: int = 500


class PortfolioBacktestResponse(BaseModel):
    """Portfolio backtest response"""
    tickers: List[str]
    strategy: str
    params: Dict[str, Any]
    weights: List[float]
    leverage: float
    initial: float
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    nav_final: float
    start_date: str
    end_date: str
    report: str
    trade_count: int
    message: str
    image_base64: Optional[str] = None












