"""
教师端答案提取独立脚本
用于在独立进程中运行教师端答案提取功能，避免与学生端Playwright冲突
"""

import sys
import os

# 设置标准输出编码为UTF-8，支持emoji
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
    except:
        # 如果失败，使用环境变量
        os.environ['PYTHONIOENCODING'] = 'utf-8'
else:
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# 添加项目根目录到路径（确保能导入src模块）
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.extraction.extractor import extract_course_answers


def main():
    """
    主函数：从命令行参数获取课程ID并提取答案
    """
    if len(sys.argv) < 2:
        print("用法: python -m src.extract_answers <course_id>")
        sys.exit(1)
    
    course_id = sys.argv[1]
    print(f"📚 开始提取课程答案，课程ID: {course_id}")
    
    # 调用答案提取函数
    extracted_data = extract_course_answers(course_id=course_id)
    
    if extracted_data:
        print("\n✅ 答案提取成功！")
        
        # 导出答案数据
        from src.extraction.exporter import DataExporter
        exporter = DataExporter()
        try:
            course_name = extracted_data.get("course_info", {}).get("courseID", course_id)
            filename = f"{course_name}_答案"
            output_file = exporter.export_data(extracted_data, filename)
            print(f"✅ 答案已导出到：{output_file}")
        except Exception as e:
            print(f"⚠️  导出答案失败：{str(e)}")
        
        sys.exit(0)
    else:
        print("\n❌ 答案提取失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
