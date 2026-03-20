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
import atexit
from typing import Optional

# 在打包环境中，确保 exit 函数可用（Flet 内部可能使用 exit()）
if 'exit' not in dir(__builtins__):
    __builtins__.exit = lambda code=0: sys.exit(code)

# 设置控制台编码为 UTF-8（Windows 打包环境必需）
if sys.platform == 'win32':
    try:
        import codecs
        # 确保 stdout 和 stderr 使用 UTF-8 编码
        # 先检查是否已经被重新定向
        if hasattr(sys.stdout, 'buffer') and hasattr(sys.stderr, 'buffer'):
            sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)
            sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer)
        elif hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        # 如果上述方法失败，使用环境变量
        os.environ['PYTHONIOENCODING'] = 'utf-8'

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入版本信息
import version

# 导入应用状态管理器
from src.core.app_state import get_app_state

# 获取应用状态管理器实例
app_state = get_app_state()

# 显示版本信息
version.print_version_info()

# 设置Playwright浏览器路径（支持打包后的exe）
def setup_playwright_browser(silent=False):
    """设置Playwright浏览器路径

    Args:
        silent: 是否静默模式（不打印信息）
    """
    def log(msg):
        """内部日志函数"""
        if not silent:
            print(msg)

    try:
        # 检查是否在打包环境中
        if getattr(sys, 'frozen', False):
            # 在打包环境中，使用临时目录中的浏览器
            import tempfile
            import shutil

            # 获取打包的浏览器目录
            browsers_dir = Path(sys._MEIPASS) / "playwright_browsers"

            if browsers_dir.exists():
                # 检查打包的浏览器目录结构是否正确
                # Playwright 期望: playwright_browsers/chromium-XXXX/chrome-win*/
                # 但旧版本打包可能直接是: playwright_browsers/chrome-win/

                # 检查浏览器目录结构
                # 期望: playwright_browsers/chromium-XXXX/chrome-win64/
                chromium_dirs = list(browsers_dir.glob("chromium-*"))

                if chromium_dirs:
                    # 检查是否使用 chrome-win64
                    chromium_dir = chromium_dirs[0]
                    chrome_win64 = chromium_dir / "chrome-win64"
                    chrome_win = chromium_dir / "chrome-win"

                    if chrome_win64.exists():
                        log(f"[OK] 使用打包的浏览器: {chromium_dir.name}/chrome-win64/")
                    elif chrome_win.exists():
                        # 需要重命名为 chrome-win64
                        print("[INFO] 检测到 chrome-win，正在重命名为 chrome-win64...")
                        try:
                            shutil.move(str(chrome_win), str(chrome_win64))
                            log(f"[OK] 已重命名为 chrome-win64: {chromium_dir.name}/chrome-win64/")
                        except Exception as e:
                            log(f"[WARN] 重命名失败: {e}")
                    else:
                        log(f"[WARN] 未找到浏览器目录: {chromium_dir}")

                    # 检查版本号是否匹配，如果不匹配，创建符号链接
                    try:
                        import re
                        from playwright.sync_api import sync_playwright
                        with sync_playwright() as p:
                            # 获取 Playwright 期望的版本号
                            expected_revision = p.chromium.executable_path.rsplit('-', 1)[-1].split('\\')[-1]
                            # 例如: C:\...\chromium-1208\chrome-win\chrome.exe -> 1208
                    except:
                        expected_revision = None

                    if expected_revision and chromium_dir.name != f"chromium-{expected_revision}":
                        # 版本号不匹配，创建符号链接或重命名
                        print(f"[INFO] 版本号不匹配: {chromium_dir.name} vs chromium-{expected_revision}")
                        print(f"[INFO] 创建兼容性链接...")

                        correct_dir = browsers_dir / f"chromium-{expected_revision}"
                        try:
                            # 创建符号链接（需要管理员权限）或重命名
                            if correct_dir.exists():
                                shutil.rmtree(correct_dir)

                            # 创建目录符号链接或 junction（Windows）
                            if sys.platform == 'win32':
                                import subprocess
                                subprocess.run(['mklink', '/J', str(chromium_dir), str(correct_dir)], check=False, shell=True)
                            else:
                                shutil.copytree(str(chromium_dir), str(correct_dir))

                            log(f"[OK] 已创建版本兼容链接: {correct_dir}")
                        except Exception as e:
                            # 如果符号链接失败，直接重命名
                            try:
                                shutil.move(str(chromium_dir), str(correct_dir))
                                log(f"[OK] 已重命名为: {correct_dir.name}")
                            except:
                                log(f"[WARN] 版本号不匹配，但尝试继续使用: {chromium_dir.name}")

                # 设置Playwright浏览器路径环境变量
                os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(browsers_dir)
                # 同时设置用户数据目录指向临时目录
                os.environ['PLAYWRIGHT_USER_DATA_DIR'] = str(Path(tempfile.gettempdir()) / "playwright_user_data")
                log(f"[OK] 使用打包的浏览器")

                # 设置Playwright浏览器路径环境变量
                os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(browsers_dir)
                # 同时设置用户数据目录指向临时目录
                os.environ['PLAYWRIGHT_USER_DATA_DIR'] = str(Path(tempfile.gettempdir()) / "playwright_user_data")
                log(f"[OK] 使用打包的浏览器: {browsers_dir}")
            else:
                # 最小化构建：浏览器不存在，需要用户手动安装
                log(f"[INFO] 打包的浏览器目录不存在: {browsers_dir}")
                log("[INFO] 检测到最小化构建版本")

                # 使用用户数据目录作为浏览器路径（默认位置）
                # Windows: AppData\Local\ms-playwright, Linux/Mac: ~/.cache/ms-playwright
                if sys.platform == 'win32':
                    user_data_dir = Path.home() / "AppData" / "Local" / "ms-playwright"
                else:
                    user_data_dir = Path.home() / ".cache" / "ms-playwright"

                os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(user_data_dir)
                os.environ['PLAYWRIGHT_USER_DATA_DIR'] = str(Path(tempfile.gettempdir()) / "playwright_user_data")

                # 检查浏览器是否已下载（支持 chrome-win 和 chrome-win64）
                import glob
                import time

                log("[INFO] 检查浏览器...")
                chromium_paths = glob.glob(str(user_data_dir / "chromium-*" / "chrome-win*" / "chrome.exe"))
                if not chromium_paths:
                    # 浏览器未安装，显示提示
                    log("[INFO] 浏览器未安装，准备自动下载...")
                    print()  # 空行
                    time.sleep(1)  # 让用户看到提示
                    # 浏览器未安装，尝试使用 Playwright API 自动安装
                    print("\n" + "=" * 70)
                    print("⚠️  Playwright 浏览器未安装")
                    print("=" * 70)
                    print("📦 正在自动下载 Chromium 浏览器（约 170MB）")
                    print("   这可能需要几分钟，请耐心等待...")
                    print("=" * 70)
                    print()
                    print("💡 提示：首次运行需要下载浏览器，请保持网络连接畅通")
                    print("   下载完成后，下次启动将无需等待")
                    print()
                    print("📊 下载进度：")
                    print("-" * 70)
                    print(flush=True)

                    install_success = False

                    # 方法：使用 subprocess 调用 playwright 命令行工具安装浏览器
                    try:
                        # 使用 subprocess 调用 playwright install 命令
                        # 不捕获输出，让用户看到实时进度
                        import subprocess
                        result = subprocess.run(
                            [sys.executable, "-m", "playwright", "install", "chromium"],
                            timeout=600  # 10分钟超时
                        )

                        # 检查安装结果
                        if result.returncode == 0:
                            print("-" * 70)
                            print()
                            # 验证浏览器是否安装成功
                            chromium_paths = glob.glob(str(user_data_dir / "chromium-*" / "chrome-win*" / "chrome.exe"))
                            if chromium_paths:
                                print("\n" + "=" * 70)
                                print("✅ 浏览器安装成功！")
                                print(f"   位置: {user_data_dir}")
                                print("=" * 70)
                                print()
                                print("🎉 所有组件准备完毕！")
                                print("⏳ 正在启动程序...")
                                print()
                                time.sleep(2)  # 让用户看到成功消息
                                install_success = True
                            else:
                                raise Exception("浏览器安装验证失败（文件未找到）")
                        else:
                            raise Exception(f"安装命令执行失败（返回码: {result.returncode}）")

                    except subprocess.TimeoutExpired:
                        print()
                        print("-" * 70)
                        raise Exception("下载超时（超过10分钟），请检查网络连接")
                    except Exception as e:
                        print()
                        print("-" * 70)
                        print("\n" + "=" * 70)
                        print(f"❌ 自动安装失败: {e}")
                        print("=" * 70)
                        print()
                        print("请手动安装浏览器：")
                        print()
                        print("📌 方法 1: 使用系统 Python（推荐）")
                        print("   打开命令提示符，运行：")
                        print("   playwright install chromium")
                        print()
                        print("📌 方法 2: 使用 pip")
                        print("   pip install playwright")
                        print("   playwright install chromium")
                        print()
                        print("浏览器将安装到:")
                        print(f"   {user_data_dir}")
                        print()
                        print("安装完成后重新运行程序即可")
                        print("=" * 70 + "\n")

                    if not install_success:
                        # 暂停一下让用户看到错误信息
                        import time
                        time.sleep(3)
                else:
                    print(f"[OK] 使用缓存的浏览器: {user_data_dir}")
                    print("⏳ 正在启动程序...")
                    print(flush=True)
        else:
            # 开发环境，使用系统浏览器
            log("[OK] 使用系统浏览器")
    except Exception as e:
        log(f"[WARN] 设置浏览器路径失败: {e}")


