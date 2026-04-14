"""
ZX Answering Assistant - 云考试数据模型

定义云考试模块使用的数据结构
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class QuestionOption:
    """题目选项"""
    option_id: str  # 选项ID
    option_content: str  # 选项内容
    is_correct: bool = False  # 是否正确答案（从题库获取）
    option_order: int = 0  # 选项顺序

    def __repr__(self) -> str:
        return f"QuestionOption(id={self.option_id[:8]}..., content={self.option_content[:20]}...)"


@dataclass
class ExamQuestion:
    """考试题目"""
    question_id: str  # 题目ID
    question_title: str  # 题目标题
    question_type: int = 0  # 题型（0=单选，1=多选等）
    difficulty: int = 0  # 难度
    score: float = 0.0  # 分值
    options: List[QuestionOption] = field(default_factory=list)  # 选项列表
    student_answer_id: Optional[str] = None  # 学生已提交的答案ID
    is_answered: bool = False  # 是否已答题

    def __repr__(self) -> str:
        return f"ExamQuestion(id={self.question_id[:8]}..., title={self.question_title[:20]}...)"

    def get_correct_answer_id(self) -> Optional[str]:
        """
        从题库选项中获取正确答案ID

        Returns:
            Optional[str]: 正确答案的选项ID，如果未标记则返回None
        """
        for option in self.options:
            if option.is_correct:
                return option.option_id
        return None


@dataclass
class ExamPaper:
    """试卷"""
    exp_id: str  # 考试ID（expID）
    exam_member_id: Optional[str] = None  # 考试成员ID（提交答案时需要）
    questions: List[ExamQuestion] = field(default_factory=list)  # 题目列表
    raw_data: Optional[Dict[str, Any]] = None  # 原始API响应数据

    # ⚠️ TODO: exam_member_id 获取方式待确定
    # 该字段是提交答案的必需参数，但当前不知道如何获取
    # 可能需要从考试页面的某个API响应、本地存储或DOM中提取

    def __repr__(self) -> str:
        return f"ExamPaper(exp_id={self.exp_id[:8]}..., questions={len(self.questions)})"

    def get_question_by_id(self, question_id: str) -> Optional[ExamQuestion]:
        """
        根据题目ID查找题目

        Args:
            question_id: 题目ID

        Returns:
            Optional[ExamQuestion]: 题目对象，如果未找到则返回None
        """
        for question in self.questions:
            if question.question_id == question_id:
                return question
        return None

    def get_answered_questions_count(self) -> int:
        """
        获取已答题数量

        Returns:
            int: 已答题数量
        """
        return sum(1 for q in self.questions if q.is_answered)

    def get_total_questions_count(self) -> int:
        """
        获取总题数

        Returns:
            int: 总题数
        """
        return len(self.questions)
