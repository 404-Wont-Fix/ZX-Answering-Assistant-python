"""
澄清队列策略与留痕 - Clarification queue policy and durable records.

对应 PRD §5：

- 问题分级：``阻断`` / ``确认`` / ``自决``；
- 弹窗敏感度门控：宽松（仅阻断）/ 标准（阻断+确认，默认）/ 严格（全部）；
- 「☑ 本批次同类问题都按此处理」→ :meth:`ClarificationQueue.resolve_kind`；
- 关闭(×) = :meth:`ClarificationQueue.defer`（保持挂起）；
- 「跳过该知识点」= :meth:`ClarificationQueue.skip`（标记缺失，结果页可［补生成］）；
- 所有回答（含 AI 自决）都写入 ``draft.clarification_records`` 供［查看澄清记录］追溯。
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from .models import CLARIFICATION_LEVELS

# 敏感度 → 需要弹窗的级别（宽松只弹阻断；标准加确认；严格全弹）
SENSITIVITY_GATES: dict[str, tuple[str, ...]] = {
    "宽松": ("阻断",),
    "标准": ("阻断", "确认"),
    "严格": ("阻断", "确认", "自决"),
}

# 状态
STATUS_PENDING = "pending"
STATUS_ANSWERED = "answered"
STATUS_SKIPPED = "skipped"
STATUS_DEFERRED = "pending"  # 关闭(×) 后仍为挂起
STATUS_AUTO = "auto_decided"

AI_DECIDES = "由AI自行决定"
SKIP_POINT_CHOICE = "跳过该知识点"


@dataclass
class Clarification:
    """一条待澄清问题。"""

    # 问题分类键（用于「本批次同类问题都按此处理」的复用）
    kind: str
    level: str = "确认"
    chapter_name: str = ""
    point_name: str = ""
    question_no: str = ""
    question: str = ""
    # ［查看依据］折叠区展示的 AI 判断依据
    basis: str = ""
    # 2~4 个快捷选项；recommended 用选项文本标识推荐项
    options: list[str] = field(default_factory=list)
    recommended: str = ""
    # 回答结果
    choice: str = ""
    scope: str = ""
    status: str = STATUS_PENDING
    source: str = "dialog"  # dialog | auto | reuse
    timestamp: str = ""
    # 跨线程握手（worker 线程等待，Flet 事件循环线程 set）
    event: Any = field(default=None, repr=False, compare=False)
    # ``release()`` 已唤醒 worker。关闭(×) 也会置位，
    # 此时 ``status`` 仍为 pending（供［待澄清 n］重开），但 worker 必须停止等待。
    event_released: bool = field(default=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.level not in CLARIFICATION_LEVELS:
            self.level = "确认"
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def location(self) -> str:
        """关联定位（章节 / 知识点 / 题号）。"""
        parts = []
        if self.chapter_name:
            parts.append(f"章节：{self.chapter_name}")
        if self.point_name:
            parts.append(f"知识点：{self.point_name}")
        if self.question_no:
            parts.append(f"题号：{self.question_no}")
        return " ｜ ".join(parts)

    def wait(self, timeout: float | None = None) -> bool:
        """（worker 线程侧）阻塞等待 UI 线程给出回答。"""
        if self.event is None:
            return False
        return bool(self.event.wait(timeout))

    def release(self) -> None:
        """（UI 线程侧）唤醒等待中的 worker —— **必须在写回结果之后**调用。"""
        self.event_released = True
        if self.event is not None:
            self.event.set()

    def to_record(self) -> dict[str, Any]:
        """转成可落盘的澄清记录（问题/选择/影响范围/时间）。"""
        return {
            "kind": self.kind,
            "level": self.level,
            "question": self.question,
            "choice": self.choice,
            "scope": self.scope or self.location,
            "point_name": self.point_name,
            "chapter_name": self.chapter_name,
            "question_no": self.question_no,
            "status": self.status,
            "source": self.source,
            "timestamp": self.timestamp,
        }


class ClarificationQueue:
    """
    澄清队列：一次只弹一个，支持同类复用与跳过。

    Args:
        sensitivity: 弹窗敏感度（``宽松`` / ``标准`` / ``严格``）
        on_record: 每产生一条最终记录时的回调（用于写入草稿留痕）
        event_factory: 生成跨线程握手原语（默认 ``threading.Event``，便于测试注入）
    """

    def __init__(
        self,
        *,
        sensitivity: str = "标准",
        on_record: Callable[[dict[str, Any]], None] | None = None,
        event_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.sensitivity = sensitivity if sensitivity in SENSITIVITY_GATES else "标准"
        self._on_record = on_record
        self._event_factory = event_factory or threading.Event
        self._items: list[Clarification] = []
        self._resolved_kinds: dict[str, str] = {}
        self._skipped_points: set[tuple[int, int]] = set()
        self.records: list[dict[str, Any]] = []

    # ------------------------------------------------------------ 敏感度
    @property
    def gated_levels(self) -> tuple[str, ...]:
        return SENSITIVITY_GATES.get(self.sensitivity, SENSITIVITY_GATES["标准"])

    def should_ask(self, level: str) -> bool:
        """该级别在当前敏感度下是否需要弹窗。"""
        return level in self.gated_levels

    # ------------------------------------------------------------ 入队
    def add(self, clarification: Clarification) -> Clarification:
        """
        入队一条澄清。

        若同 ``kind`` 已被「本批次同类问题都按此处理」或「AI 自决」覆盖，
        则**不**入队，直接套用既有答案并记入留痕（``source="reuse"``）。
        若该级别在当前敏感度下无需弹窗，则由 AI 自行决定并留痕。
        """
        reused = self._resolved_kinds.get(clarification.kind)
        if reused is not None:
            clarification.choice = reused
            clarification.status = STATUS_AUTO
            clarification.source = "reuse"
            clarification.scope = f"同类问题批量复用（{clarification.kind}）"
            self.record(clarification)
            return clarification

        if not self.should_ask(clarification.level):
            clarification.choice = AI_DECIDES
            clarification.status = STATUS_AUTO
            clarification.source = "auto"
            clarification.scope = f"{clarification.level}级问题（敏感度：{self.sensitivity}）"
            self.record(clarification)
            return clarification

        if clarification.event is None:
            clarification.event = self._event_factory()
        self._items.append(clarification)
        return clarification

    # ------------------------------------------------------------ 查询
    def pending(self) -> list[Clarification]:
        """当前仍挂起（未回答/已关闭未答）的澄清，按题目顺序稳定返回。"""
        return [item for item in self._items if item.status == STATUS_PENDING]

    def current(self) -> Clarification | None:
        pending = self.pending()
        return pending[0] if pending else None

    def all_items(self) -> list[Clarification]:
        return list(self._items)

    @property
    def total(self) -> int:
        """本批次出现过的澄清总数（用于「澄清 n/m」）。"""
        return len(self._items)

    def resolved_count(self) -> int:
        return sum(1 for item in self._items if item.status != STATUS_PENDING)

    def counter_text(self) -> str:
        return f"澄清 {self.resolved_count()}/{self.total}"

    # ------------------------------------------------------------ 回答
    def answer(
        self,
        clarification: Clarification | None = None,
        choice: str = "",
        *,
        apply_to_kind: bool = False,
        keep_pending: bool = False,
        scope: str = "",
    ) -> Clarification | None:
        """
        回答一条澄清。

        Args:
            clarification: 目标澄清（None 时取队首）
            choice: 教师选择（快捷选项文本 / 自由输入 / :data:`AI_DECIDES`）
            apply_to_kind: 是否「本批次同类问题都按此处理」
            keep_pending: True 时保持挂起（对应关闭(×) 的 defer 语义）
            scope: 影响范围描述
        """
        item = clarification or self.current()
        if item is None:
            return None

        item.choice = (choice or "").strip() or AI_DECIDES
        item.source = "dialog"

        if keep_pending:
            return self.defer(item, scope=scope)

        item.status = STATUS_ANSWERED
        item.scope = scope or f"{item.point_name or ''}（单条）".strip("（）") or "单条"

        if apply_to_kind:
            self._resolved_kinds[item.kind] = item.choice
            item.scope = f"{item.scope}；本批次同类问题（{item.kind}）均按此处理"

        self.record(item)
        item.release()
        return item

    def resolve_kind(self, kind: str, choice: str) -> None:
        """登记「同类都按此处理」的答案（不需要挂起的调用方可直接用）。"""
        self._resolved_kinds[kind] = choice

    def defer(self, clarification: Clarification | None = None, *, scope: str = "") -> Clarification | None:
        """
        关闭(×)：暂时不回答，保持挂起（进度区显示［待澄清 n］）。

        关键：状态仍为 ``pending``（之后可从［待澄清 n］重开），但必须唤醒
        worker 让它**不再无限等待**，否则会死循环。
        """
        item = clarification or self.current()
        if item is None:
            return None

        item.status = STATUS_DEFERRED
        item.scope = scope or "暂不回答（保持挂起）"
        item.release()
        return item

    def skip(self, clarification: Clarification | None = None) -> Clarification | None:
        """
        「跳过该知识点」：该知识点标记缺失，结果页灰行 +［补生成］。
        """
        item = clarification or self.current()
        if item is None:
            return None

        item.choice = SKIP_POINT_CHOICE
        item.status = STATUS_SKIPPED
        item.source = "dialog"
        item.scope = f"跳过知识点：{item.point_name}"
        self.record(item)
        item.release()
        return item

    def mark_point_skipped(self, chapter_order: int, point_order: int) -> None:
        """记录被跳过的知识点（供 Step6 灰行展示）。"""
        self._skipped_points.add((int(chapter_order), int(point_order)))

    def skipped_points(self) -> set[tuple[int, int]]:
        return set(self._skipped_points)

    def is_point_skipped(self, chapter_order: int, point_order: int) -> bool:
        return (int(chapter_order), int(point_order)) in self._skipped_points

    # ------------------------------------------------------------ 留痕
    def record(self, clarification: Clarification) -> dict[str, Any]:
        """写入澄清记录（问题/选择/影响范围/时间）并回调落盘。"""
        entry = clarification.to_record()
        self.records.append(entry)
        if self._on_record is not None:
            self._on_record(entry)
        return entry

    def auto_record(
        self,
        *,
        kind: str,
        level: str,
        question: str,
        choice: str = AI_DECIDES,
        scope: str,
        chapter_name: str = "",
        point_name: str = "",
        question_no: str = "",
    ) -> dict[str, Any]:
        """直接留痕一条「AI 自决」记录（不弹窗）。"""
        item = Clarification(
            kind=kind,
            level=level,
            chapter_name=chapter_name,
            point_name=point_name,
            question_no=question_no,
            question=question,
            choice=choice,
            scope=scope,
            status=STATUS_AUTO,
            source="auto",
        )
        return self.record(item)

    # ------------------------------------------------------------ 批量兜底
    def release_all(self) -> None:
        """唤醒所有仍挂起的澄清（暂停/取消/cleanup 兜底，防线程泄漏）。"""
        for item in self._items:
            if item.status == STATUS_PENDING:
                item.release()

    def clear(self) -> None:
        self.release_all()
        self._items.clear()


def summarize_records(records: Iterable[dict[str, Any]]) -> dict[str, int]:
    """统计澄清记录：总数 / 各状态数（Step6 概览用）。"""
    summary = {"total": 0, STATUS_PENDING: 0, STATUS_ANSWERED: 0, STATUS_SKIPPED: 0, STATUS_AUTO: 0}
    for entry in records or []:
        summary["total"] += 1
        status = (entry or {}).get("status", STATUS_PENDING)
        if status in summary:
            summary[status] += 1
    return summary
