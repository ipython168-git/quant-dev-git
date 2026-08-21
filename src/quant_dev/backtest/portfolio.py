# quant_dev/backtest/portfolio.py
"""
Portfolio - Multi-strategy portfolio backtesting (CV version).
Features: Multi-strategy weighting, NAV/ATH/DD, simplified metrics.
Removed: YAML Config, restore_from_trx, plotting.
"""
import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any 
import matplotlib.pyplot as plt
from .strategy import Strategy


class Portfolio:
    """Multi-strategy portfolio backtesting engine (CV version)."""
    def __init__(
        self,
        strategies: List[Strategy],
        weights: Optional[List[float]] = None,
        leverage: float = 1.0,
        initial: float = 10000.0,
        fee: float = 2.0,
    ):
        """
        Initialize the Portfolio.

        Args:
            strategies: List of already-run Strategy objects
            weights: Weight for each strategy (sum to 1)
            leverage: Leverage multiplier
            initial: Initial capital
            fee: Transaction fee per trade
        """
        if not strategies:
            raise ValueError("strategies cannot be empty")

        self.strategies = strategies
        self.tickers = [s.ticker for s in strategies]
        self.leverage = leverage
        self.initial = initial
        self.fee = fee

        n = len(strategies)
        if weights is None:
            self.weights = [1.0 / n] * n
        else:
            self.weights = weights

        if len(self.weights) != n:
            raise ValueError("number of weights must match number of strategies")

        # Initialize
        self.df = None
        self.metrics: Dict[str, Any] = {}
        self._backtest_done = False

    # ================================================================
    # Core Backtest
    # ================================================================

    def backtest(self) -> "Portfolio":
        """Run portfolio backtest"""
        self._validate_strategies()
        self._build_arrays()
        self._calculate_all_strategy_returns()
        self._run_loop()
        self._finalize_arrays()
        self._compute_metrics()
        self._backtest_done = True
        return self

    def _validate_strategies(self):
        """Align all Strategy time axes"""
        unified_idx = self.strategies[0].df.index
        for strat in self.strategies[1:]:
            unified_idx = unified_idx.union(strat.df.index)
        unified_idx = unified_idx.sort_values()

        for strat in self.strategies:
            if not strat.df.index.equals(unified_idx):
                strat.df = strat.df.reindex(unified_idx)
                for col in ["Open", "High", "Low", "Close", "Volume"]:
                    if col in strat.df.columns:
                        strat.df[col] = strat.df[col].ffill()

                # ✅ 如果第一行仲係 NaN，用第一個有效值填
                for col in ["Open", "High", "Low", "Close"]:
                    if pd.isna(strat.df[col].iloc[0]):
                        first_valid = strat.df[col].dropna().iloc[0] if not strat.df[col].dropna().empty else 0.0
                        strat.df.loc[strat.df.index[0], col] = first_valid
               


                strat.df["position"] = strat.df["position"].fillna(0).astype(int)
                strat.df["entry"] = strat.df["entry"].fillna(np.nan)
                strat.df["exit"] = strat.df["exit"].fillna(np.nan)

        self.df = pd.DataFrame(index=unified_idx)

    def _build_arrays(self):
        """Build numpy arrays"""
        n_strats = len(self.strategies)
        n_rows = len(self.df)

        self._arrays = {
            "Close": [],
            "High": [],
            "Low": [],
            "position": [],
            "entry": [],
            "exit": [],
            "temp_c": [],
            "contract": [],
        }

        self._open_prices = []

        for i, strat in enumerate(self.strategies):
            ticker = self.tickers[i]
            for f in ["Close", "High", "Low", "position", "entry", "exit"]:
                arr = strat.df[f].to_numpy(dtype=float)
                self._arrays[f].append(arr)
                if f not in ["Close", "High", "Low"]:
                    self.df[f"{f}{i}_{ticker}"] = arr

            # ✅ 搵第一個有效嘅 Open（跳過 NaN）
            open_series = strat.df["Open"]
            first_valid_open = open_series.dropna().iloc[0] if not open_series.dropna().empty else 1.0
            self._open_prices.append(first_valid_open) 
            #self._open_prices.append(strat.df["Open"].iloc[0])

            self._arrays["temp_c"].append(np.zeros(n_rows))
            self._arrays["contract"].append(np.zeros(n_rows))
            self.df[f"temp_c{i}_{ticker}"] = 0
            self.df[f"contract{i}_{ticker}"] = 0

        self._nav = np.ones(n_rows)
        self._cash = np.full(n_rows, self.initial)
        self._cashflow = np.zeros(n_rows)
        self._ath = np.ones(n_rows)
        self._dd = np.ones(n_rows)

        self.df["cashflow"] = 0.0
        self.df["cash"] = self.initial
        self.df["nav"] = 1.0
        self.df["ath"] = 1.0
        self.df["dd"] = 1.0

    # ================================================================
    # PnL 計算
    # ================================================================

    def _calculate_all_strategy_returns(self):
        for n in range(len(self.strategies)):
            self._calculate_strategy_returns(n)

    def _calculate_strategy_returns(self, n: int):
        ticker = self.tickers[n]
        entry_col = f"entry{n}_{ticker}"
        exit_col = f"exit{n}_{ticker}"
        pnl_col = f"pnl{n}_{ticker}"
        pnl_rate_col = f"pnl_rate{n}_{ticker}"

        mask_entry = self.df[entry_col].notna()
        mask_exit = self.df[exit_col].notna()
        n_entry = mask_entry.sum()
        n_exit = mask_exit.sum()

        if n_entry != n_exit:
            raise ValueError(
                f"Strategy {n} ({ticker}) entry/exit count mismatch: {n_entry} vs {n_exit}"
            )

        entries = self.df.loc[mask_entry, entry_col].values
        exits = self.df.loc[mask_exit, exit_col].values
        pnl_values = entries + exits

        with np.errstate(divide="ignore", invalid="ignore"):
            pnl_rate_values = np.where(
                entries != 0,
                np.abs(exits / entries) - 1,
                np.nan
            )

        self.df[pnl_col] = np.nan
        self.df[pnl_rate_col] = np.nan
        self.df.loc[mask_exit, pnl_col] = pnl_values
        self.df.loc[mask_exit, pnl_rate_col] = pnl_rate_values

    # ================================================================
    # 逐行計算
    # ================================================================

    def _run_loop(self):
        n_rows = len(self.df)
        n_strats = len(self.strategies)

        for i in range(n_rows):
            if i == 0:
                self._process_first_row()
            else:
                self._process_row(i)

            self._nav[i] = self._cash[i] + sum(
                self._arrays["position"][n][i]
                * self._arrays["contract"][n][i]
                * self._arrays["Close"][n][i]
                for n in range(n_strats)
            )

            self._ath[i] = max(self._nav[i], self._ath[i - 1]) if i > 0 else self._nav[i]
            self._dd[i] = (self._nav[i] / self._ath[i]) - 1 if self._ath[i] != 0 else 0.0

    def _process_first_row(self):
        n_strats = len(self.strategies)
        total_cf = 0.0

        for n in range(n_strats):
            open_price = self._open_prices[n]
            temp_c = int(self.initial * self.leverage * self.weights[n] / open_price)
            self._arrays["temp_c"][n][0] = temp_c

            entry = self._arrays["entry"][n][0]
            exit_ = self._arrays["exit"][n][0]
            has_entry = not np.isnan(entry)
            has_exit = not np.isnan(exit_)

            cf = 0.0
            if has_exit and has_entry:
                self._arrays["contract"][n][0] = 0
                cf = temp_c * exit_ - self.fee
                cf += temp_c * entry - self.fee
            elif has_entry:
                self._arrays["contract"][n][0] = temp_c
                cf = temp_c * entry - self.fee
            else:
                self._arrays["contract"][n][0] = 0

            total_cf += cf

        self._cashflow[0] = total_cf
        self._cash[0] = self.initial + total_cf

    def _process_row(self, i: int):
        n_strats = len(self.strategies)
        total_cf = 0.0

        for n in range(n_strats):
            prev_close = self._arrays["Close"][n][i - 1]
            temp_c = int(
                self._nav[i - 1] * self.leverage * self.weights[n] / prev_close
            )
            self._arrays["temp_c"][n][i] = temp_c

            entry = self._arrays["entry"][n][i]
            exit_ = self._arrays["exit"][n][i]
            has_entry = not np.isnan(entry)
            has_exit = not np.isnan(exit_)

            cf = 0.0
            if has_exit:
                self._arrays["contract"][n][i] = 0
                prev_contract = self._arrays["contract"][n][i - 1]
                cf = prev_contract * exit_ - self.fee
                if has_entry:
                    cf += temp_c * entry - self.fee
            elif has_entry:
                self._arrays["contract"][n][i] = temp_c
                cf = temp_c * entry - self.fee
            else:
                self._arrays["contract"][n][i] = self._arrays["contract"][n][i - 1]

            total_cf += cf

        self._cashflow[i] = total_cf
        self._cash[i] = self._cash[i - 1] + total_cf

    # ================================================================
    # 寫回 DataFrame
    # ================================================================

    def _finalize_arrays(self):
        for n, ticker in enumerate(self.tickers):
            self.df[f"temp_c{n}_{ticker}"] = self._arrays["temp_c"][n]
            self.df[f"contract{n}_{ticker}"] = self._arrays["contract"][n]
            self.df[f"position{n}_{ticker}"] = self._arrays["position"][n]

        self.df["cashflow"] = self._cashflow
        self.df["cash"] = self._cash
        self.df["nav"] = self._nav
        self.df["ath"] = self._ath
        self.df["dd"] = self._dd

        self._compute_trade_pnl()

    def _compute_trade_pnl(self):
        """Compute portfolio-weighted PnL"""
        pnl_cols = []
        for n, ticker in enumerate(self.tickers):
            col = f"pnl{n}_{ticker}"
            if col in self.df.columns:
                pnl_cols.append(col)

        if pnl_cols:
            pnl_df = self.df[pnl_cols].fillna(0)
            weighted_pnl = pnl_df.values @ np.array(self.weights)
            self.df["trade_pnl"] = np.where(
                pnl_df.isna().all(axis=1), np.nan, weighted_pnl
            )
            self.df["trade_return"] = self.df["trade_pnl"] / self.initial

    # ================================================================
    # 精簡 Metrics（只保留最常用嘅）
    # ================================================================

    def _compute_metrics(self):
        """Compute simplified performance metrics: total return, annual return, sharpe, max dd, win rate"""
        nav = self.df["nav"]
        dd = self.df["dd"]

        if len(nav) < 2:
            self.metrics = {}
            return

        # Total Return
        total_return = (nav.iloc[-1] / nav.iloc[0]) - 1

        # Annual Return (假設 252 交易日)
        n = len(nav)
        annual_return = (1 + total_return) ** (252 / n) - 1 if n > 0 else 0

        # Sharpe Ratio
        daily_return = nav.pct_change().fillna(0)
        volatility = daily_return.std() * np.sqrt(252) if n > 1 else 0
        sharpe = annual_return / volatility if volatility > 0 else 0

        # Max Drawdown
        max_dd = dd.min() if len(dd) > 0 else 0

        # Win Rate（用 trade_pnl 計算）
        trades = self.df["trade_pnl"].dropna()
        win_rate = (trades > 0).mean() if len(trades) > 0 else 0
        total_trades = len(trades)

        self.metrics = {
            "Total Return (%)": round(total_return * 100, 2),
            "Annual Return (%)": round(annual_return * 100, 2),
            "Sharpe Ratio": round(sharpe, 2),
            "Max Drawdown (%)": round(max_dd * 100, 2),
            "Win Rate (%)": round(win_rate * 100, 2),
            "Total Trades": total_trades,
        }

    # ================================================================
    # Public API
    # ================================================================

    def get_metric(self, key: str) -> Any:
        if not self._backtest_done:
            raise RuntimeError("Please run backtest() first")
        return self.metrics.get(key)

    def generate_report(self) -> str:
        if not self._backtest_done:
            self.backtest()

        weights_str = ", ".join(
            f"{t}: {w:.3f}" for t, w in zip(self.tickers, self.weights)
        )

        lines = [
            "=" * 50,
            "Portfolio Performance Report",
            "=" * 50,
            f"Initial Capital: ${self.initial:,.2f}",
            f"Final NAV: ${self.df['nav'].iloc[-1]:,.2f}",
            f"Portfolio Weights: {weights_str}",
            f"Leverage: {self.leverage}x",
            "-" * 50,
            "Performance Metrics:",
        ]

        for k, v in self.metrics.items():
            lines.append(f"  {k}: {v}")

        lines.append("=" * 50)
        return "\n".join(lines)

    def get_trade_log(self, rolling: int = 0) -> pd.DataFrame:
        if not self._backtest_done:
            self.backtest()

        flag = (self.df["cashflow"] != 0).astype(int)
        flag.iloc[-1] = 1

        if rolling > 0:
            window = rolling * 2 + 1
            flag = (
                flag.rolling(window=window, min_periods=1, center=True)
                .max()
                .fillna(0)
                .astype(bool)
            )

        return self.df[flag.astype(bool)].sort_index(ascending=False)

    def plot(self, figsize: tuple = (12, 6), title: str = None):
        """
        Plot Portfolio NAV and Drawdown.

        Args:
            figsize: Figure size (default: (12, 6))
            title: Chart title (default: auto-generated)
        """
        if not self._backtest_done:
            self.backtest()

        if title is None:
            ticker_str = "_".join(self.tickers)
            title = f"Portfolio NAV ({ticker_str})"

        fig, axes = plt.subplots(2, 1, figsize=figsize, sharex=True)

        # 圖1: NAV
        ax1 = axes[0]
        ax1.plot(self.df.index, self.df['nav'], label='Portfolio NAV', color='blue', linewidth=1.5)
        ax1.axhline(y=self.initial, color='gray', linestyle='--', label=f'Initial Capital (${self.initial:,.0f})')
        ax1.set_title(title)
        ax1.set_ylabel('NAV ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 圖2: Drawdown
        ax2 = axes[1]
        ax2.fill_between(self.df.index, 0, self.df['dd'] * 100, color='red', alpha=0.3, label='Drawdown')
        ax2.set_title('Drawdown')
        ax2.set_ylabel('Drawdown (%)')
        ax2.set_xlabel('Date')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.show()
        return fig



if __name__ == "__main__":
    # Usage example
    from quant_dev.backtest.portfolio import Portfolio
    pf = Portfolio(
        strategies=strats,
        weights=[0.6, 0.4],      # 60% AAPL, 40% TSLA
        leverage=1.0,
        initial=100000.0, 
    )

    # Run backtest
    pf.backtest()

    # View results
    print(pf.generate_report())

    # View trade log
    trade_log = pf.get_trade_log() 
    print(trade_log[['nav', 'cash', 'trade_pnl']].head(10))
 
    import matplotlib.pyplot as plt

    plt.figure(figsize=(12, 6))
    plt.plot(pf.df.index, pf.df['nav'], label='Portfolio NAV')
    plt.axhline(y=pf.initial, color='gray', linestyle='--', label='Initial Capital')
    plt.title('Portfolio NAV')
    plt.xlabel('Date')
    plt.ylabel('NAV ($)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.show()









