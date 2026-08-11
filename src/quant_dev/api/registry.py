# quant_dev/api/registry.py
"""
策略註冊表 - 所有可用策略嘅登記處
"""
from quant_dev.strategies import (
    create_golden_and_death_cross_strategy,
    create_donchian_breakout_strategy,
)


# ============================================================
# 策略註冊表
# ============================================================
STRATEGY_REGISTRY = {
    "golden_cross": {
        "name": "golden_cross",
        "display_name": "黃金交叉/死亡交叉",
        "description": "短期 SMA 升穿/跌穿長期 SMA 時進出",
        "function": create_golden_and_death_cross_strategy,
        "default_params": {
            "sma_fast": 20,
            "sma_slow": 50,
            "direction": "buy",
            "entry_order_type": "stop",
            "exit_order_type": "stop",
            "gap_entry": "open",
            "gap_exit": "open",
        },
        "required_params": ["sma_fast", "sma_slow"],
    },
    "donchian": {
        "name": "donchian",
        "display_name": "Donchian 突破策略",
        "description": "價格突破 N 日高/低位時進出",
        "function": create_donchian_breakout_strategy,
        "default_params": {
            "period": 20,
            "direction": "buy",
            "entry_order_type": "stop",
            "exit_order_type": "stop",
            "gap_entry": "open",
            "gap_exit": "open",
        },
        "required_params": ["period"],
    },
}


def get_strategy(name: str):
    """攞策略 function"""
    if name not in STRATEGY_REGISTRY:
        return None
    return STRATEGY_REGISTRY[name]


def list_strategies():
    """列出所有策略"""
    return [
        {
            "name": info["name"],
            "display_name": info["display_name"],
            "description": info["description"],
            "default_params": info["default_params"],
            "required_params": info["required_params"],
        }
        for info in STRATEGY_REGISTRY.values()
    ]