"""
输出格式化模块

支持配置文件中的文案可编辑
"""

import json
import os
from typing import Any


# 全局配置引用
_config: dict[str, Any] = {}
_schema: dict[str, Any] = {}
_overrides: dict[str, Any] = {"output": {}}
_overrides_loaded = False


def _get_schema_path() -> str:
    """获取 Schema 文件路径"""
    return os.path.join(os.path.dirname(__file__), "..", "_conf_schema.json")


def _get_overrides_path() -> str:
    """获取覆盖文件路径"""
    return os.path.join(os.path.dirname(__file__), "..", "data", "overrides.json")


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


def _load_overrides() -> dict:
    """加载本地覆盖文件"""
    global _overrides, _overrides_loaded
    if _overrides_loaded:
        return _overrides
    _overrides_loaded = True
    
    overrides_path = _get_overrides_path()
    try:
        if os.path.exists(overrides_path):
            with open(overrides_path, "r", encoding="utf-8") as f:
                _overrides = json.load(f)
    except Exception:
        _overrides = {"output": {}}
    
    _overrides.setdefault("output", {})
    return _overrides


def _save_overrides():
    """保存覆盖数据到文件"""
    overrides_path = _get_overrides_path()
    try:
        os.makedirs(os.path.dirname(overrides_path), exist_ok=True)
        with open(overrides_path, "w", encoding="utf-8") as f:
            json.dump(_overrides, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _resolve_path(source: dict, keys: list[str]) -> Any:
    """按点路径读取配置节点"""
    value = source
    for key in keys:
        if not isinstance(value, dict):
            return None
        if key not in value:
            return None
        value = value[key]
        if isinstance(value, dict) and "default" in value:
            value = value["default"]
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
    # 优先查本地覆盖
    overrides = _load_overrides()
    if path in overrides.get("config", {}):
        return overrides["config"][path]
    
    # 从配置中获取
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
    1. 本地覆盖 (overrides.json)
    2. 运行时配置 (config.toml)
    3. Schema 默认值 (_conf_schema.json)
    
    Args:
        key: 模板路径，如 "output.dice.normal.success"
        **kwargs: 模板变量
    
    Returns:
        格式化后的文本
    """
    # 优先查本地覆盖
    overrides = _load_overrides()
    if key in overrides.get("output", {}):
        template = overrides["output"][key]
        if isinstance(template, str) and template.strip():
            try:
                return template.format(**kwargs)
            except Exception:
                return template
    
    # 从运行时配置中获取
    template = _resolve_path(_config, key.split("."))
    if isinstance(template, str) and template.strip():
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    
    # 从 Schema 中获取默认值
    schema = _load_schema()
    template = _resolve_path(schema, key.split("."))
    if isinstance(template, str) and template.strip():
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    
    return str(kwargs) if kwargs else ""


def set_output_override(key: str, value: str) -> tuple[bool, str]:
    """
    设置输出模板的覆盖值
    
    Args:
        key: 模板路径
        value: 新的模板值
    
    Returns:
        (成功, 消息)
    """
    _load_overrides()
    if not isinstance(value, str) or not value.strip():
        return False, f"输出模板 [{key}] 不能为空。"
    _overrides["output"][key] = value
    _save_overrides()
    return True, f"输出模板 [{key}] 已更新。"


def get_output_list() -> dict:
    """返回当前所有覆盖项"""
    _load_overrides()
    return dict(_overrides)


def get_default_output(key: str, **kwargs) -> str:
    """获取默认输出（别名）"""
    return get_output(key, **kwargs)
