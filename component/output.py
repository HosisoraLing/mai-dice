"""
输出格式化模块

支持通过 config.toml 配置文案
"""

import json
import os
from typing import Any


# 全局配置引用
_config: dict[str, Any] = {}
_schema: dict[str, Any] = {}


def _get_schema_path() -> str:
    """获取 Schema 文件路径"""
    return os.path.join(os.path.dirname(__file__), "..", "_conf_schema.json")


def _load_schema() -> dict:
    """加载配置 Schema"""
    global _schema
    if _schema:
        return _schema
    
    schema_path = _get_schema_path()
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            _schema = json.load(f)
        return _schema
    except Exception:
        return {}


def _resolve_path(source: dict, keys: list[str]) -> Any:
    """按点路径读取配置节点"""
    value = source
    for key in keys:
        if not isinstance(value, dict):
            return None
        if key not in value:
            return None
        value = value[key]
    return value


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
    
    优先级：
    1. config.toml 中的 output 配置
    2. Schema 默认值 (_conf_schema.json)
    
    Args:
        key: 模板路径，如 "dice.success" 或 "skill.success"
        **kwargs: 模板变量
    
    Returns:
        格式化后的文本
    """
    # 从 config.toml 的 output 配置中获取
    output_config = _config.get("output", {})
    
    # 将 key 映射到配置路径
    template = None
    
    # 检查是否有直接匹配
    if key in output_config:
        template = output_config[key]
    
    # 检查嵌套匹配（如 dice.success -> output.dice.success）
    if template is None:
        keys = key.split(".")
        template = _resolve_path(output_config, keys)
    
    # 如果配置中没有，从 Schema 中获取默认值
    if template is None:
        schema = _load_schema()
        output_schema = schema.get("output", {})
        template = _resolve_path(output_schema, keys if 'keys' in dir() else key.split("."))
    
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
