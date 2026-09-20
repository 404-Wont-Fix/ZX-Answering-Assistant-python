"""
与 UI / AI 无关的质量检查 - Quality checks that do not depend on the UI or AI provider.

这些检查用于 Step5 生成后的自检与 Step6 汇总提示，全部是纯函数便于单测。
"""

from __future__ import annotations

from typing import Any, Iterable

from .models import DIFFICULTIES, OPTION_LETTERS, QUESTION_TYPES, Question

# 单题成本估算用的粗略 token 假设（仅用于给教师一个量级参考）
_PROMPT_TOKENS_PER_POINT = 350
_COMPLETION_TOKENS_PER_QUESTION = 160
_COST_PER_1K_TOKENS = 0.0014  # 元/1K tokens（DeepSeek 量级）


def duplicate_pairs(questions: Iterable[Question]) -> list[tuple[int, int]]:
    """
    找出题干高度重复的题对（返回 1-based 下标对）。

    用「规范化文本完全相同」判定——保守策略，避免误报。
    """
    seen: dict[str, int] = {}
    duplicates: list[tuple[int, int]] = []

    for index, question in enumerate(questions or [], start=1):
        key = _normalize_stem(question.stem)
        if not key:
            continue
        if key in seen:
            duplicates.append((seen[key], index))
        else:
            seen[key] = index

    return duplicates


def _normalize_stem(stem: str) -> str:
    """去掉空白、括号与标点，仅保留字符与数字，用于重复判定。"""
    text = str(stem or "")
    return "".join(
        ch for ch in text if ch.isalnum() or "\u4e00" <= ch <= "\u9fff"
    )


def answer_distribution_warning(questions: Iterable[Question]) -> list[str]:
    """
    答案分布预警：单选题答案过度集中在同一字母时给出提示。

    教学场景下答案位置过于集中会让背答案的学生获益，因此超过 60% 时提醒。
    """
    warnings: list[str] = []
    single_choice = [q for q in (questions or []) if q.question_type == "单选"]
    if len(single_choice) < 5:
        return warnings

    counter: dict[str, int] = {}
    for question in single_choice:
        letter = (question.answer or "").strip().upper()[:1]
        if letter:
            counter[letter] = counter.get(letter, 0) + 1

    if not counter:
        return warnings

    letter, count = max(counter.items(), key=lambda item: item[1])
    ratio = count / len(single_choice)
    if ratio > 0.6:
        warnings.append(
            f"单选题答案 {letter} 占比 {ratio:.0%}（{count}/{len(single_choice)}），建议打散"
        )
    return warnings


def coverage(questions: Iterable[Question], tags: Iterable[str] | None = None) -> dict[str, Any]:
    """
    覆盖率检查：每个考点 tag 是否至少有一题命中（FR4.6 / FR3.6 的「每考点至少1题」）。

    Returns:
        dict: ``{"total": n, "covered": [...], "missing": [...], "ratio": 0.0~1.0}``
    """
    tag_list = [str(tag).strip() for tag in (tags or []) if str(tag).strip()]
    questions = list(questions or [])

    if not tag_list:
        return {"total": 0, "covered": [], "missing": [], "ratio": 1.0}

    haystack = "\n".join(
        f"{q.stem}\n{q.rationale}" for q in questions
    )

    covered = [tag for tag in tag_list if tag in haystack]
    missing = [tag for tag in tag_list if tag not in covered]

    return {
        "total": len(tag_list),
        "covered": covered,
        "missing": missing,
        "ratio": len(covered) / len(tag_list) if tag_list else 1.0,
    }


def type_difficulty_summary(questions: Iterable[Question]) -> dict[str, dict[str, int]]:
    """统计题型 × 难度的分布（Step6 概览条用）。"""
    summary = {
        question_type: {difficulty: 0 for difficulty in DIFFICULTIES}
        for question_type in QUESTION_TYPES
    }

    for question in questions or []:
        if question.question_type in summary and question.difficulty in DIFFICULTIES:
            summary[question.question_type][question.difficulty] += 1

    return summary


def estimate_cost(
    point_count: int,
    question_count: int,
    *,
    price_per_1k_tokens: float = _COST_PER_1K_TOKENS,
) -> dict[str, Any]:
    """
    粗略估算一次生成的 token 与费用（仅作量级参考，不代表真实计费）。

    Returns:
        dict: ``{"prompt_tokens", "completion_tokens", "total_tokens", "cost"（元）}``
    """
    points = max(int(point_count or 0), 0)
    questions = max(int(question_count or 0), 0)

    prompt_tokens = points * _PROMPT_TOKENS_PER_POINT
    completion_tokens = questions * _COMPLETION_TOKENS_PER_QUESTION
    total_tokens = prompt_tokens + completion_tokens

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost": round(total_tokens / 1000 * float(price_per_1k_tokens), 4),
    }


def option_length_warning(questions: Iterable[Question], *, max_chars: int = 120) -> list[str]:
    """选项过长预警（平台为纯文本单行单元格，过长会影响导入后的可读性）。"""
    warnings: list[str] = []
    for index, question in enumerate(questions or [], start=1):
        for letter_index, option in enumerate(question.options or []):
            if len(str(option)) <= max_chars:
                continue
            letter = OPTION_LETTERS[letter_index] if letter_index < len(OPTION_LETTERS) else "?"
            label = question.internal_id or f"第 {index} 题"
            warnings.append(f"{label} 选项{letter} 超过 {max_chars} 字，建议精简")
    return warnings
