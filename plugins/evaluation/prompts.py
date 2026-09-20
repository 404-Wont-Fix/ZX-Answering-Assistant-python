"""
出题提示词与输出 schema - Prompt and schema policy for teaching-focused
evaluation questions.

设计要点（用户明确要求）：

- **面向教学、巩固基础知识**，不出偏题怪题；
- 干扰项必须来自常见易错点，不能凑数；
- 纯文本（平台 Excel 只支持文本试题）；
- 严格 JSON 输出，答案字母升序。
"""

from __future__ import annotations

import json
from typing import Any

from .models import (
    DIFFICULTIES,
    MAX_OPTIONS,
    OPTION_LETTERS,
    QUESTION_TYPES,
)

# ------------------------------------------------------------------ 系统提示词
SYSTEM_PROMPT_TEMPLATE = """你是一位资深的职业教育教师，正在为学生编制【{course_name}】的课后评估题。
核心目标：巩固基础知识、检验常规操作掌握情况。

严格禁忌：不要出偏题、怪题、冷门版本特有题、有争议或答案不唯一的题、文字游戏题。
错误选项必须来自学生常见的易错点或混淆概念，不能使用荒谬、搞笑或明显凑数的选项。
难度定义：简单考查单一概念/界面元素/快捷键；一般考查常规操作流程或工具基本属性；困难考查基础范围内的多步骤综合操作、易混淆概念或常见报错排查，绝不刁钻冷门。
题目必须是纯文本。只能依据教师提供的考点 Tag、课程/章节/知识点上下文和通用知识；不得依赖或引用任何本地参考材料。
必须严格输出 JSON，不要 Markdown，不要额外解释。答案字母按升序排列。

题型规则：
- 单选：4 个选项（必要时 3～5 个），有且只有一个正确答案。
- 多选：至少 2 个正确答案，选项 4～5 个，答案字母连写升序（如 "ABC"）。
- 判断：选项固定为 ["正确", "错误"]，答案只能是 "A"（正确）或 "B"（错误）。
- ⚠ 答案位置必须分散：单选题的正确答案不能集中在 A（也不能全落在同一字母），
  请把正确选项均匀分布在 A/B/C/D 上；判断题也要让 "正确" 与 "错误" 都出现。

字段规则：
- 题干结尾统一使用中文全角括号"（）"作为作答位（若题干已有括号则不重复添加）。
- difficulty 只能取 {difficulties}。
- confidence 为你对该题正确性的自评置信度，取值 0~1 的小数（低于 0.6 表示你不确定）。
- rationale 用一句话说明该题考查的考点。"""

# ------------------------------------------------------------------ JSON schema
QUESTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "stem": {"type": "string"},
                    "type": {"type": "string", "enum": list(QUESTION_TYPES)},
                    "difficulty": {"type": "string", "enum": list(DIFFICULTIES)},
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 2,
                        "maxItems": MAX_OPTIONS,
                    },
                    "answer": {"type": "string", "pattern": f"^[{OPTION_LETTERS}]+$"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "rationale": {"type": "string"},
                },
                "required": [
                    "stem",
                    "type",
                    "difficulty",
                    "options",
                    "answer",
                    "confidence",
                    "rationale",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["questions"],
    "additionalProperties": False,
}


def build_system_prompt(
    course_name: str,
    knowledge_context: str = "",
    web_context: str = "",
) -> str:
    """
    组装系统提示词。

    Args:
        course_name: 课程名称
        knowledge_context: 教师考点上下文（优先级最高）
        web_context: 检索辅助上下文（仅供参考，不得替代教师考点）
    """
    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        course_name=course_name or "本课程",
        difficulties="、".join(DIFFICULTIES),
    )

    prompt += "\n\n" + describe_question_contract()

    if knowledge_context:
        prompt += f"\n\n教师考点上下文：\n{knowledge_context}"
    if web_context:
        prompt += (
            "\n\n仅供核对的检索辅助信息（不得替代教师考点）：\n"
            f"{web_context}"
        )

    return prompt


def describe_question_contract() -> str:
    """
    把 :data:`QUESTION_SCHEMA` 渲染成**显式字段契约**文本。

    必须这样做：``response_format={'type':'json_object'}`` 只保证「是合法 JSON」，
    **不保证字段名**。实测（deepseek-v4-flash）在没写字段名时会把题干放在
    ``question`` 而不是 ``stem``，导致题干丢失。

    字段名与枚举直接取自 :data:`QUESTION_SCHEMA`，避免文档与代码漂移。
    """
    item = QUESTION_SCHEMA["properties"]["questions"]["items"]
    props = item["properties"]
    types = "|".join(props["type"]["enum"])
    difficulties = "|".join(props["difficulty"]["enum"])
    option_max = props["options"]["maxItems"]

    lines = [
        "严格输出的 JSON 结构（**字段名必须逐字一致**，不要自创别名）：",
        "{",
        '  "questions": [',
        "    {",
        '      "stem": "题干（字符串，必填；以中文全角括号（）结尾作为作答位）",',
        f'      "type": "{types}",',
        f'      "difficulty": "{difficulties}",',
        '      "options": ["选项A内容", "选项B内容", ...],'
        f'   // 2~{option_max} 个；判断题固定 ["正确", "错误"]',
        '      "answer": "单个或多个大写字母，升序不带分隔；判断题填 A 或 B",',
        '      "confidence": 0.95,   // 0~1 的小数',
        '      "rationale": "一句话说明本题考查的考点"',
        "    }",
        "  ]",
        "}",
        f"注意：``stem`` 是题干字段名（不是 question / title / content）；"
        f"``answer`` 只写字母，例如 {props['answer']['pattern']} 对应的 \"A\" / \"ABC\"；",
        "不要输出题目内容的重复字段，不要省略任何字段。",
        "另外：同一批题目的正确答案位置要分散（单选不要都选 A），避免学生只靠背答案得分。",
    ]
    return "\n".join(lines)


