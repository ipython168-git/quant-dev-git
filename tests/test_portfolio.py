# tests/test_portfolio.py
"""
單元測試：Portfolio 組合回測
"""
import pytest
import pandas as pd
import numpy as np

from quant_dev.data.manager import DataManager
from quant_dev.backtest.strategy import Strategy, StrategyOption
from quant_dev.backtest.portfolio import Portfolio
from quant_dev.strategies import create_golden_and_death_cross_strategy
from quant_dev.utils import check_strategy_vs_portfolio


@pytest.fixture(scope="module")
def sample_data():
    """載入測試用數據"""
    dm = DataManager()
    try:
        df_aapl = dm.load_csv("AAPL", timeframe="1d", start_date="2023-01-01", end_date="2023-12-31")
        df_tsla = dm.load_csv("TSLA", timeframe="1d", start_date="2023-01-01", end_date="2023-12-31")
    except FileNotFoundError:
        # Fallback: 如果 CSV 唔存在，用 get_or_fetch
        dm = DataManager()
        df_aapl = dm.get_or_fetch("AAPL", timeframe="1d", days=365)
        df_tsla = dm.get_or_fetch("TSLA", timeframe="1d", days=365)
    
    return {"AAPL": df_aapl, "TSLA": df_tsla}


@pytest.fixture
def sample_strategies():
    """建立兩個測試用 Strategy（用 ticker 自動 load data）"""
    strategies = []
    for ticker in ["AAPL", "TSLA"]:
        strat = create_golden_and_death_cross_strategy(
            ticker=ticker,  # ✅ 只傳 ticker，唔傳 df
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
        """測試：Portfolio 能正確初始化"""
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
        """測試：backtest() 能正確執行"""
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
        """測試：績效指標能正確計算"""
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
        """測試：報告能正確生成"""
        pf = Portfolio(
            strategies=sample_strategies,
            weights=[0.6, 0.4],
        )
        pf.backtest()
        report = pf.generate_report()
        
        assert "Portfolio 績效報告" in report
        assert "Sharpe Ratio" in report
        assert "AAPL" in report
        assert "TSLA" in report

    def test_get_trade_log(self, sample_strategies):
        """測試：get_trade_log() 能正確返回交易記錄"""
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
        """測試：權重總和為 1"""
        pf = Portfolio(
            strategies=sample_strategies,
            weights=[0.6, 0.4],
        )
        assert abs(sum(pf.weights) - 1.0) < 0.001

    def test_default_weights(self, sample_strategies):
        """測試：如果冇提供 weights，會自動均等分配"""
        pf = Portfolio(
            strategies=sample_strategies,
        )
        assert pf.weights == [0.5, 0.5]

    def test_strategy_portfolio_consistency(self, sample_strategies):
        """測試：Strategy 與 Portfolio 嘅 entry/exit 一致"""
        pf = Portfolio(
            strategies=sample_strategies,
            weights=[0.6, 0.4],
        )
        pf.backtest()
        
        # 用 validation 工具檢查
        result = check_strategy_vs_portfolio(pf)
        assert result is True

    def test_trade_pnl_computed(self, sample_strategies):
        """測試：trade_pnl 同 trade_return 有被計算"""
        pf = Portfolio(
            strategies=sample_strategies,
            weights=[0.6, 0.4],
        )
        pf.backtest()
        
        assert "trade_pnl" in pf.df.columns
        assert "trade_return" in pf.df.columns

    def test_no_empty_strategies(self):
        """測試：空 strategies 會 raise error"""
        with pytest.raises(ValueError, match="strategies 不可為空"):
            Portfolio(strategies=[])

    def test_weights_mismatch(self, sample_strategies):
        """測試：weights 數量與 strategies 數量不匹配會 raise error"""
        with pytest.raises(ValueError, match="weights 數量必須與 strategies 數量一致"):
            Portfolio(
                strategies=sample_strategies,
                weights=[0.5],  # 只有 1 個，但 strategies 有 2 個
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
