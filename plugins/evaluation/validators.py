"""
导出与生成题目校验规则 - Export and generated-question validation rules.

对应 PRD FR6.9：导出前自动校验（枚举值合规、选项数 ≤ 8、多选答案 ≥ 2 字母、
答案字母与选项列一一对应、判断题固定选项），校验不过则阻断导出并定位到题。
"""

from __future__ import annotations

from typing import Iterable

from .models import (
    DIFFICULTIES,
    JUDGE_OPTIONS,
    MAX_OPTIONS,
    OPTION_LETTERS,
    QUESTION_TYPE_ORDER,
    QUESTION_TYPES,
    Question,
)


def validate_question(question: Question) -> list[str]:
    """
    校验单题，返回问题描述列表（空列表 = 合规）。

    返回的文案可直接展示给教师，用于「定位到题」。
    """
    errors: list[str] = []

    if not (question.stem or "").strip():
        errors.append("题干不能为空")

    if question.question_type not in QUESTION_TYPES:
        errors.append(f"题型枚举不合规：{question.question_type!r}")

    if question.difficulty not in DIFFICULTIES:
        errors.append(f"难度枚举不合规：{question.difficulty!r}")

    options = list(question.options or [])
    if len(options) > MAX_OPTIONS:
        errors.append(f"选项不能超过{MAX_OPTIONS}个（当前{len(options)}个）")

    if question.question_type == "判断":
        if [str(item).strip() for item in options] != list(JUDGE_OPTIONS):
            errors.append("判断题选项必须为A.正确、B.错误")
        if (question.answer or "").strip().upper() not in ("A", "B"):
            errors.append("判断题答案必须为A或B")
        return errors

    answer = (question.answer or "").strip().upper()
    if not answer:
        errors.append("正确答案项不能为空")
        return errors

    letters = [ch for ch in answer]
    if any(ch not in OPTION_LETTERS for ch in letters):
        errors.append(f"答案字母必须在A~{OPTION_LETTERS[-1]}之间：{question.answer!r}")

    if len(set(letters)) != len(letters):
        errors.append(f"答案字母不能重复：{question.answer!r}")

    if question.question_type == "多选" and len(set(letters)) < 2:
        errors.append("多选答案至少包含两个字母")

    if question.question_type == "单选" and len(set(letters)) != 1:
        errors.append("单选答案只能有一个字母")

    # 答案字母必须与选项列一一对应（不能指向不存在的选项）
    for letter in sorted(set(letters)):
        index = OPTION_LETTERS.find(letter)
        if index >= len(options):
            errors.append(f"答案 {letter} 没有对应选项（仅 {len(options)} 个选项）")

    if any(not str(item).strip() for item in options):
        errors.append("选项内容不能为空")

    return errors


def validate_questions(questions: Iterable[Question]) -> list[str]:
    """
    批量校验，返回带定位信息的错误文案列表。

    定位格式：``知识点“X” 第 3 题（1-2-D-3）：多选答案至少包含两个字母``
    """
    errors: list[str] = []

    for index, question in enumerate(questions or [], start=1):
        problems = validate_question(question)
        if not problems:
            continue

        label = question.internal_id or f"第 {index} 题"
        for problem in problems:
            errors.append(f"{label}：{problem}")

    return errors


def sort_questions(questions: Iterable[Question]) -> list[Question]:
    """
    按导出顺序排列：题型（单选→多选→判断）→ 题号。

    题号形如 ``1-2-D-3``，按 (章, 知识点, 序号) 数值升序；缺失题号排在该题型末尾。
    """
    def sort_key(question: Question):
        type_rank = QUESTION_TYPE_ORDER.get(question.question_type, len(QUESTION_TYPES))
        return (type_rank, _question_no_key(question))

    return sorted(questions or [], key=sort_key)


def _question_no_key(question: Question) -> tuple:
    """把题号解析成可比较的数值元组；无法解析时排到末尾。"""
    raw = (question.internal_id or "").strip()
    if not raw:
        return (1, (), raw)

    parts = raw.split("-")
    numbers = []
    for part in parts:
        try:
            numbers.append(int(part))
        except ValueError:
            numbers.append(-1)
    return (0, tuple(numbers), raw)
