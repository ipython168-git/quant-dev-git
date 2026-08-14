
# Quant Dev - Quantitative Trading Backtesting System

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![CI](https://github.com/ipython168-git/quant-dev-git/actions/workflows/test.yml/badge.svg)](https://github.com/ipython168-git/quant-dev-git/actions)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2)](https://www.linkedin.com/in/ka-on-yip-5775b0429/)

A complete **quantitative trading backtesting system** built from scratch, supporting multi-strategy portfolios, multiple order types, comprehensive performance metrics, and a RESTful API.

---

## 🎯 Key Features

- **📊 Data Management**: Automated download, caching, and normalization of Yahoo Finance data (daily / minute bars)
- **⚙️ Strategy Backtesting**: Support for **Market / Limit / Stop Orders** with full **Gap Handling**
- **📈 Portfolio Management**: Multi-strategy weighting, leverage, NAV/ATH/DD calculations
- **📡 RESTful API**: FastAPI service with auto-generated Swagger documentation
- **🧪 Testing & CI**: 38 unit tests, automated via GitHub Actions

---

## 🏗️ System Architecture
```
DataManager → Strategy → Portfolio → FastAPI → Swagger UI
     ↓            ↓          ↓          ↓
  (Data)  (Trading)  (Portfolio)  (API Service)
```

---

## 🚀 Quick Start

### 1. Installation
```bash
git clone https://github.com/ipython168-git/quant-dev-git.git
cd quant-dev-git
pip install -e .
```

### 2. Set ngrok token
```bash
export NGROK_AUTHTOKEN="your_ngrok_authtoken"
```

### 3. Test with Colab / Jupyter
```python
from quant_dev.data.manager import DataManager
from quant_dev.strategies import create_golden_and_death_cross_strategy
from quant_dev.backtest.portfolio import Portfolio

# Download data
dm = DataManager()
df = dm.get_or_fetch("AAPL", days=500)

# Create strategy
strat = create_golden_and_death_cross_strategy(ticker="AAPL")

# Portfolio backtest
pf = Portfolio(strategies=[strat], weights=[1.0])
pf.backtest()
print(pf.generate_report())
```
 
### 4. Start API Server
```bash
# With ngrok (mobile / remote testing)
python -m quant_dev

# Local development
python -m quant_dev --fg

# Run vm run
chmod +x run.sh stop.sh status.sh
./run.sh
```

---

## 📡 API Demo

After starting the server, open `/docs` in your browser to see Swagger UI:

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

**Sample Backtest Results:**
```
Total Return: 56.16%
Annual Return: 17.85%
Sharpe Ratio: 0.77
Max Drawdown: -24.07%
```

---

## 📂 Project Structure

```
quant-dev-git/
├── src/quant_dev/
│   ├── api/          # FastAPI service
│   ├── backtest/     # Backtest engine (Strategy + Portfolio)
│   ├── data/         # Data management (DataManager)
│   ├── strategies/   # Built-in strategies (Golden Cross / Donchian)
│   └── server/       # Server launcher (ngrok + uvicorn)
├── tests/            # 38 unit tests
├── run.sh            # One-click launch (Colab / VM)
└── pyproject.toml    # Python dependency management
```

---

## 🛠️ Tech Stack

| Category | Tools |
|------|------|
| Language | Python 3.12 |
| Data | Pandas, NumPy, yfinance |
| API | FastAPI, Uvicorn |
| Testing | pytest, GitHub Actions |
| Deployment | ngrok, Bash |
| Management | pyproject.toml, pip |

---

## 📊 Test Coverage

| Module | Tests | Status |
|------|--------|------|
| DataManager | 7 | ✅ PASS |
| Strategy | 12 | ✅ PASS |
| Portfolio | 11 | ✅ PASS |
| API | 8 | ✅ PASS |
| **Total** | **38** | ✅ **全部 PASS** |

---

## 📄 License
 
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🙋‍♂️ About Me

Passionate about **Python development** and **quantitative trading system design**. This project is a complete backtesting system built from scratch, showcasing my **engineering capabilities** and **quantitative mindset**.


- 🔗 GitHub: [ipython168-git](https://github.com/ipython168-git/quant-dev-git)
- 💼 LinkedIn: [LinkedIn](https://www.linkedin.com/in/ka-on-yip-5775b0429/)

---

## ⭐ If this project helps you, please give it a Star!












 