"""src/ui/components.AnswerProgressDialog 的单元测试。

用 FakePage（直接执行 run_task 的 coroutine）避免真实 Flet 运行时，
验证进度对话框的构建、进度更新、日志追加/截断行为。
"""

import asyncio
import unittest

import flet as ft

from src.ui.components import AnswerProgressDialog


class FakePage:
    """模拟 ft.Page：run_task 直接同步执行 async 函数；update 计数。"""

    def __init__(self):
        self.update_count = 0

    def update(self):
        self.update_count += 1

    def run_task(self, fn, *args, **kwargs):
        result = fn(*args, **kwargs)
        if asyncio.iscoroutine(result):
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(result)
            finally:
                loop.close()


class AnswerProgressDialogBuildTests(unittest.TestCase):
    def test_blue_theme_builds_alert_dialog(self):
        dlg = AnswerProgressDialog(FakePage(), title="答题", theme="blue", show_big_percent=True)
        self.assertIsInstance(dlg.dialog, ft.AlertDialog)
        self.assertTrue(dlg.dialog.modal)

    def test_orange_theme_with_log_panel_creates_log_text(self):
        dlg = AnswerProgressDialog(
            FakePage(), title="认证答题", theme="orange", show_log_panel=True, width=650
        )
        self.assertIsInstance(dlg.dialog, ft.AlertDialog)
        # show_log_panel=True 时内部应创建日志文本控件
        self.assertIsNotNone(dlg._log_text)

    def test_no_log_panel_leaves_log_text_none(self):
        dlg = AnswerProgressDialog(FakePage(), title="答题", show_log_panel=False)
        self.assertIsNone(dlg._log_text)


class AnswerProgressDialogUpdateTests(unittest.TestCase):
    def setUp(self):
        self.page = FakePage()
        self.dlg = AnswerProgressDialog(self.page, title="答题", theme="blue", show_big_percent=True)

    def test_update_progress_with_values_sets_percent_and_count(self):
        self.dlg.update_progress(3, 10)
        self.assertAlmostEqual(self.dlg._progress_bar.value, 0.3)
        self.assertEqual(self.dlg._percent_text.value, "30%")
        self.assertEqual(self.dlg._count_text.value, "3/10")
        self.assertGreaterEqual(self.page.update_count, 1)

    def test_update_progress_clamps_over_100(self):
        self.dlg.update_progress(12, 10)  # current > total
        self.assertAlmostEqual(self.dlg._progress_bar.value, 1.0)
        self.assertEqual(self.dlg._percent_text.value, "100%")

    def test_update_progress_indeterminate_shows_hourglass(self):
        self.dlg.update_progress()  # 无 current/total
        self.assertIsNone(self.dlg._progress_bar.value)
        self.assertEqual(self.dlg._percent_text.value, "⏳")
        self.assertEqual(self.dlg._count_text.value, "正在处理...")

    def test_update_progress_message_only_shows_in_count(self):
        self.dlg.update_progress(message="正在初始化浏览器...")
        self.assertEqual(self.dlg._count_text.value, "正在初始化浏览器...")
        self.assertIsNone(self.dlg._progress_bar.value)

    def test_update_progress_skips_when_no_page(self):
        dlg = AnswerProgressDialog(None, title="答题")
        # 无 page 时不应抛异常
        dlg.update_progress(1, 10)
        self.assertEqual(dlg._progress_bar.value, 0.0)  # 未被更新


class AnswerProgressDialogLogTests(unittest.TestCase):
    def setUp(self):
        self.page = FakePage()
        self.dlg = AnswerProgressDialog(
            self.page, title="认证", theme="orange", show_log_panel=True
        )

    def test_append_log_appends_lines(self):
        self.dlg.append_log("第一行")
        self.assertIn("第一行", self.dlg._log_text.value)
        self.dlg.append_log("第二行")
        self.assertIn("第一行", self.dlg._log_text.value)
        self.assertIn("第二行", self.dlg._log_text.value)
        # 两条日志应分两行
        self.assertEqual(self.dlg._log_text.value.count("\n"), 2)

    def test_append_log_truncates_over_2000_chars(self):
        long_line = "A" * 2500
        self.dlg.append_log(long_line)
        value = self.dlg._log_text.value
        self.assertIn("日志已截断", value)
        self.assertLessEqual(len(value), 2100)  # 截断标记 + 2000 字符上限

    def test_append_log_no_op_without_log_panel(self):
        dlg = AnswerProgressDialog(FakePage(), title="答题", show_log_panel=False)
        # 无日志区时 append_log 不应抛异常
        dlg.append_log("不应出现")
        self.assertIsNone(dlg._log_text)


if __name__ == "__main__":
    unittest.main()
