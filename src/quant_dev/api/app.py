# quant_dev/api/app.py
"""
FastAPI App - 極簡量化回測 API
"""
from fastapi import FastAPI, HTTPException
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import io
import base64

from .models import (
    PortfolioBacktestRequest,
    PortfolioBacktestResponse,
)
from .registry import STRATEGY_REGISTRY, get_strategy, list_strategies

from quant_dev.data.manager import DataManager
from quant_dev.backtest.portfolio import Portfolio 


app = FastAPI(
    title="Quant Dev API",
    description="極簡量化回測 API",
    version="0.1.0"
)

import logging
logger = logging.getLogger(__name__)


# ============================================================
# Helper: 檢查 CSV 是否存在
# ============================================================
def _check_csv_exists(ticker: str, timeframe: str = "1d") -> bool:
    """檢查 ticker 嘅 CSV 是否存在（用 DataManager 實際儲存路徑）"""
    dm = DataManager()
    interval = dm._timeframe_to_interval(timeframe)
    cache_path = dm._get_cache_path(ticker.upper(), interval, prepost=False)
    return cache_path.exists()


# ============================================================
# Endpoints
# ============================================================

@app.get("/")
def root():
    return {
        "message": "Quant Dev API is running",
        "version": "0.1.0",
        "endpoints": [
            "GET  /",
            "GET  /strategies",
            "POST /data",
            "POST /portfolio/backtest",
        ],
        "timestamp": datetime.now().isoformat()
    }


@app.get("/strategies")
def get_strategies():
    """列出所有可用策略"""
    return {
        "count": len(STRATEGY_REGISTRY),
        "strategies": list_strategies()
    }


@app.post("/data")
def download_ohlc(ticker: str, days: int = 500, force_download: bool = False):
    """下載 OHLC 數據"""
    dm = DataManager()
    try:
        df = dm.get_or_fetch(
            ticker=ticker,
            timeframe="1d",
            days=days,
            force_download=force_download
        )
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"無法下載 {ticker} 嘅數據")
        
        return {
            "status": "success",
            "ticker": ticker,
            "days": days,
            "rows": len(df),
            "start_date": df.index[0].strftime("%Y-%m-%d"),
            "end_date": df.index[-1].strftime("%Y-%m-%d"),
            "columns": list(df.columns),
            "message": f"✅ {ticker} 數據已下載 ({len(df)} 行)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/backtest", response_model=PortfolioBacktestResponse)
def run_portfolio_backtest(request: PortfolioBacktestRequest):
    """
    組合回測（多 ticker + 多策略）

    Request body:
    {
        "tickers": ["AAPL", "TSLA"],
        "strategy": "golden_cross",
        "params": {"sma_fast": 20, "sma_slow": 50},
        "weights": [0.6, 0.4],
        "leverage": 1.0,
        "initial": 100000,
        "days": 500
    }
    """
    tickers = request.tickers
    strategy_name = request.strategy
    params = request.params or {}
    weights = request.weights
    leverage = request.leverage
    initial = request.initial
    days = request.days



    # 如果冇提供 weights，自動均等分配
    if weights is None:
        weights = [1.0 / len(tickers)] * len(tickers)

    if len(weights) != len(tickers):
        raise HTTPException(
            status_code=400,
            detail=f"weights 數量 ({len(weights)}) 與 tickers 數量 ({len(tickers)}) 不匹配"
        )

    # 檢查策略是否存在
    strategy_info = get_strategy(strategy_name)
    if strategy_info is None:
        raise HTTPException(
            status_code=400,
            detail=f"策略 '{strategy_name}' 不存在。可用策略: {list(STRATEGY_REGISTRY.keys())}"
        )

    # 合併參數
    default_params = strategy_info["default_params"].copy()
    final_params = {**default_params, **params}

    # 檢查 required params
    for req in strategy_info["required_params"]:
        if req not in final_params:
            raise HTTPException(
                status_code=400,
                detail=f"缺少必要參數: {req}。需要: {strategy_info['required_params']}"
            )

    # 建立 ticker entry/exit
    strats = []
    strategy_func = strategy_info["function"]

    for ticker in tickers:
        # 檢查 CSV 是否存在 
        if not _check_csv_exists(ticker):
            raise HTTPException(
                status_code=404,
                detail=f"📁 未找到 {ticker} 嘅數據檔案。請先 call POST /data?ticker={ticker}&days={days} 下載數據"
            )
            
        logger.info(f"建立策略: {ticker}, days={days}, params={final_params}")

        # 執行策略（內部自己 load data）
        strat = strategy_func(
            ticker=ticker,
            **final_params
        )
        strats.append(strat)

    # 建立 Portfolio
    pf = Portfolio(
        strategies=strats,
        weights=weights,
        leverage=leverage,
        initial=initial,
        fee=0.0,
    )
    pf.backtest()

    # 提取 metrics
    metrics = pf.metrics
    trade_log = pf.get_trade_log(rolling=0)

    # 生成報告
    report = pf.generate_report()

    # 繪圖並轉為 base64
    fig = pf.plot()
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)  
    
    return PortfolioBacktestResponse(
        tickers=tickers,
        strategy=strategy_name,
        params=final_params,
        weights=weights,
        leverage=leverage,
        initial=initial,
        total_return=metrics.get("Total Return (%)", 0.0),
        annual_return=metrics.get("Annual Return (%)", 0.0),
        sharpe_ratio=metrics.get("Sharpe Ratio", 0.0),
        max_drawdown=metrics.get("Max Drawdown (%)", 0.0),
        win_rate=metrics.get("Win Rate (%)", 0.0),
        total_trades=metrics.get("Total Trades", 0),
        nav_final=pf.df['nav'].iloc[-1],
        start_date=pf.df.index[0].strftime("%Y-%m-%d"),
        end_date=pf.df.index[-1].strftime("%Y-%m-%d"),
        report=report,
        trade_count=len(trade_log),
        image_base64=img_base64,  
        message=f"✅ 組合回測完成 ({len(tickers)} 個策略)"
    )








    
