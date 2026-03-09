"""
答题模块

包含浏览器答题和API答题功能。
"""

# 延迟导入以避免循环依赖

def get_auto_answer():
    """获取 AutoAnswer 类（延迟导入）"""
    from src.answering.browser_answer import AutoAnswer
    return AutoAnswer

def get_api_auto_answer():
    """获取 APIAutoAnswer 类（延迟导入）"""
    from src.answering.api_answer import APIAutoAnswer
    return APIAutoAnswer

# 为了向后兼容，仍然提供直接导入
from src.answering.browser_answer import AutoAnswer
from src.answering.api_answer import APIAutoAnswer

__all__ = ['AutoAnswer', 'APIAutoAnswer', 'get_auto_answer', 'get_api_auto_answer']