# 注册退出时的清理函数
def cleanup_on_exit():
    """
    程序退出时的清理函数

    由 atexit 自动调用，确保所有浏览器资源被正确释放
    避免 Node.js 进程挂起
    """
    try:
        # 尝试使用浏览器管理器清理
        from src.core.browser import get_browser_manager
        manager = get_browser_manager()
        if manager._browser is not None:
            print("🔄 [atexit] 正在清理浏览器资源...")
            manager.close_browser()
            print("✅ [atexit] 浏览器资源已清理")
    except Exception as e:
        print(f"⚠️ [atexit] 清理浏览器时出错: {e}")

    # 强制终止残留的 Node.js 进程
    try:
        import psutil
        current_pid = os.getpid()
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid']):
            try:
                # 查找 Playwright Node.js driver 进程
                if proc.info['name'] and 'node.exe' in proc.info['name'].lower():
                    # 检查是否是当前进程的子进程
                    if proc.info['ppid'] == current_pid:
                        # 检查命令行中是否包含 playwright
                        cmdline = proc.info['cmdline']
                        if cmdline and any('playwright' in str(cmd).lower() for cmd in cmdline):
                            print(f"🔄 [atexit] 终止残留的 Node.js 进程 (PID: {proc.info['pid']})...")
                            proc.terminate()
                            print("✅ [atexit] Node.js 进程已终止")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except ImportError:
        # psutil 未安装，跳过强制终止
        pass
    except Exception as e:
        # 忽略其他错误
        pass


