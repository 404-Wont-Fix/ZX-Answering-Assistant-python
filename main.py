"""
ZX Answering Assistant - 主程序入口
智能答题助手系统

支持两种运行模式:
- GUI模式: 使用Flet图形界面
- CLI模式: 使用命令行界面
"""

import sys
from pathlib import Path
import subprocess
import os
import argparse

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入版本信息
import version

# 显示版本信息
version.print_version_info()

# 设置Playwright浏览器路径（支持打包后的exe）
def setup_playwright_browser():
    """设置Playwright浏览器路径"""
    try:
        # 检查是否在打包环境中
        if getattr(sys, 'frozen', False):
            # 在打包环境中，使用临时目录中的浏览器
            import tempfile
            import shutil

            # 获取打包的浏览器目录
            browsers_dir = Path(sys._MEIPASS) / "playwright_browsers"
            if browsers_dir.exists():
                # 设置Playwright浏览器路径
                os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(browsers_dir)
                print(f"✅ 使用打包的浏览器: {browsers_dir}")
        else:
            # 开发环境，使用系统浏览器
            print("✅ 使用系统浏览器")
    except Exception as e:
        print(f"⚠️ 设置浏览器路径失败: {e}")


def setup_flet_executable():
    """
    设置Flet可执行文件
    如果是打包环境，尝试将预先下载的Flet复制到临时目录
    """
    try:
        if getattr(sys, 'frozen', False):
            # 在打包环境中，尝试使用预下载的Flet
            from src.build_tools import copy_flet_to_temp_on_startup

            # 尝试将Flet复制到临时目录
            success = copy_flet_to_temp_on_startup()
            if success:
                print("✅ 使用预下载的Flet可执行文件")
            else:
                print("⚠️ 未找到预下载的Flet，运行时将从GitHub下载")
        else:
            # 开发环境，Flet会自动处理
            print("✅ 使用系统Flet")
    except Exception as e:
        print(f"⚠️ 设置Flet可执行文件失败: {e}")


# 在导入Playwright和Flet之前设置路径
setup_playwright_browser()
setup_flet_executable()

# 导入登录模块和题目提取模块
from src.teacher_login import get_access_token as teacher_get_access_token
from src.student_login import (get_student_access_token, get_student_access_token_with_credentials,
                               get_student_courses, get_uncompleted_chapters, navigate_to_course,
                               close_browser, get_course_progress_from_page, get_browser_page,
                               get_cached_access_token)
from src.course_certification import get_access_token as course_get_access_token, start_answering
from src.extract import extract_questions, extract_single_course
from src.export import DataExporter
from src.question_bank_importer import QuestionBankImporter
from src.auto_answer import AutoAnswer
from src.api_auto_answer import APIAutoAnswer
from src.settings import get_settings_manager, APIRateLevel
import time


# 全局变量，存储最后一次提取的数据和题库
last_extracted_data = None
current_question_bank = None  # 当前加载的题库数据


# ==================== CLI设置菜单功能 ====================

def settings_menu():
    """CLI设置菜单"""
    settings = get_settings_manager()

    while True:
        print("\n" + "=" * 50)
        print("⚙️ 设置菜单")
        print("=" * 50)
        print("1. 设置账号密码")
        print("2. 设置 API 请求超时重试次数")
        print("3. 设置 API 请求速率")
        print("4. 查看当前设置")
        print("5. 返回")
        print("=" * 50)

        choice = input("\n请选择操作 (1-5): ").strip()

        if choice == "1":
            # 设置账号密码
            settings_account_password(settings)
        elif choice == "2":
            # 设置API请求超时重试次数
            settings_max_retries(settings)
        elif choice == "3":
            # 设置API请求速率
            settings_rate_level(settings)
        elif choice == "4":
            # 查看当前设置
            settings.display_current_settings()
        elif choice == "5":
            # 返回
            print("\n🔙 返回主菜单")
            break
        else:
            print("\n❌ 无效的选择，请输入1-5之间的数字")


