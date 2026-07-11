"""题库答案匹配的共享原语（纯 API 答题模式专用）。

仅统一"按题目 ID 精确匹配 + 提取正确选项 ID"的逻辑，供：
- 学生端纯 API 暴力模式（src/answering/api_answer.py）
- 认证端纯 API 模式（src/certification/api_answer.py）
- 云考试插件（plugins/cloud_exam/workflow.py）
三处复用。

浏览器自动化答题路径（需返回页面 value/内容用于点击 DOM）不使用本模块——
它们的返回值语义不同（要点 DOM 而非提交 ID），是业务必需的差异，保持独立实现。

本模块全部为纯函数，无类/self 依赖，可独立单元测试。
"""

from typing import Dict, List, Optional

# 题目 ID 的常见字段名（兼容不同导出来源与 API 命名）
_QUESTION_ID_FIELDS = ("QuestionID", "questionID", "question_id", "id")
# 正确选项 ID 的常见字段名
_OPTION_ID_FIELDS = ("id", "answerID", "AnswerID")


def _iter_bank_knowledges(question_bank: Dict) -> List[Dict]:
    """收集题库中的所有知识点，兼容 4 种导出结构。

    覆盖：
    - 单课程：question_bank["class"]["course"]["chapters"]
    - 顶层章节：question_bank["chapters"]
    - 多课程（新）：question_bank["courses"][].chapters
    - 多课程（旧）：question_bank["course_list"][].chapters
    """
    if not question_bank:
        return []

    chapters: List[Dict] = []
    class_info = question_bank.get("class", {})
    course_info = class_info.get("course", {}) if isinstance(class_info, dict) else {}
    chapters.extend(course_info.get("chapters", []))

    chapters.extend(question_bank.get("chapters", []))

    for course in question_bank.get("courses", []):
        chapters.extend(course.get("chapters", []))

    for course in question_bank.get("course_list", []):
        chapters.extend(course.get("chapters", []))

    knowledges: List[Dict] = []
    for chapter in chapters:
        if isinstance(chapter, dict):
            knowledges.extend(chapter.get("knowledges", []))
    return knowledges


def _read_question_id(question: Dict) -> str:
    """从题库题目记录读取题目 ID，兼容多种字段命名。只做字段兼容，不做标题模糊匹配。"""
    if not isinstance(question, dict):
        return ""
    for key in _QUESTION_ID_FIELDS:
        value = question.get(key)
        if value is not None:
            return str(value).strip()
    return ""


def _extract_correct_option_ids(bank_question: Dict) -> List[str]:
    """提取题目中标记为正确（isTrue）的选项 ID 列表。

    过滤掉缺失 ID 的选项（避免返回空串导致调用方提交无效答案），
    并统一 str 化与去空白；选项 ID 字段兼容 id/answerID/AnswerID。
    """
    ids: List[str] = []
    if not isinstance(bank_question, dict):
        return ids
    for opt in bank_question.get("options", []):
        if not isinstance(opt, dict):
            continue
        if opt.get("isTrue"):
            for key in _OPTION_ID_FIELDS:
                value = opt.get(key)
                if value:
                    ids.append(str(value).strip())
                    break
    return ids


def find_correct_answer_ids(
    question_bank: Dict,
    question_id: str,
    *,
    scope_knowledge: Optional[Dict] = None,
) -> Optional[List[str]]:
    """按题目 ID 在题库中精确匹配，返回正确选项的 ID 列表。

    Args:
        question_bank: 题库数据（支持 4 种导出结构，见 _iter_bank_knowledges）。
        question_id: 要匹配的题目 ID。
        scope_knowledge: 可选，限定仅在该知识点 dict 内搜索；None 表示全局搜索。

    Returns:
        正确选项 ID 列表；题目未命中、或命中但无正确选项标记时返回 None。
    """
    if not question_bank or question_id is None:
        return None
    target = str(question_id).strip()
    if not target:
        return None

    if scope_knowledge is not None:
        search_knowledges: List[Dict] = [scope_knowledge]
    else:
        search_knowledges = _iter_bank_knowledges(question_bank)

    for knowledge in search_knowledges:
        if not isinstance(knowledge, dict):
            continue
        for bank_question in knowledge.get("questions", []):
            if _read_question_id(bank_question) == target:
                ids = _extract_correct_option_ids(bank_question)
                return ids if ids else None
    return None
