"""
浏览器安装与检测模块

提供 Playwright 浏览器的安装、检测、通道选择等功能。
所有函数均为无状态的模块级函数（原 BrowserManager 的 installer 方法提取）。
"""

from typing import Dict, Tuple
from pathlib import Path
import subprocess
import logging
import sys
import os

logger = logging.getLogger(__name__)


def check_playwright_browser() -> Tuple[bool, str]:
    """检查 Playwright 浏览器是否已安装。

    Returns:
        Tuple[bool, str]: (是否已安装, 错误信息)
    """
    from playwright.sync_api import sync_playwright, Error as PlaywrightError

    try:
        with sync_playwright() as p:
            try:
                executable_path = p.chromium.executable_path
                if Path(executable_path).exists():
                    logger.info(f"Chromium 浏览器已安装: {executable_path}")
                    return True, ""
                else:
                    return False, f"浏览器可执行文件不存在: {executable_path}"
            except (PlaywrightError, RuntimeError, OSError) as e:
                return False, f"无法获取浏览器路径: {str(e)}"
    except (PlaywrightError, RuntimeError, OSError) as e:
        return False, f"Playwright 浏览器检查失败: {str(e)}"


def install_playwright_browser(show_progress: bool = True) -> Tuple[bool, str]:
    """安装 Playwright 浏览器。

    Args:
        show_progress: 是否显示安装进度

    Returns:
        Tuple[bool, str]: (是否成功, 错误信息)
    """
    if show_progress:
        logger.info("开始安装 Playwright Chromium 浏览器...")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            timeout=600  # 10分钟超时
        )

        if result.returncode == 0:
            if show_progress:
                logger.info("[OK] Playwright 浏览器安装成功！")
            return True, ""
        else:
            error_msg = result.stderr or result.stdout or "未知错误"
            if show_progress:
                logger.error(f"✗ 浏览器安装失败: {error_msg}")
            return False, error_msg

    except subprocess.TimeoutExpired:
        error_msg = "浏览器安装超时（10分钟）"
        if show_progress:
            logger.error(f"✗ {error_msg}")
        return False, error_msg
    except OSError as e:
        error_msg = f"安装过程出错: {str(e)}"
        if show_progress:
            logger.error(f"✗ {error_msg}")
        return False, error_msg


def install_from_local_directory(local_path: str) -> Tuple[bool, str]:
    """从本地目录安装 Playwright 浏览器。

    Args:
        local_path: 本地浏览器路径或包含浏览器的目录

    Returns:
        Tuple[bool, str]: (是否成功, 错误信息)
    """
    logger.info(f"尝试从本地路径安装浏览器: {local_path}")

    try:
        local_path_obj = Path(local_path)

        if not local_path_obj.exists():
            return False, f"指定的路径不存在: {local_path}"

        if local_path_obj.is_dir():
            possible_executables = [
                local_path_obj / "chrome.exe" if os.name == 'nt' else local_path_obj / "chrome",
                local_path_obj / "chromium.exe" if os.name == 'nt' else local_path_obj / "chromium",
                local_path_obj / "chrome" / "chrome.exe" if os.name == 'nt' else local_path_obj / "chrome" / "chrome",
            ]

            executable_path = None
            for possible_path in possible_executables:
                if possible_path.exists():
                    executable_path = possible_path
                    break

            if executable_path:
                logger.info(f"找到本地浏览器: {executable_path}")
                os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = str(executable_path)
                return True, ""
            else:
                return False, f"在目录中未找到浏览器可执行文件: {local_path}"

        elif local_path_obj.is_file():
            logger.info(f"使用指定的浏览器文件: {local_path_obj}")
            os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = str(local_path_obj)
            return True, ""

        return False, f"无效的路径类型: {local_path}"

    except (OSError, TypeError) as e:
        return False, f"从本地目录安装失败: {str(e)}"


