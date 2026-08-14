# quant_dev/strategies/__init__.py 
"""
Strategies module - provides various default strategies (Lazy Import).
"""

__all__ = [
    "create_golden_and_death_cross_strategy",
    "create_donchian_breakout_strategy",
]

# 策略名稱列表（用於 __getattr__ 檢查）
_STRATEGY_NAMES = {
    "create_golden_and_death_cross_strategy": ".golden_and_death_cross",
    "create_donchian_breakout_strategy": ".donchian_breakout",
}


def __getattr__(name):
    if name in _STRATEGY_NAMES:
        module_name = _STRATEGY_NAMES[name]
        import importlib
        module = importlib.import_module(module_name, package=__package__) 
        return getattr(module, name)

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")