"""
教师端登录功能模块
用于获取教师端系统的access_token

已重构为使用统一的浏览器管理器 (src/browser_manager.py)
- 使用单浏览器 + 多上下文模式
- 支持与学生端、课程认证模块同时运行
- 上下文之间完全隔离，互不干扰
"""

from playwright.sync_api import sync_playwright
from typing import Optional
import time
import logging

# 导入浏览器管理器
from src.browser_manager import (
    get_browser_manager,
    BrowserType,
    run_in_thread_if_asyncio
)

# 配置日志
logger = logging.getLogger(__name__)


def _get_browser_manager():
    """获取浏览器管理器实例"""
    return get_browser_manager()


def get_access_token() -> Optional[str]:
    """
    使用Playwright模拟浏览器登录获取教师端access_token

    Returns:
        Optional[str]: 获取到的access_token，如果失败则返回None
    """
    # 使用浏览器管理器的 AsyncIO 兼容函数
    return run_in_thread_if_asyncio(_get_access_token_impl)


def _get_access_token_impl() -> Optional[str]:
    """
    教师端登录的实际实现（内部方法）

    Returns:
        Optional[str]: 获取到的access_token，如果失败则返回None
    """
    try:
        logger.info("正在启动浏览器进行教师端登录...")
        print("正在启动浏览器进行教师端登录...")

        # 尝试从配置文件读取凭据
        try:
            from src.settings import get_settings_manager
            settings = get_settings_manager()
            config_username, config_password = settings.get_teacher_credentials()

            if config_username and config_password:
                print("\n💡 检测到已保存的教师端账号")
                use_saved = input("是否使用已保存的账号？(yes/no，默认yes): ").strip().lower()

                if use_saved in ['', 'yes', 'y', '是']:
                    print(f"✅ 使用已保存的账号: {config_username[:3]}****")
                    logger.info(f"使用已保存的账号: {config_username[:3]}****")
                    username = config_username
                    password = config_password
                else:
                    print("💡 请手动输入账号密码")
                    # 获取用户输入的用户名和密码
                    username = input("请输入教师账户：").strip()
                    password = input("请输入教师密码：").strip()
            else:
                # 获取用户输入的用户名和密码
                username = input("请输入教师账户：").strip()
                password = input("请输入教师密码：").strip()
        except Exception:
            # 如果读取配置失败，继续手动输入
            username = input("请输入教师账户：").strip()
            password = input("请输入教师密码：").strip()

        if not username or not password:
            print("❌ 用户名或密码不能为空")
            logger.error("用户名或密码不能为空")
            return None

        logger.info(f"使用账户: {username}")

        # 使用浏览器管理器
        manager = _get_browser_manager()
        logger.info("正在启动浏览器...")
        manager.start_browser(headless=None)  # 从配置文件读取无头模式设置
        logger.info("浏览器已启动")

        # 获取或创建教师端上下文
        logger.info("正在创建教师端浏览器上下文...")
        context = manager.get_context(BrowserType.TEACHER)
        if context is None:
            context = manager.create_context(
                BrowserType.TEACHER,
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
            )
            logger.info("教师端浏览器上下文已创建")
        else:
            logger.info("使用已存在的教师端浏览器上下文")

        # 创建页面
        logger.info("正在创建新页面...")
        page = context.new_page()

        try:
            # 打开教师端登录页面
            login_url = "https://admin.cqzuxia.com/#/login?redirect=%2F"
            logger.info(f"正在访问登录页面: {login_url}")
            print(f"正在访问登录页面: {login_url}")
            page.goto(login_url)

            # 等待页面加载完成
            logger.info("等待页面加载完成...")
            page.wait_for_selector("input[placeholder='请输入账户']", timeout=10000)
            logger.info("页面加载完成")

            # 输入用户名
            logger.info("正在输入用户名...")
            page.fill("input[placeholder='请输入账户']", username)

            # 输入密码
            logger.info("正在输入密码...")
            page.fill("input[placeholder='请输入密码']", password)

            # 点击登录按钮
            logger.info("点击登录按钮...")
            print("正在登录...")
            page.click("button:has-text('登录')")

            # 等待登录成功（URL变化或页面元素出现）
            try:
                # 等待登录成功，最多等待15秒
                logger.info("等待登录成功...")
                page.wait_for_url("**/", timeout=15000)
                logger.info("页面已跳转到主页，登录成功")
                print("✅ 登录成功，正在获取 access_token...")

                # 等待页面加载完成，确保cookies已经设置
                time.sleep(2)

                # 获取所有cookies
                logger.info("正在获取 cookies...")
                cookies = context.cookies()

                # 查找包含access_token的cookie
                access_token = None
                for cookie in cookies:
                    if cookie["name"] == "smartedu.admin.token":
                        access_token = cookie["value"]
                        logger.info(f"成功获取 access_token: {access_token[:20]}...")
                        break

                if access_token:
                    print("✅ 成功获取 access_token")
                    return access_token
                else:
                    logger.error("登录成功，但未找到 access_token cookie")
                    print("❌ 登录成功，但未找到 access_token cookie")
                    return None
            except Exception as e:
                logger.error(f"登录过程中发生错误：{str(e)}")
                print(f"❌ 登录过程中发生错误：{str(e)}")
                return None
            finally:
                # 关闭页面（上下文保留供后续使用）
                try:
                    page.close()
                    logger.info("页面已关闭")
                except:
                    pass

        except Exception as e:
            logger.error(f"登录过程异常：{str(e)}")
            print(f"❌ 登录过程异常：{str(e)}")
            return None

    except Exception as e:
        logger.error(f"Playwright登录异常：{str(e)}")
        print(f"❌ Playwright登录异常：{str(e)}")
        return None
