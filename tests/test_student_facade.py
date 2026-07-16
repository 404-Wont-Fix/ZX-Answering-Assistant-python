"""src.auth.student façade 拆分后的导入冒烟测试。

验证 student.py 拆出 _student_courses/_student_browser_health 后，
17 个公开符号仍可从 src.auth.student 导入（façade 兼容，零调用方改动）。
"""

import unittest


# 必须保持可从 src.auth.student 导入的符号全集（被 __init__/answering_view/cloud_exam 引用）
PUBLIC_SYMBOLS = [
    "get_student_access_token",
    "get_student_access_token_with_credentials",
    "get_student_courses",
    "get_uncompleted_chapters",
    "navigate_to_course",
    "close_browser",
    "get_course_progress_from_page",
    "get_browser_page",
    "get_cached_access_token",
    "set_access_token",
    "get_access_token_from_browser",
    "is_browser_alive",
    "clear_access_token",
    "cleanup_browser",
    "ensure_browser_alive",
    "restart_browser",
    "check_and_recover_browser",
]


class StudentFacadeSmokeTest(unittest.TestCase):
    def test_student_module_importable(self):
        from src.auth import student
        self.assertIsNotNone(student)

    def test_public_symbols_available(self):
        from src.auth import student
        for name in PUBLIC_SYMBOLS:
            self.assertTrue(
                hasattr(student, name),
                f"student.{name} 缺失（façade re-export 失败）",
            )

    def test_submodule_courses_importable(self):
        from src.auth._student_courses import get_student_courses, get_uncompleted_chapters
        self.assertTrue(callable(get_student_courses))
        self.assertTrue(callable(get_uncompleted_chapters))

    def test_submodule_browser_health_importable(self):
        from src.auth._student_browser_health import (
            check_and_recover_browser,
            cleanup_browser,
            close_browser,
            ensure_browser_alive,
            is_browser_alive,
        )
        self.assertTrue(callable(is_browser_alive))
        self.assertTrue(callable(cleanup_browser))

    def test_auth_init_reexports(self):
        """src.auth.__init__ 导出的符号仍可用（间接验证 façade）。"""
        from src.auth import (
            close_browser,
            get_browser_page,
            get_cached_access_token,
            get_course_progress_from_page,
            get_student_access_token,
            get_student_courses,
            get_uncompleted_chapters,
            navigate_to_course,
            set_access_token,
        )
        self.assertTrue(callable(get_student_access_token))
        self.assertTrue(callable(get_student_courses))


if __name__ == "__main__":
    unittest.main()
