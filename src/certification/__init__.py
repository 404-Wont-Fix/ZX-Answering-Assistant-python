"""
认证模块

包含课程认证功能。
"""

# 延迟导入以避免循环依赖

def get_api_course_answer():
    """获取 APICourseAnswer 类（延迟导入）"""
    from src.certification.api_answer import APICourseAnswer
    return APICourseAnswer

# 为了向后兼容，仍然提供直接导入
from src.certification.workflow import (
    import_question_bank,
    get_question_bank,
    hello_world,
)
from src.certification.api_answer import APICourseAnswer

__all__ = [
    'import_question_bank', 'get_question_bank', 'hello_world', 'APICourseAnswer',
    'get_api_course_answer',
]
