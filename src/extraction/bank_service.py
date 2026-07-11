"""题库导入业务服务（纯业务，无 UI 依赖）。

封装对 QuestionBankImporter(src/extraction/importer.py) 的编排：
导入文件 + 生成统计预览 + 校验课程ID匹配。

供 AnsweringView / CourseCertificationView 的 _process_selected_json_file 复用，
消除两处 ~450 行的逐字重复。对话框展示由 src/ui/components.show_bank_load_result_dialog 负责。
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.extraction.importer import QuestionBankImporter


@dataclass
class BankLoadResult:
    """题库导入结果。"""

    success: bool
    file_name: str = ""
    file_path: str = ""
    bank_type: Optional[str] = None  # "single" / "multiple"
    data: Optional[dict] = None  # 题库原始数据（importer.data）
    preview: str = ""  # 统计预览文本
    error_type: str = ""  # "json" / "other" / ""
    error: str = ""  # 错误信息
    mismatch: Optional[dict] = None  # 课程不匹配信息 {selected_name, selected_id, bank_name, bank_id}


def _build_preview(importer: QuestionBankImporter, bank_type: Optional[str]) -> str:
    """生成统计预览文本（提取自两处 _process 的逐字相同部分）。"""
    if bank_type == "single":
        parsed = importer.parse_single_course()
        stats = parsed["statistics"] if parsed else {}
        return f"""
📊 题库统计：
  班级：{parsed['class']['name'] if parsed else '未知'}
  课程：{parsed['course']['courseName'] if parsed else '未知'}
  章节数：{stats.get('totalChapters', 0)}
  知识点数：{stats.get('totalKnowledges', 0)}
  题目数：{stats.get('totalQuestions', 0)}
  选项数：{stats.get('totalOptions', 0)}
"""
    if bank_type == "multiple":
        parsed = importer.parse_multiple_courses()
        stats = parsed["statistics"] if parsed else {}
        return f"""
📊 题库统计：
  班级：{parsed['class']['name'] if parsed else '未知'}
  课程数：{stats.get('totalCourses', 0)}
  章节数：{stats.get('totalChapters', 0)}
  知识点数：{stats.get('totalKnowledges', 0)}
  题目数：{stats.get('totalQuestions', 0)}
  选项数：{stats.get('totalOptions', 0)}
"""
    return "⚠️ 未知的题库类型"


def load_question_bank(
    file_path: str,
    *,
    selected_course: Optional[dict] = None,
    course_id_key: str = "courseID",
    course_name_key: str = "courseName",
) -> BankLoadResult:
    """导入题库文件 + 生成统计预览 + 校验课程ID匹配。

    纯业务函数，无 UI 依赖。捕获 JSONDecodeError/Exception 并分类填入 result。

    Args:
        file_path: JSON 题库文件路径。
        selected_course: 当前选中课程（可选）。提供且题库为 single 类型时校验课程ID。
        course_id_key: selected_course 中课程ID的字段名
            （学生端用 courseID，认证端用 eCourseID）。
        course_name_key: selected_course 中课程名的字段名
            （学生端用 courseName，认证端用 lessonName）。

    Returns:
        BankLoadResult：success=True 表示导入成功且（若校验）匹配；
        success=False + mismatch 非空表示课程不匹配；
        success=False + error_type 表示导入异常（json/other）。
    """
    file_name = Path(file_path).name

    try:
        importer = QuestionBankImporter()
        success = importer.import_from_file(file_path)
        if not success:
            raise ValueError("无法导入题库文件")

        bank_type = importer.get_bank_type()
        print("\n" + importer.format_output())
        preview = _build_preview(importer, bank_type)

        # 课程ID校验（仅 single 类型 + 提供了 selected_course 时）
        if selected_course and bank_type == "single":
            parsed = importer.parse_single_course()
            bank_course_id = ""
            bank_course_name = ""
            if parsed and "course" in parsed:
                bank_course_id = parsed["course"].get("courseID", "")
                bank_course_name = parsed["course"].get("courseName", "")

            selected_course_id = selected_course.get(course_id_key, "")
            selected_course_name = selected_course.get(course_name_key, "未知课程")

            print(f"DEBUG: 题库课程ID = {bank_course_id}")
            print(f"DEBUG: 选择课程ID = {selected_course_id}")

            if bank_course_id and selected_course_id and bank_course_id != selected_course_id:
                print("❌ 题库课程不匹配")
                return BankLoadResult(
                    success=False,
                    file_path=file_path, file_name=file_name,
                    bank_type=bank_type,
                    data=importer.data,
                    preview=preview,
                    mismatch={
                        "selected_name": selected_course_name,
                        "selected_id": selected_course_id,
                        "bank_name": bank_course_name,
                        "bank_id": bank_course_id,
                    },
                )

        print(f"✅ 成功加载JSON题库: {file_name}")
        return BankLoadResult(
            success=True,
            file_path=file_path, file_name=file_name,
            bank_type=bank_type,
            data=importer.data,
            preview=preview,
        )

    except Exception as ex:
        print(f"❌ 读取文件失败: {ex}")
        return BankLoadResult(
            success=False,
            file_path=file_path, file_name=file_name,
            error_type="other",
            error=str(ex),
        )


def apply_bank_result(view, result: BankLoadResult) -> None:
    """根据导入结果更新 view.question_bank_data。

    精确还原两处原 _process 的状态语义：
    - 成功：存入新数据；
    - 课程不匹配：清除题库数据（原逻辑"先存后清"，含已有数据）；
    - JSON/其他错误：保持原值不动（异常前未赋值）。

    两个 View 的题库属性同名（question_bank_data），故可共享。
    """
    if result.success:
        view.question_bank_data = result.data
    elif result.mismatch is not None:
        view.question_bank_data = None
    # error_type 为 json/other 时保持原值
