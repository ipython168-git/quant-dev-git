# tests/test_portfolio.py
"""
單元測試：Portfolio 組合回測
"""
import pytest
import pandas as pd
import numpy as np

from quant_dev.data.manager import DataManager
from quant_dev.backtest.portfolio import Portfolio
from quant_dev.strategies import create_golden_and_death_cross_strategy
from quant_dev.utils import check_strategy_vs_portfolio


@pytest.fixture(scope="module")
def sample_strategies():
    """建立兩個測試用 Strategy（先下載 CSV，再用 ticker load）"""
    dm = DataManager()
    
    # ✅ 先用 get_or_fetch 下載 CSV（確保 CI 環境有數據）
    for ticker in ["AAPL", "TSLA"]:
        dm.get_or_fetch(ticker, timeframe="1d", days=365)
    
    # ✅ 然後 call 策略函數（內部會用 load_csv 讀取）
    strategies = []
    for ticker in ["AAPL", "TSLA"]:
        strat = create_golden_and_death_cross_strategy(
            ticker=ticker,
            sma_fast=10,
            sma_slow=30,
            direction="buy",
            entry_order_type="stop",
            exit_order_type="stop",
            gap_entry="open",
            gap_exit="open",
        )
        strategies.append(strat)
    
    return strategies


class TestPortfolio:
    """Portfolio 單元測試"""

    def test_initialization(self, sample_strategies):
        pf = Portfolio(
            strategies=sample_strategies,
            weights=[0.6, 0.4],
            initial=100000,
        )
        assert pf.strategies is not None
        assert len(pf.strategies) == 2
        assert pf.tickers == ["AAPL", "TSLA"]
        assert pf.weights == [0.6, 0.4]
        assert pf.initial == 100000

    def test_backtest_runs(self, sample_strategies):
        pf = Portfolio(
            strategies=sample_strategies,
            weights=[0.6, 0.4],
        )
        pf.backtest()
        
        assert pf.df is not None
        assert "nav" in pf.df.columns
        assert "ath" in pf.df.columns
        assert "dd" in pf.df.columns
        assert "cash" in pf.df.columns
        assert len(pf.df) > 0

    def test_metrics_computed(self, sample_strategies):
        pf = Portfolio(
            strategies=sample_strategies,
            weights=[0.6, 0.4],
        )
        pf.backtest()
        metrics = pf.metrics
        
        assert "Total Return (%)" in metrics
        assert "Annual Return (%)" in metrics
        assert "Sharpe Ratio" in metrics
        assert "Max Drawdown (%)" in metrics
        assert "Win Rate (%)" in metrics
        assert "Total Trades" in metrics

    def test_generate_report(self, sample_strategies):
        pf = Portfolio(
            strategies=sample_strategies,
            weights=[0.6, 0.4],
        )
        pf.backtest()
        report = pf.generate_report()
        
        assert "Portfolio Performance Report" in report
        assert "Sharpe Ratio" in report
        assert "AAPL" in report
        assert "TSLA" in report

    def test_get_trade_log(self, sample_strategies):
        pf = Portfolio(
            strategies=sample_strategies,
            weights=[0.6, 0.4],
        )
        pf.backtest()
        
        trade_log = pf.get_trade_log(rolling=0)
        assert len(trade_log) > 0
        assert "nav" in trade_log.columns
        assert "cash" in trade_log.columns

    def test_weights_sum_to_one(self, sample_strategies):
        pf = Portfolio(
            strategies=sample_strategies,
            weights=[0.6, 0.4],
        )
        assert abs(sum(pf.weights) - 1.0) < 0.001

    def test_default_weights(self, sample_strategies):
        pf = Portfolio(
            strategies=sample_strategies,
        )
        assert pf.weights == [0.5, 0.5]

    def test_strategy_portfolio_consistency(self, sample_strategies):
        pf = Portfolio(
            strategies=sample_strategies,
            weights=[0.6, 0.4],
        )
        pf.backtest()
        
        result = check_strategy_vs_portfolio(pf)
        assert result is True

    def test_trade_pnl_computed(self, sample_strategies):
        pf = Portfolio(
            strategies=sample_strategies,
            weights=[0.6, 0.4],
        )
        pf.backtest()
        
        assert "trade_pnl" in pf.df.columns
        assert "trade_return" in pf.df.columns

    def test_no_empty_strategies(self):
        with pytest.raises(ValueError, match="strategies cannot be empty"):
            Portfolio(strategies=[])

    def test_weights_mismatch(self, sample_strategies):
        with pytest.raises(ValueError, match="weights weights must match number of strategies"):
            Portfolio(
                strategies=sample_strategies,
                weights=[0.5],
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