def register_cleanup_handlers():
    """注册程序退出时的清理处理器"""
    # 注册 atexit 处理器（在程序正常退出时调用）
    atexit.register(cleanup_on_exit)


def setup_flet_executable(silent=False):
    """
    设置Flet可执行文件
    简化版本 - 只设置环境变量

    Args:
        silent: 是否静默模式（不打印信息）
    """
    def log(msg):
        """内部日志函数"""
        if not silent:
            print(msg)

    try:
        # 设置环境变量，让 Flet 使用 pip 而不是 uv
        os.environ["UV_SYSTEM_PYTHON"] = "1"

        if getattr(sys, 'frozen', False):
            log("[OK] 打包环境：Flet desktop 已包含")
        else:
            log("[OK] 使用系统Flet")
    except Exception as e:
        log(f"[WARN] 设置Flet可执行文件失败: {e}")


# 在导入Playwright和Flet之前设置路径（静默模式）
# 只有在确定使用 GUI 模式时才会显示详细信息
setup_playwright_browser(silent=True)
setup_flet_executable(silent=True)

# 导入CLI模式所需的模块
# 注意：这些导入在模块级别，目前没有循环导入风险
import time

# 登录和认证模块
from src.auth.teacher import get_access_token as teacher_get_access_token
from src.auth.student import (
    get_student_access_token,
    get_student_access_token_with_credentials,
    get_student_courses,
    get_uncompleted_chapters,
    navigate_to_course,
    close_browser,
    get_course_progress_from_page,
    get_browser_page,
    get_cached_access_token
)

# 课程认证模块
from src.certification.workflow import get_access_token as course_get_access_token, start_answering

# 数据提取和导出模块
from src.extraction.extractor import extract_questions, extract_single_course
from src.extraction.exporter import DataExporter
from src.extraction.importer import QuestionBankImporter

# 自动答题模块
from src.answering.browser_answer import AutoAnswer
from src.answering.api_answer import APIAutoAnswer

# 设置模块
from src.core.config import get_settings_manager, APIRateLevel


# 全局变量已被 AppState 替代
# 使用 app_state.get('last_extracted_data') 和 app_state.get('current_question_bank') 访问


# ==================== CLI设置菜单功能 ====================