def settings_account_password(settings):
    """设置账号密码子菜单"""
    while True:
        print("\n" + "=" * 50)
        print("🔑 设置账号密码")
        print("=" * 50)
        print("1. 设置学生端账号密码")
        print("2. 设置教师端账号密码")
        print("3. 删除学生端账号密码")
        print("4. 删除教师端账号密码")
        print("5. 返回")
        print("=" * 50)

        choice = input("\n请选择操作 (1-5): ").strip()

        if choice == "1":
            # 设置学生端账号密码
            print("\n👤 设置学生端账号密码")
            print("💡 提示：设置后，登录时将自动填充账号密码")
            username = input("请输入学生账户: ").strip()
            if not username:
                print("❌ 账户不能为空")
                continue

            password = input("请输入学生密码: ").strip()
            if not password:
                print("❌ 密码不能为空")
                continue

            confirm = input("\n确认保存？(yes/no): ").strip().lower()
            if confirm in ['yes', 'y', '是']:
                if settings.set_student_credentials(username, password):
                    print("\n✅ 学生端账号密码已保存")
                else:
                    print("\n❌ 保存失败")
            else:
                print("\n❌ 已取消")

        elif choice == "2":
            # 设置教师端账号密码
            print("\n👨‍🏫 设置教师端账号密码")
            print("💡 提示：设置后，登录时将自动填充账号密码")
            username = input("请输入教师账户: ").strip()
            if not username:
                print("❌ 账户不能为空")
                continue

            password = input("请输入教师密码: ").strip()
            if not password:
                print("❌ 密码不能为空")
                continue

            confirm = input("\n确认保存？(yes/no): ").strip().lower()
            if confirm in ['yes', 'y', '是']:
                if settings.set_teacher_credentials(username, password):
                    print("\n✅ 教师端账号密码已保存")
                else:
                    print("\n❌ 保存失败")
            else:
                print("\n❌ 已取消")

        elif choice == "3":
            # 删除学生端账号密码
            student_username, _ = settings.get_student_credentials()
            if not student_username:
                print("\n⚠️ 学生端账号密码未设置")
                continue

            print("\n🗑️ 删除学生端账号密码")
            confirm = input("确认删除？(yes/no): ").strip().lower()
            if confirm in ['yes', 'y', '是']:
                if settings.clear_student_credentials():
                    print("\n✅ 学生端账号密码已删除")
                else:
                    print("\n❌ 删除失败")
            else:
                print("\n❌ 已取消")

        elif choice == "4":
            # 删除教师端账号密码
            teacher_username, _ = settings.get_teacher_credentials()
            if not teacher_username:
                print("\n⚠️ 教师端账号密码未设置")
                continue

            print("\n🗑️ 删除教师端账号密码")
            confirm = input("确认删除？(yes/no): ").strip().lower()
            if confirm in ['yes', 'y', '是']:
                if settings.clear_teacher_credentials():
                    print("\n✅ 教师端账号密码已删除")
                else:
                    print("\n❌ 删除失败")
            else:
                print("\n❌ 已取消")

        elif choice == "5":
            # 返回
            print("\n🔙 返回设置菜单")
            break
        else:
            print("\n❌ 无效的选择，请输入1-5之间的数字")


def settings_max_retries(settings):
    """设置API请求超时重试次数"""
    print("\n⚙️ 设置 API 请求超时重试次数")
    print(f"当前值: {settings.get_max_retries()} 次")
    print("💡 提示：当API请求失败时，系统会自动重试指定次数")

    while True:
        value = input("\n请输入重试次数 (0-10，直接回车取消): ").strip()

        if not value:
            print("\n❌ 已取消")
            return

        try:
            max_retries = int(value)
            if max_retries < 0 or max_retries > 10:
                print("❌ 重试次数必须在 0-10 之间")
                continue

            confirm = input(f"\n确认设置为 {max_retries} 次？(yes/no): ").strip().lower()
            if confirm in ['yes', 'y', '是']:
                if settings.set_max_retries(max_retries):
                    print(f"\n✅ API请求超时重试次数已设置为 {max_retries} 次")
                else:
                    print("\n❌ 设置失败")
            else:
                print("\n❌ 已取消")
            return

        except ValueError:
            print("❌ 请输入有效的数字")


