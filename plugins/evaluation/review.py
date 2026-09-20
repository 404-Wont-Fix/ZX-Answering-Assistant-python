"""
结果审核与生成运行控制 - Review and generation control services.

对应 PRD §4.6：

- FR6.2 每知识点操作：预览 / 编辑 / 重生成；被跳过者灰行 +［补生成］
- FR6.3 逐题审核默认开启；**红色置信度题目必须人工确认后方可导出**
- FR6.5 导出 zip
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from .models import (
    QUESTION_TYPES,
    CourseDraft,
    KnowledgePoint,
    Question,
)
from .state import generation_is_stale
from .validators import sort_questions, validate_question

# 置信度低于该值时视为「红色」，必须人工确认
RED_CONFIDENCE = 0.6
# 黄色区间下界
AMBER_CONFIDENCE = 0.8


# ---------------------------------------------------------------- 概览
@dataclass
class ReviewSummary:
    """Step6 汇总信息。"""

    point_count: int = 0
    question_count: int = 0
    reviewed: int = 0
    unreviewed: int = 0
    red: int = 0
    amber: int = 0
    green: int = 0
    skipped_points: list[str] = field(default_factory=list)
    invalid: list[str] = field(default_factory=list)

    @property
    def all_reviewed(self) -> bool:
        return self.unreviewed == 0

    def as_lines(self) -> list[str]:
        lines = [
            f"知识点 {self.point_count} 个 ｜ 题目 {self.question_count} 道",
            f"已审核 {self.reviewed} / {self.question_count}",
            f"置信度：绿 {self.green} ｜ 黄 {self.amber} ｜ 红 {self.red}",
        ]
        if self.skipped_points:
            lines.append(f"待补生成：{len(self.skipped_points)} 个知识点")
        if self.invalid:
            lines.append(f"待修正题目：{len(self.invalid)} 道")
        return lines


def assign_internal_ids(draft: CourseDraft) -> None:
    """
    为全部题目分配内部唯一 ID（形如 ``1-2-D-3``），并可安全重复调用。

    同一知识点内按题型（单→多→判）+ 原顺序重新编号，保证导出顺序稳定。
    """
    for point in draft.all_points:
        code_map = {"单选": "X", "多选": "D", "判断": "P"}
        ordered = sort_questions(point.questions)
        counters: dict[str, int] = {name: 0 for name in QUESTION_TYPES}
        for question in ordered:
            code = code_map.get(question.question_type, "X")
            counters[question.question_type] = counters.get(question.question_type, 0) + 1
            question.internal_id = (
                f"{point.chapter_order}-{point.order}-{code}-{counters[question.question_type]}"
            )
        point.questions = ordered


def review_summary(draft: CourseDraft) -> ReviewSummary:
    """统计 Step6 概览（含置信度色标分布与无效题定位）。"""
    summary = ReviewSummary()

    for point in draft.all_points:
        summary.point_count += 1
        if point.skipped:
            summary.skipped_points.append(point.name)

        for question in point.questions:
            summary.question_count += 1
            if question.reviewed:
                summary.reviewed += 1
            else:
                summary.unreviewed += 1

            color = question.confidence_color
            if color == "green":
                summary.green += 1
            elif color == "amber":
                summary.amber += 1
            else:
                summary.red += 1

            problems = validate_question(question)
            if problems:
                label = question.internal_id or point.name
                summary.invalid.append(f"{label}：{'；'.join(problems)}")

    return summary


def mark_reviewed(question: Question, reviewed: bool = True) -> Question:
    """标记单题已人工确认。"""
    question.reviewed = bool(reviewed)
    return question


def mark_point_reviewed(point: KnowledgePoint, reviewed: bool = True) -> int:
    """把整个知识点的题目标记为已审核，返回受影响题数。"""
    for question in point.questions:
        question.reviewed = bool(reviewed)
    return len(point.questions)


def replace_question(point: KnowledgePoint, index: int, question: Question) -> Question:
    """替换知识点内某一道题（编辑/重生成单个题目）。"""
    if 0 <= index < len(point.questions):
        keep_reviewed = point.questions[index].reviewed
        question.reviewed = keep_reviewed
        point.questions[index] = question
    else:
        point.questions.append(question)
    return question


def append_generated(
    point: KnowledgePoint,
    questions: Iterable[Question],
    *,
    replace: bool = False,
) -> int:
    """
    把新生成的题目并入知识点。

    Args:
        replace: True 时整体替换（重生成）；False 时追加（补生成）

    Returns:
        int: 合并后该知识点的题目总数
    """
    incoming = list(questions or [])
    if replace:
        point.questions = incoming
    else:
        if not point.questions:
            point.questions = incoming[:]
        else:
            # 追加时按题型配额补齐，避免同一题型超出配额
            existing_ratio = {
                name: sum(1 for q in point.questions if q.question_type == name)
                for name in QUESTION_TYPES
            }
            for question in incoming:
                if existing_ratio.get(question.question_type, 0) >= int(
                    point.type_counts.get(question.question_type, 0) or 0
                ):
                    continue
                point.questions.append(question)
                existing_ratio[question.question_type] = (
                    existing_ratio.get(question.question_type, 0) + 1
                )

    point.skipped = False
    return len(point.questions)


def export_blockers(draft: CourseDraft) -> list[str]:
    """
    导出阻断项（FR6.3 + FR6.9）。

    阻断条件：
    1. 题目校验不合规；
    2. **红色置信度题目未经人工确认**；
    3. 开启逐题审核时存在未审核题目；
    4. 没有任何可导出题目；
    5. 草稿在生成后被修改过（产物已不对应当前草稿），必须重新生成。
    """
    blockers: list[str] = []

    summary = review_summary(draft)

    if summary.question_count == 0:
        blockers.append("没有可导出的题目")

    if generation_is_stale(draft):
        blockers.append("草稿已修改，请回到第⑤步重新生成后再导出")

    blockers.extend(summary.invalid)

    serious = [
        question
        for question in _all_questions(draft)
        if question.confidence < RED_CONFIDENCE and not question.reviewed
    ]
    for question in serious:
        blockers.append(
            f"{question.internal_id or '未编号题目'}：置信度 {question.confidence:.2f}（红色）需人工确认"
        )

    if draft.review_mode == "逐题":
        unreviewed = [q for q in _all_questions(draft) if not q.reviewed]
        if unreviewed:
            blockers.append(f"仍有 {len(unreviewed)} 道题未逐题审核")

    return blockers


def _all_questions(draft: CourseDraft) -> list[Question]:
    return [
        question
        for point in draft.all_points
        if not point.skipped
        for question in point.questions
    ]


def ready_for_export(draft: CourseDraft) -> tuple[bool, list[str]]:
    """返回 (是否可导出, 阻断原因列表)。"""
    blockers = export_blockers(draft)
    return (not blockers), blockers


def points_for_export(draft: CourseDraft) -> list[KnowledgePoint]:
    """导出顺序：章节序 → 知识点序；跳过被标记为缺失的知识点。"""
    points = []
    for chapter in draft.chapters:
        for point in chapter.knowledge_points:
            if point.skipped or not point.questions:
                continue
            points.append(point)
    return points


def confidence_legend() -> list[tuple[str, str]]:
    """置信度色标图例：(颜色键, 说明)。"""
    return [
        ("green", "≥0.8 可直接采用"),
        ("amber", "0.6~0.8 建议复核"),
        ("red", "<0.6 必须人工确认"),
    ]


# ---------------------------------------------------------------- 生成运行
class GenerationRun:
    """
    一次生成的运行状态机（可供 UI 绑定：暂停 / 恢复 / 取消）。

    与 :class:`plugins.evaluation.generator.GenerationController` 的区别：
    本类只维护状态与允许跳过的知识点集合，不持有 AI 客户端；
    便于在没有真实 AI 的情况下单测 UI 控制流。
    """

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETE = "complete"

    def __init__(
        self,
        run_id: str,
        *,
        on_state_change: Callable[[str], None] | None = None,
    ) -> None:
        self.run_id = run_id
        self._state = self.IDLE
        self._lock = threading.Lock()
        self._on_state_change = on_state_change
        self._skipped_points: set[str] = set()
        self._skip_event = threading.Event()

    # ------------------------------------------------------------ 状态
    @property
    def state(self) -> str:
        return self._state

    @property
    def paused(self) -> bool:
        return self._state == self.PAUSED

    @property
    def cancelled(self) -> bool:
        return self._state == self.CANCELLED

    @property
    def completed(self) -> bool:
        return self._state == self.COMPLETE

    def _set_state(self, state: str) -> None:
        with self._lock:
            self._state = state
        if self._on_state_change is not None:
            self._on_state_change(state)

    def start(self) -> None:
        self._skip_event.set()
        self._set_state(self.RUNNING)

    def pause(self) -> None:
        if self.cancelled or self.completed:
            return
        self._skip_event.clear()
        self._set_state(self.PAUSED)

    def resume(self) -> None:
        if self.cancelled or self.completed:
            return
        self._skip_event.set()
        self._set_state(self.RUNNING)

    def cancel(self) -> None:
        self._skip_event.set()
        self._set_state(self.CANCELLED)

    def finish(self) -> None:
        if self.cancelled:
            return
        self._set_state(self.COMPLETE)

    # ------------------------------------------------------------ 跳过
    def skip_point(self, point_name: str) -> None:
        """标记该知识点为缺失（结果页灰行 +［补生成］）。"""
        self._skipped_points.add(str(point_name))

    def should_skip(self, point_name: str) -> bool:
        """局部暂停：仅跳过往被标记的知识点，其余继续。"""
        if self.cancelled:
            return True
        return str(point_name) in self._skipped_points

    def wait_if_paused(self, timeout: float = 0.2) -> bool:
        """
        暂停时阻塞等待（返回 False 表示已取消）。

        注意：取消会把 ``_skip_event`` 置位以唤醒等待者，因此循环退出后
        必须**重新检查** ``cancelled``，否则会把取消误判为「已恢复」。
        """
        while self.paused and not self.cancelled:
            self._skip_event.wait(timeout=timeout)
        return not self.cancelled

    def skipped_points(self) -> set[str]:
        return set(self._skipped_points)


def resolve_clarification_action(
    choice: str,
    *,
    point: KnowledgePoint | None = None,
) -> dict[str, Any]:
    """
    把教师的澄清选择翻译成动作指令（供 view / generator 统一使用）。

    Returns:
        dict: ``{"skip_question": bool, "skip_point": bool, "regenerate": bool, "choice": str}``
    """
    text = str(choice or "").strip()

    skip_point = "跳过该知识点" in text or "跳过知识点" in text
    regenerate = "重新生成" in text
    skip_question = (not skip_point) and (not regenerate) and "丢弃" in text

    return {
        "choice": text,
        "skip_question": skip_question,
        "skip_point": skip_point,
        "regenerate": regenerate,
    }


def build_clarification_choices(
    *,
    recommended: str,
    alternatives: Iterable[str],
) -> list[str]:
    """组装 2~4 个快捷选项，把推荐项放首位并去重（FR7.1）。"""
    ordered: list[str] = []
    for item in [recommended, *alternatives]:
        text = str(item or "").strip()
        if text and text not in ordered:
            ordered.append(text)
    return ordered[:4]
