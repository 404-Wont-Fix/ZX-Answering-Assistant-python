"""``plugins/evaluation/view.py`` 与通用插件设置组件的单元测试。

用 FakePage 模拟 Flet Page（``run_task`` 入队由测试主线程执行、``run_thread``
启动真实线程），从而在没有 Flet 运行时的情况下验证：

- 六步向导的构建与「下一步」门控（PRD §7）；
- 澄清弹窗跨线程握手：worker 阻塞 → 事件循环线程弹窗 → 回答后唤醒；
- 关闭(×) = defer 不阻塞、不悬挂线程（§H-1 回归）；
- 生成完成后自动进入第⑥步（FR5.4）；
- manifest ``settings_schema`` 驱动的通用设置弹窗（保存 / 必填校验）。
"""

import asyncio
import dataclasses
import json
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
PLUGINS_DIR = ROOT / "plugins"
for candidate in (str(PLUGINS_DIR), str(ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from evaluation.ai_client import StructuredAIClient
from evaluation.clarification import STATUS_PENDING
from evaluation.models import Chapter, CourseDraft, KnowledgePoint, Question
from evaluation.review import mark_reviewed, ready_for_export
from evaluation.state import WizardValidator, generation_is_stale
from evaluation.view import (
    _FRAME_CHROME_HEIGHT as FRAME_CHROME_HEIGHT,
    _LOG_PANEL_HEIGHT as LOG_PANEL_HEIGHT,
    EvaluationView,
)
from src.core.plugin_settings import setting_value, validate_settings
from src.ui.components import build_plugin_settings_dialog
from src.ui.theme import Palette


class FakeDialog(ft.AlertDialog):
    """仅用于类型断言的占位（不参与渲染）。"""


def _iter_controls(node, seen=None):
    """递归产出控件树里的所有 Flet 控件（跳过重复引用）。"""
    if seen is None:
        seen = set()
    if id(node) in seen:
        return
    seen.add(id(node))

    if isinstance(node, ft.Control):
        yield node

    if dataclasses.is_dataclass(node) and not isinstance(node, type):
        for field in dataclasses.fields(node):
            if "skip" in field.metadata:
                continue
            yield from _iter_controls(getattr(node, field.name, None), seen)
    elif isinstance(node, dict):
        for value in node.values():
            yield from _iter_controls(value, seen)
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from _iter_controls(value, seen)


class FakePage:
    """模拟 ft.Page：run_task 入队、run_thread 起真线程。"""

    def __init__(self):
        self.update_count = 0
        self.dialogs: list = []
        self.tasks: list = []
        self.threads: list = []
        self._snack = None

    # --- Page API -----------------------------------------------------
    def update(self):
        self.update_count += 1

    def run_task(self, handler, *args, **kwargs):
        self.tasks.append((handler, args, kwargs))

    def run_thread(self, handler, *args, **kwargs):
        thread = threading.Thread(target=handler, args=args, kwargs=kwargs, daemon=True)
        self.threads.append(thread)
        thread.start()

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        if self.dialogs:
            self.dialogs.pop()

    @property
    def snack_bar(self):
        return self._snack

    @snack_bar.setter
    def snack_bar(self, value):
        self._snack = value

    # --- 测试辅助 -----------------------------------------------------
    def run_one_task(self) -> bool:
        """在「事件循环线程」上执行一个排队的任务。"""
        if not self.tasks:
            return False
        handler, args, kwargs = self.tasks.pop(0)
        result = handler(*args, **kwargs)
        if hasattr(result, "__await__"):
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(result)
            finally:
                loop.close()
        return True

    def pending_task_names(self) -> list:
        return [getattr(handler, "__name__", "?") for handler, _, _ in self.tasks]

    def worker_alive(self) -> bool:
        return any(thread.is_alive() for thread in self.threads)

    def wait_for_task(self, name: str, timeout: float = 10.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if name in self.pending_task_names():
                return True
            if not self.worker_alive():
                return False
            time.sleep(0.02)
        return False

    def wait_workers(self, timeout: float = 20.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline and self.worker_alive():
            self.run_one_task()
            time.sleep(0.02)
        return not self.worker_alive()


class _StubResponse:
    def __init__(self, payload):
        self._payload = payload
        self.headers = {"Content-Type": "application/json"}

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload

    def iter_lines(self, decode_unicode=False):
        return iter([])


class _StubSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls: list = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _StubResponse(self.responses.pop(0))


def _questions_payload(questions: list) -> dict:
    return {"choices": [{"message": {"content": json.dumps({"questions": questions})}}]}


def valid_question(stem: str = "题一（）") -> dict:
    return {
        "stem": stem,
        "type": "单选",
        "difficulty": "简单",
        "options": ["a", "b", "c", "d"],
        "answer": "A",
        "confidence": 0.9,
        "rationale": "r",
    }


def invalid_question() -> dict:
    return {
        "stem": "坏题",
        "type": "多选",
        "difficulty": "简单",
        "options": ["a", "b"],
        "answer": "A",
        "confidence": 0.5,
        "rationale": "r",
    }


class WizardBaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.page = FakePage()
        self.view = EvaluationView(self.page, project_root=self.tmp)

    def tearDown(self):
        try:
            self.view.cleanup()
        finally:
            shutil.rmtree(self.tmp, ignore_errors=True)

    # ------------------------------------------------------------------
    def fill_through_step_two(self) -> None:
        self.view._set_field("course_name", "CorelDraw")
        self.view._set_field("target", "24级大数据")
        self.view._set_field("tool_version", "CorelDraw X4")
        self.view._next(None)
        self.view._commit_chapter("界面介绍")
        self.view._add_points(["窗口结构", "工具栏"])
        self.view._next(None)

    def stub_ai(self, responses: list) -> _StubSession:
        session = _StubSession(responses)
        self.view._build_clients = lambda: (
            StructuredAIClient(
                {"api_key": "k", "base_url": "https://example.invalid/v1", "model": "m"},
                session=session,
                logger=self.view._log,
            ),
            None,
        )
        return session


class ViewConstructionTests(WizardBaseTests):
    def test_content_builds_and_starts_at_step_one(self):
        content = self.view.get_content()
        self.assertIsInstance(content, ft.Column)
        # 打开插件先显示欢迎页
        self.assertIsNotNone(self.view._current_content)
        self.assertIsInstance(
            self.view._current_content.content, ft.Column
        )

        # 点击“开始使用”后进入向导
        self.view._on_start_click()
        self.assertEqual(len(self.view._step_bar.controls), 6)
        self.assertEqual(self.view.draft.current_step, 1)

    def test_wizard_has_no_duplicate_page_title(self):
        """主界面框架顶部已有插件标题，向导页内不得重复（否则挤占内容空间）。"""
        self.view.get_content()
        self.view._on_start_click()

        controls = list(_iter_controls(self.view._root))
        labels = [
            control.value
            for control in controls
            if isinstance(control, ft.Text) and isinstance(control.value, str)
        ]
        self.assertNotIn(
            "评估出题助手",
            labels,
            "向导页不应再重复渲染插件标题",
        )
        self.assertNotIn("按平台模板生成课程评估题（单选/多选/判断）并导出 Word/Excel", labels)

        # 向导内容仍完整：6 个步骤卡片 + 第一步正文
        self.assertEqual(len(self.view._step_bar.controls), 6)
        self.assertTrue(self.view._body.controls)

    def test_welcome_page_shows_even_with_existing_draft(self):
        """回归：草稿已存在（course_name 非空）时，欢迎页仍然必须显示。"""
        import tempfile as _tempfile

        isolated = Path(_tempfile.mkdtemp())
        try:
            seed = EvaluationView(FakePage(), project_root=isolated)
            seed._set_field("course_name", "已存在的课程")
            seed._save_now()
            seed.cleanup()

            other_page = FakePage()
            other = EvaluationView(other_page, project_root=isolated)
            try:
                self.assertEqual(other.draft.course_name, "已存在的课程")
                content = other.get_content()
                self.assertIsInstance(content, ft.Column)
                # 仍然先展示欢迎页（AnimatedSwitcher 尚未切到向导）
                self.assertIsNotNone(other._current_content)
                labels = [
                    c.content
                    for c in _iter_controls(other._current_content)
                    if isinstance(c, ft.FilledButton)
                ]
                self.assertIn("开始使用", labels)

                # 开始后才渲染向导
                other._on_start_click()
                self.assertEqual(len(other._step_bar.controls), 6)
            finally:
                other.cleanup()
        finally:
            shutil.rmtree(isolated, ignore_errors=True)

    def test_fresh_draft_is_loaded_from_disk(self):
        self.view._set_field("course_name", "CorelDraw")
        self.view._save_now()

        other = EvaluationView(FakePage(), project_root=self.tmp)
        try:
            other.get_content()
            self.assertEqual(other.draft.course_name, "CorelDraw")
        finally:
            other.cleanup()

    def test_cleanup_cancels_and_flushes(self):
        self.view.cleanup()
        self.assertTrue(
            (self.tmp / "output" / "evaluation" / "draft.json").is_file()
        )
        self.assertFalse(self.page.worker_alive())


class StepGatingTests(WizardBaseTests):
    """PRD §7 步骤校验汇总。"""

    def test_step_one_requires_course_name(self):
        self.view._next(None)
        self.assertEqual(self.view.draft.current_step, 1)
        self.assertEqual(self.view.message, "课程名称不能为空")

        self.view._set_field("course_name", "CorelDraw")
        self.view._next(None)
        self.assertEqual(self.view.draft.current_step, 2)

    def test_step_two_requires_chapter_and_points(self):
        self.view._set_field("course_name", "CorelDraw")
        self.view._next(None)

        self.view._next(None)
        self.assertEqual(self.view.draft.current_step, 2)
        self.assertEqual(self.view.message, "至少创建一个章节")

        self.view._commit_chapter("界面介绍")
        self.view._next(None)
        self.assertEqual(self.view.draft.current_step, 2)
        self.assertIn("至少需要一个知识点", self.view.message)

        self.view._add_points(["窗口结构"])
        self.view._next(None)
        self.assertEqual(self.view.draft.current_step, 3)

    def test_step_three_passes_with_defaults(self):
        self.fill_through_step_two()
        self.view._next(None)
        self.assertEqual(self.view.draft.current_step, 4)

    def test_step_four_blocks_when_questions_too_few(self):
        self.fill_through_step_two()
        self.view._next(None)
        point = self.view.draft.all_points[0]
        point.set_type_ratio({"单选": 34, "多选": 33, "判断": 33}, question_count=2)

        self.view._next(None)
        self.assertEqual(self.view.draft.current_step, 4)
        self.assertIn("题数不足以覆盖已选题型", self.view.message)

    def test_step_four_advances_and_infers_tags(self):
        self.fill_through_step_two()
        self.view._next(None)
        self.view._next(None)
        self.assertEqual(self.view.draft.current_step, 5)
        for point in self.view.draft.all_points:
            self.assertEqual(
                point.inferred_tags, ["CorelDraw", "界面介绍", point.name]
            )

    def test_back_navigation_and_jump(self):
        self.fill_through_step_two()
        self.assertEqual(self.view.draft.current_step, 3)
        self.view._previous(None)
        self.assertEqual(self.view.draft.current_step, 2)
        self.view._jump(1)
        self.assertEqual(self.view.draft.current_step, 1)


class StepContentTests(WizardBaseTests):
    def test_step_two_shows_placeholder_without_chapter(self):
        self.view._go(2)
        controls = self.view._body.controls
        self.assertTrue(controls)

    def test_step_three_applies_global_details_to_unfilled_points(self):
        self.fill_through_step_two()
        self.view._go(3)
        self.view.global_details["level"] = "明星"
        self.view.global_details["knowledge_type"] = "掌握"
        self.view.global_details["tags"] = ["基础操作"]
        self.view._apply_global_details(None)

        for point in self.view.draft.all_points:
            self.assertEqual(point.level, "明星")
            self.assertEqual(point.knowledge_type, "掌握")
            self.assertEqual(point.tags, ["基础操作"])

    def test_tags_can_be_added_and_removed(self):
        self.fill_through_step_two()
        point = self.view.draft.all_points[0]
        self.view._add_tag(point, "标题栏", None)
        self.view._add_tag(point, "标题栏", None)
        self.assertEqual(point.tags, ["标题栏"])
        self.view._remove_tag(point, "标题栏")
        self.assertEqual(point.tags, [])

    def test_step_four_apply_and_reset_distribution(self):
        self.fill_through_step_two()
        self.view._go(4)
        self.view._set_global_count("12")
        self.view._apply_global_defaults(None)

        for point in self.view.draft.all_points:
            self.assertEqual(point.question_count, 12)
            self.assertEqual(sum(point.type_counts.values()), 12)
            self.assertFalse(point.overridden)

        target = self.view.draft.all_points[0]
        target.overridden = True
        self.view._reset_point_distribution(target)
        self.assertFalse(target.overridden)
        self.assertEqual(target.question_count, 12)

    def test_distribution_view_toggle(self):
        self.fill_through_step_two()
        self.view._go(4)

        class _Control:
            selected = {"ratio"}

        class _Event:
            control = _Control()

        self.view._on_distribution_view_change(_Event())
        self.assertEqual(self.view.distribution_view, "ratio")

    def test_sensitivity_change_updates_queue(self):
        self.fill_through_step_two()
        self.view._go(4)

        class _Control:
            value = "严格"

        class _Event:
            control = _Control()

        self.view._set_sensitivity(_Event())
        self.assertEqual(self.view.draft.sensitivity, "严格")
        self.assertEqual(self.view.queue.sensitivity, "严格")

    def test_summary_bar_totals(self):
        self.fill_through_step_two()
        summary = self.view._summary_bar()
        self.assertIn("知识点 2 个", summary.content.controls[0].value)
        self.assertIn("总题数 20 题", summary.content.controls[2].value)


class GenerationGateTests(WizardBaseTests):
    def test_generation_without_api_key_shows_guidance_and_stays_idle(self):
        self.fill_through_step_two()
        self.view._go(5)
        self.view._start_generation(None)

        self.assertEqual(self.view.draft.generation_status, "idle")
        self.assertEqual(len(self.page.dialogs), 1)
        self.assertFalse(self.page.worker_alive())

    def test_settings_dialog_opens_from_guidance(self):
        self.view._open_settings()
        self.assertEqual(len(self.page.dialogs), 1)
        self.assertIsInstance(self.page.dialogs[0], ft.AlertDialog)


class ClarificationHandshakeTests(WizardBaseTests):
    """§H-1：worker 阻塞、事件循环线程弹窗、回答后唤醒。"""

    def _prepare_single_point(self, ai_responses: list):
        self.view._set_field("course_name", "CorelDraw")
        self.view._commit_chapter("界面介绍")
        self.view._add_points(["窗口结构"])
        self.view._next(None)
        self.view._next(None)
        self.view._add_tag(self.view.draft.all_points[0], "标题栏", None)
        self.view._next(None)
        point = self.view.draft.all_points[0]
        point.set_type_ratio({"单选": 100, "多选": 0, "判断": 0})
        point.set_question_count(1)
        self.view._save_now()
        self.view._go(5)
        return self.stub_ai(ai_responses)

    def test_worker_blocks_then_answer_releases_it(self):
        self._prepare_single_point([_questions_payload([invalid_question()])])

        self.view._start_generation(None)
        self.assertEqual(self.view.draft.generation_status, "running")
        self.assertTrue(self.page.wait_for_task("_show_clarification_dialog"))

        # 事件循环线程弹窗
        self.assertTrue(self.page.run_one_task())
        clarification = self.view.queue.current()
        self.assertIsNotNone(clarification)
        self.assertEqual(clarification.kind, "invalid_question")
        self.assertEqual(clarification.level, "确认")
        self.assertEqual(clarification.status, STATUS_PENDING)
        self.assertTrue(self.page.worker_alive(), "worker 应阻塞等待澄清")

        # 回答 → 唤醒 worker
        self.view._answer_clarification(clarification, "丢弃该题", True)
        self.assertEqual(clarification.status, "answered")
        self.assertEqual(self.view.queue.pending(), [])

        self.assertTrue(self.page.wait_workers())
        self.assertEqual(self.view.draft.generation_status, "complete")
        self.assertEqual(self.view.draft.current_step, 6)
        records = self.view.draft.clarification_records
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["choice"], "丢弃该题")
        self.assertEqual(records[0]["source"], "dialog")

    def test_close_dialog_defers_without_hanging_worker(self):
        self._prepare_single_point(
            [
                _questions_payload([invalid_question()]),
                _questions_payload([valid_question("补生成（）")]),
            ]
        )

        self.view._start_generation(None)
        self.assertTrue(self.page.wait_for_task("_show_clarification_dialog"))
        self.assertTrue(self.page.run_one_task())

        clarification = self.view.queue.current()
        self.view._defer_clarification(clarification)

        # 关闭(×) 保持挂起，但 worker 必须被唤醒并继续
        self.assertEqual(clarification.status, STATUS_PENDING)
        self.assertEqual(len(self.view.queue.pending()), 1)
        self.assertTrue(
            self.page.wait_workers(timeout=20), "关闭弹窗后 worker 不能悬挂"
        )
        self.assertEqual(self.view.draft.generation_status, "complete")

    def test_answering_deferred_clarification_regenerates_point(self):
        self._prepare_single_point(
            [
                _questions_payload([invalid_question()]),
                _questions_payload([valid_question("补生成（）")]),
            ]
        )

        self.view._start_generation(None)
        self.assertTrue(self.page.wait_for_task("_show_clarification_dialog"))
        self.assertTrue(self.page.run_one_task())
        clarification = self.view.queue.current()
        self.view._defer_clarification(clarification)
        self.assertTrue(self.page.wait_workers())

        point = self.view.draft.all_points[0]
        self.assertEqual(len(point.questions), 0)

        # 从［待澄清 n］重开并回答 → 应触发补生成
        self.view._open_clarifications(None)
        self.assertTrue(self.page.run_one_task())
        reopened = self.view.queue.current()
        self.view._answer_clarification(reopened, "保留（导出前修正）", False)

        self.assertTrue(self.page.wait_workers())
        self.assertEqual(len(point.questions), 1)
        self.assertEqual(self.view.queue.pending(), [])

    def test_skip_marks_point_missing(self):
        self._prepare_single_point([_questions_payload([invalid_question()])])

        self.view._start_generation(None)
        self.assertTrue(self.page.wait_for_task("_show_clarification_dialog"))
        self.assertTrue(self.page.run_one_task())

        clarification = self.view.queue.current()
        self.view._skip_clarification(clarification)
        self.assertTrue(self.page.wait_workers())

        point = self.view.draft.all_points[0]
        self.assertTrue(point.skipped)
        self.assertEqual(clarification.status, "skipped")
        self.assertIn((point.chapter_order, point.order), self.view.queue.skipped_points())

    def test_cleanup_releases_blocked_worker(self):
        self._prepare_single_point([_questions_payload([invalid_question()])])
        self.view._start_generation(None)
        self.assertTrue(self.page.wait_for_task("_show_clarification_dialog"))
        self.assertTrue(self.page.run_one_task())
        self.assertTrue(self.page.worker_alive())

        self.view.cleanup()
        self.assertTrue(
            self.page.wait_workers(timeout=5), "cleanup 必须唤醒并结束 worker"
        )


class PauseCancelTests(WizardBaseTests):
    def _prepare(self):
        self.view._set_field("course_name", "CorelDraw")
        self.view._commit_chapter("界面介绍")
        self.view._add_points(["窗口结构", "工具栏"])
        self.view._next(None)
        self.view._next(None)
        self.view._next(None)
        self.view._go(5)

    def test_pause_then_resume_updates_status(self):
        self._prepare()
        self.stub_ai(
            [
                _questions_payload([valid_question("题一（）")]),
                _questions_payload([valid_question("题二（）")]),
            ]
        )
        self.view._start_generation(None)
        self.assertTrue(self.page.wait_workers())

        self.view.draft.generation_status = "running"
        self.view._toggle_pause(None)
        self.assertEqual(self.view.draft.generation_status, "paused")
        self.view._toggle_pause(None)
        self.assertEqual(self.view.draft.generation_status, "running")

    def test_cancel_sets_cancelled_status(self):
        self._prepare()
        self.view._start_generation(None)
        self.view._cancel_generation(None)
        self.assertEqual(self.view.draft.generation_status, "cancelled")
        # 取消是正常退出路径，不能当成「生成失败」弹出错误框
        self.assertTrue(self.page.wait_workers(timeout=10))
        error_titles = [
            dialog for dialog in self.page.dialogs
            if getattr(dialog, "content", None) is not None
            and "失败" in str(getattr(dialog.content, "value", ""))
        ]
        self.assertEqual(error_titles, [])


class RegenerationTests(WizardBaseTests):
    """回归：生成过一次后，改动草稿必须能再次触发生成（不能只剩「下一步」）。"""

    def _prepare(self, responses: list):
        self.view._set_field("course_name", "CorelDraw")
        self.view._commit_chapter("界面介绍")
        self.view._add_points(["窗口结构"])
        self.view._next(None)  # -> step2
        self.view._next(None)  # -> step3
        self.view._add_tag(self.view.draft.all_points[0], "标题栏", None)
        self.view._next(None)  # -> step4
        point = self.view.draft.all_points[0]
        point.set_type_ratio({"单选": 100, "多选": 0, "判断": 0})
        point.set_question_count(1)
        self.view._save_now()
        self.view._go(5)
        return self.stub_ai(responses)

    @staticmethod
    def _action_labels(actions) -> list[str]:
        return [getattr(control, "content", None) for control in actions]

    def test_second_generation_is_triggered_after_draft_modification(self):
        session = self._prepare(
            [
                _questions_payload([valid_question("第一轮（）")]),
                _questions_payload([valid_question("第二轮（）")]),
            ]
        )

        # ---- 第一轮生成
        self.view._start_generation(None)
        self.assertTrue(self.page.wait_workers())
        self.assertEqual(self.view.draft.generation_status, "complete")
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(self.view.draft.all_points[0].questions[0].stem, "第一轮（）")
        self.assertFalse(generation_is_stale(self.view.draft))

        # ---- 回到 Step5 修改草稿（新增考点）
        self.view._go(5)
        self.view._add_tag(self.view.draft.all_points[0], "新增考点", None)
        self.assertTrue(
            generation_is_stale(self.view.draft),
            "修改考点后旧产物应被判定为过期",
        )
        self.assertIn(
            "草稿已修改",
            "；".join(WizardValidator().validate_step(self.view.draft, 5)),
        )

        # 过期时按钮必须是「重新生成」，且不允许直接下一步
        self.assertIn("重新生成", self._action_labels(self.view._build_generation_actions()))
        self.view._next(None)
        self.assertEqual(self.view.draft.current_step, 5)
        self.assertIn("草稿已修改", self.view.message)

        # ---- 第二轮生成：必须真的再调一次 AI
        self.view._start_generation(None)
        self.assertTrue(self.page.wait_workers())
        self.assertEqual(len(session.calls), 2, "第二次生成必须再次调用 AI 接口")
        self.assertEqual(self.view.draft.all_points[0].questions[0].stem, "第二轮（）")
        self.assertFalse(generation_is_stale(self.view.draft))
        self.assertEqual(self.view.draft.current_step, 6)

    def test_completed_generation_offers_regenerate_button(self):
        self._prepare([_questions_payload([valid_question()])])
        self.view._start_generation(None)
        self.assertTrue(self.page.wait_workers())

        self.view._go(5)
        labels = self._action_labels(self.view._build_generation_actions())
        self.assertIn("重新生成", labels)
        self.assertIn("下一步", labels)

    def test_regeneration_replaces_previous_questions(self):
        """重生成必须替换旧题，而不是把两轮题目叠在一起。"""
        session = self._prepare(
            [
                _questions_payload([valid_question("第一轮（）")]),
                _questions_payload([valid_question("第二轮（）")]),
            ]
        )
        self.view._start_generation(None)
        self.assertTrue(self.page.wait_workers())
        self.view._go(5)

        self.view._start_generation(None)
        self.assertTrue(self.page.wait_workers())

        stems = [q.stem for q in self.view.draft.all_points[0].questions]
        self.assertEqual(stems, ["第二轮（）"])
        self.assertEqual(len(session.calls), 2)

    def test_failed_regeneration_keeps_previous_questions(self):
        """重生成失败时不能把上一轮题目弄丢。"""
        session = self._prepare([_questions_payload([valid_question("第一轮（）")])])
        self.view._start_generation(None)
        self.assertTrue(self.page.wait_workers())
        self.assertEqual(len(self.view.draft.all_points[0].questions), 1)

        # 第二轮：AI 请求直接报错
        self.view._go(5)
        session.responses = [RuntimeError("网络挂了")]
        self.view._start_generation(None)
        self.assertTrue(self.page.wait_workers())

        # 单知识点失败不会抛到外层，但旧题必须被回填
        self.assertEqual(len(self.view.draft.all_points[0].questions), 1)
        self.assertEqual(self.view.draft.all_points[0].questions[0].stem, "第一轮（）")

    def test_stale_draft_cannot_bypass_export(self):
        """即使从步骤条直接跳到第⑥步，旧产物也不能被导出。"""
        self._prepare([_questions_payload([valid_question("旧题（）")])])
        self.view._start_generation(None)
        self.assertTrue(self.page.wait_workers())
        point = self.view.draft.all_points[0]
        mark_reviewed(point.questions[0], True)
        self.view.draft.review_mode = "按项"
        self.view.draft.export_word = False
        self.view._save_now()

        # 绕过第⑤步直接改草稿，再跳到第⑥步导出
        self.view._add_tag(point, "新增考点", None)
        ready, blockers = ready_for_export(self.view.draft)
        self.assertFalse(ready)
        self.assertTrue(any("重新生成" in item for item in blockers))

        self.view._go(6)
        before = list((self.tmp / "output" / "evaluation").glob("*.zip"))
        self.view._export(None)
        self.assertTrue(self.page.wait_workers(timeout=10))
        after = list((self.tmp / "output" / "evaluation").glob("*.zip"))
        self.assertEqual(before, after, "过期草稿不得产出导出文件")


class StepSixTests(WizardBaseTests):
    def _draft_with_questions(self):
        self.fill_through_step_two()
        point = self.view.draft.all_points[0]
        point.questions = [
            Question(
                stem="x（）",
                question_type="单选",
                difficulty="简单",
                options=["a", "b", "c", "d"],
                answer="A",
                confidence=0.5,
                internal_id="1-1-X-1",
            )
        ]
        self.view.draft.generation_status = "complete"
        self.view._save_now()
        return point

    def test_red_confidence_blocks_export_until_reviewed(self):
        point = self._draft_with_questions()
        ready, blockers = ready_for_export(self.view.draft)
        self.assertFalse(ready)
        self.assertTrue(any("红色" in item for item in blockers))

        mark_reviewed(point.questions[0], True)
        self.view.draft.review_mode = "按项"
        ready, blockers = ready_for_export(self.view.draft)
        self.assertTrue(ready, blockers)

    def test_export_without_questions_is_blocked_with_dialog(self):
        self.view._go(6)
        self.view._export(None)
        self.assertEqual(len(self.page.dialogs), 1)
        # show_error_dialog: title 是 Row(Icon, Text)，正文提到阻断原因
        self.assertIn("没有可导出的题目", self.page.dialogs[0].content.value)

    def test_preview_toggle(self):
        self._draft_with_questions()
        point = self.view.draft.all_points[0]
        self.view._toggle_preview(point)
        self.assertIn(point.name, self.view.review_expanded)
        self.view._toggle_preview(point)
        self.assertNotIn(point.name, self.view.review_expanded)

    def test_expanded_point_supports_bulk_review_and_renders_options(self):
        self._draft_with_questions()
        point = self.view.draft.all_points[0]
        point.questions[0].options = ["选项甲", "选项乙"]
        point.questions[0].answer = "B"
        self.view._toggle_preview(point)

        self.view._set_point_reviewed(point, True)
        self.assertTrue(all(question.reviewed for question in point.questions))
        options = self.view._question_options(point.questions[0])
        labels = [
            control.value
            for control in _iter_controls(options)
            if isinstance(control, ft.Text)
        ]
        self.assertTrue(any("A. 选项甲" in label for label in labels))
        self.assertTrue(any("B. 选项乙" in label and "正确答案" in label for label in labels))

        self.view._set_point_reviewed(point, False)
        self.assertTrue(all(not question.reviewed for question in point.questions))

    def test_step_two_uses_text_batch_input_without_excel_import(self):
        self.fill_through_step_two()
        self.view._go(2)
        labels = [
            control.value
            for control in _iter_controls(self.view._body)
            if isinstance(control, ft.Text)
        ]
        self.assertFalse(any("Excel" in (label or "") for label in labels))

    def test_clarification_records_dialog(self):
        self.view.draft.clarification_records.append(
            {
                "kind": "invalid_question",
                "level": "确认",
                "question": "q",
                "choice": "丢弃该题",
                "scope": "P1",
                "status": "answered",
                "timestamp": "2026-09-20 10:00:00",
            }
        )
        self.view._show_clarification_records(None)
        self.assertEqual(len(self.page.dialogs), 1)

    def test_export_produces_zip(self):
        point = self._draft_with_questions()
        mark_reviewed(point.questions[0], True)
        self.view.draft.review_mode = "按项"
        self.view.draft.export_word = False
        self.view._save_now()

        self.view._export(None)
        self.assertTrue(self.page.wait_workers())
        zips = list((self.tmp / "output" / "evaluation").glob("*.zip"))
        self.assertEqual(len(zips), 1)
        self.assertIn("评估题库", zips[0].name)


class NewDraftTests(WizardBaseTests):
    def test_new_draft_resets_state(self):
        self.fill_through_step_two()
        self.assertTrue(self.view.draft.chapters)

        class _Control:
            pass

        self.view._new_draft()
        dialog = self.page.dialogs[-1]
        confirm = dialog.actions[0]
        confirm.on_click(None)

        self.assertEqual(self.view.draft.course_name, "")
        self.assertEqual(self.view.draft.chapters, [])
        self.assertEqual(self.view.draft.current_step, 1)


class FletSerializableTreeTests(WizardBaseTests):
    """Flet 用 msgpack 传控制树，Dart 侧无法反序列化 ``set``，
    会在运行时抛 ``can not serialize 'set' object`` 并白屏（SegmentedButton.
    ``selected`` 曾是 ``list[str]`` 却被误传 set）。

    此处逐个步骤完整构建控件树，确保没有 set/callable 泄漏进去 ——
    这是单测能捕获的、最接近真实渲染的检查。
    """

    def _seed(self) -> None:
        self.view._set_field("course_name", "CorelDraw")
        self.view._set_field("target", "24级")
        self.view._commit_chapter("章节1")
        self.view._add_points(["知识点A", "知识点B"])
        point = self.view.draft.all_points[0]
        point.tags = ["考点1"]
        point.questions = [
            Question(
                stem="x（）",
                question_type="单选",
                difficulty="简单",
                options=["a", "b", "c", "d"],
                answer="A",
                confidence=0.5,
                internal_id="1-1-X-1",
            )
        ]
        self.view.review_expanded.add(point.name)

    def _scan(self, node, path="root", seen=None, findings=None):
        if findings is None:
            findings = []
        if seen is None:
            seen = set()

        if isinstance(node, (set, frozenset)):
            findings.append(f"{path}: {type(node).__name__}")
            return findings
        # 事件处理器（on_*）是合法 callable：Flet 编码器会把它们序列化成布尔值，
        # 因此只在**非 on_* 字段**上把 callable 视为异常。
        if callable(node) and not isinstance(node, type):
            leaf = path.rsplit(".", 1)[-1]
            if not leaf.startswith("on_"):
                findings.append(f"{path}: callable")
            return findings

        if id(node) in seen:
            return findings
        seen.add(id(node))

        if dataclasses.is_dataclass(node) and not isinstance(node, type):
            for field in dataclasses.fields(node):
                if "skip" in field.metadata:
                    continue
                self._scan(
                    getattr(node, field.name, None), f"{path}.{field.name}", seen, findings
                )
        elif isinstance(node, dict):
            for key, value in node.items():
                self._scan(value, f"{path}[{key!r}]", seen, findings)
        elif isinstance(node, (list, tuple)):
            for index, value in enumerate(node):
                self._scan(value, f"{path}[{index}]", seen, findings)

        return findings

    def test_every_step_builds_a_serialisable_control_tree(self):
        self._seed()
        for step in range(1, 7):
            with self.subTest(step=step):
                self.view.draft.generation_status = (
                    "complete" if step >= 5 else "idle"
                )
                self.view.draft.current_step = step
                self.view._render()
                self.assertEqual(self._scan(self.view._root, f"step{step}"), [])

    def test_scanner_detects_set_in_control_tree(self):
        """自检：确认上面的扫描真的能抓到 set（防止测试变成假阴性）。"""
        bad = ft.SegmentedButton(
            segments=[ft.Segment(value="counts", label=ft.Text("x"))],
            selected={"counts"},
        )
        findings = self._scan(ft.Column(controls=[bad]))
        self.assertTrue(findings, "扫描器必须能发现 set")
        self.assertIn("selected", findings[0])

    def test_segmented_button_avoided_in_favour_of_textbutton_toggle(self):
        """回归：Flet 0.82 的 SegmentedButton 在中文标签下会算错段宽把文字截断，
        且曾因 ``selected`` 传 set 导致运行时白屏，因此改用 TextButton 手搭。"""
        self.fill_through_step_two()
        self.view.draft.current_step = 4
        self.view._render()

        controls = list(_iter_controls(self.view._root))
        self.assertEqual(
            [c for c in controls if isinstance(c, ft.SegmentedButton)],
            [],
            "Step4 不应再使用 SegmentedButton",
        )

        toggle = self.view._distribution_toggle()
        buttons = [c for c in _iter_controls(toggle) if isinstance(c, ft.TextButton)]
        self.assertEqual([b.content for b in buttons], ["按题数", "按比例"])

    def test_distribution_toggle_switches_view(self):
        self.fill_through_step_two()
        self.view.draft.current_step = 4
        self.view._render()

        self.view._set_distribution_view("ratio")
        self.assertEqual(self.view.distribution_view, "ratio")
        self.assertEqual(
            "按比例", self.view._body.controls[1].content.controls[0].value.split("（")[1].rstrip("）")
        )

        self.view._set_distribution_view("counts")
        self.assertEqual(self.view.distribution_view, "counts")

    def test_distribution_view_event_entrypoint_is_tolerant(self):
        """兼容事件式入口：list / set / tuple / 空 都能处理。"""
        self.fill_through_step_two()

        def event_with(selected):
            class _Control:
                pass

            control = _Control()
            control.selected = selected
            return type("_Event", (), {"control": control})()

        for value, expected in (
            (["ratio"], "ratio"),
            ({"ratio"}, "ratio"),
            (("ratio",), "ratio"),
            (["counts"], "counts"),
        ):
            with self.subTest(selected=value):
                self.view._on_distribution_view_change(event_with(value))
                self.assertEqual(self.view.distribution_view, expected)

        # 空选择（[] / None）应保持当前视图不变，而不是重置
        for value in ([], None):
            with self.subTest(selected=value, behaviour="keep-current"):
                self.view._set_distribution_view("ratio")
                self.view._on_distribution_view_change(event_with(value))
                self.assertEqual(self.view.distribution_view, "ratio")

    def test_drag_handles_do_not_stack_with_default_handles(self):
        """回归：Flet 默认拖拽手柄会叠在行尾删除按钮上，必须关闭并自备手柄。"""
        self.fill_through_step_two()
        self.view.draft.current_step = 2
        self.view._render()

        controls = list(_iter_controls(self.view._root))
        reorderable = [c for c in controls if isinstance(c, ft.ReorderableListView)]
        self.assertTrue(reorderable)
        for view_list in reorderable:
            self.assertFalse(
                view_list.show_default_drag_handles,
                "必须关闭默认拖拽手柄，否则会与删除按钮重叠",
            )

        handles = [c for c in controls if isinstance(c, ft.ReorderableDragHandle)]
        # fill_through_step_two 造出 1 个章节 + 2 个知识点 → 3 个拖拽手柄
        self.assertEqual(len(handles), 3)

    def test_each_row_has_exactly_one_drag_handle_before_actions(self):
        self.fill_through_step_two()
        self.view.draft.current_step = 2
        self.view._render()

        rows = [
            control
            for control in _iter_controls(self.view._root)
            if isinstance(control, ft.Container)
            and str(getattr(control, "key", "")).startswith(("chapter-", "point-"))
        ]
        self.assertEqual(len(rows), 3)
        for row in rows:
            kinds = []
            for control in _iter_controls(row):
                if isinstance(control, ft.ReorderableDragHandle):
                    kinds.append("handle")
                elif isinstance(control, ft.IconButton):
                    kinds.append("button")
            self.assertEqual(
                kinds, ["handle", "button", "button"], f"{row.key} 图标顺序异常: {kinds}"
            )


    def test_no_expanded_child_inside_a_wrapping_row(self):
        """回归（高危）：``ft.Container(expand=True)`` 不能出现在 ``wrap=True`` 的
        Row 里 —— Flutter 的 Wrap 不支持 Expanded，会渲染成一大块灰色错误块
        并吞掉后续控件（曾命中 Step3×2 / Step4 / Step5 / Step6 共 5 处）。

        这是运行时检查（不是 AST）——直接扫真实控件树，因此能拦住以后任何
        新建的 wrap Row。
        """
        self._seed()
        for step in range(1, 7):
            with self.subTest(step=step):
                self.view.draft.generation_status = (
                    "complete" if step >= 5 else "idle"
                )
                self.view.draft.current_step = step
                self.view._render()

                offenders = []
                for control in _iter_controls(self.view._root):
                    if not isinstance(control, ft.Row) or not control.wrap:
                        continue
                    for child in _iter_controls(control.controls):
                        if child is control:
                            continue
                        if getattr(child, "expand", None):
                            offenders.append(
                                f"step{step}: wrap Row 内含 expand 子控件 {type(child).__name__}"
                            )
                self.assertEqual(offenders, [])

    def test_action_buttons_are_not_squeezed_out_of_chip_rows(self):
        """Step5 / Step6 的状态胶囊行必须仍能带上操作按钮（曾经被灰块吞掉）。"""
        self._seed()
        for step in (5, 6):
            with self.subTest(step=step):
                self.view.draft.current_step = step
                self.view.draft.generation_status = "complete"
                self.view._render()

                labels = [
                    control.content
                    for control in _iter_controls(self.view._root)
                    if isinstance(control, ft.TextButton)
                ]
                self.assertIn("查看澄清记录", labels)
        # Step5 多一个待澄清入口
        self.view.draft.current_step = 5
        self.view._render()
        labels = [
            control.content
            for control in _iter_controls(self.view._root)
            if isinstance(control, ft.TextButton)
        ]
        self.assertIn("待澄清队列", labels)

    def test_step_three_and_four_expose_apply_buttons(self):
        """Step3 / Step4 的「应用到全部」按钮必须真的在控件树里。"""
        self._seed()
        for step, expected in (
            (3, "应用到全部未填写知识点"),
            (4, "应用到全部知识点"),
        ):
            with self.subTest(step=step):
                self.view.draft.current_step = step
                self.view._render()
                labels = [
                    control.content
                    for control in _iter_controls(self.view._root)
                    if isinstance(control, ft.FilledButton)
                ]
                self.assertIn(expected, labels)


    def test_no_value_input_controls_as_direct_child_of_a_wrapping_row(self):
        """回归：``ft.Checkbox`` / ``ft.Switch`` / ``ft.Radio`` / ``ft.Slider`` 不能作为
        ``wrap=True`` Row 的**直接子项** —— Wrap 只按直接子项确定宽度，这类控件
        实测会被各自排成一行（Step6 的［Word/Excel］因此被竖排）。

        修法：包一层**显式宽度**的 Container（已用探针页验证可行），
        这样既能保留自动换行，又不会竖排。
        """
        self._seed()
        risky = (ft.Checkbox, ft.Switch, ft.Radio, ft.Slider)
        for step in range(1, 7):
            with self.subTest(step=step):
                self.view.draft.generation_status = (
                    "complete" if step >= 5 else "idle"
                )
                self.view.draft.current_step = step
                self.view._render()

                offenders = []
                for row in _iter_controls(self.view._root):
                    if not isinstance(row, ft.Row) or not row.wrap:
                        continue
                    for child in row.controls:
                        if isinstance(child, risky):
                            offenders.append(
                                f"step{step}: wrap Row 的直接子项是 {type(child).__name__}"
                            )
                        elif getattr(child, "width", None) is None and any(
                            isinstance(inner, risky)
                            for inner in _iter_controls(child)
                        ):
                            offenders.append(
                                f"step{step}: wrap Row 直接子项 {type(child).__name__} "
                                f"未设宽度且内含风险控件"
                            )
                self.assertEqual(offenders, [])

    def test_wrap_row_rule_is_sensitive(self):
        """自检：确认上面的检查真能抓到「Switch 作为 wrap Row 直接子项」。"""
        bad = ft.Row([ft.Text("a"), ft.Switch(value=True)], wrap=True)
        fixed = ft.Row(
            [ft.Text("a"), ft.Container(content=ft.Switch(value=True), width=200)],
            wrap=True,
        )

        def offenders(root):
            risky = (ft.Checkbox, ft.Switch, ft.Radio, ft.Slider)
            found = []
            for row in _iter_controls(root):
                if not isinstance(row, ft.Row) or not row.wrap:
                    continue
                for child in row.controls:
                    if isinstance(child, risky):
                        found.append(type(child).__name__)
                    elif getattr(child, "width", None) is None and any(
                        isinstance(inner, risky) for inner in _iter_controls(child)
                    ):
                        found.append(f"unwrapped:{type(child).__name__}")
            return found

        self.assertEqual(offenders(ft.Column([bad])), ["Switch"])
        self.assertEqual(offenders(ft.Column([fixed])), [])

    def test_export_format_row_lays_out_horizontally(self):
        """Step6 的导出格式行必须是**非 wrap** Row，且包含 Word/Excel 勾选框。"""
        self._seed()
        self.view.draft.current_step = 6
        self.view._render()

        row = self.view._export_format_row()
        self.assertFalse(row.wrap)
        labels = [
            control.label
            for control in _iter_controls(row)
            if isinstance(control, ft.Checkbox)
        ]
        self.assertEqual(labels, ["Word", "Excel"])
        self.assertEqual(
            len([c for c in _iter_controls(row) if isinstance(c, ft.Switch)]), 1
        )

    def test_generation_log_panel_fills_card_width(self):
        """回归：日志面板必须用 Row + expand 撑满，否则卡片会按文字宽度缩成窄条。"""
        self._seed()
        self.view.logs = ["[10:00:00] 一行日志"]
        self.view.draft.current_step = 5
        self.view._render()

        panels = [
            control
            for control in _iter_controls(self.view._root)
            if isinstance(control, ft.Container)
            and control.height == LOG_PANEL_HEIGHT
            and control.bgcolor == Palette.SURFACE_ALT
        ]
        self.assertEqual(len(panels), 1)
        self.assertTrue(panels[0].expand, "日志面板需要 expand 才能撑满宽度")
        # 向导区拉高后日志面板应当有实际可用的高度
        self.assertGreaterEqual(LOG_PANEL_HEIGHT, 240)

    def test_wizard_shell_fills_frame_height(self):
        """向导区必须撑满主框架剩余高度，否则底部会留一截无用空白。"""
        self.page.height = 900
        self.view.get_content()
        self.view._on_start_click()

        shell = self.view._wizard_shell
        self.assertIsNotNone(shell)
        self.assertEqual(shell.height, 900 - FRAME_CHROME_HEIGHT)
        # 操作栏固定在底部：内容区可滚动且撑满，步骤条与操作栏不参与滚动
        self.assertTrue(self.view._body.expand)
        self.assertIsNotNone(self.view._body.scroll)
        self.assertIsNone(self.view._root.scroll)
        self.assertEqual(
            [type(c).__name__ for c in self.view._root.controls],
            ["Row", "Column", "Row"],
        )

    def test_wizard_shell_height_has_safe_minimum(self):
        """拿不到 page.height 时使用安全下限，不能把向导区压成 0。"""
        self.page.height = None
        self.assertGreaterEqual(self.view._wizard_height(), 420)
        self.page.height = 100
        self.assertGreaterEqual(self.view._wizard_height(), 420)


class PluginSettingsSchemaTests(unittest.TestCase):
    """通用插件设置组件（manifest settings_schema 驱动）。"""

    def setUp(self):
        self.schema = json.loads(
            (PLUGINS_DIR / "evaluation" / "manifest.json").read_text(encoding="utf-8")
        )["settings_schema"]

        class _SettingsManager:
            def __init__(self):
                self.store: dict = {}

            def get_plugin_config(self, plugin_id, key, default=None):
                return self.store.get((plugin_id, key), default)

            def set_plugin_config(self, plugin_id, key, value):
                self.store[(plugin_id, key)] = value
                return True

        self.settings = _SettingsManager()
        self.page = FakePage()

    def test_manifest_declares_expected_fields(self):
        keys = [field["key"] for field in self.schema]
        self.assertEqual(
            keys, ["api_key", "base_url", "model", "exa_mcp_url", "exa_api_key"]
        )
        defaults = {field["key"]: field.get("default") for field in self.schema}
        self.assertEqual(defaults["base_url"], "https://api.deepseek.com/v1")
        self.assertEqual(defaults["model"], "deepseek-chat")
        self.assertEqual(defaults["exa_mcp_url"], "https://mcp.exa.ai/mcp")
        self.assertTrue(
            next(f for f in self.schema if f["key"] == "api_key")["required"]
        )

    def test_dialog_renders_all_fields(self):
        dialog = build_plugin_settings_dialog(
            self.page, "evaluation", "评估出题助手", self.schema, self.settings
        )
        self.assertIsInstance(dialog, ft.AlertDialog)
        self.assertEqual(len(dialog.content.controls), len(self.schema))
        labels = [action.content for action in dialog.actions]
        self.assertEqual(labels, ["取消", "保存"])

    def test_required_field_blocks_save(self):
        dialog = build_plugin_settings_dialog(
            self.page, "evaluation", "评估出题助手", self.schema, self.settings
        )
        dialog.actions[1].on_click(None)
        self.assertEqual(self.settings.store, {})
        self.assertEqual(len(self.page.dialogs), 0)

    def test_save_persists_values_with_correct_types(self):
        schema = list(self.schema) + [
            {"key": "top_k", "label": "TopK", "type": "number", "default": 5},
            {"key": "strict", "label": "严格", "type": "switch", "default": False},
        ]
        dialog = build_plugin_settings_dialog(
            self.page, "evaluation", "评估出题助手", schema, self.settings
        )
        # 依次为：api_key / base_url / model / exa_mcp_url / exa_api_key / top_k / strict
        controls = [row.controls[1] for row in dialog.content.controls]
        controls[0].value = "sk-test"
        controls[5].value = "7"
        controls[6].value = True

        dialog.actions[1].on_click(None)
        stored = {
            key: value for (plugin_id, key), value in self.settings.store.items()
        }
        self.assertEqual(stored["api_key"], "sk-test")
        self.assertEqual(stored["model"], "deepseek-chat")
        self.assertEqual(stored["top_k"], 7)
        self.assertIs(stored["strict"], True)

    def test_cancel_closes_dialog_without_saving(self):
        dialog = build_plugin_settings_dialog(
            self.page, "evaluation", "评估出题助手", self.schema, self.settings
        )
        self.page.show_dialog(dialog)
        dialog.actions[0].on_click(None)
        self.assertEqual(self.settings.store, {})
        self.assertEqual(self.page.dialogs, [])

    def test_setting_value_normalises_number_and_switch(self):
        self.assertEqual(setting_value({"type": "number", "default": 3}, "12"), 12)
        self.assertEqual(setting_value({"type": "number", "default": 3}, "bad"), 3)
        self.assertIs(setting_value({"type": "switch", "default": False}, None), False)
        self.assertIs(setting_value({"type": "switch", "default": False}, True), True)
        self.assertEqual(setting_value({"type": "text", "default": ""}, None), "")

    def test_validate_settings_reports_missing_required(self):
        errors = validate_settings(
            [{"key": "api_key", "label": "AI API Key", "required": True}], {}
        )
        self.assertEqual(errors, ["AI API Key不能为空"])
        self.assertEqual(
            validate_settings(
                [{"key": "api_key", "label": "AI API Key", "required": True}],
                {"api_key": "x"},
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