def settings_menu():
    """CLI设置菜单"""
    settings = get_settings_manager()

    while True:
        print("\n  [1] 🔑 设置账号密码")
        print("  [2] 🔄 设置 API 请求超时重试次数")
        print("  [3] ⚡ 设置 API 请求速率")
        print("  [4] 📋 查看当前设置")
        print("  [0] 🔙 返回主菜单")
        print("\n" + "━" * 60)

        choice = input("\n👉 请选择功能 [0-4]: ").strip()

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
        elif choice == "0":
            # 返回
            print("\n🔙 返回主菜单...\n")
            break
        else:
            print("\n⚠️  无效的选择，请输入 0-4 之间的数字")


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
        print("0. 返回")
        print("=" * 50)

        choice = input("\n请选择操作 (1-4 或 0): ").strip()

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

        elif choice == "0":
            # 返回
            print("\n🔙 返回设置菜单")
            break
        else:
            print("\n❌ 无效的选择，请输入 1-4 或 0")


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
        print("\n  [1] 🎯 开始做题")
        print("  [2] 🔑 获取 access_token")
        print("  [3] 📚 导入题库")
        print("  [0] 🔙 返回主菜单")
        print("\n" + "━" * 60)

        choice = input("\n👉 请选择功能 [0-3]: ").strip()

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
            # 导入题库
            print("\n📚 导入题库功能")
            print("=" * 50)
            print("请输入题库JSON文件的路径（例如：output/course_20250129_123456.json）：")
            file_path = input("文件路径: ").strip()

            if not file_path:
                print("❌ 文件路径不能为空")
                continue

            # 调用题库导入功能
            from src.certification.workflow import import_question_bank
            success = import_question_bank(file_path)

            if success:
                print("\n✅ 题库导入成功！")
                print("💡 现在可以选择'开始做题'使用导入的题库进行答题")
            else:
                print("\n❌ 题库导入失败")
        elif choice == "0":
            print("\n🔙 返回主菜单...\n")
            break
        else:
            print("\n⚠️  无效的选择，请输入 0-3 之间的数字")


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


# ============================================================================
# 答题菜单处理器类
# ============================================================================

