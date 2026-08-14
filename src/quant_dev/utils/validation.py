# src/quant_dev/utils/validation.py

"""
Validation utilities - check consistency between Strategy and Portfolio.
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional

from ..backtest.strategy import Strategy
from ..backtest.portfolio import Portfolio

def check_strategy_vs_portfolio(pf):
    """
    Check that each Strategy's entry/exit matches the Portfolio's trade log.
    """
    print("=" * 70)
    print("Strategy vs Portfolio Consistency Check")
    print("=" * 70)
    
    all_match = True
    
    for idx, strat in enumerate(pf.strategies):
        ticker = strat.ticker
        weight = pf.weights[idx]
        
        print(f"\n📊 {ticker} (Weight: {weight:.1%})")
        print("-" * 50)
        
        # 1. Strategy trade log
        strat_trades = strat.get_trade_log(rolling=0)
        strat_entries = strat_trades[strat_trades['entry'].notna()]
        strat_exits = strat_trades[strat_trades['exit'].notna()]
        
        print(f"  Strategy trades: {len(strat_trades)}")
        print(f"    - Entries: {len(strat_entries)}")
        print(f"    - Exits: {len(strat_exits)}")
        
        # 2. Portfolio trade log for this ticker
        pf_trades = pf.get_trade_log(rolling=0)
        
        # Portfolio df column names
        entry_col = f"entry{idx}_{ticker}"
        exit_col = f"exit{idx}_{ticker}"
        
        if entry_col in pf.df.columns and exit_col in pf.df.columns:
            pf_entries = pf.df[pf.df[entry_col].notna()]
            pf_exits = pf.df[pf.df[exit_col].notna()]
            
            print(f"\n  Portfolio records ({ticker}):")
            print(f"    - Entries: {len(pf_entries)}")
            print(f"    - Exits: {len(pf_exits)}")
            
            # 3. Compare entry counts
            if len(strat_entries) == len(pf_entries):
                print(f"    ✅ Entry count matches: {len(strat_entries)}")
            else:
                print(f"    ❌ Entry count mismatch: Strategy={len(strat_entries)}, Portfolio={len(pf_entries)}")
                all_match = False
            
            # 4. Compare exit counts
            if len(strat_exits) == len(pf_exits):
                print(f"    ✅ Exit count matches: {len(strat_exits)}")
            else:
                print(f"    ❌ Exit count mismatch: Strategy={len(strat_exits)}, Portfolio={len(pf_exits)}")
                all_match = False
            
            # 5. Compare entry prices (check first 5 entries)
            if len(strat_entries) > 0 and len(pf_entries) > 0:
                strat_entry_prices = strat_entries['entry'].head(5).values
                pf_entry_prices = pf_entries[entry_col].head(5).values
                
                match_count = 0
                for i, (s, p) in enumerate(zip(strat_entry_prices, pf_entry_prices)):
                    if pd.isna(s) and pd.isna(p):
                        match_count += 1
                    elif not pd.isna(s) and not pd.isna(p) and abs(s - p) < 0.001:
                        match_count += 1
                    else:
                        print(f"    ⚠️  Entry price mismatch (item {i+1}): Strategy={s}, Portfolio={p}")
                
                if match_count == len(strat_entry_prices):
                    print(f"    ✅ Entry price matches (first {len(strat_entry_prices)} items)")
            
            # 6. Compare exit prices (check first 5 exits)
            if len(strat_exits) > 0 and len(pf_exits) > 0:
                strat_exit_prices = strat_exits['exit'].head(5).values
                pf_exit_prices = pf_exits[exit_col].head(5).values
                
                match_count = 0
                for i, (s, p) in enumerate(zip(strat_exit_prices, pf_exit_prices)):
                    if pd.isna(s) and pd.isna(p):
                        match_count += 1
                    elif not pd.isna(s) and not pd.isna(p) and abs(s - p) < 0.001:
                        match_count += 1
                    else:
                        print(f"    ⚠️  Exit price mismatch (item  {i+1}): Strategy={s}, Portfolio={p}")
                
                if match_count == len(strat_exit_prices):
                    print(f"    ✅ Exit price matches (first {len(strat_exit_prices)} items)")
        else:
            print(f"  ⚠️  Could not find entry/exit columns for {ticker} in Portfolio")
            all_match = False
    
    # Summary
    print("\n" + "=" * 70)
    if all_match:
        print("✅ All checks passed! Strategy and Portfolio are consistent")
    else:
        print("❌ Inconsistencies found, please check the flagged items above")
    print("=" * 70)
    
    return all_match
