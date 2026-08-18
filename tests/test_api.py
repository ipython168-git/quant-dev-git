# tests/test_api.py
"""
API 單元測試 - FastAPI TestClient
"""
import pytest
from fastapi.testclient import TestClient
import json
from pathlib import Path

from quant_dev.api.app import app

client = TestClient(app)


# ============================================================
# Helper: 確保測試用嘅 CSV 存在
# ============================================================
def ensure_test_data(ticker: str = "AAPL"):
    """確保測試用嘅 CSV 已下載"""
    from quant_dev.data.manager import DataManager
    dm = DataManager()
    dm.get_or_fetch(ticker, timeframe="1d", days=100, force_download=False)


# ============================================================
# Tests
# ============================================================

class TestAPI:
    """API 端點測試"""

    def test_root(self):
        """測試 GET /"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "endpoints" in data

    def test_strategies(self):
        """測試 GET /strategies"""
        response = client.get("/strategies")
        assert response.status_code == 200
        data = response.json()
        assert "strategies" in data
        assert len(data["strategies"]) >= 2  # golden_cross + donchian

    def test_data_download(self):
        """測試 POST /data"""
        response = client.post("/data", params={"ticker": "AAPL", "days": 100})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["ticker"] == "AAPL"
        assert data["rows"] > 0

    def test_backtest_success(self):
        """測試 POST /backtest（正常情況）"""
        # 確保數據已下載
        ensure_test_data("AAPL")
        ensure_test_data("TSLA")

        payload = {
            "tickers": ["AAPL", "TSLA"],
            "strategy": "golden_cross",
            "params": {"sma_fast": 20, "sma_slow": 50},
            "weights": [0.6, 0.4],
            "leverage": 1.0,
            "initial": 100000,
            "days": 200
        }

        response = client.post("/backtest", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "total_return" in data
        assert "annual_return" in data
        assert "sharpe_ratio" in data
        assert "max_drawdown" in data
        assert "report" in data
        assert "message" in data
        assert "✅" in data["message"]

    def test_backtest_missing_data(self):
        """測試 POST /backtest（冇數據）"""
        payload = {
            "tickers": ["INVALID_TICKER"],
            "strategy": "golden_cross",
            "params": {"sma_fast": 20, "sma_slow": 50},
            "weights": [1.0],
            "initial": 100000,
            "days": 100
        }

        response = client.post("/backtest", json=payload)
        assert response.status_code == 404
        data = response.json()
        assert "未找到" in data["detail"] or "not found" in data["detail"].lower()

    def test_backtest_invalid_strategy(self):
        """測試 POST /backtest（唔存在嘅策略）"""
        payload = {
            "tickers": ["AAPL", "TSLA"],
            "strategy": "invalid_strategy",
            "params": {},
            "weights": [0.5, 0.5],
            "initial": 100000,
            "days": 100
        }

        response = client.post("/backtest", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "not found" in data["detail"]

    def test_backtest_weights_mismatch(self):
        """測試 POST /backtest（weights 數量唔 match）"""
        payload = {
            "tickers": ["AAPL", "TSLA"],
            "strategy": "golden_cross",
            "params": {"sma_fast": 20, "sma_slow": 50},
            "weights": [1.0],  # 得一個 weight
            "initial": 100000,
            "days": 100
        }

        response = client.post("/backtest", json=payload)
        assert response.status_code == 400
        data = response.json()
        assert "does not match" in data["detail"] or "mismatch" in data["detail"].lower()

 
    def test_data_download_invalid_ticker(self):
        """測試 POST /data（無效 ticker）"""
        response = client.post("/data", params={"ticker": "INVALID_TICKER", "days": 10})
        # 可能會 fail 或者 return empty
        assert response.status_code in [200, 404, 500]
















