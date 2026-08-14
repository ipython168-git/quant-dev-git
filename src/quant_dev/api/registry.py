# quant_dev/api/registry.py
"""
Strategy registry - registration point for all available strategies.
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
        "display_name": "Golden Cross / Death Cross",
        "description": "Entry/exit when short-term SMA crosses above/below long-term SMA",
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
        "display_name": "Donchian Breakout",
        "description": "Entry/exit when price breaks above/below N-day high/low",
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
    """Get strategy function by name"""
    if name not in STRATEGY_REGISTRY:
        return None
    return STRATEGY_REGISTRY[name]


def list_strategies():
    """List all available strategies"""
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