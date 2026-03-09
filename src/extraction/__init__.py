"""
提取模块

包含答案提取、导出和导入功能。
"""

# 延迟导入以避免循环依赖

def get_extractor():
    """获取 Extractor 类（延迟导入）"""
    from src.extraction.extractor import Extractor
    return Extractor

# 为了向后兼容，仍然提供直接导入
from src.extraction.extractor import Extractor, extract_course_answers, extract_questions, extract_single_course
from src.extraction.exporter import DataExporter
from src.extraction.importer import QuestionBankImporter
from src.extraction.file_handler import FileHandler

__all__ = [
    'Extractor', 'extract_course_answers', 'extract_questions', 'extract_single_course',
    'DataExporter', 'QuestionBankImporter', 'FileHandler',
    'get_extractor',
]