def settings_rate_level(settings):
    """设置API请求速率"""
    print("\n⚙️ 设置 API 请求速率")
    print(f"当前值: {settings.get_rate_level().get_display_name()}")
    print("💡 提示：控制API请求之间的延迟时间，避免请求过快被限制")
    print("\n可选速率：")
    print("1. 低（API之间延迟50毫秒）")
    print("2. 中（API之间延迟1秒）")
    print("3. 中高（API之间延迟2秒）")
    print("4. 高（API之间延迟3秒）")
    print("0. 返回")

    while True:
        choice = input("\n请选择速率 (0-4): ").strip()

        if choice == "0":
            print("\n❌ 已取消")
            return
        elif choice == "1":
            rate_level = APIRateLevel.LOW
            display_name = rate_level.get_display_name()
        elif choice == "2":
            rate_level = APIRateLevel.MEDIUM
            display_name = rate_level.get_display_name()
        elif choice == "3":
            rate_level = APIRateLevel.MEDIUM_HIGH
            display_name = rate_level.get_display_name()
        elif choice == "4":
            rate_level = APIRateLevel.HIGH
            display_name = rate_level.get_display_name()
        else:
            print("❌ 无效的选择，请输入0-4之间的数字")
            continue

        confirm = input(f"\n确认设置为 {display_name}？(yes/no): ").strip().lower()
        if confirm in ['yes', 'y', '是']:
            if settings.set_rate_level(rate_level):
                print(f"\n✅ API请求速率已设置为 {display_name}")
            else:
                print("\n❌ 设置失败")
        else:
            print("\n❌ 已取消")
        return


def course_certification_menu():
    """课程认证菜单"""
    while True:
        print("\n" + "=" * 50)
        print("🎓 课程认证")
        print("=" * 50)
        print("1. 开始做题")
        print("2. 获取access_token")
        print("3. 返回")
        print("=" * 50)

        choice = input("\n请选择操作 (1-3): ").strip()

        if choice == "1":
            # 开始做题
            start_answering()
        elif choice == "2":
            # 调用课程认证模块的登录功能
            result = course_get_access_token(keep_browser_open=False)
            if result:
                access_token = result[0]  # result 是 (access_token, None, None, None)
                print("\n💡 token 已获取，可以用于后续的 API 调用")
            # TODO: 可以在这里保存 token 到全局变量或文件，供后续使用
        elif choice == "3":
            print("\n🔙 返回主菜单")
            break
        else:
            print("\n❌ 无效的选择，请输入1-3之间的数字")


def display_progress_bar(progress_info: dict):
    """
    显示课程进度条

    Args:
        progress_info: 包含进度信息的字典
    """
    total = progress_info.get('total', 0)
    completed = progress_info.get('completed', 0)
    failed = progress_info.get('failed', 0)
    not_started = progress_info.get('not_started', 0)
    progress_percentage = progress_info.get('progress_percentage', 0)

    print("\n" + "=" * 60)
    print("📊 课程学习进度")
    print("=" * 60)

    # 计算进度条长度
    bar_width = 40
    filled_width = int(bar_width * progress_percentage / 100)

    # 构建进度条
    progress_bar = "█" * filled_width + "░" * (bar_width - filled_width)

    # 显示进度条
    print(f"\n进度: [{progress_bar}] {progress_percentage:.1f}%")
    print(f"\n📈 统计信息:")
    print(f"   ✅ 已完成: {completed} 个")
    print(f"   ❌ 做错过: {failed} 个")
    print(f"   ⏳ 未开始: {not_started} 个")
    print(f"   📝 总计: {total} 个")

    print("\n" + "=" * 60 + "\n")


