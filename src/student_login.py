"""
学生端登录功能模块
用于获取学生端系统的access_token

已重构为使用统一的浏览器管理器 (src/browser_manager.py)
- 使用单浏览器 + 多上下文模式
- 支持与教师端、课程认证模块同时运行
- 上下文之间完全隔离，互不干扰
"""

from playwright.sync_api import Browser, Page, BrowserContext
from typing import Optional, List, Dict, Tuple
import time
import json
import logging
import requests
import sys
import io

# 导入浏览器管理器
from src.browser_manager import (
    get_browser_manager,
    BrowserType,
    run_in_thread_if_asyncio
)

# 创建自定义的 StreamHandler 来处理 Unicode 编码
class UTF8StreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # 尝试使用 UTF-8 编码，如果失败则使用 errors='replace'
            if hasattr(stream, 'buffer'):
                stream.buffer.write(msg.encode('utf-8') + b'\n')
            else:
                stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('student_login.log', encoding='utf-8'),
        UTF8StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# 全局变量，缓存access_token
_cached_access_token = None
_token_expiry_time = None  # token过期时间（5小时有效期）


# ============================================================================
# 浏览器管理辅助函数（使用 BrowserManager）
# ============================================================================

def _get_browser_manager():
    """获取浏览器管理器实例"""
    return get_browser_manager()


def _ensure_context_and_page() -> Tuple[Optional[BrowserContext], Optional[Page]]:
    """
    确保学生端上下文和页面存在

    Returns:
        Tuple[Optional[BrowserContext], Optional[Page]]: (上下文, 页面)
    """
    manager = _get_browser_manager()
    context, page = manager.get_context_and_page(BrowserType.STUDENT)

    if context is None or page is None:
        # 创建新的上下文和页面
        context = manager.create_context(BrowserType.STUDENT)
        page = context.new_page()
        logger.info("已创建学生端浏览器上下文和页面")

    return context, page


def _get_student_browser() -> Tuple[Optional[Browser], Optional[Page]]:
    """
    获取学生端的浏览器实例和页面（向后兼容）

    Returns:
        Tuple[Optional[Browser], Optional[Page]]: (浏览器, 页面)
    """
    manager = _get_browser_manager()
    browser = manager.get_browser()
    _, page = manager.get_context_and_page(BrowserType.STUDENT)
    return browser, page


def get_student_access_token(username: str = None, password: str = None, keep_browser: bool = True) -> Optional[str]:
    """
    使用Playwright模拟浏览器登录获取学生端access_token

    Args:
        username: 学生账户，如果为None则从配置读取或询问用户输入
        password: 学生密码，如果为None则从配置读取或询问用户输入
        keep_browser: 是否保持浏览器开启，默认为True

    Returns:
        Optional[str]: 获取到的access_token，如果失败则返回None
    """
    # 使用浏览器管理器的 AsyncIO 兼容函数
    return run_in_thread_if_asyncio(_get_student_access_token_impl, username, password, keep_browser)


