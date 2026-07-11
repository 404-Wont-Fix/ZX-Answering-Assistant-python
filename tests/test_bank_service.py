"""src/extraction/bank_service.py 的单元测试。

用 tempfile 构造合法/非法/不匹配的 JSON，验证 load_question_bank 各分支与
apply_bank_result 的状态语义（成功存入 / 不匹配清除 / 错误保持原值）。
"""

import json
import os
import sys
import tempfile
import unittest

# load_question_bank 内部保留了原 _process 的 emoji print（如 "❌"），
# Windows GBK 控制台 stdout 默认无法编码 emoji，这里把测试 stdout 切到 utf-8。
# （GUI 运行环境下 stdout 已是 utf-8，不受影响。）
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from src.extraction.bank_service import BankLoadResult, apply_bank_result, load_question_bank


def _write_temp_json(data) -> str:
    """把 dict（json.dump）或 str（原始内容，用于造非法 JSON）写入临时文件，返回路径。"""
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        if isinstance(data, str):
            f.write(data)
        else:
            json.dump(data, f, ensure_ascii=False)
    return path


def _single_bank(course_id="course-1", course_name="数学") -> dict:
    """最小可被 importer 识别为 single 的题库结构。"""
    return {
        "class": {
            "name": "高三1班",
            "course": {
                "courseID": course_id,
                "courseName": course_name,
                "chapters": [
                    {
                        "chapterID": "ch-1",
                        "chapterTitle": "第一章",
                        "knowledges": [
                            {
                                "KnowledgeID": "k-1",
                                "Knowledge": "知识点1",
                                "questions": [
                                    {
                                        "QuestionID": "q-1",
                                        "QuestionTitle": "1+1=?",
                                        "options": [
                                            {"id": "opt-1", "isTrue": True, "oppentionContent": "2"},
                                            {"id": "opt-2", "isTrue": False, "oppentionContent": "3"},
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        }
    }


def _multiple_bank() -> dict:
    """最小可被 importer 识别为 multiple 的题库结构。"""
    return {
        "class": {"name": "高三1班"},
        "course_list": [{"courseID": "course-1", "courseName": "数学"}],
        "chapters": [
            {
                "chapterID": "ch-1",
                "chapterTitle": "第一章",
                "knowledges": [
                    {
                        "KnowledgeID": "k-1",
                        "Knowledge": "知识点1",
                        "questions": [{"QuestionID": "q-1", "QuestionTitle": "1+1=?", "options": [{"id": "o1", "isTrue": True, "oppentionContent": "2"}]}],
                    }
                ],
            }
        ],
    }


class _FakeView:
    """模拟 View 的题库状态属性。"""

    def __init__(self, initial=None):
        self.question_bank_data = initial


class LoadQuestionBankTests(unittest.TestCase):
    def setUp(self):
        self._temp_paths = []

    def tearDown(self):
        for p in self._temp_paths:
            try:
                os.remove(p)
            except OSError:
                pass

    def _bank_file(self, data) -> str:
        path = _write_temp_json(data)
        self._temp_paths.append(path)
        return path

    def test_load_single_success(self):
        result = load_question_bank(self._bank_file(_single_bank()))
        self.assertTrue(result.success)
        self.assertEqual(result.bank_type, "single")
        self.assertIsNotNone(result.data)
        self.assertIn("数学", result.preview)
        self.assertEqual(result.error_type, "")
        self.assertIsNone(result.mismatch)

    def test_load_multiple_success(self):
        result = load_question_bank(self._bank_file(_multiple_bank()))
        self.assertTrue(result.success)
        self.assertEqual(result.bank_type, "multiple")
        self.assertIsNotNone(result.data)
        self.assertIn("课程数", result.preview)

    def test_load_invalid_json(self):
        # importer.import_from_file 内部已捕获 JSONDecodeError 并返回 False，
        # 因此 load_question_bank 走 ValueError → except Exception → error_type="other"。
        # （与原 _process 实际行为一致：非法 JSON 显示"读取文件失败"而非"JSON格式错误"。）
        result = load_question_bank(self._bank_file("{not valid json"))
        self.assertFalse(result.success)
        self.assertEqual(result.error_type, "other")
        self.assertTrue(result.error)

    def test_load_other_error_when_file_missing(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(path)  # 确保路径不存在
        result = load_question_bank(path)
        # importer.import_from_file 返回 False → load_question_bank raise ValueError → other
        self.assertFalse(result.success)
        self.assertEqual(result.error_type, "other")

    def test_load_course_mismatch(self):
        result = load_question_bank(
            self._bank_file(_single_bank(course_id="course-1")),
            selected_course={"courseID": "course-2", "courseName": "其他课"},
        )
        self.assertFalse(result.success)
        self.assertIsNotNone(result.mismatch)
        self.assertEqual(result.mismatch["bank_id"], "course-1")
        self.assertEqual(result.mismatch["selected_id"], "course-2")
        self.assertEqual(result.mismatch["selected_name"], "其他课")

    def test_load_course_match(self):
        result = load_question_bank(
            self._bank_file(_single_bank(course_id="course-1")),
            selected_course={"courseID": "course-1", "courseName": "数学"},
        )
        self.assertTrue(result.success)
        self.assertIsNone(result.mismatch)

    def test_load_skips_check_without_selected_course(self):
        result = load_question_bank(self._bank_file(_single_bank(course_id="course-1")))
        self.assertTrue(result.success)

    def test_load_uses_custom_course_keys(self):
        """认证端字段 eCourseID/lessonName 也能正确校验。"""
        result = load_question_bank(
            self._bank_file(_single_bank(course_id="course-1")),
            selected_course={"eCourseID": "course-2", "lessonName": "认证课"},
            course_id_key="eCourseID",
            course_name_key="lessonName",
        )
        self.assertFalse(result.success)
        self.assertIsNotNone(result.mismatch)
        self.assertEqual(result.mismatch["selected_id"], "course-2")
        self.assertEqual(result.mismatch["selected_name"], "认证课")


class ApplyBankResultTests(unittest.TestCase):
    def test_success_sets_data(self):
        result = BankLoadResult(success=True, data={"some": "bank"})
        view = _FakeView(initial="old")
        apply_bank_result(view, result)
        self.assertEqual(view.question_bank_data, {"some": "bank"})

    def test_mismatch_clears_data(self):
        result = BankLoadResult(
            success=False,
            mismatch={"selected_name": "a", "selected_id": "1", "bank_name": "b", "bank_id": "2"},
        )
        view = _FakeView(initial="old-bank")
        apply_bank_result(view, result)
        self.assertIsNone(view.question_bank_data)

    def test_json_error_preserves_existing_data(self):
        result = BankLoadResult(success=False, error_type="json", error="bad")
        view = _FakeView(initial="old-bank")
        apply_bank_result(view, result)
        self.assertEqual(view.question_bank_data, "old-bank")

    def test_other_error_preserves_existing_data(self):
        result = BankLoadResult(success=False, error_type="other", error="io")
        view = _FakeView(initial="old-bank")
        apply_bank_result(view, result)
        self.assertEqual(view.question_bank_data, "old-bank")


if __name__ == "__main__":
    unittest.main()
