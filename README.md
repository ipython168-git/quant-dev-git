
# Quant Dev - 量化交易回測系統

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![CI](https://github.com/ipython168-git/quant-dev-git/actions/workflows/test.yml/badge.svg)](https://github.com/ipython168-git/quant-dev-git/actions)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2)](https://www.linkedin.com/in/ka-on-yip-5775b0429/)

一個由零開始構建嘅 **量化交易回測系統**，支援多策略組合、多種訂單類型、完整嘅績效指標，同埋 RESTful API。

---

## 🎯 核心功能

- **📊 數據管理**：自動下載、快取、標準化 Yahoo Finance 數據（支援日K／分鐘K）
- **⚙️ 策略回測**：支援 **Market / Limit / Stop Order**，完整嘅 **Gap Handling**
- **📈 組合管理**：多策略加權組合、槓桿、NAV/ATH/DD 計算
- **📡 RESTful API**：用 FastAPI 建立，自動生成 Swagger 文件
- **🧪 單元測試 + CI**：38 個 tests，GitHub Actions 自動執行

---

## 🏗️ 系統架構
```
DataManager → Strategy → Portfolio → FastAPI → Swagger UI
     ↓            ↓          ↓          ↓
  (數據下載)  (交易模擬)  (組合管理)  (API 服務)
```

---

## 🚀 快速開始

### 1. 安裝
```bash
git clone https://github.com/ipython168-git/quant-dev-git.git
cd quant-dev-git
pip install -e .
```

### 2. 用 Colab / Jupyter 測試
```python
from quant_dev.data.manager import DataManager
from quant_dev.strategies import create_golden_and_death_cross_strategy
from quant_dev.backtest.portfolio import Portfolio

# 下載數據
dm = DataManager()
df = dm.get_or_fetch("AAPL", days=500)

# 建立策略
strat = create_golden_and_death_cross_strategy(ticker="AAPL")

# 組合回測
pf = Portfolio(strategies=[strat], weights=[1.0])
pf.backtest()
print(pf.generate_report())
```
 
### 3. 起 API Server
```bash
# 用 ngrok （ 手機／remote 測試 ）
python -m quant_dev

# 本地開發
python -m quant_dev --fg

# 直接 vm run
chmod +x run.sh stop.sh status.sh
./run.sh
```

---

## 📡 API 示範

啟動 server 後，開 browser 去 `/docs` 就會見到 Swagger UI：

```
https://your-ngrok-url.ngrok-free.dev/docs
```

### POST /backtest
```json
{
    "tickers": ["AAPL", "TSLA"],
    "strategy": "golden_cross",
    "params": {"sma_fast": 20, "sma_slow": 50},
    "weights": [0.6, 0.4],
    "initial": 100000,
    "days": 500
}
```

**回測結果示例：**
```
總回報: 56.16%
年化回報: 17.85%
Sharpe Ratio: 0.77
最大回撤: -24.07%
```

---

## 📂 目錄結構

```
quant-dev-git/
├── src/quant_dev/
│   ├── api/          # FastAPI 服務
│   ├── backtest/     # 回測引擎 (Strategy + Portfolio)
│   ├── data/         # 數據管理 (DataManager)
│   ├── strategies/   # 內置策略 (黃金交叉 / Donchian)
│   └── server/       # Server 啟動 (ngrok + uvicorn)
├── tests/            # 38 個單元測試
├── run.sh            # 一鍵啟動 (Colab / VM)
└── pyproject.toml    # Python 依賴管理
```

---

## 🛠️ 技術棧

| 類別 | 工具 |
|------|------|
| 語言 | Python 3.12 |
| 數據 | Pandas, NumPy, yfinance |
| API | FastAPI, Uvicorn |
| 測試 | pytest, GitHub Actions |
| 部署 | ngrok, Bash |
| 管理 | pyproject.toml, pip |

---

## 📊 測試覆蓋

| 模組 | 測試數 | 狀態 |
|------|--------|------|
| DataManager | 7 | ✅ PASS |
| Strategy | 12 | ✅ PASS |
| Portfolio | 11 | ✅ PASS |
| API | 8 | ✅ PASS |
| **總計** | **38** | ✅ **全部 PASS** |

---

## 📄 License
 
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🙋‍♂️ 關於我

熱衷於 **Python 開發** 同 **量化交易系統設計**。呢個專案係我由零開始構建嘅完整量化回測系統，展示我嘅 **工程能力** 同 **量化思維**。

- 🔗 GitHub: [ipython168-git](https://github.com/ipython168-git/quant-dev-git)
- 💼 LinkedIn: [LinkedIn](https://www.linkedin.com/in/ka-on-yip-5775b0429/)

---

## ⭐ 如果呢個專案幫到你，請俾個 Star！
```
 