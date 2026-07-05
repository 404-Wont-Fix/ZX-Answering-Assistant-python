"""
文本处理工具函数

提供题库文本标准化和章节提取等共享功能。
"""

import html
import re
from typing import Any, Dict, List


def normalize_text(text: str, preserve_angles: bool = False) -> str:
    """
    标准化文本，用于题库匹配。

    Args:
        text: 待标准化的文本
        preserve_angles: 是否保留尖括号内容（如 <Limit>）并过滤特殊字符。
            设为 True 时行为与 browser_answer.py 的原始逻辑一致。

    Returns:
        标准化后的文本
    """
    if not text:
        return ""

    # 解码HTML实体
    text = html.unescape(text)

    # 移除HTML注释（支持跨行）
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)

    if preserve_angles:
        # 保留尖括号内的内容（如 <Limit>, <Allow>），移除其他HTML标签
        angle_bracket_contents = re.findall(r'<([^/>]+)>', text)
        text = re.sub(r'<[^>]+>', ' ', text)

        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)

        # 移除特殊字符（保留中文、英文、数字、常用标点和代码符号）
        # 代码符号：{}[]().,;=+*/<>!?
        pattern = r'[^一-龥a-zA-Z0-9\s\.,;:!?()（）【】《》、“”‘’[]{}+=*/<>-]'
        text = re.sub(pattern, '', text)

        text = text.strip()

        # 如果提取出的文本为空，但原始内容中有尖括号内容，尝试使用这些内容
        if not text and angle_bracket_contents:
            text = ' '.join(angle_bracket_contents)

        return text
    else:
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)

        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)

        return text.strip()


def get_chapters(question_bank: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从题库数据中提取章节列表。

    支持两种题库格式：
    - 单课程格式：question_bank["class"]["course"]["chapters"]
    - 多课程格式：question_bank["chapters"]

    Args:
        question_bank: 题库字典数据

    Returns:
        章节列表，若无法提取则返回空列表
    """
    if not question_bank:
        return []

    if "class" in question_bank and "course" in question_bank["class"]:
        return question_bank["class"]["course"].get("chapters", [])
    elif "chapters" in question_bank:
        return question_bank["chapters"]

    return []
