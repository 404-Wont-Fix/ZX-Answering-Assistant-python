"""
ZX Answering Assistant - Main Entry Point
智能答题助手系统

纯 GUI 模式应用启动入口
"""

import sys
from pathlib import Path
import os
import atexit

# 在打包环境中，确保 exit 函数可用（Flet 内部可能使用 exit()）
# 兼容 __builtins__ 是字典或模块的情况
try:
    if 'exit' not in dir(__builtins__):
        if isinstance(__builtins__, dict):
            __builtins__['exit'] = lambda code=0: sys.exit(code)
        else:
            __builtins__.exit = lambda code=0: sys.exit(code)
except (TypeError, AttributeError):
    # 如果上述方法失败，直接添加到字典中
    if isinstance(__builtins__, dict):
        __builtins__['exit'] = lambda code=0: sys.exit(code)

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

# 【重要】在所有网络操作之前配置 SSL 证书
# 这必须在导入 Flet 或 Playwright 之前完成
def _setup_ssl():
    """配置 SSL 证书，解决 Windows 下 certifi 根证书问题"""
    try:
        import certifi, ssl as _ssl
        cert_path = certifi.where()
        os.environ['SSL_CERT_FILE'] = cert_path
        os.environ['REQUESTS_CA_BUNDLE'] = cert_path
        os.environ['CURL_CA_BUNDLE'] = cert_path
        _ssl._create_default_https_context = lambda: _ssl.create_default_context(cafile=cert_path)
    except ImportError:
        pass  # certifi 未安装时使用系统证书

_setup_ssl()

# 导入版本信息
import version

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
                            raise Exception(f"安装命令执行失败（返回码: {result.returncode})")

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
    程序退出时的清理函数（atexit 兜底）。

    正常情况下 main.py 的 finally 已用 os._exit(0) 结束进程，atexit 不会执行；
    此函数仅在其它退出路径（如显式 sys.exit）下作为最后兜底，强杀子进程树。
    """
    try:
        from src.core.browser import get_browser_manager
        get_browser_manager().force_kill_process_tree()
    except Exception as e:
        print(f"⚠️ [atexit] 清理浏览器时出错: {e}")


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
        # 【重要】在 Flet 尝试下载可执行文件之前配置 SSL
        # Flet 首次运行时会从 GitHub 下载可执行文件，需要正确的 SSL 证书
        import ssl, urllib.request
        try:
            import certifi
            urllib.request.ssl_context = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            pass
        if not silent:
            log("[OK] SSL 证书已配置（用于 Flet 下载）")

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

        # 检查 Flet 库安装状态
        print("   ✓ 检查 Flet 库...")
        from src.core.flet_installer import ensure_flet_installed
        flet_ok, flet_error = ensure_flet_installed(auto_install=False)
        if not flet_ok:
            print()
            print("❌ Flet 库检查失败！")
            print(f"错误信息: {flet_error}")
            print()
            print("💡 请手动安装 Flet 库:")
            print("   pip install flet>=0.82.0")
            print("   或")
            print("   pip install -r requirements.txt")
            print()
            input("按 Enter 键退出...")
            sys.exit(1)

        print("   ✓ Flet 库就绪")

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
        # 直接强杀整棵子进程树（Node driver + 浏览器 + 渲染进程）。
        # 注意：不再调用 cleanup_browser()/close_browser()/manager.close_browser()——
        # 它们会派发到 Playwright 工作线程，submit_task 内部 future.result(timeout=300)
        # 在工作线程卡住时会阻塞最多 5 分钟，反而拖慢甚至卡死退出流程。
        # force_kill_process_tree 已能彻底清理（递归杀掉全部后代进程）。
        try:
            from src.core.browser import get_browser_manager
            get_browser_manager().force_kill_process_tree()
        except Exception:
            pass
        print("✅ 浏览器资源清理完成")
        # 终极兜底：直接强制退出进程。
        # Flet + Playwright 在 Windows 上退出时，asyncio 管道与守护线程可能让解释器无法自然退出，
        # 导致终端挂起。资源已在上面清理完毕，此处 os._exit 保证进程立即结束。
        try:
            sys.stdout.flush()
        except Exception:
            pass
        import os as _os
        _os._exit(0)


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

    # 注册退出清理处理器
    register_cleanup_handlers()

    # 启动GUI模式
    run_gui_mode()
