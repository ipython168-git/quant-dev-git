# tests/test_strategy.py
"""
單元測試：Strategy 回測引擎
"""
import pytest
import pandas as pd
import numpy as np
from src.quant_dev.backtest.strategy import Strategy, StrategyConfig


@pytest.fixture
def sample_data():
    """建立模擬數據"""
    dates = pd.date_range(start="2024-01-01", periods=20, freq="D")
    df = pd.DataFrame({
        "Open": np.linspace(100, 119, 20) + np.random.randn(20) * 0.5,
        "High": np.linspace(102, 121, 20) + np.random.randn(20) * 0.5,
        "Low": np.linspace(98, 117, 20) + np.random.randn(20) * 0.5,
        "Close": np.linspace(101, 120, 20) + np.random.randn(20) * 0.5,
        "Volume": np.random.randint(1000, 10000, 20)
    }, index=dates)
    return df


@pytest.fixture
def sample_signal(sample_data):
    """建立模擬信號：第5日買入，第15日賣出"""
    signal = pd.Series(0, index=sample_data.index)
    signal.iloc[5] = 1   # 第5日買入
    signal.iloc[15] = -1 # 第15日賣出
    return signal


class TestStrategy:
    """Strategy 單元測試"""

    def test_initialization(self, sample_data):
        """測試：Strategy 能正確初始化"""
        config = StrategyConfig(ticker="TEST")
        strat = Strategy(config, sample_data)
        assert strat.df is not None
        assert "position" in strat.df.columns
        assert "entry" in strat.df.columns
        assert "exit" in strat.df.columns

    def test_add_signal(self, sample_data, sample_signal):
        """測試：add_signal 能正確加入信號"""
        config = StrategyConfig(ticker="TEST")
        strat = Strategy(config, sample_data)
        strat.add_signal(sample_signal)
        
        # 檢查 signal column 存在同長度正確
        assert "signal" in strat.df.columns
        assert len(strat.df["signal"]) == len(sample_data)
        # 檢查信號值
        assert strat.df["signal"].iloc[5] == 1
        assert strat.df["signal"].iloc[15] == -1

    def test_set_entry_exit_price(self, sample_data, sample_signal):
        """測試：set_entry_price / set_exit_price 能正確設定"""
        config = StrategyConfig(ticker="TEST")
        strat = Strategy(config, sample_data)
        strat.add_signal(sample_signal)
        
        # 用 High 做入市目標，Low 做出市目標
        strat.set_entry_price(sample_data["High"].shift(1))
        strat.set_exit_price(sample_data["Low"].shift(1))
        
        assert "entry_price" in strat.df.columns
        assert "exit_price" in strat.df.columns
        # 檢查 entry_price 係咪 High.shift(1)
        pd.testing.assert_series_equal(
            strat.df["entry_price"], 
            sample_data["High"].shift(1),
            check_names=False
        )

    def test_run_basic(self, sample_data, sample_signal):
        """測試：run() 能正確執行基本回測"""
        config = StrategyConfig(
            ticker="TEST",
            direction="buy",
            mode="normal",
            entry_order_type="market",
            exit_order_type="market"
        )
        strat = Strategy(config, sample_data)
        strat.add_signal(sample_signal)
        strat.set_entry_price(sample_data["Open"])
        strat.set_exit_price(sample_data["Open"])
        strat.run()
        
        # 檢查 position 有變化
        assert "position" in strat.df.columns
        assert strat.df["position"].sum() != 0  # 有交易發生
        
        # 檢查 entry 有值（第5日應該入市）
        assert not pd.isna(strat.df["entry"].iloc[5])
        
        # 檢查 exit 有值（第15日應該出市）
        assert not pd.isna(strat.df["exit"].iloc[15])

    def test_run_strong_hold(self, sample_data):
        """測試：Strong Hold 模式"""
        config = StrategyConfig(
            ticker="TEST",
            direction="buy",
            mode="strong_hold"
        )
        strat = Strategy(config, sample_data)
        # Strong Hold 唔需要 signal
        strat.run()
        
        # 檢查：第一日應該入市，最後一日應該平倉
        assert strat.df["position"].iloc[0] == 1
        assert strat.df["position"].iloc[-1] == 0
        assert not pd.isna(strat.df["entry"].iloc[0])
        assert not pd.isna(strat.df["exit"].iloc[-1])

    def test_run_eac_mode(self, sample_data, sample_signal):
        """測試：Exit-at-Close 模式"""
        config = StrategyConfig(
            ticker="TEST",
            direction="buy",
            mode="exit_at_close",
            entry_order_type="market",
            exit_order_type="market"
        )
        strat = Strategy(config, sample_data)
        strat.add_signal(sample_signal)
        strat.set_entry_price(sample_data["Open"])
        strat.set_exit_price(sample_data["Open"])
        strat.run()
        
        # 檢查：有信號嗰日應該 entry = open，exit = close（同日平倉）
        if not pd.isna(strat.df["entry"].iloc[5]):
            # 如果第5日有入市，應該同日平倉
            assert not pd.isna(strat.df["exit"].iloc[5])
            # exit 應該等於 close（你嘅 logic 係用 close 平倉）
            assert strat.df["exit"].iloc[5] == strat.df["Close"].iloc[5]