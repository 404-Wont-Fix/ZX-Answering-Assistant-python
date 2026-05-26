"""
ZX Answering Assistant - 源代码模块

此模块提供向后兼容的导入，同时避免在包初始化阶段加载浏览器等重依赖。
"""

from importlib import import_module


_EXPORTS = {
    # 核心模块
    'BrowserManager': ('src.core.browser', 'BrowserManager'),
    'get_browser_manager': ('src.core.browser', 'get_browser_manager'),
    'BrowserType': ('src.core.browser', 'BrowserType'),
    'APIClient': ('src.core.api_client', 'APIClient'),
    'get_api_client': ('src.core.api_client', 'get_api_client'),
    'SettingsManager': ('src.core.config', 'SettingsManager'),
    'get_settings_manager': ('src.core.config', 'get_settings_manager'),
    'APIRateLevel': ('src.core.config', 'APIRateLevel'),
    'AppState': ('src.core.app_state', 'AppState'),
    'get_app_state': ('src.core.app_state', 'get_app_state'),

    # 认证模块
    'teacher_get_access_token': ('src.auth.teacher', 'get_access_token'),
    'get_student_access_token': ('src.auth.student', 'get_student_access_token'),
    'get_student_access_token_with_credentials': ('src.auth.student', 'get_student_access_token_with_credentials'),
    'get_student_courses': ('src.auth.student', 'get_student_courses'),
    'get_uncompleted_chapters': ('src.auth.student', 'get_uncompleted_chapters'),
    'navigate_to_course': ('src.auth.student', 'navigate_to_course'),
    'close_browser': ('src.auth.student', 'close_browser'),
    'get_course_progress_from_page': ('src.auth.student', 'get_course_progress_from_page'),
    'get_browser_page': ('src.auth.student', 'get_browser_page'),
    'get_cached_access_token': ('src.auth.student', 'get_cached_access_token'),
    'set_access_token': ('src.auth.student', 'set_access_token'),
    'TokenManager': ('src.auth.token_manager', 'TokenManager'),
    'get_token_manager': ('src.auth.token_manager', 'get_token_manager'),

    # 答题模块
    'AutoAnswer': ('src.answering.browser_answer', 'AutoAnswer'),
    'APIAutoAnswer': ('src.answering.api_answer', 'APIAutoAnswer'),

    # 提取模块
    'Extractor': ('src.extraction.extractor', 'Extractor'),
    'extract_course_answers': ('src.extraction.extractor', 'extract_course_answers'),
    'extract_questions': ('src.extraction.extractor', 'extract_questions'),
    'extract_single_course': ('src.extraction.extractor', 'extract_single_course'),
    'DataExporter': ('src.extraction.exporter', 'DataExporter'),
    'QuestionBankImporter': ('src.extraction.importer', 'QuestionBankImporter'),
    'FileHandler': ('src.extraction.file_handler', 'FileHandler'),

    # 认证模块（课程认证）
    'import_question_bank': ('src.certification.workflow', 'import_question_bank'),
    'get_question_bank': ('src.certification.workflow', 'get_question_bank'),
    'APICourseAnswer': ('src.certification.api_answer', 'APICourseAnswer'),

    # 工具模块
    'retry': ('src.utils.retry', 'retry'),
    'RetryConfig': ('src.utils.retry', 'RetryConfig'),
    'retry_on_exception': ('src.utils.retry', 'retry_on_exception'),
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    """按需加载兼容导出，避免 import src 时触发重依赖导入。"""
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = _EXPORTS[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value
