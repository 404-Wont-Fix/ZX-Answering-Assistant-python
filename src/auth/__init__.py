"""
认证模块

包含学生、教师和课程认证相关的登录和token管理功能。
"""

# Token管理
from src.auth.token_manager import TokenManager, get_token_manager

# 学生登录（只导出实际存在的函数）
from src.auth.student import (
    get_student_access_token,
    get_student_access_token_with_credentials,
    get_student_courses,
    get_uncompleted_chapters,
    navigate_to_course,
    close_browser,
    get_course_progress_from_page,
    get_browser_page,
    get_cached_access_token,
    set_access_token,
)

# 教师登录
from src.auth.teacher import get_access_token as teacher_get_access_token

__all__ = [
    'TokenManager', 'get_token_manager',
    'teacher_get_access_token',
    'get_student_access_token', 'get_student_access_token_with_credentials',
    'get_student_courses', 'get_uncompleted_chapters', 'navigate_to_course',
    'close_browser', 'get_course_progress_from_page', 'get_browser_page',
    'get_cached_access_token', 'set_access_token',
]
