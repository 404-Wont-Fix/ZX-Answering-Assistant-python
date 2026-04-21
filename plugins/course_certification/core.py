"""
课程认证插件核心业务逻辑

实现课程认证的主要功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.certification.workflow import get_access_token, start_answering, import_question_bank


class Workflow:
    """课程认证工作流"""

    def __init__(self, context):
        """
        初始化工作流

        Args:
            context: PluginContext 实例，包含注入的依赖
        """
        self.context = context
        # ✅ 正确：使用注入的依赖
        self.api_client = context.api_client
        self.browser_manager = context.browser_manager
        self.settings_manager = context.settings_manager

        # 工作流状态
        self.access_token = None
        self.question_bank = None

    def execute(self, question_bank_path: str = None):
        """
        执行课程认证工作流

        Args:
            question_bank_path: 题库文件路径（可选）

        Returns:
            dict: 工作流执行结果
        """
        print(f"[CourseCertification Plugin] 执行课程认证工作流")

        result = {
            'success': False,
            'message': '',
            'token_obtained': False,
            'question_bank_loaded': False,
        }

        try:
            # 1. 获取访问令牌
            print(f"[CourseCertification Plugin] 获取教师访问令牌...")
            self.access_token = get_access_token()

            if self.access_token:
                result['token_obtained'] = True
                result['message'] = "成功获取教师访问令牌"
                print(f"[CourseCertification Plugin] {result['message']}")
            else:
                result['message'] = "获取教师访问令牌失败"
                print(f"[CourseCertification Plugin] {result['message']}")
                return result

            # 2. 加载题库（如果提供）
            if question_bank_path:
                print(f"[CourseCertification Plugin] 加载题库: {question_bank_path}")
                self.question_bank = import_question_bank(question_bank_path)

                if self.question_bank:
                    result['question_bank_loaded'] = True
                    result['message'] += f"\n成功加载题库，共 {len(self.question_bank)} 道题"
                    print(f"[CourseCertification Plugin] 题库加载成功")
                else:
                    result['message'] += "\n加载题库失败"
                    print(f"[CourseCertification Plugin] 题库加载失败")
                    return result

            # 3. 开始答题（如果有令牌）
            if self.access_token:
                print(f"[CourseCertification Plugin] 开始课程认证答题...")
                # 这里可以调用 start_answering() 开始实际答题
                # 但需要用户在GUI中触发
                result['success'] = True
                result['message'] += "\n准备就绪，可以开始答题"
                return result

        except Exception as e:
            error_msg = f"执行课程认证工作流时出错: {str(e)}"
            result['message'] = error_msg
            print(f"[CourseCertification Plugin] {error_msg}")
            import traceback
            traceback.print_exc()
            return result

    def start_answering_with_bank(self):
        """
        使用题库开始答题

        Returns:
            dict: 答题结果
        """
        if not self.access_token:
            return {
                'success': False,
                'message': '请先获取访问令牌'
            }

        if not self.question_bank:
            return {
                'success': False,
                'message': '请先加载题库'
            }

        try:
            result = start_answering(self.question_bank)
            return {
                'success': True,
                'message': '答题完成',
                'result': result
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'答题失败: {str(e)}'
            }

    def load_question_bank(self, file_path: str):
        """
        加载题库文件

        Args:
            file_path: 题库文件路径

        Returns:
            bool: 是否成功
        """
        try:
            self.question_bank = import_question_bank(file_path)
            return self.question_bank is not None
        except Exception as e:
            print(f"[CourseCertification Plugin] 加载题库失败: {e}")
            return False
