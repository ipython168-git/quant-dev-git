# src/quant_dev/utils/validation.py

"""
驗證工具 - 檢查 Strategy 與 Portfolio 的一致性
"""
import pandas as pd
import numpy as np
from typing import List, Tuple, Optional

from ..backtest.strategy import Strategy
from ..backtest.portfolio import Portfolio


"""
檢查 Strategy entry/exit 同 Portfolio trade_log 是否一致
"""

def check_strategy_vs_portfolio(pf):
    """
    檢查 Portfolio 入面每個 Strategy 嘅 entry/exit
    同 Portfolio 嘅 trade_log 是否匹配 
    """
    print("=" * 70)
    print("Strategy vs Portfolio 一致性檢查")
    print("=" * 70)
    
    all_match = True
    
    for idx, strat in enumerate(pf.strategies):
        ticker = strat.ticker
        weight = pf.weights[idx]
        
        print(f"\n📊 {ticker} (權重: {weight:.1%})")
        print("-" * 50)
        
        # 1. Strategy 嘅交易記錄
        strat_trades = strat.get_trade_log(rolling=0)
        strat_entries = strat_trades[strat_trades['entry'].notna()]
        strat_exits = strat_trades[strat_trades['exit'].notna()]
        
        print(f"  Strategy 交易次數: {len(strat_trades)}")
        print(f"    - 入市: {len(strat_entries)} 次")
        print(f"    - 出市: {len(strat_exits)} 次")
        
        # 2. Portfolio 嘅交易記錄（篩選返呢個 ticker）
        pf_trades = pf.get_trade_log(rolling=0)
        
        # Portfolio df 入面嘅 column 名
        entry_col = f"entry{idx}_{ticker}"
        exit_col = f"exit{idx}_{ticker}"
        
        if entry_col in pf.df.columns and exit_col in pf.df.columns:
            pf_entries = pf.df[pf.df[entry_col].notna()]
            pf_exits = pf.df[pf.df[exit_col].notna()]
            
            print(f"\n  Portfolio 記錄 ({ticker}):")
            print(f"    - 入市: {len(pf_entries)} 次")
            print(f"    - 出市: {len(pf_exits)} 次")
            
            # 3. 比對 entry 數量
            if len(strat_entries) == len(pf_entries):
                print(f"    ✅ Entry 數量匹配: {len(strat_entries)}")
            else:
                print(f"    ❌ Entry 數量不匹配: Strategy={len(strat_entries)}, Portfolio={len(pf_entries)}")
                all_match = False
            
            # 4. 比對 exit 數量
            if len(strat_exits) == len(pf_exits):
                print(f"    ✅ Exit 數量匹配: {len(strat_exits)}")
            else:
                print(f"    ❌ Exit 數量不匹配: Strategy={len(strat_exits)}, Portfolio={len(pf_exits)}")
                all_match = False
            
            # 5. 比對 entry 價格（抽查頭 5 筆）
            if len(strat_entries) > 0 and len(pf_entries) > 0:
                strat_entry_prices = strat_entries['entry'].head(5).values
                pf_entry_prices = pf_entries[entry_col].head(5).values
                
                # 因為 Portfolio 嘅 entry 可能同 Strategy 嘅 entry 有 sign 分別
                # Portfolio 嘅 entry 應該同 Strategy 嘅 entry 一致
                match_count = 0
                for i, (s, p) in enumerate(zip(strat_entry_prices, pf_entry_prices)):
                    if pd.isna(s) and pd.isna(p):
                        match_count += 1
                    elif not pd.isna(s) and not pd.isna(p) and abs(s - p) < 0.001:
                        match_count += 1
                    else:
                        print(f"    ⚠️  Entry 價格不匹配 (第 {i+1} 筆): Strategy={s}, Portfolio={p}")
                
                if match_count == len(strat_entry_prices):
                    print(f"    ✅ Entry 價格匹配 (頭 {len(strat_entry_prices)} 筆)")
            
            # 6. 比對 exit 價格（抽查頭 5 筆）
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
                        print(f"    ⚠️  Exit 價格不匹配 (第 {i+1} 筆): Strategy={s}, Portfolio={p}")
                
                if match_count == len(strat_exit_prices):
                    print(f"    ✅ Exit 價格匹配 (頭 {len(strat_exit_prices)} 筆)")
        else:
            print(f"  ⚠️  Portfolio 中找不到 {ticker} 嘅 entry/exit columns")
            all_match = False
    
    # 總結
    print("\n" + "=" * 70)
    if all_match:
        print("✅ 所有檢查通過！Strategy 與 Portfolio 一致")
    else:
        print("❌ 發現不一致，請檢查以上標記")
    print("=" * 70)
    
    return all_match
