"""学生端登录（token 捕获）+ 浏览器重启。

从 src/auth/student.py 抽出。依赖 browser_manager + browser_health.cleanup_browser + token_manager。
"""

import json
import time
import logging
from typing import Optional

from src.core.browser import get_browser_manager, BrowserType, run_in_thread_if_asyncio
from ._student_browser_health import cleanup_browser
from src.auth.token_manager import get_token_manager

logger = logging.getLogger(__name__)
_token_manager = get_token_manager()


def get_student_access_token(
    username: str = None,
    password: str = None,
    keep_browser: bool = True,
    browser_type: BrowserType = BrowserType.STUDENT
) -> Optional[str]:
    """使用 Playwright 模拟浏览器登录获取学生端 access_token。"""
    return run_in_thread_if_asyncio(_get_student_access_token_impl, username, password, keep_browser, browser_type)


def _get_student_access_token_impl(
    username: str = None,
    password: str = None,
    keep_browser: bool = True,
    browser_type: BrowserType = BrowserType.STUDENT
) -> Optional[str]:
    """学生端登录的实际实现（内部方法）。"""
    try:
        # 如果没有提供用户名和密码，尝试从配置读取或询问用户
        if username is None or password is None:
            try:
                from src.core.config import get_settings_manager
                settings = get_settings_manager()
                config_username, config_password = settings.get_student_credentials()

                if config_username and config_password:
                    print("\n💡 检测到已保存的学生端账号")
                    use_saved = input("是否使用已保存的账号？(yes/no，默认yes): ").strip().lower()

                    if use_saved in ['', 'yes', 'y', '是']:
                        print(f"✅ 使用已保存的账号: {config_username[:3]}****")
                        username = config_username
                        password = config_password
                    else:
                        print("💡 请手动输入账号密码")
                        if username is None:
                            username = input("请输入学生账户: ").strip()
                            if not username:
                                print("❌ 账户不能为空")
                                return None
                        if password is None:
                            password = input("请输入学生密码: ").strip()
                            if not password:
                                print("❌ 密码不能为空")
                                return None
                else:
                    if username is None:
                        username = input("请输入学生账户: ").strip()
                        if not username:
                            print("❌ 账户不能为空")
                            return None
                    if password is None:
                        password = input("请输入学生密码: ").strip()
                        if not password:
                            print("❌ 密码不能为空")
                            return None
            except Exception:
                if username is None:
                    username = input("请输入学生账户: ").strip()
                    if not username:
                        print("❌ 账户不能为空")
                        return None
                if password is None:
                    password = input("请输入学生密码: ").strip()
                    if not password:
                        print("❌ 密码不能为空")
                        return None

        logger.info("正在启动浏览器进行学生端登录...")
        logger.info(f"使用账户: {username}")

        access_token = None

        manager = get_browser_manager()
        manager.start_browser(headless=None)

        context = manager.get_context(browser_type)
        if context is None:
            context = manager.create_context(
                browser_type,
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
            )

        page = manager.create_page(browser_type)
        logger.debug(f"学生端页面已创建并保存到浏览器管理器: {browser_type.value}")

        try:
            def handle_request(request):
                if "/connect/token" in request.url and request.method == "POST":
                    logger.info(f"捕获到token请求: {request.url}")

            def handle_response(response):
                nonlocal access_token
                if "/connect/token" in response.url:
                    logger.info(f"捕获到token响应: status={response.status}")
                    if response.status == 200:
                        try:
                            response_body = response.body()
                            response_data = json.loads(response_body.decode('utf-8'))
                            if "access_token" in response_data:
                                access_token = response_data["access_token"]
                                logger.info("✅ 成功获取access_token")
                            else:
                                logger.warning(f"⚠️ token响应缺少access_token字段，响应键: {list(response_data.keys())}")
                        except Exception as e:
                            logger.error(f"解析token响应失败: {str(e)}")
                    else:
                        logger.warning(f"⚠️ token响应状态码非200: {response.status}")

            page.on("request", handle_request)
            page.on("response", handle_response)

            login_url = "https://ai.cqzuxia.com/#/login"
            logger.info(f"正在访问登录页面: {login_url}")
            page.goto(login_url, timeout=30000)

            logger.info("等待页面加载完成...")
            page.wait_for_selector("input[placeholder='请输入账户']", timeout=10000)

            logger.info("正在输入用户名...")
            page.fill("input[placeholder='请输入账户']", username)

            logger.info("正在输入密码...")
            page.fill("input[placeholder='请输入密码']", password)

            time.sleep(0.5)

            logger.info("点击登录按钮...")
            page.wait_for_selector(".loginbtn", timeout=5000, state="visible")

            try:
                page.click(".loginbtn", timeout=3000)
            except Exception as e:
                logger.warning(f"使用类选择器点击失败: {str(e)}")
                try:
                    page.click("text=登录", timeout=3000)
                except Exception as e2:
                    logger.warning(f"使用文本选择器点击失败: {str(e2)}")
                    page.evaluate("document.querySelector('.loginbtn').click()")
                    logger.info("使用JavaScript强制点击登录按钮")

            try:
                start_time = time.time()
                while not access_token and (time.time() - start_time) < 40:
                    time.sleep(0.3)
                    try:
                        error_element = page.query_selector(".el-message--error, .el-message.error")
                        if error_element:
                            error_text = error_element.text_content()
                            logger.error(f"登录错误提示: {error_text}")
                    except Exception as e:
                        logger.debug(f"检查登录错误提示失败: {e}")

                if access_token:
                    logger.info("✅ 成功获取access_token")
                    _token_manager.set_student_token(access_token)
                    time.sleep(0.5)

                    if not keep_browser:
                        page.close()
                        logger.info("学生端页面已关闭")

                    return access_token
                else:
                    current_url = page.url
                    logger.info(f"当前页面URL: {current_url}（已等待 {time.time()-start_time:.0f} 秒）")
                    if "home" in current_url or "home-2024" in current_url:
                        logger.warning("⚠️ 页面已跳转主页但未捕获到access_token（token响应未到达或解析失败）")
                        if not keep_browser:
                            page.close()
                        return None
                    else:
                        logger.error("❌ 登录失败，未跳转到主页（可能凭证错误、网络超时或token响应事件未监听到）")
                        if not keep_browser:
                            page.close()
                        return None
            except Exception as e:
                logger.error(f"登录过程中发生错误：{str(e)}")
                if not keep_browser:
                    page.close()
                return None
        except Exception as e:
            logger.error(f"登录过程异常：{str(e)}")
            if not keep_browser:
                try:
                    page.close()
                except Exception:
                    pass
            return None

    except Exception as e:
        logger.error(f"Playwright登录异常：{str(e)}")
        return None


def get_student_access_token_with_credentials() -> Optional[str]:
    """获取学生端 access_token，使用用户输入的凭据。"""
    try:
        from src.core.config import get_settings_manager
        settings = get_settings_manager()
        config_username, config_password = settings.get_student_credentials()

        if config_username and config_password:
            print("\n💡 检测到已保存的学生端账号")
            use_saved = input("是否使用已保存的账号？(yes/no，默认yes): ").strip().lower()

            if use_saved in ['', 'yes', 'y', '是']:
                print(f"✅ 使用已保存的账号: {config_username[:3]}****")
                return get_student_access_token(config_username, config_password)
            else:
                print("💡 请手动输入账号密码")
    except Exception:
        pass

    username = input("请输入学生账户（直接回车使用默认账户）: ").strip()
    password = input("请输入学生密码（直接回车使用默认密码）: ").strip()

    if not username:
        username = None
    if not password:
        password = None

    return get_student_access_token(username, password)


def restart_browser(username: str = None, password: str = None) -> Optional[str]:
    """重启浏览器并重新登录（清理旧实例 + 重新登录）。"""
    logger.info("🔄 正在重启浏览器...")
    cleanup_browser()
    return get_student_access_token(username, password, keep_browser=True)
