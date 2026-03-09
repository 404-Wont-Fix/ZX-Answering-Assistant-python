"""
ZX Answering Assistant - 源代码模块

此模块提供向后兼容的导入，同时支持新的目录结构。
"""

# ============================================================================
# 向后兼容的导入（保持旧代码正常工作）
# ============================================================================

# 核心模块
from src.core.browser import BrowserManager, get_browser_manager, BrowserType
from src.core.api_client import APIClient, get_api_client
from src.core.config import SettingsManager, get_settings_manager, APIRateLevel
from src.core.app_state import AppState, get_app_state

# 认证模块（只导出实际存在的函数）
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
from src.auth.teacher import get_access_token as teacher_get_access_token
from src.auth.token_manager import TokenManager, get_token_manager

# 答题模块
from src.answering.browser_answer import AutoAnswer
from src.answering.api_answer import APIAutoAnswer

# 提取模块
from src.extraction.extractor import Extractor, extract_course_answers, extract_questions, extract_single_course
from src.extraction.exporter import DataExporter
from src.extraction.importer import QuestionBankImporter
from src.extraction.file_handler import FileHandler

# 认证模块（课程认证）
from src.certification.workflow import import_question_bank, get_question_bank
from src.certification.api_answer import APICourseAnswer

# 工具模块
from src.utils.retry import retry, RetryConfig, retry_on_exception

__all__ = [
    # 核心模块
    'BrowserManager', 'get_browser_manager', 'BrowserType',
    'APIClient', 'get_api_client',
    'SettingsManager', 'get_settings_manager', 'APIRateLevel',
    'AppState', 'get_app_state',

    # 认证模块
    'teacher_get_access_token',
    'get_student_access_token', 'get_student_access_token_with_credentials',
    'get_student_courses', 'get_uncompleted_chapters', 'navigate_to_course',
    'close_browser', 'get_course_progress_from_page', 'get_browser_page',
    'get_cached_access_token', 'set_access_token',
    'TokenManager', 'get_token_manager',

    # 答题模块
    'AutoAnswer', 'APIAutoAnswer',

    # 提取模块
    'Extractor', 'extract_course_answers', 'extract_questions', 'extract_single_course',
    'DataExporter', 'QuestionBankImporter', 'FileHandler',

    # 认证模块（课程认证）
    'import_question_bank', 'get_question_bank', 'APICourseAnswer',

    # 工具模块
    'retry', 'RetryConfig', 'retry_on_exception',
]