def _get_student_access_token_impl(username: str = None, password: str = None, keep_browser: bool = True) -> Optional[str]:
    """
    学生端登录的实际实现（内部方法）

    Args:
        username: 学生账户
        password: 学生密码
        keep_browser: 是否保持浏览器开启

    Returns:
        Optional[str]: 获取到的access_token，如果失败则返回None
    """
    try:
        # 如果没有提供用户名和密码，尝试从配置读取或询问用户
        if username is None or password is None:
            try:
                from src.settings import get_settings_manager
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
                    # 配置中没有保存的凭据，询问用户输入
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
                # 如果读取配置失败，继续询问用户输入
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

        # 存储获取到的access_token
        access_token = None

        # 使用浏览器管理器
        manager = _get_browser_manager()
        manager.start_browser(headless=None)  # 从配置文件读取无头模式设置

        # 获取或创建学生端上下文
        context = manager.get_context(BrowserType.STUDENT)
        if context is None:
            context = manager.create_context(
                BrowserType.STUDENT,
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
            )

        # 创建页面
        page = context.new_page()

        try:
            # 设置请求拦截器，监听网络请求
            def handle_request(request):
                # 监听token请求
                if "/connect/token" in request.url and request.method == "POST":
                    logger.info(f"捕获到token请求: {request.url}")

            def handle_response(response):
                nonlocal access_token
                # 监听token响应
                if "/connect/token" in response.url and response.status == 200:
                    try:
                        response_body = response.body()
                        response_data = json.loads(response_body.decode('utf-8'))
                        if "access_token" in response_data:
                            access_token = response_data["access_token"]
                            logger.info(f"成功获取access_token: {access_token[:20]}...")
                    except Exception as e:
                        logger.error(f"解析token响应失败: {str(e)}")

            page.on("request", handle_request)
            page.on("response", handle_response)

            # 打开学生端登录页面
            login_url = "https://ai.cqzuxia.com/#/login"
            logger.info(f"正在访问登录页面: {login_url}")
            page.goto(login_url)

            # 等待页面加载完成
            logger.info("等待页面加载完成...")
            page.wait_for_selector("input[placeholder='请输入账户']", timeout=10000)

            # 输入用户名
            logger.info("正在输入用户名...")
            page.fill("input[placeholder='请输入账户']", username)

            # 输入密码
            logger.info("正在输入密码...")
            page.fill("input[placeholder='请输入密码']", password)

            # 等待一下，确保输入完成
            time.sleep(0.5)

            # 点击登录按钮
            logger.info("点击登录按钮...")
            # 等待登录按钮可点击
            page.wait_for_selector(".loginbtn", timeout=5000, state="visible")

            # 尝试多种方式点击登录按钮
            try:
                # 方法1: 使用类选择器点击
                page.click(".loginbtn", timeout=3000)
            except Exception as e:
                logger.warning(f"使用类选择器点击失败: {str(e)}")
                try:
                    # 方法2: 使用文本选择器点击
                    page.click("text=登录", timeout=3000)
                except Exception as e2:
                    logger.warning(f"使用文本选择器点击失败: {str(e2)}")
                    # 方法3: 使用JS强制点击
                    page.evaluate("document.querySelector('.loginbtn').click()")
                    logger.info("使用JavaScript强制点击登录按钮")

            # 等待登录成功或获取到token
            try:
                # 等待最多20秒获取token
                start_time = time.time()
                while not access_token and (time.time() - start_time) < 20:
                    time.sleep(0.3)
                    # 检查是否有错误提示
                    try:
                        error_element = page.query_selector(".el-message--error, .el-message.error")
                        if error_element:
                            error_text = error_element.text_content()
                            logger.error(f"登录错误提示: {error_text}")
                    except:
                        pass

                if access_token:
                    logger.info("✅ 成功获取access_token")
                    # 缓存access_token
                    set_access_token(access_token)
                    # 等待一下确保完全获取到token
                    time.sleep(0.5)

                    # 如果不需要保持浏览器，关闭页面
                    if not keep_browser:
                        page.close()
                        logger.info("学生端页面已关闭")

                    return access_token
                else:
                    # 检查是否登录成功
                    current_url = page.url
                    logger.info(f"当前页面URL: {current_url}")
                    if "home" in current_url or "home-2024" in current_url:
                        logger.warning("⚠️ 登录成功但未捕获到access_token")
                        if not keep_browser:
                            page.close()
                        return None
                    else:
                        logger.error("❌ 登录失败，未跳转到主页")
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
                except:
                    pass
            return None

    except Exception as e:
        logger.error(f"Playwright登录异常：{str(e)}")
        return None


def get_student_access_token_with_credentials() -> Optional[str]:
    """
    获取学生端access_token，使用用户输入的凭据

    Returns:
        Optional[str]: 获取到的access_token，如果失败则返回None
    """
    # 尝试从配置文件读取凭据
    try:
        from src.settings import get_settings_manager
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
        pass  # 如果读取配置失败，继续手动输入

    # 获取用户输入的用户名和密码
    username = input("请输入学生账户（直接回车使用默认账户）: ").strip()
    password = input("请输入学生密码（直接回车使用默认密码）: ").strip()

    # 如果用户没有输入，则使用默认账户
    if not username:
        username = None
    if not password:
        password = None

    return get_student_access_token(username, password)


