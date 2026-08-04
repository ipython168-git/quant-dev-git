# tests/test_data_manager.py 
"""
單元測試：DataManager
使用 pytest 執行
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import shutil

# 假設你嘅 module 可以喺 tests 環境被 import
from src.quant_dev.data.manager import DataManager

# ==========================================
# 測試前的準備工作 (Fixture)
# ==========================================

@pytest.fixture
def temp_data_dir(tmp_path):
    """為每個測試建立一個臨時目錄，避免測試之間互相干擾"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir

@pytest.fixture
def dm(temp_data_dir):
    """建立一個使用臨時目錄嘅 DataManager 實例"""
    return DataManager(data_dir=str(temp_data_dir))

@pytest.fixture
def sample_dataframe():
    """建立一個模擬嘅 DataFrame，用嚟測試 read/write"""
    dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
    df = pd.DataFrame({
        "Open": np.random.rand(10) * 100,
        "High": np.random.rand(10) * 100 + 10,
        "Low": np.random.rand(10) * 90,
        "Close": np.random.rand(10) * 100,
        "Volume": np.random.randint(1000, 10000, 10)
    }, index=dates)
    df.index.name = "Date"
    return df

# ==========================================
# 測試 Cases
# ==========================================

class TestDataManager:
    """DataManager 單元測試群組"""

    def test_initialization(self, temp_data_dir):
        """測試：DataManager 能正確初始化"""
        dm = DataManager(data_dir=str(temp_data_dir))
        assert dm.data_dir == temp_data_dir
        assert dm.market_tz == "America/New_York"
        assert dm.data_dir.exists()

    def test_save_and_read_csv(self, dm, sample_dataframe):
        """測試：儲存同讀取 CSV 嘅功能正確"""
        file_path = dm.data_dir / "test.csv"
        
        # 1. 儲存
        dm._save_csv(sample_dataframe, file_path)
        assert file_path.exists()
        
        # 2. 讀取
        df_loaded = dm._read_csv(file_path)
        
        # 3. 驗證：數據應該完全一致
        pd.testing.assert_frame_equal(sample_dataframe, df_loaded, check_freq=False)
        assert df_loaded.index.name == "Date"

    def test_get_or_fetch_cache(self, dm, sample_dataframe, monkeypatch):
        """測試：get_or_fetch 能否正確使用快取"""
        ticker = "TEST"
        
        # 1. Mock 下載過程：直接將 sample_dataframe 放入 cache
        cache_path = dm.data_dir / f"{ticker}.csv"
        dm._save_csv(sample_dataframe, cache_path)
        
        # 2. 呼叫 get_or_fetch，應該直接讀取 cache，唔會真正 download
        df = dm.get_or_fetch(ticker, timeframe="1d", days=10)
        
        # 3. 驗證回傳嘅數據同 sample 一致
        pd.testing.assert_frame_equal(sample_dataframe, df, check_freq=False)

    def test_get_or_fetch_force_download(self, dm, sample_dataframe, monkeypatch):
        """測試：force_download=True 時會繞過 cache"""
        ticker = "TEST"
        
        # 1. 先放入一個舊 cache
        cache_path = dm.data_dir / f"{ticker}.csv"
        dm._save_csv(sample_dataframe, cache_path)
        
        # 2. Mock yfinance 下載行為 (回傳唔同嘅數據)
        class MockTicker:
            def history(self, **kwargs):
                new_df = sample_dataframe.copy()
                new_df["Close"] = new_df["Close"] + 10  # 改動數據
                return new_df
        
        monkeypatch.setattr("yfinance.Ticker", lambda x: MockTicker())
        
        # 3. force_download=True
        df = dm.get_or_fetch(ticker, timeframe="1d", days=10, force_download=True)
        
        # 4. 驗證回傳嘅數據係新嘅 (Close 值已被改動)
        assert not df["Close"].equals(sample_dataframe["Close"])

    def test_normalize_daily_index(self, dm):
        """測試：日K Index 會被標準化為純日期"""
        # 建立一個有時區嘅 index
        dates = pd.date_range(start="2024-01-01", periods=5, freq="D", tz="UTC")
        df = pd.DataFrame({"Close": [100, 101, 102, 103, 104]}, index=dates)
        
        normalized_df = dm._normalize_daily_index(df)
        
        # 驗證：tz 已被移除，且 normalize 為日期
        assert normalized_df.index.tz is None
        assert normalized_df.index[0] == pd.Timestamp("2024-01-01")

    def test_timeframe_to_interval(self, dm):
        """測試：timeframe 轉換邏輯正確"""
        assert dm._timeframe_to_interval("1d") == "1d"
        assert dm._timeframe_to_interval("1h") == "60m"
        assert dm._timeframe_to_interval("15m") == "15m"
        assert dm._timeframe_to_interval("5m") == "5m"
        # 預設值測試
        assert dm._timeframe_to_interval("unknown") == "unknown"

    def test_info_method(self, dm, sample_dataframe):
        """測試：info() 方法能正常執行並返回字串"""
        info_str = dm.info(sample_dataframe)
        assert isinstance(info_str, str)
        assert "Shape:" in info_str
        assert "Columns:" in info_str