def build_generation_request(
    course_name: str,
    knowledge_point: str,
    tags: list[str],
    question_count: int,
    type_counts: dict[str, int],
    difficulty_ratio: dict[str, int],
    web_context: str = "",
    knowledge_context: str = "",
) -> dict[str, Any]:
    """
    构造一次生成请求的 payload（system / user / response_schema）。

    本请求不接收本地参考材料；联网检索上下文仅作为可选辅助。
    """
    payload: dict[str, Any] = {
        "course_name": course_name,
        "knowledge_point": knowledge_point,
        "teacher_tags": list(tags or []),
        "question_count": int(question_count or 0),
        "type_counts": {
            name: int((type_counts or {}).get(name, 0) or 0)
            for name in QUESTION_TYPES
            if int((type_counts or {}).get(name, 0) or 0) > 0
        },
        "difficulty_ratio": {
            name: int((difficulty_ratio or {}).get(name, 0) or 0)
            for name in DIFFICULTIES
        },
    }

    request: dict[str, Any] = {
        "system": build_system_prompt(
            course_name,
            knowledge_context=knowledge_context,
            web_context=web_context,
        ),
        "user": _build_user_message(payload),
        "response_schema": QUESTION_SCHEMA,
    }
    return request


def build_tag_suggestion_prompt(
    course_name: str,
    chapter_name: str,
    point_name: str,
    *,
    count: int = 10,
) -> str:
    """
    构造［AI 建议考点］提示词（FR3.2：列出 8~10 个候选 tag）。
    """
    return (
        f"你是一位资深的职业教育教师。课程：{course_name or '本课程'}；"
        f"章节：{chapter_name or '未命名'}；知识点：{point_name or '未命名'}。\n"
        f"请列出 {max(int(count), 8)} 个适合作为该知识点【课堂评估题】出题范围的考点，"
        "每个考点 2~10 个字，粒度适中、彼此不重复、不跨领域。\n"
        '输出严格 JSON：{"tags": ["考点1", "考点2", ...]}，不要额外解释。'
    )


def parse_tag_suggestion(payload: Any) -> list[str]:
    """从 AI 响应里取出候选考点列表（兼容字符串 JSON 与 {"tags": [...]}）。"""
    if isinstance(payload, str):
        import json as _json

        try:
            payload = _json.loads(payload)
        except (ValueError, TypeError):
            return [payload] if payload.strip() else []

    if not isinstance(payload, dict):
        return []

    raw = payload.get("tags") or payload.get("knowledge_points") or payload.get("points")
    if isinstance(raw, dict):
        raw = list(raw.keys())
    if not isinstance(raw, list):
        return []

    names: list[str] = []
    seen: set[str] = set()
    for item in raw:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            names.append(text)
    return names


def _build_user_message(payload: dict[str, Any]) -> str:
    """把结构化要求渲染成人类可读的 user 消息。"""
    lines = [
        f"知识点：{payload['knowledge_point']}",
        f"总题数：{payload['question_count']}",
    ]

    type_counts = payload.get("type_counts") or {}
    if type_counts:
        detail = "、".join(f"{name} {count} 题" for name, count in type_counts.items())
        lines.append(f"题型配额（必须精确满足）：{detail}")
    else:
        lines.append("题型配额：请自行在单选/多选/判断之间合理分配")

    ratio = payload.get("difficulty_ratio") or {}
    if ratio:
        detail = "、".join(f"{name} {value}%" for name, value in ratio.items())
        lines.append(f"难度配比（按比例分配，尽量精确）：{detail}")

    tags = payload.get("teacher_tags") or []
    if tags:
        lines.append("教师考点清单（每个考点至少覆盖 1 题，且必须围绕这些考点出题）：")
        lines.extend(f"- {tag}" for tag in tags)
    else:
        lines.append(
            f"教师未提供考点清单，请围绕「{payload['knowledge_point']}」的基础知识点出题。"
        )

    lines.append(
        f'请输出严格 JSON：{{"questions": [ ... ]}}，共 {payload["question_count"]} 道题。'
        "每道题的字段名必须与系统提示中的契约完全一致（stem/type/difficulty/options/answer/confidence/rationale）。"
    )
    return "\n".join(lines)