def get_browser_page() -> Optional[Tuple[Browser, Page]]:
    """
    获取当前的浏览器实例和页面
    如果浏览器已挂掉，自动清理并返回None

    Returns:
        Optional[Tuple[Browser, Page]]: 浏览器和页面的元组，如果不存在则返回None
    """
    # 检查浏览器是否存活
    if not is_browser_alive():
        logger.warning("⚠️ 浏览器已挂掉，已自动清理")
        return None

    manager = _get_browser_manager()
    browser = manager.get_browser()
    _, page = manager.get_context_and_page(BrowserType.STUDENT)

    if browser and page:
        return browser, page
    return None


def get_access_token_from_browser() -> Optional[str]:
    """
    从已登录的浏览器中提取access_token
    通过刷新页面并监听/connect/token API来获取

    Returns:
        Optional[str]: 提取到的access_token，如果失败则返回None
    """
    try:
        manager = _get_browser_manager()
        _, page = manager.get_context_and_page(BrowserType.STUDENT)

        if not page:
            logger.error("❌ 浏览器未初始化，请先登录")
            return None

        logger.info("🔍 从浏览器中提取access_token...")

        # 方法1：先尝试从localStorage获取
        js_code = """
        () => {
            // 检查常见的token存储位置
            const keys = ['access_token', 'token', 'auth_token', 'student_token', 'oidc.user:https://ai.cqzuxia.com:zhzx'];

            for (let key of keys) {
                const value = localStorage.getItem(key);
                if (value) {
                    // 如果是JSON格式（oidc），尝试解析
                    try {
                        const parsed = JSON.parse(value);
                        if (parsed.access_token) {
                            return parsed.access_token;
                        }
                    } catch (e) {
                        // 不是JSON，直接返回
                        if (value.length > 50) {
                            return value;
                        }
                    }
                }
            }

            return null;
        }
        """

        result = page.evaluate(js_code)

        if result and len(result) > 50:
            logger.info(f"✅ 从localStorage提取到access_token: {result[:20]}...")
            return result

        # 方法2：刷新页面并监听网络请求
        logger.info("💡 localStorage中未找到，尝试刷新页面获取...")

        access_token = None

        def handle_response(response):
            nonlocal access_token
            if "/connect/token" in response.url and response.status == 200:
                try:
                    response_body = response.body()
                    response_data = json.loads(response_body.decode('utf-8'))
                    if "access_token" in response_data:
                        access_token = response_data["access_token"]
                        logger.info(f"✅ 拦截到access_token")
                except Exception as e:
                    logger.debug(f"解析token响应失败: {str(e)}")

        # 添加监听器
        page.on("response", handle_response)

        # 刷新页面触发token请求
        current_url = page.url
        if "ai.cqzuxia.com" in current_url:
            logger.info("正在刷新页面...")
            page.reload(wait_until="networkidle")
        else:
            logger.info("正在导航到登录页...")
            page.goto("https://ai.cqzuxia.com/#/login", wait_until="networkidle")

        # 等待获取token
        start_time = time.time()
        while not access_token and (time.time() - start_time) < 10:
            time.sleep(0.3)

        if access_token:
            logger.info(f"✅ 成功从浏览器提取access_token: {access_token[:20]}...")
            return access_token
        else:
            logger.warning("⚠️ 浏览器中未找到有效的access_token")
            logger.info("💡 提示：请确保已经在浏览器中登录学生端")
            return None

    except Exception as e:
        logger.error(f"❌ 从浏览器提取access_token失败: {str(e)}")
        return None


