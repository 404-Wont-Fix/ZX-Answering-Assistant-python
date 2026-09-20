"""
出题编排 - Question generation orchestration.

职责边界：

- 只负责「按知识点逐个生成」的循环与暂停/恢复/取消语义；
- **不**直接操作 Flet（弹窗生命周期由 view 层在事件循环线程持有）；
- 需要澄清时，通过 ``on_clarification`` 回调把 :class:`Clarification` 交给 view，
  然后由 view 决定何时 :meth:`Clarification.release`。

关键需求：

- FR5.3 局部暂停：只有出问题的知识点被挂起，其余知识点继续生成；
- FR5.2 澄清为模态队列，一次一个；
- 取消后立刻停止新增请求。
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Iterable

from .ai_client import HttpMcpSearchClient, StructuredAIClient, should_search
from .clarification import STATUS_PENDING, Clarification, ClarificationQueue
from .models import (
    JUDGE_OPTIONS,
    MAX_OPTIONS,
    OPTION_LETTERS,
    QUESTION_TYPES,
    CourseDraft,
    KnowledgePoint,
    Question,
    allocate_with_floor,
)
from .prompts import build_generation_request
from .validators import validate_question


class GenerationCancelled(RuntimeError):
    """用户取消生成时抛出，用于跳出循环。"""


class GenerationController:
    """
    逐知识点生成控制器。

    Args:
        ai_client: 已配置的 :class:`StructuredAIClient`
        search_client: 可选的 :class:`HttpMcpSearchClient`（None 表示不联网）
        clarification_queue: 澄清队列（None 时自动创建）
        logger: 日志回调（进度区展示）
    """

    def __init__(
        self,
        ai_client: StructuredAIClient,
        search_client: HttpMcpSearchClient | None = None,
        clarification_queue: ClarificationQueue | None = None,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.ai_client = ai_client
        self.search_client = search_client
        self.queue = clarification_queue or ClarificationQueue()
        self._log = logger or (lambda message: None)

        self._pause_event = threading.Event()
        self._pause_event.set()  # set = 运行中
        self._cancel_event = threading.Event()
        self._lock = threading.Lock()
        self._index = 0
        self._total = 0
        self._current_point: str = ""
        # 标记「需重新生成该知识点」（教师在澄清中选择「重新生成」时置位）
        self.regenerate_requested: set[str] = set()
        # 标记「因关闭(×)而挂起」的知识点（题目已丢弃，待教师从［待澄清 n］重开）
        self.suspended_points: set[str] = set()

    # ------------------------------------------------------------ 状态
    @property
    def paused(self) -> bool:
        return not self._pause_event.is_set()

    @property
    def cancelled(self) -> bool:
        return self._cancel_event.is_set()

    @property
    def progress(self) -> tuple[int, int, str]:
        """(已完成, 总数, 当前知识点名)。"""
        return self._index, self._total, self._current_point

    # ------------------------------------------------------------ 控制
    def pause(self) -> None:
        """暂停：当前请求完成后不再开始下一个知识点。"""
        self._pause_event.clear()
        self._log("⏸ 已暂停，当前知识点完成后不再继续")

    def resume(self) -> None:
        self._pause_event.set()
        self._log("▶ 已恢复生成")

    def cancel(self) -> None:
        """取消：停止循环并唤醒所有挂起的澄清，避免线程泄漏。"""
        self._cancel_event.set()
        self._pause_event.set()
        self.queue.release_all()
        self._log("⛔ 已请求取消生成")

    def should_skip(self) -> bool:
        return self.cancelled

    def _checkpoint(self) -> None:
        """在每次请求前检查取消/暂停状态。"""
        if self.cancelled:
            raise GenerationCancelled("用户取消生成")

        if self.paused:
            self._log("⏸ 等待恢复...")
            while not self._pause_event.wait(timeout=0.2):
                if self.cancelled:
                    raise GenerationCancelled("用户取消生成")

    # ------------------------------------------------------------ 主循环
    def generate_point(
        self,
        point: KnowledgePoint,
        draft: CourseDraft,
        *,
        retries: int = 2,
        on_question: Callable[[Question], None] | None = None,
        on_clarification: Callable[[Clarification], None] | None = None,
        uncertainty: bool = False,
    ) -> list[Question]:
        """
        为单个知识点生成题目（不抛网络异常，失败时返回已生成的部分）。

        Args:
            point: 目标知识点
            draft: 课程草稿（提供课程名 / 联网开关 / 样例）
            retries: AI JSON 不合规时的重试次数
            on_question: 每产出一题回调（用于增量落盘 / UI 刷新）
            on_clarification: 需要澄清时的回调；返回后本方法会等待该澄清被释放
            uncertainty: AI 对该知识点是否不确定（决定是否联网检索）
        """
        active_types = point.active_types or allocate_with_floor(
            point.question_count, point.type_ratio
        )
        question_count = int(point.question_count or 0)
        if question_count <= 0 or not active_types:
            self._log(f"⚠ 知识点「{point.name}」未配置题型题数，已跳过")
            return []

        self._current_point = point.name
        self._checkpoint()

        web_context = ""
        if should_search(uncertainty, draft.online_search) and self.search_client:
            self._log(f"🔎 联网检索：{point.name}")
            web_context = self.search_client.search(
                f"{draft.course_name} {point.chapter_name} {point.name}"
            )
            if not web_context:
                self.queue.auto_record(
                    kind="search_unavailable",
                    level="自决",
                    question="联网检索不可用，已降级为模型自有知识出题",
                    scope=point.name,
                    chapter_name=point.chapter_name,
                    point_name=point.name,
                )

        request = build_generation_request(
            course_name=draft.course_name,
            knowledge_point=point.name,
            tags=point.effective_tags,
            question_count=question_count,
            type_counts=active_types,
            difficulty_ratio=point.difficulty_ratio,
            web_context=web_context,
            knowledge_context=self._knowledge_context(point),
        )

        try:
            payload = self.ai_client.generate(request, retries=retries)
        except Exception as exc:  # noqa: BLE001 - 单点失败不应中断整批
            self._log(f"✖ 知识点「{point.name}」生成失败：{exc}")
            self.queue.auto_record(
                kind="generation_failed",
                level="自决",
                question=f"知识点「{point.name}」生成失败：{exc}",
                scope=point.name,
                chapter_name=point.chapter_name,
                point_name=point.name,
            )
            return []

        questions = self._normalize_payload(
            payload, point, active_types, draft, on_clarification=on_clarification
        )

        for question in questions:
            if on_question is not None:
                on_question(question)

        return questions

    def run(
        self,
        draft: CourseDraft,
        *,
        on_point_start: Callable[[KnowledgePoint], None] | None = None,
        on_point_done: Callable[[KnowledgePoint, list[Question]], None] | None = None,
        on_question: Callable[[Question], None] | None = None,
        on_clarification: Callable[[Clarification], None] | None = None,
        uncertainty_points: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        """
        遍历所有知识点生成题目。

        Returns:
            dict: ``{"completed": n, "skipped": [...], "cancelled": bool}``
        """
        points = [point for point in draft.all_points if not point.skipped]
        uncertain = {str(name) for name in (uncertainty_points or [])}

        self._total = len(points)
        self._index = 0
        skipped: list[str] = []

        for point in points:
            if self.cancelled:
                break

            try:
                self._checkpoint()
            except GenerationCancelled:
                break

            if on_point_start is not None:
                on_point_start(point)

            try:
                questions = self.generate_point(
                    point,
                    draft,
                    on_question=on_question,
                    on_clarification=on_clarification,
                    uncertainty=point.name in uncertain,
                )
            except GenerationCancelled:
                break

            if questions:
                point.questions = questions
            else:
                skipped.append(point.name)

            self._index += 1
            if on_point_done is not None:
                on_point_done(point, questions)

        return {
            "completed": self._index,
            "skipped": skipped,
            "cancelled": self.cancelled,
            "regenerate": sorted(self.regenerate_requested),
            "suspended": sorted(self.suspended_points),
        }

    # ------------------------------------------------------------ 内部
    @staticmethod
    def _knowledge_context(point: KnowledgePoint) -> str:
        """出题依据优先级：教师考点清单 ＞ 考纲/大纲 ＞ AI 通用知识。"""
        lines = []
        tags = point.effective_tags
        if tags:
            lines.append("考点：" + "、".join(tags))
        if point.special_requirements:
            lines.append("特殊要求：" + point.special_requirements)
        lines.append(f"知识点：{point.name}（{point.chapter_name}）")
        lines.append(f"知识点等级：{point.level}；知识点类型：{point.knowledge_type}")
        return "\n".join(lines)

    def _normalize_payload(
        self,
        payload: dict[str, Any],
        point: KnowledgePoint,
        active_types: dict[str, int],
        draft: CourseDraft,
        *,
        on_clarification: Callable[[Clarification], None] | None,
    ) -> list[Question]:
        """把 AI 原始 JSON 规整成合规的 :class:`Question` 列表。"""
        raw_questions = [
            item for item in (payload.get("questions") or []) if isinstance(item, dict)
        ]

        questions: list[Question] = []

        for raw in raw_questions:
            question = self._build_question(raw, point, questions)
            problems = validate_question(question)

            if problems:
                self._log(f"⚠ 「{point.name}」第 {len(questions) + 1} 题不合规：{'；'.join(problems)}")
                clarification = Clarification(
                    kind="invalid_question",
                    level="确认",
                    chapter_name=point.chapter_name,
                    point_name=point.name,
                    question_no=question.internal_id or f"{point.chapter_order}-{point.order}-?",
                    question=(
                        f"AI 生成的题目不合规：{'；'.join(problems)}。"
                        "该题如何处理？"
                    ),
                    basis=f"原始题目：{raw.get('stem', '')}\n答案：{raw.get('answer', '')}",
                    options=["保留（导出前修正）", "丢弃该题", "重新生成该知识点"],
                    recommended="保留（导出前修正）",
                )
                choice = self._resolve_clarification(on_clarification, clarification)

                if clarification.status == STATUS_PENDING:
                    # 关闭(×)：暂不回答 → 丢弃该题，本知识点留待教师稍后处理
                    self.suspended_points.add(point.name)
                    continue
                if "丢弃" in choice:
                    continue
                if "重新生成" in choice:
                    self.regenerate_requested.add(point.name)
                    continue
                if self.cancelled:
                    # 取消时不再把未确认的题目并入结果（保持部分产出干净）
                    break

            questions.append(question)

        return questions

    def _build_question(
        self,
        raw: dict[str, Any],
        point: KnowledgePoint,
        existing: list[Question],
    ) -> Question:
        """
        从 AI 原始项构造 Question。

        容错策略（实测：即使提示词写了字段契约，模型仍会自创别名，
        deepseek-v4-flash 曾把题干放在 ``question``）：

        - 字段名走 :func:`plugins.evaluation.ai_client.pick_field` 的别名表，
          命中非标准名时**记日志告警**，避免静默丢题干；
        - 判断题选项强制平台标准（FR6.8）；
        - 答案只做大小写/去重/升序归一，**绝不自行补足或截断字母**
          （那会改变正确答案，异常交给 validate_question + 澄清弹窗）。
        """
        from .ai_client import pick_field

        stem_value, stem_key = pick_field(raw, "stem")
        if stem_key and stem_key != "stem":
            self._log(
                f"⚠ AI 用非标准字段名 {stem_key!r} 作题干，已兼容"
                f"（建议核对提示词/模型）"
            )

        type_value, _ = pick_field(raw, "type", "单选")
        question_type = str(type_value or "单选").strip()
        if question_type not in QUESTION_TYPES:
            question_type = "单选"

        difficulty_value, _ = pick_field(raw, "difficulty", "一般")
        options_value, _ = pick_field(raw, "options", [])
        answer_value, _ = pick_field(raw, "answer", "")
        confidence_value, _ = pick_field(raw, "confidence", 1.0)
        rationale_value, _ = pick_field(raw, "rationale", "")

        if isinstance(options_value, str):
            options_value = [p for p in options_value.splitlines() if p.strip()]
        if isinstance(answer_value, (list, tuple)):
            answer_value = "".join(str(item) for item in answer_value)

        options = [str(item) for item in (options_value or [])][:MAX_OPTIONS]
        answer = str(answer_value or "").strip().upper()

        if question_type == "判断":
            # FR6.8：判断题选项平台固定为 A.正确 / B.错误
            options = list(JUDGE_OPTIONS)
        else:
            # 去掉空白选项，保持字母顺序紧凑
            options = [item for item in options if item.strip()]

        letters = sorted({ch for ch in answer if ch in OPTION_LETTERS})
        answer = "".join(letters) if letters else answer

        try:
            confidence = float(confidence_value)
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = min(max(confidence, 0.0), 1.0)

        index = len(existing) + 1
        code = {"单选": "X", "多选": "D", "判断": "P"}.get(question_type, "X")

        return Question(
            stem=str(stem_value or "").strip(),
            question_type=question_type,
            difficulty=str(difficulty_value or "一般").strip(),
            options=options,
            answer=answer,
            confidence=confidence,
            rationale=str(rationale_value or "").strip(),
            internal_id=f"{point.chapter_order}-{point.order}-{code}-{index}",
        )

    def _resolve_clarification(
        self,
        on_clarification: Callable[[Clarification], None] | None,
        clarification: Clarification,
    ) -> str:
        """
        把澄清交给 view 并**阻塞等待**教师的回答。

        流程（与 §H-1 约定一致）：

        1. ``queue.add()`` —— 可能因敏感度门控/同类复用而直接自决（无需等待）；
        2. 仍需弹窗时，调 ``on_clarification`` 让 view 在 Flet 事件循环线程上
           调度弹窗（view 内部只 `page.run_task`，不阻塞）；
        3. 本（worker）线程循环 ``wait(timeout)``，同时检查取消，避免死等；
        4. 返回教师的选择（或 ``由AI自行决定``）。
        """
        queued = self.queue.add(clarification)
        if queued.status != STATUS_PENDING:
            return queued.choice

        if on_clarification is not None:
            on_clarification(queued)

        # 等待 UI 写回结果；关闭(×)（defer）会置 event_released 但状态仍为 pending，
        # 此时必须退出等待，否则会死循环。
        while queued.status == STATUS_PENDING and not queued.event_released:
            if self.cancelled:
                self.queue.defer(queued, scope="生成已取消")
                break
            queued.wait(timeout=0.2)

        return queued.choice

    def _ask(
        self,
        on_clarification: Callable[[Clarification], None] | None,
        clarification: Clarification,
    ) -> str:
        """向后兼容的别名（不阻塞版语义已废弃，统一走 _resolve_clarification）。"""
        return self._resolve_clarification(on_clarification, clarification)


def sleep_briefly(seconds: float = 0.05) -> None:
    """便于测试/限速的小工具（保持模块内无裸 ``time.sleep`` 调用点集中）。"""
    time.sleep(max(seconds, 0.0))
