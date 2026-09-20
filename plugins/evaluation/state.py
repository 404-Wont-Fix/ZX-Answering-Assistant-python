"""
草稿持久化与向导校验 - Draft persistence and wizard validation.

- :class:`DraftStore`：把向导草稿落到 ``output/evaluation/draft.json``，
  带**脏标记 + 防抖**（生成过程中逐题落盘会显著拖慢速度）与**原子写**。
- :class:`WizardValidator`：把 PRD §7「步骤校验汇总」实现为可单测的纯函数。
- :func:`apply_global_defaults` / :func:`apply_global_details`：Step3 / Step4 的
  「应用到全部」语义。
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Iterable

from .models import (
    DEFAULT_DIFFICULTY_RATIO,
    DEFAULT_QUESTION_COUNT,
    DEFAULT_TYPE_RATIO,
    DIFFICULTIES,
    QUESTION_TYPES,
    CourseDraft,
    KnowledgePoint,
    allocate_with_floor,
)

DRAFT_RELATIVE_PATH = Path("output") / "evaluation" / "draft.json"

# 校验用：
#   - 最小步骤号 / 最大步骤号
MIN_STEP = 1
MAX_STEP = 6


class DraftStore:
    """
    向导草稿的落盘与恢复。

    写盘策略：

    - :meth:`mark_dirty` 只置脏标记，**不**落盘；
    - :meth:`flush_if_due` 满足「距上次落盘 ≥ ``min_interval`` 秒」**或**
      「累计变更 ≥ ``every_n_writes`` 次」才真正写；
    - :meth:`flush` 默认强制写（``force=True``），供步骤切换、生成完成/取消/暂停、
      导出前、``view.cleanup()`` 调用。
    """

    def __init__(
        self,
        project_root: str | Path,
        *,
        min_interval: float = 2.0,
        every_n_writes: int = 5,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self.project_root = Path(project_root)
        self.path = self.project_root / DRAFT_RELATIVE_PATH
        self.min_interval = float(min_interval)
        self.every_n_writes = max(int(every_n_writes), 1)
        self._time_fn = time_fn

        self._dirty = False
        self._pending_writes = 0
        self._last_flush = 0.0
        self.flush_count = 0

    # ------------------------------------------------------------ 读
    def load(self) -> CourseDraft:
        """恢复草稿；文件缺失/损坏时返回全新草稿（不抛异常）。"""
        if not self.path.is_file():
            return CourseDraft()

        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[Evaluation] 草稿读取失败，已忽略: {exc}")
            return CourseDraft()

        if not isinstance(payload, dict):
            return CourseDraft()

        draft = CourseDraft.from_dict(payload)
        self._last_flush = self._time_fn()
        return draft

    # ------------------------------------------------------------ 写
    def mark_dirty(self) -> None:
        """标记草稿已变更（不落盘）。"""
        self._dirty = True
        self._pending_writes += 1

    @property
    def dirty(self) -> bool:
        return self._dirty

    def flush_if_due(self, draft: CourseDraft) -> bool:
        """
        按防抖策略决定是否落盘。

        Returns:
            bool: 本次是否真的写盘
        """
        if not self._dirty:
            return False

        due_by_count = self._pending_writes >= self.every_n_writes
        due_by_time = (self._time_fn() - self._last_flush) >= self.min_interval
        if not (due_by_count or due_by_time):
            return False

        return self.flush(draft, force=True)

    def flush(self, draft: CourseDraft, *, force: bool = False) -> bool:
        """
        落盘草稿。

        Args:
            draft: 待写入的草稿
            force: True 时忽略脏标记与防抖直接落盘

        Returns:
            bool: 是否写入成功
        """
        if not force and not self._dirty:
            return False

        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(draft.to_dict(), ensure_ascii=False, indent=2)
            tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp_path.write_text(payload, encoding="utf-8")
            os.replace(tmp_path, self.path)
        except OSError as exc:
            print(f"[Evaluation] 草稿落盘失败: {exc}")
            return False

        self._dirty = False
        self._pending_writes = 0
        self._last_flush = self._time_fn()
        self.flush_count += 1
        return True

    def clear(self) -> None:
        """丢弃磁盘上的草稿与内存脏状态。"""
        self._dirty = False
        self._pending_writes = 0
        try:
            self.path.unlink(missing_ok=True)
        except OSError as exc:
            print(f"[Evaluation] 草稿清理失败: {exc}")


class WizardValidator:
    """
    PRD §7 逐步校验。

    ``validate_step(draft, step)`` 返回错误文案列表（空列表 = 通过）。
    """

    def validate_step(self, draft: CourseDraft, step: int) -> list[str]:
        step = int(step or 0)
        if step <= MIN_STEP:
            return self._step_one(draft)
        if step == 2:
            return self._step_two(draft)
        if step == 3:
            return []
        if step == 4:
            return self._step_four(draft)
        if step == 5:
            return self._step_five(draft)
        return self._step_six(draft)

    # ------------------------------------------------------------ 各步
    @staticmethod
    def _step_one(draft: CourseDraft) -> list[str]:
        errors: list[str] = []
        if not (draft.course_name or "").strip():
            errors.append("课程名称不能为空")
        return errors

    @staticmethod
    def _step_two(draft: CourseDraft) -> list[str]:
        errors: list[str] = []
        if not draft.chapters:
            errors.append("至少创建一个章节")
            return errors

        for chapter in draft.chapters:
            if not chapter.knowledge_points:
                errors.append(f"章节“{chapter.name or '未命名'}”至少需要一个知识点")
        return errors

    @staticmethod
    def _step_four(draft: CourseDraft) -> list[str]:
        errors: list[str] = []
        for point in draft.all_points:
            label = point.name or "未命名"
            active = point.active_types

            if not active:
                errors.append(f"知识点“{label}”至少勾选一个题型")
                continue

            # FR4.5：勾选题型比例合计必须为 100%
            if point.selected_ratio_total != 100:
                errors.append(f"知识点“{label}”题型比例必须合计100%")

            # FR4.5：勾选题型各至少 1 题
            if point.question_count < len(point.selected_types):
                errors.append(f"知识点“{label}”题数不足以覆盖已选题型")
            elif any(
                int(point.type_counts.get(name, 0) or 0) < 1
                for name in point.selected_types
            ):
                errors.append(f"知识点“{label}”题数不足以覆盖已选题型")

            # FR4.3：各题型题数合计必须等于总题数
            if point.active_type_total != point.question_count:
                errors.append(f"知识点“{label}”题型题数合计必须等于总题数")

            # 难度配比必须合计 100%
            difficulty_total = sum(
                max(int(point.difficulty_ratio.get(name, 0) or 0), 0)
                for name in DEFAULT_DIFFICULTY_RATIO
            )
            if difficulty_total != 100:
                errors.append(f"知识点“{label}”难度比例必须合计100%")

        return errors

    @staticmethod
    def _step_five(draft: CourseDraft) -> list[str]:
        errors: list[str] = []
        if draft.generation_status != "complete":
            errors.append("生成尚未完成")
        elif generation_is_stale(draft):
            # 改动过课程/章节/知识点/题量题型后，上一轮产物已不对应当前草稿
            errors.append("草稿已修改，请重新生成")
        pending = pending_clarifications(draft)
        if pending:
            errors.append(f"仍有 {len(pending)} 项待澄清")
        return errors

    @staticmethod
    def _step_six(draft: CourseDraft) -> list[str]:
        errors: list[str] = []
        if not draft.all_points:
            errors.append("至少勾选1个知识点")
        elif not any(not point.skipped for point in draft.all_points):
            errors.append("至少勾选1个知识点")
        return errors


def pending_clarifications(draft: CourseDraft) -> list[dict[str, Any]]:
    """返回草稿中状态仍为 ``pending`` 的澄清记录。"""
    return [
        record
        for record in (draft.clarification_records or [])
        if (record or {}).get("status") == "pending"
    ]


def generation_fingerprint(draft: CourseDraft) -> str:
    """生成输入指纹：只包含**影响出题结果**的字段。

    用途：判断已完成的生成是否仍然对应当前草稿。教师的任何修改
    （课程信息、知识点、考点、题量题型、难度配比、联网开关）都会改变
    指纹，从而触发「需重新生成」。不包含生成产物、审核状态等输出字段。

    Returns:
        str: 16 进制指纹（空草稿也返回稳定值）
    """
    payload = {
        "course_name": (draft.course_name or "").strip(),
        "target": (draft.target or "").strip(),
        "tool_version": (draft.tool_version or "").strip(),
        "online_search": bool(draft.online_search),
        "sensitivity": draft.sensitivity,
        "points": [
            {
                "chapter_order": point.chapter_order,
                "chapter_name": point.chapter_name,
                "order": point.order,
                "name": point.name,
                "level": point.level,
                "knowledge_type": point.knowledge_type,
                "tags": list(point.tags),
                "inferred_tags": list(point.inferred_tags),
                "special_requirements": point.special_requirements,
                "question_count": int(point.question_count or 0),
                "type_counts": {
                    name: int(point.type_counts.get(name, 0) or 0)
                    for name in QUESTION_TYPES
                },
                "difficulty_ratio": {
                    name: int(point.difficulty_ratio.get(name, 0) or 0)
                    for name in DIFFICULTIES
                },
                "skipped": bool(point.skipped),
            }
            for point in draft.all_points
        ],
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


def generation_is_stale(draft: CourseDraft) -> bool:
    """生成结果为「完成」但已不对应当前草稿（需要重新生成）。

    旧版本草稿没有指纹（空串）时视为**非** stale，避免升级后立刻
    把所有历史草稿标成需重生成。
    """
    if draft.generation_status != "complete":
        return False
    if not draft.generation_fingerprint:
        return False
    return draft.generation_fingerprint != generation_fingerprint(draft)


def apply_global_defaults(
    draft: CourseDraft,
    *,
    question_count: int = DEFAULT_QUESTION_COUNT,
    type_ratio: dict[str, int] | None = None,
    difficulty_ratio: dict[str, int] | None = None,
    targets: Iterable[KnowledgePoint] | None = None,
) -> int:
    """
    Step4 的「应用到全部知识点」：把全局默认题量/题型比例/难度配比写进目标知识点。

    题型比例按**最大余数法**换算成各题型题数，保证合计等于总题数（FR4.3）。

    Returns:
        int: 实际被更新的知识点数量
    """
    ratio = dict(type_ratio or DEFAULT_TYPE_RATIO)
    diff_ratio = dict(difficulty_ratio or DEFAULT_DIFFICULTY_RATIO)
    count = max(int(question_count or 0), 0)

    affected = 0
    for point in list(targets if targets is not None else draft.all_points):
        point.question_count = count
        point.type_ratio = {
            name: max(int(ratio.get(name, 0) or 0), 0) for name in QUESTION_TYPES
        }
        point.type_counts = allocate_with_floor(count, point.type_ratio)
        point.difficulty_ratio = dict(diff_ratio)
        point.overridden = False
        affected += 1

    return affected


def apply_global_details(
    draft: CourseDraft,
    *,
    level: str | None = None,
    knowledge_type: str | None = None,
    tags: Iterable[str] | None = None,
    special_requirements: str | None = None,
    only_unfilled: bool = True,
    targets: Iterable[KnowledgePoint] | None = None,
) -> int:
    """
    Step3 的「应用到全部未填写知识点」（FR3.5）。

    ``only_unfilled=True`` 时只覆盖**考点清单为空**的知识点；
    等级/类型/特殊要求则按传入值覆盖（传 None 表示不动该字段）。

    Returns:
        int: 实际被更新的知识点数量
    """
    tag_list = list(tags) if tags is not None else None

    affected = 0
    for point in list(targets if targets is not None else draft.all_points):
        if level is not None:
            point.level = level
        if knowledge_type is not None:
            point.knowledge_type = knowledge_type
        if special_requirements is not None:
            point.special_requirements = special_requirements

        if tag_list is not None and (not only_unfilled or not point.tags):
            point.tags = list(tag_list)

        affected += 1

    return affected
