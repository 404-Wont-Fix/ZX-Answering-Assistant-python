"""成绩导出（openpyxl 写盘，纯 I/O，无 UI 依赖）。

从 LazyAIGradingView._on_export_grades 的 openpyxl 部分抽出。
FilePicker 协程（ft.FilePicker().save_file）仍由 view 处理（属 UI 控件）；
view 拿到保存路径后调 ExcelExporter.export(list, path)。
"""


class ExcelExporter:
    """成绩导出（openpyxl 写盘）。"""

    @staticmethod
    def export(graded_list, save_path: str) -> None:
        """按 pro_score 降序写 姓名/分数 两列到 xlsx 文件。

        Args:
            graded_list: 已评分学生列表（需有 student_name/pro_score 属性）。
            save_path: 保存路径。
        """
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "成绩"

        # 表头
        ws.append(["姓名", "分数"])

        # 数据行：按分数降序
        for r in sorted(graded_list, key=lambda x: x.pro_score, reverse=True):
            ws.append([r.student_name, r.pro_score])

        # 列宽
        ws.column_dimensions["A"].width = 20
        ws.column_dimensions["B"].width = 12

        wb.save(save_path)