def detect_system_browsers() -> Dict[str, str]:
    """检测系统中已安装的浏览器。

    Returns:
        Dict[str, str]: 可用浏览器及其路径，格式 {"chrome": "路径", "msedge": "路径"}
    """
    browsers = {}

    try:
        if sys.platform == 'win32':
            chrome_paths = [
                Path(os.environ.get('PROGRAMFILES', 'C:\\Program Files')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
                Path(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
                Path(os.environ.get('LOCALAPPDATA', '')) / 'Google' / 'Chrome' / 'Application' / 'chrome.exe',
            ]
            edge_paths = [
                Path(os.environ.get('PROGRAMFILES', 'C:\\Program Files')) / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe',
                Path(os.environ.get('PROGRAMFILES(X86)', 'C:\\Program Files (x86)')) / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe',
            ]

        elif sys.platform == 'linux':
            chrome_paths = [
                Path('/usr/bin/google-chrome'),
                Path('/usr/bin/google-chrome-stable'),
                Path('/opt/google/chrome/chrome'),
            ]
            edge_paths = [
                Path('/usr/bin/microsoft-edge'),
                Path('/opt/microsoft-edge/msedge'),
            ]

        elif sys.platform == 'darwin':
            chrome_paths = [
                Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
            ]
            edge_paths = [
                Path('/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'),
            ]
        else:
            return browsers

        for path in chrome_paths:
            if path.exists():
                browsers['chrome'] = str(path)
                logger.info(f"[OK] 检测到 Google Chrome: {path}")
                break

        for path in edge_paths:
            if path.exists():
                browsers['msedge'] = str(path)
                logger.info(f"[OK] 检测到 Microsoft Edge: {path}")
                break

        if not browsers:
            logger.warning("未检测到系统浏览器（Chrome 或 Edge）")

    except (OSError, TypeError) as e:
        logger.error(f"检测系统浏览器时出错: {e}")

    return browsers


def get_available_browser_channel() -> Tuple[str, str]:
    """获取可用的浏览器通道。

    Returns:
        Tuple[str, str]: (浏览器通道, 显示信息)

    优先级：
    1. 配置文件中指定的浏览器通道
    2. 自动检测系统浏览器
    3. 使用 Playwright 内置浏览器
    """
    from src.core.browser import BrowserChannel

    try:
        from src.core.config import get_settings_manager
        settings = get_settings_manager()
        config_channel = settings.get_browser_channel()

        if config_channel and config_channel != BrowserChannel.BUNDLED.value:
            if config_channel in ['chrome', 'msedge']:
                system_browsers = detect_system_browsers()
                if config_channel in system_browsers:
                    logger.info(f"[OK] 使用配置的浏览器通道: {config_channel}")
                    return config_channel, f"使用系统浏览器: {BrowserChannel.from_string(config_channel).get_display_name()}"
                else:
                    logger.warning(f"⚠️ 配置的浏览器通道 '{config_channel}' 不可用，将尝试其他选项")

        system_browsers = detect_system_browsers()
        if system_browsers:
            if 'chrome' in system_browsers:
                logger.info("[OK] 自动选择系统 Google Chrome")
                return 'chrome', "自动选择系统浏览器: Google Chrome"
            elif 'msedge' in system_browsers:
                logger.info("[OK] 自动选择系统 Microsoft Edge")
                return 'msedge', "自动选择系统浏览器: Microsoft Edge"

        logger.info("[OK] 使用 Playwright 内置浏览器")
        return '', "使用 Playwright 内置浏览器"

    except (ImportError, AttributeError, KeyError, TypeError, ValueError, OSError) as e:
        logger.warning(f"获取浏览器通道配置时出错: {e}，使用默认配置")
        return '', "使用 Playwright 内置浏览器（配置读取失败）"


def ensure_browser_installed(local_browser_path: str = None) -> Tuple[bool, str, bool]:
    """确保浏览器已安装，提供多种备选方案。

    Args:
        local_browser_path: 本地浏览器路径（可选）

    Returns:
        Tuple[bool, str, bool]: (是否成功, 错误信息, 是否已确认安装)
    """
    logger.info("检查 Playwright 浏览器安装状态...")

    # 方案1: 检查浏览器是否已安装
    is_installed, error_msg = check_playwright_browser()
    if is_installed:
        return True, "", True

    logger.warning(f"浏览器未安装: {error_msg}")

    # 方案2: 使用指定的本地浏览器
    if local_browser_path:
        logger.info(f"尝试使用本地浏览器: {local_browser_path}")
        success, error = install_from_local_directory(local_browser_path)
        if success:
            return True, "", True
        else:
            logger.warning(f"本地浏览器设置失败: {error}")

    # 方案3: 自动安装浏览器
    logger.info("尝试自动安装浏览器...")
    success, error = install_playwright_browser(show_progress=True)
    if success:
        return True, "", True

    # 所有方案都失败
    error_msg = f"""
    ================================================
    浏览器安装失败！
    ================================================

    自动安装失败原因: {error}

    请尝试以下备选方案:

    方案1: 手动安装浏览器
    ------------------------
    打开命令行，执行以下命令:
        python -m playwright install chromium

    方案2: 使用本地浏览器
    ------------------------
    如果您已经有 Chromium 浏览器，可以指定路径:
    1. 在应用设置中配置，或编辑用户配置目录中的 cli_config.json
    2. 添加: "local_browser_path": "浏览器路径"
    3. Windows 示例: "C:\\Program Files\\Chromium\\chrome.exe"
    4. Linux/Mac 示例: "/usr/bin/chromium"

    方案3: 下载 Playwright 浏览器到本地
    ------------------------
    1. 访问: https://playwright.dev/python/docs/cli
    2. 下载对应平台的 Chromium 浏览器
    3. 解压到指定目录
    4. 使用方案2指定路径

    详细文档: {Path(__file__).parent.parent / "docs" / "BROWSER_SETUP.md"}
    ================================================
    """
    return False, error_msg.strip(), False
