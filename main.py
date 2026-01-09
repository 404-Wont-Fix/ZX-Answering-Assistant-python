"""
ZX Answering Assistant - 主程序入口
智能答题助手系统
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入登录模块和题目提取模块
from src.teacher_login import get_access_token
from src.student_login import get_student_access_token, get_student_access_token_with_credentials, get_student_courses, get_uncompleted_chapters
from src.extract import extract_questions, extract_single_course
from src.export import DataExporter
from src.question_bank_importer import QuestionBankImporter


# 全局变量，存储最后一次提取的数据
last_extracted_data = None


def main():
    while True:
        print("欢迎使用智能答题助手系统")
        print("1. 开始答题")
        print("2. 题目抓取")
        print("3. 设置")
        print("4. 退出系统")
        choice = input("请选择操作：")
        if choice == "1":
            # 调用开始答题功能
            print("开始答题功能")
            print("1. 开始答题")
            print("2. 获取access_token")
            print("3. 单个课程答题")
            print("4. 题库导入")
            print("5. 返回")
            sub_choice = input("请选择：")
            
            if sub_choice == "1":
                # 批量答题 - 获取token并显示课程列表
                print("正在获取学生端access_token...")
                access_token = get_student_access_token()
                if access_token:
                    print(f"\n✅ 获取学生端access_token成功！")
                    print(f"access_token: {access_token}")
                    print(f"token类型: Bearer")
                    print(f"有效期: 5小时 (18000秒)")

                    # 获取课程列表
                    print("\n正在获取课程列表...")
                    courses = get_student_courses(access_token)
                    if courses:
                        # 遍历每个课程，获取未完成的知识点以确定完成情况
                        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                        print("📚 课程列表")
                        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

                        courses_with_status = []
                        for course in courses:
                            course_id = course.get('courseID')
                            course_name = course.get('courseName', 'N/A')
                            teacher_name = course.get('teacherName', 'N/A')
                            class_name = course.get('className', 'N/A')

                            # 获取未完成的知识点
                            uncompleted_chapters = []
                            if course_id:
                                uncompleted_chapters = get_uncompleted_chapters(access_token, course_id)

                            # 判断完成状态
                            if uncompleted_chapters is not None and len(uncompleted_chapters) == 0:
                                completion_status = "✅ 已完成"
                                uncompleted_count = 0
                            elif uncompleted_chapters is not None:
                                completion_status = f"⏳ 未完成 ({len(uncompleted_chapters)} 个知识点)"
                                uncompleted_count = len(uncompleted_chapters)
                            else:
                                completion_status = "❓ 状态未知"
                                uncompleted_count = -1

                            courses_with_status.append({
                                'course': course,
                                'course_id': course_id,
                                'course_name': course_name,
                                'teacher_name': teacher_name,
                                'class_name': class_name,
                                'completion_status': completion_status,
                                'uncompleted_count': uncompleted_count,
                                'uncompleted_chapters': uncompleted_chapters
                            })

                        # 显示课程列表
                        for i, course_info in enumerate(courses_with_status, 1):
                            print(f"{i}. 【{course_info['course_name']}】")
                            print(f"   👤 指导老师: {course_info['teacher_name']}")
                            print(f"   🏫 班级: {course_info['class_name']}")
                            print(f"   📊 完成情况: {course_info['completion_status']}")
                            print()

                        # 让用户选择查看具体课程
                        while True:
                            choice_input = input("请输入课程编号查看详情（输入0返回）: ").strip()
                            if choice_input == "0":
                                print("返回上级菜单")
                                break

                            try:
                                choice_idx = int(choice_input) - 1
                                if 0 <= choice_idx < len(courses_with_status):
                                    selected_course = courses_with_status[choice_idx]
                                    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                                    print(f"📖 课程详情: {selected_course['course_name']}")
                                    print(f"👤 指导老师: {selected_course['teacher_name']}")
                                    print(f"🏫 班级: {selected_course['class_name']}")
                                    print(f"📊 完成情况: {selected_course['completion_status']}")
                                    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

                                    # 显示未完成的知识点
                                    if selected_course['uncompleted_count'] == 0:
                                        print("✅ 该课程已全部完成！")
                                    elif selected_course['uncompleted_count'] > 0:
                                        print(f"📝 未完成知识点列表 ({selected_course['uncompleted_count']} 个):\n")

                                        current_chapter = None
                                        for i, knowledge in enumerate(selected_course['uncompleted_chapters'], 1):
                                            chapter_id = knowledge['id']
                                            chapter_title = knowledge['title']
                                            chapter_content = knowledge['titleContent']

                                            # 如果章节改变，打印章节标题
                                            if chapter_id != current_chapter:
                                                if current_chapter is not None:
                                                    print()  # 章节之间空行
                                                current_chapter = chapter_id
                                                chapter_full_name = f"{chapter_title} - {chapter_content}" if chapter_content else chapter_title
                                                print(f"  📖 {chapter_full_name}")
                                                print(f"     id: {chapter_id}")

                                            print(f"    {i}. {knowledge['knowledge']}")
                                            print(f"       id: {knowledge['knowledge_id']}")
                                    else:
                                        print("❌ 无法获取未完成知识点列表")

                                    print("\n" + "━" * 40 + "\n")
                                else:
                                    print("❌ 无效的选择，请输入1-{}之间的数字".format(len(courses_with_status)))
                            except ValueError:
                                print("❌ 请输入有效的数字")
                    else:
                        print(f"\n⚠️ 获取课程列表失败或暂无课程")
                else:
                    print(f"\n❌ 获取学生端access_token失败！")
            elif sub_choice == "2":
                # 获取access_token - 只打印token
                print("正在获取学生端access_token...")
                access_token = get_student_access_token()
                if access_token:
                    print(f"\n✅ 获取学生端access_token成功！")
                    print(f"access_token: {access_token}")
                    print(f"token类型: Bearer")
                    print(f"有效期: 5小时 (18000秒)")
                else:
                    print(f"\n❌ 获取学生端access_token失败！")
            elif sub_choice == "3":
                print("单个课程答题功能")
            elif sub_choice == "4":
                # 题库导入功能
                print("题库导入功能")
                file_path = input("请输入JSON文件路径（或直接按回车使用默认路径output/）：")
                
                if not file_path:
                    # 使用默认路径，列出output目录下的JSON文件
                    output_dir = Path("output")
                    if output_dir.exists():
                        json_files = list(output_dir.glob("*.json"))
                        if json_files:
                            print("\n可用的JSON文件：")
                            for i, json_file in enumerate(json_files, 1):
                                print(f"  {i}. {json_file.name}")
                            
                            choice = input("\n请选择文件编号：")
                            try:
                                choice_idx = int(choice) - 1
                                if 0 <= choice_idx < len(json_files):
                                    file_path = str(json_files[choice_idx])
                                else:
                                    print("❌ 无效的选择")
                                    continue
                            except ValueError:
                                print("❌ 请输入有效的数字")
                                continue
                        else:
                            print("❌ output目录下没有找到JSON文件")
                            continue
                    else:
                        print("❌ output目录不存在")
                        continue
                
                # 导入题库
                importer = QuestionBankImporter()
                if importer.import_from_file(file_path):
                    bank_type = importer.get_bank_type()
                    if bank_type == "single":
                        print("\n✅ 识别为单个课程题库")
                    elif bank_type == "multiple":
                        print("\n✅ 识别为多个课程题库")
                    else:
                        print("\n❌ 未知的题库类型")
                    
                    # 格式化输出题库信息
                    print(importer.format_output())
                else:
                    print("❌ 题库导入失败")
            elif sub_choice == "5":
                print("返回主菜单")
                continue
            else:
                print("无效的选择，请重新输入")
        elif choice == "2":
            # 题目提取功能
            print("题目提取功能")
            print("1. 获取access_token")
            print("2. 全部提取")
            print("3. 提取单个课程")
            print("4. 结果导出")
            print("5. 返回")
            choice2 = input("请选择：")
            if choice2 == "1":
                # 获取access_token
                print("正在获取access_token...")
                access_token = get_access_token()
                if access_token:
                    print(f"\n✅ 获取access_token成功！")
                    print(f"access_token: {access_token}")
                    print(f"token类型: Bearer")
                    print(f"有效期: 5小时 (18000秒)")
                else:
                    print(f"\n❌ 获取access_token失败！")
            elif choice2 == "2":
                result = extract_questions()
                if result:
                    last_extracted_data = result
                    print("题目提取完成")
            elif choice2 == "3":
                result = extract_single_course()
                if result:
                    last_extracted_data = result
                    print("题目提取完成")
            elif choice2 == "4":
                # 结果导出功能
                if last_extracted_data is None:
                    print("❌ 没有可导出的数据，请先进行题目提取")
                else:
                    try:
                        exporter = DataExporter()
                        file_path = exporter.export_data(last_extracted_data)
                        print(f"✅ 导出成功！文件路径：{file_path}")
                    except Exception as e:
                        print(f"❌ 导出失败：{str(e)}")
            elif choice2 == "5":
                print("返回主菜单")
                continue
            else:
                print("无效的选择，请重新输入")
        elif choice == "3":
            # 设置功能
            print("设置功能尚未实现")
        elif choice == "4":
            # 退出系统
            print("退出系统，再见！")
            break
        else:
            print("无效的选择，请重新输入")


if __name__ == "__main__":
    main()
