"""学生端浏览器 page 操作（导航/进度解析/token 提取/取 page）。

从 src/auth/student.py 抽出。依赖 _student_browser_health 的 ensure_browser_alive/is_browser_alive。
"""

import json
import time
import logging
from typing import Dict, Optional, Tuple

from playwright.sync_api import Browser, BrowserContext, Page

from src.core.browser import get_browser_manager, BrowserType, run_in_thread_if_asyncio
from ._student_browser_health import ensure_browser_alive, is_browser_alive

logger = logging.getLogger(__name__)


def _ensure_context_and_page(browser_type: BrowserType = BrowserType.STUDENT) -> Tuple[Optional[BrowserContext], Optional[Page]]:
    """确保学生端上下文和页面存在。"""
    manager = get_browser_manager()
    context, page = manager.get_context_and_page(browser_type)

    if context is None or page is None:
        context = manager.create_context(browser_type)
        page = manager.create_page(browser_type)
        logger.info(f"已创建浏览器上下文和页面: {browser_type.value}")

    return context, page


def _get_student_browser() -> Tuple[Optional[Browser], Optional[Page]]:
    """获取学生端的浏览器实例和页面（向后兼容）。"""
    manager = get_browser_manager()
    browser = manager.get_browser()
    _, page = manager.get_context_and_page(BrowserType.STUDENT)
    return browser, page


def get_browser_page() -> Optional[Tuple[Browser, Page]]:
    """获取当前的浏览器实例和页面（浏览器挂掉则自动清理返回 None）。"""
    return run_in_thread_if_asyncio(_get_browser_page_impl)


def _get_browser_page_impl() -> Optional[Tuple[Browser, Page]]:
    if not ensure_browser_alive():
        logger.warning("⚠️ 浏览器已挂掉，已自动清理")
        return None

    manager = get_browser_manager()
    browser = manager.get_browser()
    _, page = manager.get_context_and_page(BrowserType.STUDENT)

    if browser and page:
        return browser, page
    return None


def get_access_token_from_browser() -> Optional[str]:
    """从已登录的浏览器中提取 access_token（刷新页面监听 /connect/token）。"""
    return run_in_thread_if_asyncio(_get_access_token_from_browser_impl)


def _get_access_token_from_browser_impl() -> Optional[str]:
    try:
        manager = get_browser_manager()
        _, page = manager.get_context_and_page(BrowserType.STUDENT)

        if not page:
            logger.error("❌ 浏览器未初始化，请先登录")
            return None

        logger.info("🔍 从浏览器中提取access_token...")

        # 方法1：先尝试从localStorage获取
        js_code = """
        () => {
            const keys = ['access_token', 'token', 'auth_token', 'student_token', 'oidc.user:https://ai.cqzuxia.com:zhzx'];

            for (let key of keys) {
                const value = localStorage.getItem(key);
                if (value) {
                    try {
                        const parsed = JSON.parse(value);
                        if (parsed.access_token) {
                            return parsed.access_token;
                        }
                    } catch (e) {
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
            logger.info("✅ 从localStorage提取到access_token")
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

        page.on("response", handle_response)

        current_url = page.url
        if "ai.cqzuxia.com" in current_url:
            logger.info("正在刷新页面...")
            page.reload(wait_until="domcontentloaded", timeout=30000)
        else:
            logger.info("正在导航到登录页...")
            page.goto("https://ai.cqzuxia.com/#/login", wait_until="domcontentloaded", timeout=30000)

        start_time = time.time()
        while not access_token and (time.time() - start_time) < 10:
            time.sleep(0.3)

        if access_token:
            logger.info("✅ 成功从浏览器提取access_token")
            return access_token
        else:
            logger.warning("⚠️ 浏览器中未找到有效的access_token")
            logger.info("💡 提示：请确保已经在浏览器中登录学生端")
            return None

    except Exception as e:
        logger.error(f"❌ 从浏览器提取access_token失败: {str(e)}")
        return None


def navigate_to_course(course_id: str) -> bool:
    """使用已登录的浏览器导航到指定课程的答题页面。"""
    return run_in_thread_if_asyncio(_navigate_to_course_impl, course_id)


def _navigate_to_course_impl(course_id: str) -> bool:
    try:
        if not ensure_browser_alive():
            logger.error("❌ 浏览器不可用，请重新登录")
            return False

        manager = get_browser_manager()
        _, page = manager.get_context_and_page(BrowserType.STUDENT)

        if not page:
            logger.error("❌ 浏览器未初始化，请先登录")
            return False

        evaluation_url = f"https://ai.cqzuxia.com/#/evaluation/knowledge-detail/{course_id}"

        logger.info(f"正在导航到课程页面: {evaluation_url}")
        page.goto(evaluation_url, wait_until="domcontentloaded", timeout=30000)

        logger.info("正在刷新页面...")
        page.reload(wait_until="domcontentloaded", timeout=30000)

        logger.info("✅ 成功导航到答题页面")
        return True

    except Exception as e:
        logger.error(f"❌ 导航到课程页面失败: {str(e)}")
        if not is_browser_alive():
            logger.warning("⚠️ 浏览器可能在操作过程中挂掉，已自动清理")
        return False


def get_course_progress_from_page() -> Optional[Dict]:
    """从当前页面解析课程进度信息。"""
    return run_in_thread_if_asyncio(_get_course_progress_from_page_impl)


def _get_course_progress_from_page_impl() -> Optional[Dict]:
    try:
        if not ensure_browser_alive():
            logger.error("❌ 浏览器不可用，无法获取进度")
            return None

        manager = get_browser_manager()
        _, page = manager.get_context_and_page(BrowserType.STUDENT)

        if not page:
            logger.error("❌ 页面未初始化")
            return None

        try:
            page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:
            logger.debug("等待页面加载超时，继续解析页面")

        time.sleep(0.5)

        try:
            page.wait_for_selector(".el-menu-item", state="attached", timeout=8000)
        except Exception:
            logger.debug("等待 .el-menu-item 超时，尝试直接解析")

        knowledge_items = page.query_selector_all(".el-menu-item")

        if not knowledge_items or len(knowledge_items) == 0:
            logger.warning("⚠️ 未找到 .el-menu-item 元素，页面可能未完全加载")
            return {
                'total': 0,
                'completed': 0,
                'failed': 0,
                'not_started': 0,
                'progress_percentage': 0.0
            }

        total = len(knowledge_items)
        completed = 0
        failed = 0
        not_started = 0

        for item in knowledge_items:
            pass_status = item.query_selector(".pass-status")
            if pass_status:
                check_icon = pass_status.query_selector(".el-icon-check")
                close_icon = pass_status.query_selector(".el-icon-close")

                check_display = "none"
                close_display = "none"

                if check_icon:
                    check_style = check_icon.get_attribute("style") or ""
                    check_display = "none" if "display: none" in check_style or "display:none" in check_style else "block"

                if close_icon:
                    close_style = close_icon.get_attribute("style") or ""
                    close_display = "none" if "display: none" in close_style or "display:none" in close_style else "block"

                if check_display != "none" and close_display == "none":
                    completed += 1
                elif close_display != "none" and check_display == "none":
                    failed += 1
                elif check_display == "none" and close_display == "none":
                    not_started += 1
                else:
                    item_class = item.get_attribute("class") or ""
                    if "success" in item_class:
                        completed += 1
                    else:
                        not_started += 1
            else:
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