def monitor_course_progress(interval: int = 5):
    """
    持续监控并显示课程进度

    Args:
        interval: 监控间隔（秒），默认为5秒
    """
    print("\n🔄 开始监控课程进度...")
    print("💡 提示: 按 Ctrl+C 停止监控\n")

    try:
        while True:
            progress_info = get_course_progress_from_page()

            if progress_info:
                display_progress_bar(progress_info)
            else:
                print("❌ 无法获取课程进度信息")

            # 等待指定的间隔时间
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\n⏸️  监控已停止")


def show_answer_menu(course_info: dict) -> bool:
    """
    显示答题选项菜单并处理用户选择

    Args:
        course_info: 课程信息字典，包含 course_id, course_name 等

    Returns:
        bool: 是否应该返回到课程列表（True表示返回）
    """
    global current_question_bank

    while True:
        print("\n" + "=" * 50)
        print("📚 答题选项菜单")
        print("=" * 50)
        print("1. 提取该课程的答案")
        print("2. 使用JSON题库")
        print("3. 开始自动做题" + (" (✅已加载题库)" if current_question_bank else "") + "(兼容模式)")
        print("4. 开始自动做题" + (" (✅已加载题库)" if current_question_bank else "") + "(暴力模式)")
        print("5. 退出")
        print("=" * 50)

        choice = input("\n请选择操作 (1-5): ").strip()

        if choice == "1":
            # 提取该课程的答案
            print(f"\n📚 正在提取课程答案：{course_info['course_name']}")
            print(f"🆔 课程ID: {course_info['course_id']}")

            # 调用独立进程运行教师端答案提取（避免Playwright冲突）
            print("\n🔄 正在启动教师端答案提取进程...")
            try:
                result = subprocess.run(
                    [sys.executable, "extract_answers.py", course_info['course_id']],
                    cwd=str(project_root)
                )

                if result.returncode == 0:
                    print("\n✅ 答案提取成功！")
                    # 提取成功后自动加载最新的JSON文件
                    output_dir = Path("output")
                    if output_dir.exists():
                        json_files = list(output_dir.glob("*.json"))
                        if json_files:
                            # 找最新的文件
                            latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
                            print(f"\n📁 自动加载最新题库: {latest_file.name}")
                            importer = QuestionBankImporter()
                            if importer.import_from_file(str(latest_file)):
                                current_question_bank = importer.data
                                print("✅ 题库已自动加载，现在可以开始自动做题")
                else:
                    print(f"\n❌ 答案提取失败，退出码: {result.returncode}")
            except Exception as e:
                print(f"\n❌ 启动提取进程失败：{str(e)}")

            # 询问是否启动持续监控
            monitor_choice = input("\n是否启动持续监控？(yes/no): ").strip().lower()
            if monitor_choice in ['yes', 'y', '是']:
                monitor_course_progress(interval=5)
                return True  # 监控结束后返回课程列表
            else:
                return True  # 不监控，直接返回课程列表

        elif choice == "2":
            # 使用JSON题库
            print("\n📁 使用JSON题库功能")
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

                        file_choice = input("\n请选择文件编号：")
                        try:
                            choice_idx = int(file_choice) - 1
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

                # 保存题库数据到全局变量
                current_question_bank = importer.data

                # 格式化输出题库信息
                print(importer.format_output())
            else:
                print("❌ 题库导入失败")

            # 完成后继续显示菜单
            continue

        elif choice == "3":
            # 开始自动做题
            if not current_question_bank:
                print("\n❌ 请先加载题库（选项1或选项2）")
                continue

            print("\n🤖 准备开始自动做题...")
            print(f"🆔 课程ID: {course_info['course_id']}")
            print(f"📚 课程名称: {course_info['course_name']}")

            # 获取浏览器实例
            browser_page = get_browser_page()
            if not browser_page:
                print("\n❌ 无法获取浏览器实例，请确保已登录学生端")
                continue

            print("\n💡 提示：请确保当前页面显示的是题目列表（知识点列表）")
            print("💡 如果当前已经在答题界面，请先返回到知识点列表")

            ready = input("\n是否准备好开始自动做题？(yes/no): ").strip().lower()
            if ready not in ['yes', 'y', '是']:
                print("❌ 已取消自动做题")
                continue

            # 询问是否一次性做完所有知识点
            auto_all = input("\n是否一次性做完整个课程的所有未完成知识点？(yes/no): ").strip().lower()
            auto_all_mode = auto_all in ['yes', 'y', '是']

            if auto_all_mode:
                print("\n🔄 自动全部模式：将自动完成所有未完成的知识点")
                print("💡 提示：按 Ctrl+C 可随时中断")

            # 创建自动做题器并开始
            try:
                auto_answer = AutoAnswer(browser_page[1])  # 使用page对象
                auto_answer.load_question_bank(current_question_bank)

                # 循环做题
                knowledge_count = 0
                total_success = 0
                total_failed = 0

                while True:
                    print(f"\n{'='*50}")
                    print(f"📍 知识点 #{knowledge_count + 1}")
                    print(f"{'='*50}")

                    # 第一个知识点：检索并开始做题
                    # 之后的知识点：网站自动跳转后继续做题
                    if knowledge_count == 0:
                        print("\n🔍 检索第一个可作答的知识点并开始做题...")
                        result = auto_answer.run_auto_answer(max_questions=5)
                    else:
                        print("\n⏳ 网站已自动跳转到下一个知识点，继续做题...")
                        import time
                        time.sleep(2)  # 等待跳转完成
                        result = auto_answer.continue_auto_answer(max_questions=5)

                    # 统计
                    knowledge_count += 1
                    total_success += result['success']
                    total_failed += result['failed']

                    # 显示本次统计
                    print("\n" + "=" * 50)
                    print("📊 本知识点完成统计")
                    print("=" * 50)
                    print(f"总题数: {result['total']}")
                    print(f"✅ 成功: {result['success']}")
                    print(f"❌ 失败: {result['failed']}")
                    print(f"⏭️  跳过: {result['skipped']}")
                    print("=" * 50)

                    # 检查用户是否请求停止
                    if result.get('stopped', False):
                        print("\n" + "=" * 50)
                        print("⚠️  用户请求停止做题")
                        print("=" * 50)
                        print(f"📊 本次完成: {knowledge_count} 个知识点")
                        print(f"✅ 成功作答: {total_success} 题")
                        print(f"❌ 失败: {total_failed} 题")
                        print("=" * 50)
                        break

                    # 检查是否是自动全部模式
                    if auto_all_mode:
                        # 自动全部模式：网站会自动跳转到下一个知识点，继续循环
                        print(f"\n⏳ 累计完成 {knowledge_count} 个知识点")
                        print("⏳ 网站将自动跳转到下一个知识点...")

                        # 检查是否还能继续（如果没有找到开始按钮，说明所有知识点都完成了）
                        # 通过检查当前页面是否有"开始测评"按钮来判断
                        import time
                        time.sleep(1)  # 等待跳转

                        try:
                            # 尝试查找开始测评按钮
                            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
                            try:
                                auto_answer.page.wait_for_selector("button:has-text('开始测评')", timeout=3000)
                                # 找到了，可以继续
                                print("✅ 检测到下一个知识点，继续做题...")
                                continue
                            except PlaywrightTimeoutError:
                                # 没找到，说明所有知识点都完成了
                                print("\n" + "=" * 50)
                                print("✅ 所有知识点已完成！")
                                print("=" * 50)
                                print(f"📊 总计完成 {knowledge_count} 个知识点")
                                print(f"✅ 成功作答: {total_success} 题")
                                print(f"❌ 失败: {total_failed} 题")
                                print("=" * 50)
                                break
                        except Exception as e:
                            print(f"\n❌ 检查失败: {str(e)}")
                            print("💡 可能所有知识点都已完成")
                            break
                    else:
                        # 手动模式：询问是否继续
                        continue_choice = input("\n是否继续做题其他知识点？(yes/no): ").strip().lower()
                        if continue_choice in ['yes', 'y', '是']:
                            # 询问是否切换到自动全部模式
                            switch_auto = input("\n💡 提示：是否切换到自动全部模式？(yes/no): ").strip().lower()
                            if switch_auto in ['yes', 'y', '是']:
                                auto_all_mode = True
                                print("\n🔄 已切换到自动全部模式")
                                print("⏳ 等待2秒后自动查找下一个知识点...")
                                import time
                                time.sleep(2)

                                # 尝试开始下一个知识点
                                try:
                                    can_continue = auto_answer.click_start_button()
                                    if not can_continue:
                                        print("\n✅ 所有知识点已完成！")
                                        print(f"📊 总计完成 {knowledge_count} 个知识点")
                                        print(f"✅ 成功作答: {total_success} 题")
                                        print(f"❌ 失败: {total_failed} 题")
                                        break
                                except Exception as e:
                                    print(f"\n❌ 查找下一个知识点失败: {str(e)}")
                                    break
                            else:
                                # 继续手动模式，需要用户手动切换
                                print("\n💡 请手动切换到下一个知识点，然后按任意键继续...")
                                input()
                                continue
                        else:
                            # 用户选择不继续
                            print("\n" + "=" * 50)
                            print(f"📊 累计完成 {knowledge_count} 个知识点")
                            print(f"✅ 成功作答: {total_success} 题")
                            print(f"❌ 失败: {total_failed} 题")
                            print("=" * 50)
                            break

                return True

            except KeyboardInterrupt:
                print("\n\n⚠️  用户中断自动做题")
                print(f"📊 本次完成: {knowledge_count} 个知识点, {total_success} 题")
                continue
            except Exception as e:
                print(f"\n❌ 自动做题失败：{str(e)}")
                import traceback
                traceback.print_exc()
                continue

        elif choice == "4":
            # API暴力模式自动做题
            if not current_question_bank:
                print("\n❌ 请先加载题库（选项1或选项2）")
                continue

            print("\n🚀 API暴力模式自动做题")
            print(f"🆔 课程ID: {course_info['course_id']}")
            print(f"📚 课程名称: {course_info['course_name']}")
            print("\n💡 提示：此模式使用API直接构造请求完成做题，无需浏览器操作")
            print("💡 优势：速度更快，不依赖浏览器状态")
            print("💡 前提：需要学生端的access_token")

            # 获取access_token（使用缓存管理）
            print("\n🔍 正在获取学生端access_token...")

            # 使用缓存函数，自动处理token的获取和缓存
            access_token = get_cached_access_token()

            if not access_token:
                # 缓存获取失败，提示用户手动输入
                print("\n⚠️ 自动获取access_token失败")
                access_token = input("请手动输入access_token（或回车取消）: ").strip()

                if not access_token:
                    print("❌ 已取消操作")
                    continue
                else:
                    # 手动输入后，保存到缓存
                    from src.student_login import set_access_token
                    set_access_token(access_token)

            # 询问是否自动完成所有知识点
            auto_all = input("\n是否自动完成所有未完成的知识点？(yes/no): ").strip().lower()
            auto_all_mode = auto_all in ['yes', 'y', '是']

            max_knowledges = None
            if not auto_all_mode:
                max_input = input("请输入要完成的知识点数量（直接回车完成1个）: ").strip()
                max_knowledges = int(max_input) if max_input else 1

            try:
                # 创建API自动做题器
                api_answer = APIAutoAnswer(access_token)
                api_answer.load_question_bank(current_question_bank)

                print("\n" + "=" * 60)
                print("🚀 开始API暴力模式自动做题")
                print("=" * 60)

                # 执行自动做题
                result = api_answer.auto_answer_all_knowledges(
                    course_info['course_id'],
                    max_knowledges=max_knowledges if not auto_all_mode else None
                )

                # 显示结果
                print("\n" + "=" * 60)
                print("📊 最终统计")
                print("=" * 60)
                print(f"知识点: {result['completed_knowledges']}/{result['total_knowledges']}")
                print(f"题目: 总计 {result['total_questions']} 题")
                print(f"✅ 成功: {result['success']} 题")
                print(f"❌ 失败: {result['failed']} 题")
                print(f"⏭️  跳过: {result['skipped']} 题")
                print("=" * 60)

                if auto_all_mode and result['completed_knowledges'] >= result['total_knowledges']:
                    print("\n🎉 恭喜！所有知识点已完成！")

                return True

            except KeyboardInterrupt:
                print("\n\n⚠️  用户中断自动做题")
                continue
            except Exception as e:
                print(f"\n❌ API自动做题失败：{str(e)}")
                import traceback
                traceback.print_exc()
                continue

        elif choice == "5":
            # 退出
            print("\n🔙 返回课程列表")
            return True

        else:
            print("\n❌ 无效的选择，请输入1-5之间的数字")
            continue


