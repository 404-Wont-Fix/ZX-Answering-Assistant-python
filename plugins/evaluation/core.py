"""
评估出题插件核心业务逻辑

实现评估出题的主要功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.extraction.extractor import Extractor
from src.extraction.importer import QuestionBankImporter
from src.extraction.exporter import DataExporter


class Workflow:
    """评估出题工作流"""

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

    def execute(self, export_path: str = None):
        """
        执行评估出题工作流（提取答案）

        Args:
            export_path: 导出文件路径（可选）

        Returns:
            dict: 工作流执行结果
        """
        print(f"[Evaluation Plugin] 执行评估出题工作流")

        result = {
            'success': False,
            'message': '',
            'courses_extracted': 0,
            'export_path': '',
        }

        try:
            # 创建提取器并执行提取
            print(f"[Evaluation Plugin] 初始化提取器...")
            extractor = Extractor()

            # 执行提取流程
            print(f"[Evaluation Plugin] 开始提取答案...")
            extracted_data = extractor.run_full_extraction()

            if extracted_data:
                result['success'] = True
                result['courses_extracted'] = len(extracted_data.get('course_list', []))
                result['message'] = f"成功提取 {result['courses_extracted']} 个课程的答案"
                print(f"[Evaluation Plugin] {result['message']}")

                # 如果提供了导出路径，导出数据
                if export_path:
                    print(f"[Evaluation Plugin] 导出答案到: {export_path}")
                    exporter = DataExporter()
                    exporter.export_full_data(extracted_data, export_path)
                    result['export_path'] = export_path
                    result['message'] += f"\n已导出到: {export_path}"
                else:
                    # 默认导出路径
                    default_path = "exported_answers.json"
                    print(f"[Evaluation Plugin] 导出答案到: {default_path}")
                    exporter = DataExporter()
                    exporter.export_full_data(extracted_data, default_path)
                    result['export_path'] = default_path
                    result['message'] += f"\n已导出到: {default_path}"

                return result
            else:
                result['message'] = "提取答案失败"
                print(f"[Evaluation Plugin] {result['message']}")
                return result

        except Exception as e:
            error_msg = f"执行评估出题工作流时出错: {str(e)}"
            result['message'] = error_msg
            print(f"[Evaluation Plugin] {error_msg}")
            import traceback
            traceback.print_exc()
            return result

    def import_question_bank(self, file_path: str):
        """
        导入题库文件

        Args:
            file_path: 题库文件路径

        Returns:
            dict: 导入结果
        """
        try:
            print(f"[Evaluation Plugin] 导入题库: {file_path}")
            importer = QuestionBankImporter()
            question_bank = importer.import_from_file(file_path)

            if question_bank:
                return {
                    'success': True,
                    'message': f"成功导入题库，共 {len(question_bank)} 道题",
                    'question_bank': question_bank
                }
            else:
                return {
                    'success': False,
                    'message': '导入题库失败'
                }
        except Exception as e:
            return {
                'success': False,
                'message': f'导入题库出错: {str(e)}'
            }

    def export_questions(self, data, format: str = 'json', output_path: str = None):
        """
        导出试题

        Args:
            data: 要导出的数据
            format: 导出格式（json、默认json）
            output_path: 输出文件路径

        Returns:
            dict: 导出结果
        """
        try:
            print(f"[Evaluation Plugin] 导出试题，格式: {format}")

            if not output_path:
                output_path = f"exported_questions.{format}"

            exporter = DataExporter()
            exporter.export_full_data(data, output_path)

            return {
                'success': True,
                'message': f"成功导出到: {output_path}",
                'output_path': output_path
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'导出失败: {str(e)}'
            }