def navigate_to_course(course_id: str) -> bool:
    """
    使用已登录的浏览器导航到指定课程的答题页面
    如果浏览器已挂掉，自动清理并返回False

    Args:
        course_id: 课程ID

    Returns:
        bool: 成功返回True，失败返回False
    """
    try:
        # 检查浏览器是否存活
        if not ensure_browser_alive():
            logger.error("❌ 浏览器不可用，请重新登录")
            return False

        manager = _get_browser_manager()
        _, page = manager.get_context_and_page(BrowserType.STUDENT)

        if not page:
            logger.error("❌ 浏览器未初始化，请先登录")
            return False

        # 构建答题页面URL
        evaluation_url = f"https://ai.cqzuxia.com/#/evaluation/knowledge-detail/{course_id}"

        logger.info(f"正在导航到课程页面: {evaluation_url}")
        page.goto(evaluation_url, wait_until="networkidle")

        # 刷新页面以确保正确加载
        logger.info("正在刷新页面...")
        page.reload(wait_until="networkidle")

        logger.info("✅ 成功导航到答题页面")
        return True

    except Exception as e:
        logger.error(f"❌ 导航到课程页面失败: {str(e)}")
        # 如果操作失败，可能浏览器已挂掉，尝试清理
        if not is_browser_alive():
            logger.warning("⚠️ 浏览器可能在操作过程中挂掉，已自动清理")
        return False


def close_browser():
    """
    关闭学生端浏览器上下文
    注意：这只关闭学生端上下文，不会关闭整个浏览器（可能还有其他模块在使用）
    """
    try:
        manager = _get_browser_manager()
        manager.cleanup_type(BrowserType.STUDENT)
        logger.info("学生端浏览器上下文已关闭")
    except Exception as e:
        logger.error(f"关闭浏览器时发生错误: {str(e)}")


def get_uncompleted_chapters(access_token: str, course_id: str, delay_ms: int = 600, max_retries: int = 3) -> Optional[List[Dict]]:
    """
    使用access_token和课程ID获取未完成的知识点列表

    Args:
        access_token: 学生端的access_token
        course_id: 课程ID
        delay_ms: 请求延迟（毫秒），默认600毫秒（已弃用，请使用设置菜单配置）
        max_retries: 最大重试次数，默认3次（已弃用，请使用设置菜单配置）

    Returns:
        Optional[List[Dict]]: 未完成的知识点列表，如果失败则返回None
    """
    # 使用API客户端发送请求
    try:
        from src.api_client import get_api_client

        api_client = get_api_client()

        # API端点
        url = f"https://ai.cqzuxia.com/evaluation/api/StuEvaluateReport/GetUnCompleteChapterList?CourseID={course_id}"

        # 请求头
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9",
            "authorization": f"Bearer {access_token}",
            "priority": "u=1, i",
            "referer": "https://ai.cqzuxia.com/",
            "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        }

        # 如果明确指定了max_retries且大于0，使用它（向后兼容）
        actual_max_retries = max_retries if max_retries > 0 else None

        logger.info(f"正在获取课程 {course_id} 的未完成知识点列表...")
        logger.info(f"发送请求到: {url}")

        # 发送GET请求
        response = api_client.request("GET", url, headers=headers, max_retries=actual_max_retries)

        if response and response.status_code == 200:
            logger.info(f"✅ 请求成功，状态码: {response.status_code}")

            try:
                data = response.json()

                # 检查返回的数据结构
                if isinstance(data, dict):
                    # 如果返回的是字典，提取data字段
                    if "data" in data and data.get("success"):
                        chapters_data = data["data"]
                    else:
                        logger.error(f"API返回错误: {data}")
                        return None
                else:
                    logger.error(f"未知的数据格式: {type(data)}")
                    return None

                # 解析嵌套的章节-知识点结构
                all_knowledges = []
                for chapter in chapters_data:
                    chapter_id = chapter.get('id', 'N/A')
                    chapter_title = chapter.get('title', 'N/A')
                    chapter_content = chapter.get('titleContent', '')

                    knowledge_list = chapter.get('knowledgeList', [])
                    for knowledge in knowledge_list:
                        knowledge_id = knowledge.get('id', 'N/A')
                        knowledge_name = knowledge.get('knowledge', 'N/A')

                        all_knowledges.append({
                            'id': chapter_id,
                            'title': chapter_title,
                            'titleContent': chapter_content,
                            'knowledge_id': knowledge_id,
                            'knowledge': knowledge_name
                        })

                logger.info(f"✅ 成功获取 {len(all_knowledges)} 个未完成知识点")
                return all_knowledges

            except Exception as e:
                logger.error(f"解析JSON响应失败: {str(e)}")
                logger.error(f"响应内容: {response.text[:500] if response else 'N/A'}")
                return None
        else:
            status_code = response.status_code if response else "N/A"
            logger.error(f"❌ 请求失败，状态码: {status_code}")
            logger.error(f"响应内容: {response.text[:500] if response else 'N/A'}")
            return None

    except Exception as e:
        logger.error(f"❌ 获取未完成知识点列表异常: {str(e)}")
        return None