def main():
    while True:
        print("欢迎使用智能答题助手系统")
        print("1. 开始答题")
        print("2. 题目抓取")
        print("3. 课程认证")
        print("4. 设置")
        print("5. 退出系统")
        choice = input("请选择操作：")
        if choice == "1":
            # 调用开始答题功能
            print("开始答题功能")
            print("1. 开始答题")
            print("2. 获取access_token")
            print("3. 返回")
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
                        for i, course in enumerate(courses):
                            course_id = course.get('courseID')
                            course_name = course.get('courseName', 'N/A')
                            teacher_name = course.get('teacherName', 'N/A')
                            class_name = course.get('className', 'N/A')
                            class_id = course.get('classID', '')  # 获取班级ID

                            # 添加延迟（第一个请求除外）
                            if i > 0:
                                time.sleep(0.6)  # 600毫秒延迟

                            # 获取未完成的知识点
                            uncompleted_chapters = []
                            if course_id:
                                uncompleted_chapters = get_uncompleted_chapters(access_token, course_id, delay_ms=600, max_retries=3)

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
                                'class_id': class_id,
                                'completion_status': completion_status,
                                'uncompleted_count': uncompleted_count,
                                'uncompleted_chapters': uncompleted_chapters
                            })

                        # 显示课程列表
                        for i, course_info in enumerate(courses_with_status, 1):
                            print(f"{i}. 【{course_info['course_name']}】")
                            print(f"   🆔 课程ID: {course_info['course_id']}")
                            print(f"   👤 指导老师: {course_info['teacher_name']}")
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
                                    print(f"🆔 课程ID: {selected_course['course_id']}")
                                    print(f"👤 指导老师: {selected_course['teacher_name']}")
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

                                    # 询问用户是否开始答题
                                    while True:
                                        confirm = input("\n是否开始答题该课程？(yes/no): ").strip().lower()
                                        if confirm in ['yes', 'y', '是']:
                                            print(f"\n🚀 开始答题：{selected_course['course_name']}")
                                            print(f"📖 正在打开答题页面...")
                                            print(f"🆔 课程ID: {selected_course['course_id']}")
                                            print("=" * 50)

                                            # 使用已登录的浏览器导航到答题页面
                                            success = navigate_to_course(selected_course['course_id'])

                                            if success:
                                                print("✅ 已在浏览器中打开答题页面")

                                                # 等待页面加载后获取进度信息
                                                print("\n⏳ 正在分析课程进度...")
                                                time.sleep(2)  # 等待页面完全加载

                                                # 获取并显示进度信息
                                                progress_info = get_course_progress_from_page()
                                                if progress_info:
                                                    display_progress_bar(progress_info)

                                                    # 显示答题选项菜单
                                                    should_return = show_answer_menu(selected_course)
                                                    print("=" * 50 + "\n")
                                                    if should_return:
                                                        break
                                                else:
                                                    print("⚠️  无法获取课程进度信息")
                                                    print("=" * 50 + "\n")
                                                    break
                                            else:
                                                print("❌ 打开答题页面失败")
                                                print("提示: 浏览器可能已挂掉或未初始化")

                                                # 检查浏览器状态
                                                from src.student_login import is_browser_alive
                                                if not is_browser_alive():
                                                    print("\n⚠️ 检测到浏览器已挂掉")
                                                    relogin = input("是否重新登录？(yes/no): ").strip().lower()
                                                    if relogin in ['yes', 'y', '是']:
                                                        print("\n🔄 正在重新登录...")
                                                        # 清除旧的 token
                                                        from src.student_login import clear_access_token
                                                        clear_access_token()

                                                        # 重新获取 token（会启动新的浏览器）
                                                        new_token = get_student_access_token()
                                                        if new_token:
                                                            print("✅ 重新登录成功！请重新选择课程开始答题")
                                                            # 返回课程列表
                                                            break
                                                        else:
                                                            print("❌ 重新登录失败")
                                                            print("=" * 50 + "\n")
                                                            break
                                                    else:
                                                        print("=" * 50 + "\n")
                                                        break
                                                else:
                                                    print("提示: 请先确保已登录学生端")
                                                    print("=" * 50 + "\n")
                                                    break
                                        elif confirm in ['no', 'n', '否']:
                                            print("返回课程列表\n")
                                            # 重新显示课程列表
                                            print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                                            print("📚 课程列表")
                                            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

                                            for i, course_info in enumerate(courses_with_status, 1):
                                                print(f"{i}. 【{course_info['course_name']}】")
                                                print(f"   🆔 课程ID: {course_info['course_id']}")
                                                print(f"   👤 指导老师: {course_info['teacher_name']}")
                                                print(f"   📊 完成情况: {course_info['completion_status']}")
                                                print()
                                            break
                                        else:
                                            print("❌ 请输入 yes 或 no")
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
                print("返回主菜单")
                continue
            else:
                print("无效的选择，请重新输入")
        elif choice == "2":
            # 题目提取功能
            global last_extracted_data
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
                access_token = teacher_get_access_token()
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
            # 课程认证功能
            course_certification_menu()
        elif choice == "4":
            # 设置功能
            settings_menu()
        elif choice == "5":
            # 退出系统
            print("退出系统，再见！")
            # 关闭浏览器
            close_browser()
            break
        else:
            print("无效的选择，请重新输入")


def run_gui_mode():
    """启动GUI模式"""
    try:
        from src.main_gui import run_app
        print("🚀 正在启动图形界面...")
        run_app()
    except ImportError as e:
        print(f"❌ 导入GUI模块失败: {e}")
        print("💡 请确保已安装 flet 库: pip install flet")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 启动GUI失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="ZX Answering Assistant - 智能答题助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py              # 默认启动GUI模式
  python main.py --gui        # 启动GUI模式
  python main.py --cli        # 启动命令行模式
        """
    )

    parser.add_argument(
        '--cli',
        action='store_true',
        help='使用命令行界面模式'
    )

    parser.add_argument(
        '--gui',
        action='store_true',
        help='使用图形界面模式（默认）'
    )

    return parser.parse_args()


if __name__ == "__main__":
    # 解析命令行参数
    args = parse_arguments()

    # 决定使用哪种模式
    if args.cli:
        # CLI模式
        print("🖥️  启动命令行模式...")
        main()
    else:
        # GUI模式（默认）
        run_gui_mode()
