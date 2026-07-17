import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGINS_DIR = ROOT / "plugins"
if str(PLUGINS_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGINS_DIR))


class FakePage:
    def __init__(self):
        self.update_count = 0
        self.scheduled_update_count = 0
        self.thread_targets = []

    def update(self):
        self.update_count += 1

    def schedule_update(self):
        self.scheduled_update_count += 1

    def run_thread(self, target, *args, **kwargs):
        self.thread_targets.append((target, args, kwargs))


class CloudExamPluginLocationTests(unittest.TestCase):
    def test_cloud_exam_workflow_lives_in_plugin_package(self):
        workflow_module = importlib.import_module("cloud_exam.workflow")

        module_path = Path(workflow_module.__file__).resolve()
        self.assertTrue(module_path.is_relative_to(ROOT / "plugins" / "cloud_exam"))
        self.assertFalse((ROOT / "src" / "cloud_exam" / "workflow.py").exists())


class CloudExamMatchingTests(unittest.TestCase):
    def test_network_monitor_matches_real_exam_question_api_url(self):
        from cloud_exam.workflow import NetworkMonitor

        monitor = NetworkMonitor()

        self.assertTrue(
            monitor._matches_target_url(
                "https://ai.cqzuxia.com/exam/api/StudentExam/GetQuestionsByExpId?expID=exam-1"
            )
        )
        self.assertTrue(
            monitor._matches_target_url(
                "https://ai.cqzuxia.com/exam/api/StudentExam/getquestionsbyexpid?expID=exam-1"
            )
        )
        self.assertFalse(
            monitor._matches_target_url(
                "https://ai.cqzuxia.com/exam/api/StudentExam/GetStudentAnswerList?expID=exam-1"
            )
        )

    def test_finds_answer_by_question_id_inside_multi_course_bank(self):
        from cloud_exam.workflow import CloudExamWorkflow

        workflow = CloudExamWorkflow()
        workflow.question_bank_data = {
            "courses": [
                {
                    "courseID": "course-1",
                    "chapters": [
                        {
                            "chapterID": "chapter-1",
                            "knowledges": [
                                {
                                    "KnowledgeID": "knowledge-1",
                                    "questions": [
                                        {
                                            "QuestionID": "question-1",
                                            "QuestionTitle": "same title",
                                            "options": [
                                                {"id": "wrong-answer", "isTrue": False},
                                                {"id": "right-answer", "isTrue": True},
                                            ],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        self.assertEqual(workflow._find_answer_in_bank("question-1"), ["right-answer"])


class CloudExamFletUpdateTests(unittest.TestCase):
    def test_append_log_updates_dialog_text_control(self):
        from cloud_exam.view import CloudExamView

        view = object.__new__(CloudExamView)
        view.page = FakePage()
        view._create_log_dialog("答案注入")

        view._append_log("第一条日志")
        view._append_log("第二条日志", "success")

        self.assertIn("第一条日志", view._current_log_text.value)
        self.assertIn("第二条日志", view._current_log_text.value)
        self.assertGreater(view.page.update_count + view.page.scheduled_update_count, 0)

    def test_background_work_uses_flet_page_thread_executor(self):
        from cloud_exam.view import CloudExamView

        view = object.__new__(CloudExamView)
        view.page = FakePage()

        def task():
            return None

        view._run_background(task)

        # _run_background 通过 run_background_task 委托 page.run_thread，
        # task 被包装在闭包中执行，这里只验证 run_thread 被调用了一次
        self.assertEqual(len(view.page.thread_targets), 1)


if __name__ == "__main__":
    unittest.main()