def get_course_progress_from_page() -> Optional[Dict]:
    """
    从当前页面解析课程进度信息
    如果浏览器已挂掉，自动清理并返回None

    Returns:
        Optional[Dict]: 包含进度信息的字典:
            {
                'total': int,  # 总知识点数
                'completed': int,  # 已完成数
                'failed': int,  # 做错过的数
                'not_started': int,  # 未开始的数
                'progress_percentage': float  # 完成百分比
            }
            如果失败则返回None
    """
    try:
        # 检查浏览器是否存活
        if not ensure_browser_alive():
            logger.error("❌ 浏览器不可用，无法获取进度")
            return None

        manager = _get_browser_manager()
        _, page = manager.get_context_and_page(BrowserType.STUDENT)

        if not page:
            logger.error("❌ 页面未初始化")
            return None

        # 等待页面加载完成
        page.wait_for_selector(".el-menu-item", timeout=10000)

        # 获取所有的知识点菜单项
        knowledge_items = page.query_selector_all(".el-menu-item")

        total = len(knowledge_items)
        completed = 0
        failed = 0
        not_started = 0

        for item in knowledge_items:
            # 获取pass-status元素
            pass_status = item.query_selector(".pass-status")
            if pass_status:
                # 获取check和close图标元素
                check_icon = pass_status.query_selector(".el-icon-check")
                close_icon = pass_status.query_selector(".el-icon-close")

                # 检查图标的display样式
                check_display = "none"
                close_display = "none"

                if check_icon:
                    check_style = check_icon.get_attribute("style") or ""
                    check_display = "none" if "display: none" in check_style or "display:none" in check_style else "block"

                if close_icon:
                    close_style = close_icon.get_attribute("style") or ""
                    close_display = "none" if "display: none" in close_style or "display:none" in close_style else "block"

                # 根据图标显示状态判断
                if check_display != "none" and close_display == "none":
                    # 只有check图标显示 - 已完成
                    completed += 1
                elif close_display != "none" and check_display == "none":
                    # 只有close图标显示 - 做错过（未通过）
                    failed += 1
                elif check_display == "none" and close_display == "none":
                    # 两个图标都不显示 - 未开始
                    not_started += 1
                else:
                    # 其他情况，检查class中是否有success标识
                    item_class = item.get_attribute("class") or ""
                    if "success" in item_class:
                        completed += 1
                    else:
                        not_started += 1
            else:
                # 检查class中是否有success标识
                item_class = item.get_attribute("class") or ""
                if "success" in item_class:
                    completed += 1
                else:
                    not_started += 1

        progress_percentage = (completed / total * 100) if total > 0 else 0

        progress_info = {
            'total': total,
            'completed': completed,
            'failed': failed,
            'not_started': not_started,
            'progress_percentage': progress_percentage
        }

        logger.info(f"✅ 成功解析课程进度: {progress_info}")
        return progress_info

    except Exception as e:
        logger.error(f"❌ 解析课程进度失败: {str(e)}")
        return None


