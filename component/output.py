"""
输出格式化模块

支持通过 config.toml 配置文案
"""

from typing import Any


# 全局配置引用
_config: dict[str, Any] = {}


def set_config(config: dict[str, Any]) -> None:
    """设置配置引用"""
    global _config
    _config = config


def get_config(path: str, default: Any = None) -> Any:
    """
    获取配置值
    
    Args:
        path: 配置路径，用 . 分隔，如 "dice.default_faces"
        default: 默认值
    
    Returns:
        配置值
    """
    keys = path.split(".")
    value = _config
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return default
        if value is None:
            return default
    return value


def get_output(key: str, **kwargs) -> str:
    """
    获取格式化的输出文本
    
    从 config.toml 的 output 配置中读取模板
    
    Args:
        key: 模板路径，如 "dice.success" 或 "skill.success"
        **kwargs: 模板变量
    
    Returns:
        格式化后的文本
    """
    # 从 config.toml 的 output 配置中获取
    output_config = _config.get("output", {})
    
    # 将 key 映射到配置路径
    keys = key.split(".")
    template = None
    
    # 遍历路径获取模板
    value = output_config
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            value = None
            break
    
    template = value
    
    # 格式化模板
    if isinstance(template, str) and template.strip():
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    
    return str(kwargs) if kwargs else ""


def get_default_output(key: str, **kwargs) -> str:
    """获取默认输出（别名）"""
    return get_output(key, **kwargs)
