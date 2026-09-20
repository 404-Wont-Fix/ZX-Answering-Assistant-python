"""
通用插件设置 schema 助手 - Shared plugin setting schema helpers.

供插件中心通用设置弹窗（`src.ui.components.build_plugin_settings_dialog`）
以及插件自身读取配置时复用：把「manifest 里声明的字段定义」与「已持久化的原始值」
归一化成可用值，并提供必填校验。

schema 字段结构（每个字段一个 dict）：

    {
        "key": "api_key",          # 必填，持久化时的键名
        "label": "AI API Key",     # 展示名（必填校验的报错文案会用到）
        "type": "password",        # text | password | number | switch | select
        "default": "",             # 缺省值
        "required": True,          # 是否必填（仅校验非空）
        "options": [               # 仅 type == "select" 时使用
            {"key": "high", "text": "高"}
        ],
    }
"""

from __future__ import annotations

from typing import Any

# 支持渲染的字段类型；未识别的类型按 "text" 处理。
SCHEMA_FIELD_TYPES = ("text", "password", "number", "switch", "select")


def setting_value(schema: dict, stored: Any) -> Any:
    """
    把已持久化的原始值按 schema 声明的类型归一化。

    Args:
        schema: 单个字段的 schema dict（含 "type" / "default" 可选）
        stored: `settings_manager.get_plugin_config()` 取回的原始值；
                None 表示从未保存过，回落到 schema["default"]

    Returns:
        归一化后的值：switch → bool；number → int（转换失败回落 default/0）；
        其余 → str（None → ""）
    """
    value = schema.get("default") if stored is None else stored
    kind = schema.get("type", "text")

    if kind == "switch":
        return bool(value)

    if kind == "number":
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(schema.get("default", 0) or 0)

    if value is None:
        return ""
    return str(value)


def validate_settings(schema: list[dict], values: dict) -> list[str]:
    """
    校验必填字段，返回人类可读的错误文案列表（空列表 = 通过）。

    Args:
        schema: schema 字段列表
        values: {key: value} 待保存的值

    Returns:
        list[str]: 形如 ["AI API Key不能为空"]，为空表示校验通过
    """
    errors: list[str] = []

    for field in schema:
        if not field.get("required"):
            continue
        if str(values.get(field.get("key"), "") or "").strip():
            continue
        errors.append(f"{field.get('label', field.get('key'))}不能为空")

    return errors