def _get_student_courses_request(access_token: str) -> Optional[List[Dict]]:
    """
    获取学生端课程列表的实际请求逻辑（内部方法，用于重试）

    Args:
        access_token: 学生端的access_token

    Returns:
        Optional[List[Dict]]: 课程列表，如果失败则返回None
    """
    from src.api_client import get_api_client

    # API端点
    url = "https://ai.cqzuxia.com/evaluation/api/StuEvaluateReport/GetStuLatestTermCourseReports?"

    # 请求头
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9",
        "authorization": f"Bearer {access_token}",
        "priority": "u=1, i",
        "referer": "https://ai.cqzuxia.com/",
        "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    }

    logger.info(f"发送请求到: {url}")
    logger.info(f"使用token: {access_token[:20]}...")

    # 使用APIClient发送GET请求
    api_client = get_api_client()
    response = api_client.get(url, headers=headers)

    if response is None:
        return None

    # 检查响应状态（APIClient已经处理了重试，这里只需要处理成功的响应）
    if response.status_code == 200:
        logger.info(f"✅ 请求成功，状态码: {response.status_code}")

        try:
            data = response.json()

            # 打印完整的响应数据（用于调试）
            logger.info(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")

            # 检查返回的数据结构
            if isinstance(data, list):
                # 如果直接返回列表
                courses = data
            elif isinstance(data, dict):
                # 如果返回的是字典，尝试提取课程列表
                if "data" in data:
                    courses = data["data"]
                elif "success" in data and data["success"]:
                    courses = data.get("data", [])
                else:
                    logger.error(f"API返回错误: {data}")
                    return None
            else:
                logger.error(f"未知的数据格式: {type(data)}")
                return None

            return courses

        except json.JSONDecodeError as e:
            logger.error(f"解析JSON响应失败: {str(e)}")
            logger.error(f"响应内容: {response.text[:500]}")
            return None
    else:
        logger.error(f"❌ 请求失败，状态码: {response.status_code}")
        logger.error(f"响应内容: {response.text[:500]}")
        return None


def get_student_courses(access_token: str, max_retries: Optional[int] = None, delay: int = 2) -> Optional[List[Dict]]:
    """
    使用access_token获取学生端课程列表（带重试）

    Args:
        access_token: 学生端的access_token
        max_retries: 最大重试次数，如果不提供则从配置读取
        delay: 重试延迟（秒），默认2秒（保留用于向后兼容，实际使用APIClient的指数退避）

    Returns:
        Optional[List[Dict]]: 课程列表，如果失败则返回None
    """
    from src.api_client import get_api_client

    try:
        logger.info("正在获取学生端课程列表...")

        # API端点
        url = "https://ai.cqzuxia.com/evaluation/api/StuEvaluateReport/GetStuLatestTermCourseReports?"

        # 请求头
        headers = {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9",
            "authorization": f"Bearer {access_token}",
            "priority": "u=1, i",
            "referer": "https://ai.cqzuxia.com/",
            "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        }

        logger.info(f"发送请求到: {url}")
        logger.info(f"使用token: {access_token[:20]}...")

        # 使用APIClient发送GET请求（带重试）
        api_client = get_api_client()
        response = api_client.get(url, headers=headers, max_retries=max_retries)

        if response is None:
            return None

        # 检查响应状态
        if response.status_code == 200:
            logger.info(f"✅ 请求成功，状态码: {response.status_code}")

            try:
                data = response.json()

                # 打印完整的响应数据（用于调试）
                logger.info(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")

                # 检查返回的数据结构
                if isinstance(data, list):
                    # 如果直接返回列表
                    courses = data
                elif isinstance(data, dict):
                    # 如果返回的是字典，尝试提取课程列表
                    if "data" in data:
                        courses = data["data"]
                    elif "success" in data and data["success"]:
                        courses = data.get("data", [])
                    else:
                        logger.error(f"API返回错误: {data}")
                        return None
                else:
                    logger.error(f"未知的数据格式: {type(data)}")
                    return None

                return courses

            except json.JSONDecodeError as e:
                logger.error(f"解析JSON响应失败: {str(e)}")
                logger.error(f"响应内容: {response.text[:500]}")
                return None
        else:
            logger.error(f"❌ 请求失败，状态码: {response.status_code}")
            logger.error(f"响应内容: {response.text[:500]}")
            return None

    except Exception as e:
        logger.error(f"❌ 获取课程列表异常: {str(e)}")
        return None


# ==================== Access Token 管理函数 ====================

def set_access_token(token: str):
    """
    设置access_token缓存

    Args:
        token: access_token字符串
    """
    global _cached_access_token, _token_expiry_time
    _cached_access_token = token
    # token有效期5小时（18000秒），提前10分钟过期
    _token_expiry_time = time.time() + 18000 - 600
    logger.info(f"✅ access_token已缓存，有效期至: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(_token_expiry_time))}")


def get_cached_access_token() -> Optional[str]:
    """
    获取缓存的access_token
    如果token不存在或已过期，则自动从浏览器获取

    Returns:
        Optional[str]: 有效的access_token，如果获取失败则返回None
    """
    global _cached_access_token, _token_expiry_time

    # 检查缓存是否存在
    if not _cached_access_token:
        logger.info("💡 缓存中无access_token，尝试从浏览器获取...")
        return get_access_token_from_browser()

    # 检查token是否过期
    if _token_expiry_time and time.time() > _token_expiry_time:
        logger.warning("⚠️ 缓存的access_token已过期，重新获取...")
        return get_access_token_from_browser()

    # token有效，返回缓存的token
    logger.info(f"✅ 使用缓存的access_token: {_cached_access_token[:20]}...")
    return _cached_access_token


def clear_access_token():
    """清除access_token缓存"""
    global _cached_access_token, _token_expiry_time
    _cached_access_token = None
    _token_expiry_time = None
    logger.info("🗑️ access_token缓存已清除")


def is_token_valid() -> bool:
    """
    检查缓存的access_token是否有效

    Returns:
        bool: token是否有效
    """
    global _cached_access_token, _token_expiry_time
    if not _cached_access_token:
        return False
    if _token_expiry_time and time.time() > _token_expiry_time:
        return False
    return True


# ==================== 浏览器健康检查和恢复 ====================

def is_browser_alive() -> bool:
    """
    检查浏览器实例是否仍然存活

    Returns:
        bool: 浏览器是否存活
    """
    manager = _get_browser_manager()
    return manager.is_browser_alive()


def ensure_browser_alive() -> bool:
    """
    确保浏览器实例存活，如果浏览器挂掉则清理并准备重新登录

    Returns:
        bool: 浏览器是否可用
    """
    if is_browser_alive():
        return True

    # 浏览器已挂掉，清理旧实例
    logger.warning("⚠️ 检测到浏览器已挂掉，清理旧实例...")
    cleanup_browser()

    logger.info("✅ 浏览器实例已清理，请重新登录")
    return False


def cleanup_browser():
    """
    强制清理学生端浏览器实例（包括挂掉的浏览器）
    """
    global _cached_access_token, _token_expiry_time

    try:
        manager = _get_browser_manager()
        manager.cleanup_type(BrowserType.STUDENT)
    except Exception as e:
        logger.error(f"清理浏览器时发生错误: {str(e)}")
    finally:
        # 清空 token 缓存
        _cached_access_token = None
        _token_expiry_time = None
        logger.info("✅ 学生端浏览器实例已强制清理")


def restart_browser(username: str = None, password: str = None) -> Optional[str]:
    """
    重启浏览器并重新登录

    Args:
        username: 学生账户（可选）
        password: 学生密码（可选）

    Returns:
        Optional[str]: 新的access_token，如果失败则返回None
    """
    logger.info("🔄 正在重启浏览器...")

    # 清理旧实例
    cleanup_browser()

    # 重新登录
    return get_student_access_token(username, password, keep_browser=True)


def check_and_recover_browser() -> bool:
    """
    检查浏览器状态并尝试恢复

    Returns:
        bool: 浏览器是否可用
    """
    if not is_browser_alive():
        logger.warning("⚠️ 浏览器不可用，准备清理...")
        cleanup_browser()
        return False
    return True