class AnswerMenuHandler:
    """
    答题菜单处理器

    将 show_answer_menu 函数重构为类，提高代码可维护性。
    """

    def __init__(self, course_info: dict):
        """
        初始化答题菜单处理器

        Args:
            course_info: 课程信息字典
        """
        self.course_info = course_info
        self.auto_all_mode = False

    def show_menu(self) -> bool:
        """
        显示答题菜单并处理用户选择

        Returns:
            bool: 是否应该返回到课程列表
        """
        while True:
            self._display_menu()
            choice = input("\n请选择操作 (1-4 或 0): ").strip()

            if choice == "1":
                if self._handle_extract_answers():
                    return True
            elif choice == "2":
                self._handle_load_json_bank()
            elif choice == "3":
                if self._handle_browser_auto_answer():
                    return True
            elif choice == "4":
                if self._handle_api_auto_answer():
                    return True
            elif choice == "0":
                print("\n🔙 返回课程列表")
                return True
            else:
                print("\n❌ 无效的选择，请输入 1-4 或 0")

    def _display_menu(self):
        """显示菜单选项"""
        print("\n" + "=" * 50)
        print("📚 答题选项菜单")
        print("=" * 50)
        print("1. 提取该课程的答案")
        print("2. 使用JSON题库")
        current_bank = app_state.get('current_question_bank')
        bank_status = " (✅已加载题库)" if current_bank else ""
        print(f"3. 开始自动做题{bank_status}(兼容模式)")
        print(f"4. 开始自动做题{bank_status}(暴力模式)")
        print("0. 退出")
        print("=" * 50)

    def _handle_extract_answers(self) -> bool:
        """
        处理选项1：提取答案

        Returns:
            bool: 是否返回到课程列表
        """
        print(f"\n📚 正在提取课程答案：{self.course_info['course_name']}")
        print(f"🆔 课程ID: {self.course_info['course_id']}")

        # 调用独立进程运行教师端答案提取
        print("\n🔄 正在启动教师端答案提取进程...")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "src.extract_answers", self.course_info['course_id']],
                cwd=str(project_root)
            )

            if result.returncode == 0:
                print("\n✅ 答案提取成功！")
                self._auto_load_latest_bank()
            else:
                print(f"\n❌ 答案提取失败，退出码: {result.returncode}")
        except Exception as e:
            print(f"\n❌ 启动提取进程失败：{str(e)}")

        # 询问是否启动持续监控
        monitor_choice = input("\n是否启动持续监控？(yes/no): ").strip().lower()
        if monitor_choice in ['yes', 'y', '是']:
            monitor_course_progress(interval=5)

        return True  # 返回课程列表

    def _auto_load_latest_bank(self):
        """自动加载最新的题库文件"""
        output_dir = Path("output")
        if output_dir.exists():
            json_files = list(output_dir.glob("*.json"))
            if json_files:
                latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
                print(f"\n📁 自动加载最新题库: {latest_file.name}")
                importer = QuestionBankImporter()
                if importer.import_from_file(str(latest_file)):
                    app_state.set('current_question_bank', importer.data)
                    print("✅ 题库已自动加载，现在可以开始自动做题")

    def _handle_load_json_bank(self):
        """处理选项2：加载JSON题库"""
        print("\n📁 使用JSON题库功能")
        file_path = input("请输入JSON文件路径（或直接按回车使用默认路径output/）：")

        if not file_path:
            file_path = self._select_json_file()
            if not file_path:
                return

        # 导入题库
        importer = QuestionBankImporter()
        if importer.import_from_file(file_path):
            self._display_bank_info(importer)
            app_state.set('current_question_bank', importer.data)
        else:
            print("❌ 题库导入失败")

    def _select_json_file(self) -> Optional[str]:
        """
        选择JSON文件

        Returns:
            Optional[str]: 选中的文件路径，如果取消则返回None
        """
        output_dir = Path("output")
        if not output_dir.exists():
            print("❌ output目录不存在")
            return None

        json_files = list(output_dir.glob("*.json"))
        if not json_files:
            print("❌ output目录下没有找到JSON文件")
            return None

        print("\n可用的JSON文件：")
        for i, json_file in enumerate(json_files, 1):
            print(f"  {i}. {json_file.name}")

        file_choice = input("\n请选择文件编号：")
        try:
            choice_idx = int(file_choice) - 1
            if 0 <= choice_idx < len(json_files):
                return str(json_files[choice_idx])
            else:
                print("❌ 无效的选择")
                return None
        except ValueError:
            print("❌ 请输入有效的数字")
            return None

    def _display_bank_info(self, importer):
        """显示题库信息"""
        bank_type = importer.get_bank_type()
        if bank_type == "single":
            print("\n✅ 识别为单个课程题库")
        elif bank_type == "multiple":
            print("\n✅ 识别为多个课程题库")
        else:
            print("\n❌ 未知的题库类型")

        print(importer.format_output())

    def _handle_browser_auto_answer(self) -> bool:
        """
        处理选项3：浏览器模式自动答题

        Returns:
            bool: 是否返回到课程列表
        """
        current_bank = app_state.get('current_question_bank')
        if not current_bank:
            print("\n❌ 请先加载题库（选项1或选项2）")
            return False

        if not self._prepare_auto_answer():
            return False

        try:
            return self._run_browser_auto_answer(current_bank)
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断自动做题")
            return False
        except Exception as e:
            print(f"\n❌ 自动做题失败：{str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _prepare_auto_answer(self) -> bool:
        """准备自动答题"""
        print("\n🤖 准备开始自动做题...")
        print(f"🆔 课程ID: {self.course_info['course_id']}")
        print(f"📚 课程名称: {self.course_info['course_name']}")

        browser_page = get_browser_page()
        if not browser_page:
            print("\n❌ 无法获取浏览器实例，请确保已登录学生端")
            return False

        print("\n💡 提示：请确保当前页面显示的是题目列表（知识点列表）")
        ready = input("\n是否准备好开始自动做题？(yes/no): ").strip().lower()
        return ready in ['yes', 'y', '是']

    def _run_browser_auto_answer(self, current_bank) -> bool:
        """
        运行浏览器自动答题

        Returns:
            bool: 是否返回到课程列表
        """
        browser_page = get_browser_page()
        auto_answer = AutoAnswer(browser_page[1])
        auto_answer.load_question_bank(current_bank)

        # 询问模式
        auto_all = input("\n是否一次性做完整个课程的所有未完成知识点？(yes/no): ").strip().lower()
        self.auto_all_mode = auto_all in ['yes', 'y', '是']

        if self.auto_all_mode:
            print("\n🔄 自动全部模式：将自动完成所有未完成的知识点")
            print("💡 提示：按 Ctrl+C 可随时中断")

        # 循环做题
        return self._auto_answer_loop(auto_answer)

    def _auto_answer_loop(self, auto_answer) -> bool:
        """
        自动答题循环

        Returns:
            bool: 是否返回到课程列表
        """
        knowledge_count = 0
        total_success = 0
        total_failed = 0

        while True:
            # 执行答题
            result = self._answer_one_knowledge(auto_answer, knowledge_count)

            if result is None:  # 用户中断
                break

            # 更新统计
            knowledge_count += 1
            total_success += result['success']
            total_failed += result['failed']

            # 显示本次统计
            self._display_knowledge_stats(result, knowledge_count)

            # 检查是否继续
            if not self._should_continue_auto(auto_answer, result, knowledge_count, total_success, total_failed):
                break

        return True

    def _answer_one_knowledge(self, auto_answer, knowledge_count: int) -> Optional[dict]:
        """
        答一个知识点

        Returns:
            Optional[dict]: 答题结果，如果用户中断则返回None
        """
        print(f"\n{'='*50}")
        print(f"📍 知识点 #{knowledge_count + 1}")
        print(f"{'='*50}")

        if knowledge_count == 0:
            print("\n🔍 检索第一个可作答的知识点并开始做题...")
            result = auto_answer.run_auto_answer(max_questions=5)
        else:
            print("\n⏳ 网站已自动跳转到下一个知识点，继续做题...")
            time.sleep(2)
            result = auto_answer.continue_auto_answer(max_questions=5)

        return result

    def _display_knowledge_stats(self, result: dict, knowledge_count: int):
        """显示知识点统计"""
        print("\n" + "=" * 50)
        print("📊 本知识点完成统计")
        print("=" * 50)
        print(f"总题数: {result['total']}")
        print(f"✅ 成功: {result['success']}")
        print(f"❌ 失败: {result['failed']}")
        print(f"⏭️  跳过: {result['skipped']}")
        print("=" * 50)

    def _should_continue_auto(self, auto_answer, result: dict, knowledge_count: int,
                            total_success: int, total_failed: int) -> bool:
        """
        判断是否继续自动答题

        Returns:
            bool: True表示继续，False表示停止
        """
        # 检查用户是否请求停止
        if result.get('stopped', False):
            print("\n" + "=" * 50)
            print("⚠️  用户请求停止做题")
            print("=" * 50)
            print(f"📊 本次完成: {knowledge_count} 个知识点")
            print(f"✅ 成功作答: {total_success} 题")
            print(f"❌ 失败: {total_failed} 题")
            print("=" * 50)
            return False

        # 检查模式
        if self.auto_all_mode:
            return self._handle_auto_all_mode(auto_answer, knowledge_count, total_success, total_failed)
        else:
            return self._handle_manual_mode(auto_answer, knowledge_count, total_success, total_failed)

    def _handle_auto_all_mode(self, auto_answer, knowledge_count: int,
                            total_success: int, total_failed: int) -> bool:
        """处理自动全部模式"""
        print(f"\n⏳ 累计完成 {knowledge_count} 个知识点")
        print("⏳ 网站将自动跳转到下一个知识点...")

        time.sleep(1)

        try:
            has_next = auto_answer.has_next_knowledge()
            if has_next:
                print("✅ 检测到下一个知识点，继续做题...")
                return True
            else:
                print("\n" + "=" * 50)
                print("✅ 所有知识点已完成！")
                print("=" * 50)
                print(f"📊 总计完成 {knowledge_count} 个知识点")
                print(f"✅ 成功作答: {total_success} 题")
                print(f"❌ 失败: {total_failed} 题")
                print("=" * 50)
                return False
        except Exception as e:
            print(f"\n❌ 检查失败: {str(e)}")
            print("💡 可能所有知识点都已完成")
            return False

    def _handle_manual_mode(self, auto_answer, knowledge_count: int,
                           total_success: int, total_failed: int) -> bool:
        """处理手动模式"""
        continue_choice = input("\n是否继续做题其他知识点？(yes/no): ").strip().lower()
        if continue_choice in ['yes', 'y', '是']:
            switch_auto = input("\n💡 提示：是否切换到自动全部模式？(yes/no): ").strip().lower()
            if switch_auto in ['yes', 'y', '是']:
                self.auto_all_mode = True
                print("\n🔄 已切换到自动全部模式")
                time.sleep(2)

                try:
                    can_continue = auto_answer.click_start_button()
                    if not can_continue:
                        print("\n✅ 所有知识点已完成！")
                        print(f"📊 总计完成 {knowledge_count} 个知识点")
                        print(f"✅ 成功作答: {total_success} 题")
                        print(f"❌ 失败: {total_failed} 题")
                        return False
                except Exception as e:
                    print(f"\n❌ 查找下一个知识点失败: {str(e)}")
                    return False
            else:
                print("\n💡 请手动切换到下一个知识点，然后按任意键继续...")
                input()
                return True
        else:
            print("\n" + "=" * 50)
            print(f"📊 累计完成 {knowledge_count} 个知识点")
            print(f"✅ 成功作答: {total_success} 题")
            print(f"❌ 失败: {total_failed} 题")
            print("=" * 50)
            return False

    def _handle_api_auto_answer(self) -> bool:
        """
        处理选项4：API模式自动答题

        Returns:
            bool: 是否返回到课程列表
        """
        current_bank = app_state.get('current_question_bank')
        if not current_bank:
            print("\n❌ 请先加载题库（选项1或选项2）")
            return False

        print("\n🚀 API暴力模式自动做题")
        print(f"🆔 课程ID: {self.course_info['course_id']}")
        print(f"📚 课程名称: {self.course_info['course_name']}")
        print("\n💡 提示：此模式使用API直接构造请求完成做题，无需浏览器操作")
        print("💡 优势：速度更快，不依赖浏览器状态")
        print("💡 前提：需要学生端的access_token")

        # 获取token
        access_token = self._get_access_token()
        if not access_token:
            return False

        # 询问模式
        auto_all = input("\n是否自动完成所有未完成的知识点？(yes/no): ").strip().lower()
        auto_all_mode = auto_all in ['yes', 'y', '是']

        max_knowledges = None
        if not auto_all_mode:
            max_input = input("请输入要完成的知识点数量（直接回车完成1个）: ").strip()
            max_knowledges = int(max_input) if max_input else 1

        try:
            return self._run_api_auto_answer(access_token, current_bank, auto_all_mode, max_knowledges)
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断自动做题")
            return False
        except Exception as e:
            print(f"\n❌ API自动做题失败：{str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _get_access_token(self) -> Optional[str]:
        """
        获取access_token

        Returns:
            Optional[str]: token字符串，如果获取失败则返回None
        """
        print("\n🔍 正在获取学生端access_token...")
        access_token = get_cached_access_token()

        if not access_token:
            print("\n⚠️ 自动获取access_token失败")
            access_token = input("请手动输入access_token（或回车取消）: ").strip()

            if not access_token:
                print("❌ 已取消操作")
                return None
            else:
                from src.auth.student import set_access_token
                set_access_token(access_token)

        return access_token

    def _run_api_auto_answer(self, access_token: str, current_bank: dict,
                            auto_all_mode: bool, max_knowledges: Optional[int]) -> bool:
        """
        运行API自动答题

        Returns:
            bool: 是否返回到课程列表
        """
        api_answer = APIAutoAnswer(access_token)
        api_answer.load_question_bank(current_bank)

        print("\n" + "=" * 60)
        print("🚀 开始API暴力模式自动做题")
        print("=" * 60)

        # 执行自动做题
        result = api_answer.auto_answer_all_knowledges(
            self.course_info['course_id'],
            max_knowledges=max_knowledges if not auto_all_mode else None
        )

        # 显示结果
        self._display_api_result(result, auto_all_mode)
        return True

    def _display_api_result(self, result: dict, auto_all_mode: bool):
        """显示API答题结果"""
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


# 保持向后兼容的函数
def show_answer_menu(course_info: dict) -> bool:
    """
    显示答题选项菜单并处理用户选择（向后兼容的包装函数）

    Args:
        course_info: 课程信息字典，包含 course_id, course_name 等

    Returns:
        bool: 是否应该返回到课程列表（True表示返回）
    """
    handler = AnswerMenuHandler(course_info)
    return handler.show_menu()


def main():
    """CLI 主循环"""
    while True:
        print("\n" + "=" * 60)
        print("🚀 ZX 智能答题助手 - 主菜单")
        print("=" * 60)
        print()
        print("  [1] 📝 开始答题")
        print("  [2] 📥 题目提取")
        print("  [3] 🎓 课程认证")
        print("  [4] ⚙️  系统设置")
        print("  [0] 🚪 退出系统")
        print()
        print("=" * 60)

        choice = input("\n👉 请选择功能 [0-4]: ").strip()

        if choice == "1":
            # 调用开始答题功能
            print("开始答题功能")
            print("1. 开始答题")
            print("2. 获取access_token")
            print("0. 返回")
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
                                                from src.auth.student import is_browser_alive
                                                if not is_browser_alive():
                                                    print("\n⚠️ 检测到浏览器已挂掉")
                                                    relogin = input("是否重新登录？(yes/no): ").strip().lower()
                                                    if relogin in ['yes', 'y', '是']:
                                                        print("\n🔄 正在重新登录...")
                                                        # 清除旧的 token
                                                        from src.auth.student import clear_access_token
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
            elif sub_choice == "0":
                print("返回主菜单")
                continue
            else:
                print("无效的选择，请重新输入")
        elif choice == "2":
            # 题目提取功能
            print("\n" + "━" * 60)
            print("📥 题目提取")
            print("━" * 60)
            print("  [1] 🔑 获取 access_token")
            print("  [2] 📚 全部提取")
            print("  [3] 📖 提取单个课程")
            print("  [4] 💾 结果导出")
            print("  [0] 🔙 返回主菜单")
            print("━" * 60)

            choice2 = input("\n👉 请选择功能 [0-4]: ").strip()
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
                    app_state.set('last_extracted_data', result)
                    print("题目提取完成")
            elif choice2 == "3":
                result = extract_single_course()
                if result:
                    app_state.set('last_extracted_data', result)
                    print("题目提取完成")
            elif choice2 == "4":
                # 结果导出功能
                extracted_data = app_state.get('last_extracted_data')
                if extracted_data is None:
                    print("❌ 没有可导出的数据，请先进行题目提取")
                else:
                    try:
                        exporter = DataExporter()
                        file_path = exporter.export_data(extracted_data)
                        print(f"✅ 导出成功！文件路径：{file_path}")
                    except Exception as e:
                        print(f"❌ 导出失败：{str(e)}")
            elif choice2 == "0":
                print("\n🔙 返回主菜单...\n")
                continue
            else:
                print("无效的选择，请重新输入")
        elif choice == "3":
            # 课程认证功能
            print("\n" + "━" * 60)
            print("🎓 课程认证")
            print("━" * 60)
            course_certification_menu()
        elif choice == "4":
            # 设置功能
            print("\n" + "━" * 60)
            print("⚙️  系统设置")
            print("━" * 60)
            settings_menu()
        elif choice == "0":
            # 退出系统
            print("\n" + "=" * 60)
            print("👋 感谢使用 ZX 智能答题助手！")
            print("   期待您的下次使用 😊")
            print("=" * 60 + "\n")

            # 关闭浏览器
            try:
                close_browser()
            except:
                pass
            break
        else:
            print("\n⚠️  无效的选择，请输入 0-4 之间的数字")


def run_gui_mode():
    """启动GUI模式"""
    try:
        # 显示初始化信息
        print()
        print("=" * 70)
        print("🚀 ZX 智能答题助手 - 启动中")
        print("=" * 70)
        print()
        print("📋 正在初始化组件...")
        print("   ✓ 检查浏览器环境...")
        import time
        time.sleep(0.3)

        # 在GUI模式下显示浏览器和Flet信息
        print("   ✓ 浏览器环境检查完成")
        print("   ✓ Flet 框架就绪")
        print()
        print("⏳ 正在加载图形界面...")
        print(flush=True)

        from src.main_gui import run_app
        print()
        print("🎯 图形界面已启动！")
        print("=" * 70)
        print()
        run_app()
    except ImportError as e:
        print(f"❌ 导入GUI模块失败: {e}")
        print("💡 请确保已安装 flet 库: pip install flet")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 启动GUI失败: {e}")
        sys.exit(1)
    finally:
        # 确保 GUI 退出时清理所有 Playwright 浏览器
        print()
        print("🔄 正在清理浏览器资源...")
        try:
            from src.auth.student import cleanup_browser
            cleanup_browser()
        except:
            pass
        try:
            from src.certification.workflow import close_browser
            close_browser()
        except:
            pass
        print("✅ 浏览器资源清理完成")


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


def show_startup_banner():
    """显示启动横幅"""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "          🚀 ZX 智能答题助手 - 正在启动...          ".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print(flush=True)


if __name__ == "__main__":
    # 显示启动横幅
    show_startup_banner()

    # 解析命令行参数
    args = parse_arguments()

    # 注册退出清理处理器（所有模式都需要）
    register_cleanup_handlers()

    # 决定使用哪种模式
    if args.cli:
        # CLI模式（不显示浏览器和Flet信息）
        # 禁用日志输出，保持界面整洁
        import logging
        logging.disable(logging.CRITICAL)

        # 也禁用 Playwright 和其他模块的日志
        for logger_name in ['src.core.browser', 'src.auth.student', 'src.auth.teacher', 'playwright']:
            logging.getLogger(logger_name).setLevel(logging.CRITICAL)

        main()
    else:
        # GUI模式（默认）
        run_gui_mode()
