"""
云考试插件核心业务逻辑

实现云考试的主要功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.cloud_exam.workflow import CloudExamWorkflow


class Workflow:
    """云考试工作流"""

    def __init__(self, context):
        """
        初始化工作流

        Args:
            context: PluginContext 实例，包含注入的依赖
        """
        self.context = context
        # ✅ 正确：使用注入的 API 客户端
        self.api_client = context.api_client
        # ✅ 正确：使用注入的浏览器管理器
        self.browser_manager = context.browser_manager

        # 创建云考试工作流实例
        self.workflow = CloudExamWorkflow()

    def execute(self, exp_id: str = None, question_bank_path: str = None):
        """
        执行云考试工作流

        Args:
            exp_id: 考试ID（可选）
            question_bank_path: 题库文件路径（可选）

        Returns:
            dict: 工作流执行结果
        """
        print(f"[CloudExam Plugin] 执行云考试工作流")

        result = {
            'success': False,
            'message': '',
            'exam_paper': None,
            'match_rate': 0,
        }

        try:
            # 如果提供了exp_id，获取考试试卷
            if exp_id:
                print(f"[CloudExam Plugin] 获取考试试卷: exp_id={exp_id}")
                exam_paper = self.workflow.capture_exam_paper(exp_id)

                if exam_paper:
                    result['exam_paper'] = exam_paper
                    result['message'] = f"成功获取考试试卷，共 {len(exam_paper.questions)} 道题"
                    print(f"[CloudExam Plugin] {result['message']}")
                else:
                    result['message'] = "获取考试试卷失败"
                    print(f"[CloudExam Plugin] {result['message']}")
                    return result

            # 如果提供了题库，加载并验证
            if question_bank_path and exp_id:
                print(f"[CloudExam Plugin] 加载题库: {question_bank_path}")
                question_bank = self.workflow.load_question_bank(question_bank_path)

                if question_bank and result['exam_paper']:
                    # 验证题库匹配率
                    match_rate = self.workflow.validate_question_bank(result['exam_paper'])
                    result['match_rate'] = match_rate

                    if match_rate >= 0.3:  # 30%匹配率阈值
                        result['message'] += f"\n题库匹配率: {match_rate*100:.1f}% (满足要求)"
                        print(f"[CloudExam Plugin] 题库验证通过，匹配率: {match_rate*100:.1f}%")
                    else:
                        result['message'] += f"\n题库匹配率: {match_rate*100:.1f}% (不足30%，请使用完整题库)"
                        print(f"[CloudExam Plugin] 题库匹配率不足: {match_rate*100:.1f}%")
                        return result
                elif question_bank_path:
                    result['message'] = "加载题库失败"
                    print(f"[CloudExam Plugin] {result['message']}")
                    return result

            result['success'] = True
            return result

        except Exception as e:
            error_msg = f"执行云考试工作流时出错: {str(e)}"
            result['message'] = error_msg
            print(f"[CloudExam Plugin] {error_msg}")
            import traceback
            traceback.print_exc()
            return result

    def get_exam_paper(self, exp_id: str):
        """
        获取考试试卷

        Args:
            exp_id: 考试ID

        Returns:
            ExamPaper: 考试试卷对象
        """
        return self.workflow.capture_exam_paper(exp_id)

    def load_question_bank(self, file_path: str):
        """
        加载题库文件

        Args:
            file_path: 题库文件路径

        Returns:
            dict: 题库数据
        """
        return self.workflow.load_question_bank(file_path)

    def inject_answers(self, exam_member_id: str, exam_paper, answer_map):
        """
        注入答案

        Args:
            exam_member_id: 考试成员ID
            exam_paper: 考试试卷对象
            answer_map: 答案映射

        Returns:
            bool: 是否成功
        """
        return self.workflow.inject_answers(exam_member_id)
