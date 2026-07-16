"""
课程认证模块

用于处理课程相关的认证功能

已重构为使用统一的浏览器管理器 (src/browser_manager.py)
- 使用单浏览器 + 多上下文模式
- 支持与学生端、教师端模块同时运行
- 上下文之间完全隔离，互不干扰
"""

from playwright.sync_api import Page
from typing import Optional, List, Dict
import time
import logging
import threading
import requests
from src.core.api_client import get_api_client
from src.certification.api_answer import APICourseAnswer

# 导入浏览器管理器
from src.core.browser import (
    get_browser_manager,
    BrowserType,
    run_in_thread_if_asyncio
)
from src.utils.text import normalize_text, get_chapters
from src.core.headers import get_api_headers
from src.answering.base_answer import BaseAnswer

# 配置日志
logger = logging.getLogger(__name__)

# 题库缓存（模块级变量）
_question_bank_data = None


# ============================================================================
# 浏览器管理辅助函数（使用 BrowserManager）
# ============================================================================


def _ensure_context_and_page() -> tuple:
    """
    确保课程认证上下文和页面存在

    Returns:
        tuple: (context, page)
    """
    manager = get_browser_manager()
    context, page = manager.get_context_and_page(BrowserType.COURSE_CERTIFICATION)

    if context is None or page is None:
        # 创建新的上下文
        context = manager.create_context(
            BrowserType.COURSE_CERTIFICATION,
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0"
        )
        # 使用 manager.create_page() 而不是 context.new_page()
        page = manager.create_page(BrowserType.COURSE_CERTIFICATION)
        print("[OK] 已创建课程认证浏览器上下文和页面")

    return context, page


def import_question_bank(file_path: str) -> bool:
    """
    导入题库文件

    Args:
        file_path: 题库JSON文件路径

    Returns:
        bool: 导入是否成功
    """
    try:
        from src.extraction.importer import QuestionBankImporter

        print(f"\n正在导入题库文件: {file_path}")

        # 创建题库导入器
        importer = QuestionBankImporter()

        # 导入题库
        success = importer.import_from_file(file_path)

        if not success:
            print("[ERROR] 题库文件导入失败")
            return False

        # 保存到缓存
        global _question_bank_data
        _question_bank_data = importer.data

        # 显示简化的题库统计信息
        print("\n" + "=" * 60)
        print("📊 题库信息")
        print("=" * 60)

        # 获取题库类型
        bank_type = importer.get_bank_type()

        if bank_type == "single":
            # 单个课程
            parsed = importer.parse_single_course()
            if parsed:
                print("\n📖 班级信息：")
                print(f"  {parsed['class']['name']} ({parsed['class']['grade']})")

                print("\n📚 课程信息：")
                print(f"  {parsed['course']['courseName']}")

                print("\n📊 统计信息：")
                stats = parsed['statistics']
                print(f"  章节：{stats['totalChapters']} 章")
                print(f"  知识点：{stats['totalKnowledges']} 个")
                print(f"  题目：{stats['totalQuestions']} 题")
                print(f"  选项：{stats['totalOptions']} 个")

        elif bank_type == "multiple":
            # 多个课程
            parsed = importer.parse_multiple_courses()
            if parsed:
                print("\n📖 班级信息：")
                print(f"  {parsed['class']['name']} ({parsed['class']['grade']})")

                print("\n📚 课程列表：")
                for i, course in enumerate(parsed['courses'], 1):
                    print(f"  {i}. {course['courseName']}")

                print("\n📊 统计信息：")
                stats = parsed['statistics']
                print(f"  课程：{stats['totalCourses']} 门")
                print(f"  章节：{stats['totalChapters']} 章")
                print(f"  知识点：{stats['totalKnowledges']} 个")
                print(f"  题目：{stats['totalQuestions']} 题")
                print(f"  选项：{stats['totalOptions']} 个")

        print("=" * 60)
        print(f"[OK] 题库已缓存")

        return True

    except Exception as e:
        print(f"[ERROR] 导入题库异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def get_question_bank() -> Optional[Dict]:
    """
    获取缓存的题库数据

    Returns:
        Optional[Dict]: 题库数据，如果未导入则返回None
    """
    return _question_bank_data


def close_browser():
    """
    关闭课程认证浏览器上下文
    注意：这只关闭课程认证上下文，不会关闭整个浏览器（可能还有其他模块在使用）
    """
    try:
        manager = get_browser_manager()
        manager.cleanup_type(BrowserType.COURSE_CERTIFICATION)
        print("[OK] 课程认证浏览器上下文已关闭")
    except Exception as e:
        print(f"[WARNING] 关闭浏览器时发生错误: {str(e)}")


def _get_access_token_impl(keep_browser_open: bool, skip_prompt: bool, username: str, password: str) -> Optional[tuple]:
    """
    get_access_token 的内部实现函数
    包含所有实际的 Playwright 操作

    这个函数应该在单独的线程中运行，以避免与 asyncio 冲突

    Args:
        keep_browser_open: 是否保持浏览器打开
        skip_prompt: 是否跳过交互式提示
        username: 用户名
        password: 密码

    Returns:
        Optional[tuple]: (access_token, page) 如果成功
    """
    try:
        logger.info(f"使用账户: {username}")

        # 使用浏览器管理器
        manager = get_browser_manager()
        logger.info("正在启动浏览器...")
        manager.start_browser(headless=None)  # 从配置文件读取无头模式设置
        logger.info("浏览器已启动")

        # 获取或创建课程认证上下文
        logger.info("正在创建课程认证浏览器上下文...")
        context = manager.get_context(BrowserType.COURSE_CERTIFICATION)
        if context is None:
            context = manager.create_context(
                BrowserType.COURSE_CERTIFICATION,
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0"
            )
            logger.info("课程认证浏览器上下文已创建")
        else:
            logger.info("使用已存在的课程认证浏览器上下文")

        # 创建页面
        logger.info("正在创建新页面...")
        # 使用 manager.create_page() 而不是 context.new_page()
        page = manager.create_page(BrowserType.COURSE_CERTIFICATION)
        captured_data = None

        try:
            def handle_response(response):
                nonlocal captured_data
                if 'token' in response.url:
                    logger.info(f"捕获到 token 响应: {response.url}")
                    print(f"[DEBUG] 捕获到 token 响应")
                    try:
                        data = response.json()
                        captured_data = data
                        logger.info("成功捕获响应数据")
                        print(f"[OK] 成功捕获响应数据")
                    except Exception as e:
                        logger.error(f"解析响应失败: {e}")
                        print(f"解析失败: {e}")

            page.on('response', handle_response)

            login_url = "https://zxsz.cqzuxia.com/#/login/index"
            logger.info(f"正在访问登录页面: {login_url}")
            print(f"正在打开登录页面: {login_url}")
            page.goto(login_url, timeout=30000)

            logger.info("等待登录表单加载...")
            print("等待登录表单加载...")
            page.wait_for_selector("input[placeholder='登录账号']", timeout=10000)
            logger.info("登录表单加载完成")

            logger.info(f"正在填写账户: {username}")
            print(f"正在填写账户: {username}")
            page.fill("input[placeholder='登录账号']", username)

            logger.info("正在填写密码...")
            print("正在填写密码")
            page.fill("input[placeholder='登录密码']", password)

            logger.info("点击登录按钮...")
            print("正在点击登录按钮...")
            page.click(".lic-clf-loginbut")

            logger.info("等待登录成功...")
            print("等待登录成功...")
            try:
                page.wait_for_url("**/home", timeout=15000)
                logger.info("页面已跳转到 home，登录成功")
                print("[OK] 页面已跳转到 home，登录成功")
                time.sleep(1)
            except Exception as e:
                logger.warning(f"等待页面跳转超时: {e}")
                print(f"[WARNING] 等待页面跳转超时: {e}")
                print("继续检查是否捕获到 token...")

            if captured_data and 'access_token' in captured_data:
                access_token = captured_data['access_token']
                logger.info("成功获取 access_token")
                print("\n" + "=" * 50)
                print("[OK] 登录成功！")
                print("=" * 50)
                print("access_token: 已获取（内容已隐藏）")
                print(f"token类型: Bearer")
                print(f"有效期: 5小时 (18000秒)")
                print("=" * 50)

                if not keep_browser_open:
                    # 关闭页面但保留上下文
                    try:
                        page.close()
                        logger.info("页面已关闭")
                    except Exception as e:
                        logger.debug(f"关闭页面失败: {e}")
                    return (access_token, None)
                else:
                    # 返回页面供后续使用
                    logger.info("浏览器保持打开状态")
                    return (access_token, page)
            else:
                logger.error("未能在响应中捕获到 access_token")
                print("[ERROR] 未能在响应中捕获到 access_token")
                if captured_data:
                    captured_fields = list(captured_data) if isinstance(captured_data, dict) else type(captured_data).__name__
                    logger.warning("令牌响应缺少 access_token；响应字段: %s", captured_fields)
                    print(f"响应字段: {captured_fields}")
                return None

        except Exception as e:
            logger.error(f"登录过程异常：{str(e)}")
            print(f"[ERROR] 登录过程异常：{str(e)}")
            return None

    except Exception as e:
        logger.error(f"Playwright登录异常：{str(e)}")
        print(f"[ERROR] Playwright登录异常：{str(e)}")
        import traceback
        traceback.print_exc()
        return None


def get_access_token(keep_browser_open: bool = False, skip_prompt: bool = False) -> Optional[tuple]:
    """
    使用Playwright模拟浏览器登录获取课程认证access_token

    支持异步兼容模式：在 Flet GUI (asyncio) 环境中自动使用线程包装

    Args:
        keep_browser_open: 是否保持浏览器打开（用于后续操作）
        skip_prompt: 是否跳过交互式提示（GUI模式下使用，自动使用已保存的账号）

    Returns:
        Optional[tuple]: (access_token, page) 如果成功
                         如果 keep_browser_open=False，page 为 None
    """
    try:
        logger.info("正在启动浏览器进行课程认证登录...")
        print("正在启动浏览器进行课程认证登录...")

        # 尝试从配置文件读取凭据
        try:
            from src.core.config import get_settings_manager
            settings = get_settings_manager()
            config_username, config_password = settings.get_teacher_credentials()

            if config_username and config_password:
                print("\n[INFO] 检测到已保存的教师端账号")
                logger.info("检测到已保存的教师端账号")

                # 如果跳过提示（GUI模式），直接使用已保存的账号
                if skip_prompt:
                    print(f"[OK] 使用已保存的账号: {config_username[:3]}****")
                    logger.info(f"使用已保存的账号: {config_username[:3]}****")
                    username = config_username
                    password = config_password
                else:
                    # CLI模式，询问用户是否使用已保存的账号
                    use_saved = input("是否使用已保存的账号？(yes/no，默认yes): ").strip().lower()

                    if use_saved in ['', 'yes', 'y', '是']:
                        print(f"[OK] 使用已保存的账号: {config_username[:3]}****")
                        logger.info(f"使用已保存的账号: {config_username[:3]}****")
                        username = config_username
                        password = config_password
                    else:
                        print("[INFO] 请手动输入账号密码")
                        username = input("请输入课程认证账户：").strip()
                        password = input("请输入课程认证密码：").strip()
            else:
                # 没有已保存的账号
                if skip_prompt:
                    print("[ERROR] 未找到已保存的教师端账号")
                    logger.warning("未找到已保存的教师端账号")
                    return None
                else:
                    username = input("请输入课程认证账户：").strip()
                    password = input("请输入课程认证密码：").strip()
        except Exception:
            if skip_prompt:
                print("[ERROR] 读取配置文件失败")
                logger.error("读取配置文件失败")
                return None
            else:
                username = input("请输入课程认证账户：").strip()
                password = input("请输入课程认证密码：").strip()

        if not username or not password:
            print("[ERROR] 用户名或密码不能为空")
            logger.error("用户名或密码不能为空")
            return None

        # 使用异步兼容模式：在 asyncio 环境中运行 Playwright 操作
        return run_in_thread_if_asyncio(
            _get_access_token_impl,
            keep_browser_open,
            skip_prompt,
            username,
            password
        )

    except Exception as e:
        logger.error(f"获取访问令牌失败：{str(e)}")
        print(f"[ERROR] 获取访问令牌失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return None


def start_answering():
    """
    开始做题功能
    登录并获取课程列表
    """
    manager = get_browser_manager()
    if not manager.is_worker_thread():
        return manager.submit_task(start_answering)

    try:
        print("\n" + "=" * 60)
        print("🎓 课程认证 - 开始做题")
        print("=" * 60)

        # 1. 获取 access_token（保持浏览器打开）
        print("\n步骤 1/2: 正在登录...")
        result = get_access_token(keep_browser_open=True)

        if not result:
            print("\n[ERROR] 登录失败，无法继续")
            return

        access_token, page = result

        print("\n步骤 2/2: 正在获取课程列表...")

        # 2. 请求课程列表API
        api_url = "https://zxsz.cqzuxia.com/teacherCertifiApi/api/ModuleTeacher/GetLessonListByTeacher"

        headers = get_api_headers(
            "edge_144", access_token,
            referer="https://zxsz.cqzuxia.com/",
            extra_headers={
                "dnt": "1",
                "sec-gpc": "1",
                "priority": "u=1, i",
            },
        )

        try:
            # 使用 API 客户端以获得自动重试功能
            api_client = get_api_client()
            response = api_client.get(api_url, headers=headers)

            if response is None:
                print("[ERROR] 请求失败，未收到有效响应")
                close_browser()
                return

            if response.status_code == 200:
                data = response.json()

                if data.get('code') == 0 and 'data' in data:
                    courses = data['data']

                    # 取消筛选，显示所有课程
                    filtered_courses = courses

                    print("\n" + "=" * 60)
                    print(f"📚 课程列表（共 {len(filtered_courses)} 门）")
                    print("=" * 60 + "\n")

                    if not filtered_courses:
                        print("📭 没有可做的课程")
                        close_browser()
                        return

                    for i, course in enumerate(filtered_courses, 1):
                        lesson_name = course.get('lessonName', 'N/A')
                        ecourse_id = course.get('eCourseID', 'N/A')

                        print(f"{i}. 【{lesson_name}】")
                        print(f"   🆔 eCourseID: {ecourse_id}")
                        print()

                    print("=" * 60)

                    # 让用户选择课程
                    while True:
                        choice_input = input("\n请输入课程编号查看详情（输入0返回）: ").strip()

                        if choice_input == "0":
                            print("返回菜单")
                            close_browser()
                            break

                        try:
                            choice_idx = int(choice_input) - 1
                            if 0 <= choice_idx < len(filtered_courses):
                                selected_course = filtered_courses[choice_idx]
                                lesson_name = selected_course.get('lessonName', 'N/A')
                                ecourse_id = selected_course.get('eCourseID', 'N/A')

                                print(f"\n你选择了: {lesson_name}")
                                print(f"eCourseID: {ecourse_id}")

                                confirm = input("\n是否跳转到该课程页面？(yes/no): ").strip().lower()
                                if confirm in ['yes', 'y', '是']:
                                    # 使用已有的浏览器实例跳转
                                    navigate_to_course_page(ecourse_id, page, access_token)
                                    # 跳转完成后关闭浏览器
                                    close_browser()
                                    break
                                else:
                                    print("已取消")
                            else:
                                print(f"[ERROR] 无效的选择，请输入 0-{len(filtered_courses)} 之间的数字")
                        except ValueError:
                            print("[ERROR] 请输入有效的数字")

                else:
                    print(f"[ERROR] API返回错误: {data.get('message', '未知错误')}")
                    close_browser()
            else:
                print(f"[ERROR] 请求失败，状态码: {response.status_code}")
                close_browser()

        except requests.exceptions.Timeout:
            print("[ERROR] 请求超时")
            close_browser()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] 请求异常: {str(e)}")
            close_browser()
        except Exception as e:
            print(f"[ERROR] 处理响应异常: {str(e)}")
            close_browser()

    except Exception as e:
        print(f"[ERROR] 开始做题异常: {str(e)}")
        import traceback
        traceback.print_exc()
        close_browser()


def _auto_answer_items(page, course_url, question_bank, skip_completed=True):
    """
    兼容模式答题的核心循环（分支 1 和 3 共享）。

    Args:
        page: Playwright Page 对象
        course_url: 课程页面 URL（用于手动返回）
        question_bank: 题库数据
        skip_completed: True=跳过已完成（兼容模式），False=全部重做

    Returns:
        (total_completed, total_failed) 元组
    """
    chapters = page.query_selector_all(".el-sub-menu")
    print(f"[INFO] 找到 {len(chapters)} 个章节")

    total_completed = 0
    total_failed = 0

    for chapter_idx, chapter in enumerate(chapters):
        try:
            chapter_title_elem = chapter.query_selector(".el-sub-menu__title span")
            chapter_title = chapter_title_elem.inner_text().strip() if chapter_title_elem else f"第{chapter_idx+1}章"
            print(f"\n📖 章节 {chapter_idx+1}: {chapter_title}")

            # 展开折叠的章节
            chapter_title_div = chapter.query_selector(".el-sub-menu__title")
            if chapter_title_div:
                chapter_class = chapter.get_attribute("class") or ""
                if "is-opened" not in chapter_class:
                    print(f"   ↕️  正在展开折叠的章节...")
                    chapter_title_div.click()
                    time.sleep(0.5)
                print(f"   [OK] 章节已展开")

            question_items_in_chapter = chapter.query_selector_all(".el-menu-item")
            print(f"   📝 该章节有 {len(question_items_in_chapter)} 个题目")

            for q_idx, item in enumerate(question_items_in_chapter):
                try:
                    span = item.query_selector("span")
                    if not span:
                        continue
                    question_name = span.inner_text().strip()

                    # 检查完成状态
                    pass_status_div = item.query_selector(".pass-status")
                    is_completed = False
                    if pass_status_div:
                        icons = pass_status_div.query_selector_all(".el-icon")
                        if len(icons) >= 2:
                            first_icon_style = icons[0].get_attribute("style") or ""
                            if "display: none" not in first_icon_style:
                                is_completed = True

                    if skip_completed and is_completed:
                        print(f"      ⏭️  [{q_idx+1}] {question_name[:40]}... (已完成)")
                        continue

                    status_text = "已完成" if is_completed else "未完成"
                    print(f"\n      🎯 开始做题: [{q_idx+1}] {question_name[:40]}... ({status_text})")

                    item.click()
                    time.sleep(2)

                    try:
                        start_button = page.wait_for_selector("button.el-button--primary:has-text('开始测评')", timeout=5000)
                        start_button.click()
                        print("      [OK] 已点击开始测评按钮")
                        time.sleep(2)

                        auto_answer = CourseAutoAnswer(page)
                        result = auto_answer.answer_with_bank(question_bank)

                        if result['total'] > 0:
                            success_rate = result['success'] / result['total']
                            print(f"      [OK] 做题完成: 成功 {result['success']}/{result['total']} 题 ({success_rate:.1%})")
                            total_completed += result['success']
                            total_failed += result['failed']
                        else:
                            print(f"      [WARNING] 没有题目被回答")

                        # 等待自动跳转检测
                        print(f"      ⏳ 等待网站显示成功提示并自动跳转...")
                        start_time = time.time()
                        success_detected = False

                        while time.time() - start_time < 10:
                            try:
                                success_element = page.query_selector(".eva-success")
                                if success_element and not success_detected:
                                    print(f"      [OK] 检测到成功提示，等待5秒自动跳转...")
                                    success_detected = True
                                    break
                                time.sleep(0.5)
                            except:
                                time.sleep(0.5)

                        if success_detected:
                            time.sleep(6)
                            print(f"      [DEBUG] 检测是否自动跳转...")

                            auto_jumped = False
                            try:
                                page.wait_for_selector(".question-type", state="hidden", timeout=3000)
                                print(f"      [OK] 已自动跳转到题目列表")
                                auto_jumped = True
                            except:
                                print(f"      [WARNING] 答题页面元素仍然存在")

                            if not auto_jumped:
                                try:
                                    sb = page.query_selector("button:has-text('开始测评')", timeout=2000)
                                    if sb:
                                        print(f"      [OK] 检测到'开始测评'按钮，已自动跳转")
                                        auto_jumped = True
                                except:
                                    pass

                            if auto_jumped:
                                print(f"      🎉 网站已自动跳转，继续下一题")
                                time.sleep(1)
                                chapters_list = page.query_selector_all(".el-sub-menu")
                                if chapter_idx < len(chapters_list):
                                    chapter = chapters_list[chapter_idx]
                                    question_items_in_chapter = chapter.query_selector_all(".el-menu-item")
                                continue
                            else:
                                print(f"      [WARNING] 未检测到自动跳转，手动返回题目列表")
                                page.goto(course_url, timeout=30000)
                                time.sleep(2)
                                chapter = page.query_selector_all(".el-sub-menu")[chapter_idx]
                                question_items_in_chapter = chapter.query_selector_all(".el-menu-item")
                                continue
                        else:
                            print(f"      [WARNING] 超时未检测到成功提示，手动返回题目列表")
                            page.goto(course_url, timeout=30000)
                            time.sleep(2)
                            chapter = page.query_selector_all(".el-sub-menu")[chapter_idx]
                            question_items_in_chapter = chapter.query_selector_all(".el-menu-item")
                            continue

                    except Exception as e:
                        print(f"      [ERROR] 做题失败: {str(e)}")
                        total_failed += 1
                        page.goto(course_url, timeout=30000)
                        time.sleep(2)
                        chapter = page.query_selector_all(".el-sub-menu")[chapter_idx]
                        question_items_in_chapter = chapter.query_selector_all(".el-menu-item")
                        continue

                except Exception as e:
                    print(f"      [WARNING] 题目处理失败: {str(e)}")
                    continue

        except Exception as e:
            print(f"   [WARNING] 章节处理失败: {str(e)}")
            continue

    return total_completed, total_failed


def navigate_to_course_page(ecourse_id: str, page, access_token: str):
    """
    使用已有的浏览器实例跳转到课程评估页面，并提取题目列表

    Args:
        ecourse_id: 课程ID
        page: Playwright page实例
        access_token: 访问令牌
    """
    manager = get_browser_manager()
    if not manager.is_worker_thread():
        return manager.submit_task(navigate_to_course_page, ecourse_id, page, access_token)

    def show_operation_menu():
        """显示操作菜单"""
        print("\n" + "=" * 60)
        print("[INFO] 操作菜单")
        print("=" * 60)
        print("1. 开始做题（兼容模式）")
        print("2. 开始做题（API模式）")
        print("3. 重新作答（兼容模式）")
        print("4. 重新作答（API模式）")
        print("5. 导入题库")
        print("0. 退出")
        print("=" * 60)

    try:
        print(f"\n正在跳转到课程页面...")

        course_url = f"https://zxsz.cqzuxia.com/#/major-course/course-evaluate/{ecourse_id}"

        print(f"📖 正在打开课程页面...")
        print(f"🔗 URL: {course_url}")

        page.goto(course_url, timeout=30000)

        # 外层循环：持续显示题目列表和菜单
        should_exit = False
        while not should_exit:
            # 等待题目列表加载
            print("⏳ 等待题目列表加载...")
            time.sleep(3)

            # 提取题目列表
            print("\n正在提取题目列表...")

            # 等待题目菜单元素出现
            try:
                page.wait_for_selector(".el-menu.el-menu--vertical", timeout=10000)
            except:
                print("[WARNING] 未找到题目列表，页面可能加载失败")
                print("\n[INFO] 浏览器将保持打开状态，你可以手动查看")
                input("按回车键关闭浏览器...")
                return

            # 获取所有题目项
            all_items = page.query_selector_all("li.el-menu-item")

            # 过滤掉章节标题项（章节标题的span在el-sub-menu__title内）
            question_items = []
            for item in all_items:
                try:
                    # 检查是否有直接的span子元素（不包含嵌套的）
                    direct_span = item.query_selector("span")
                    # 检查是否有 pass-status
                    has_pass_status = item.query_selector(".pass-status")

                    if direct_span and has_pass_status:
                        question_items.append(item)
                except:
                    continue

            if not question_items:
                print("📭 未找到任何题目")
            else:
                print("\n" + "=" * 60)
                print(f"📝 题目列表（共 {len(question_items)} 题）")
                print("=" * 60 + "\n")

                for i, item in enumerate(question_items, 1):
                    try:
                        # 获取题目名称
                        span = item.query_selector("span")
                        if span:
                            question_name = span.inner_text().strip()
                        else:
                            question_name = "未命名题目"

                        # 检查完成状态
                        pass_status_div = item.query_selector(".pass-status")
                        is_completed = False

                        if pass_status_div:
                            # 获取两个图标
                            icons = pass_status_div.query_selector_all(".el-icon")
                            if len(icons) >= 2:
                                # 检查第一个图标是否隐藏
                                first_icon_style = icons[0].get_attribute("style") or ""
                                second_icon_style = icons[1].get_attribute("style") or ""

                                # 如果第一个图标不隐藏（显示[OK]），则已完成
                                if "display: none" not in first_icon_style:
                                    is_completed = True
                                # 如果第二个图标不隐藏（显示✕），则未完成
                                elif "display: none" not in second_icon_style:
                                    is_completed = False

                        # 状态标记
                        status_mark = "[OK]" if is_completed else "[ERROR]"

                        # 如果已完成，使用灰色显示
                        if is_completed:
                            print(f"{i}. {status_mark} {question_name} (已完成)")
                        else:
                            print(f"{i}. {status_mark} {question_name}")

                    except Exception as e:
                        print(f"{i}. [ERROR] 解析题目失败: {e}")

                print("\n" + "=" * 60)
                completed_count = sum(1 for item in question_items if "已完成" in str(item.get_attribute("outerHTML")))
                print(f"📊 统计：已完成 {completed_count}/{len(question_items)} 题")
                print("=" * 60)

                # 显示操作菜单
                show_operation_menu()

                # 内层循环：处理用户操作选择
                while True:
                    choice = input("\n请选择操作 (1-5 或 0): ").strip()

                    if choice == "1":
                        print("\n[OK] 选择了：开始做题（兼容模式）")
                        question_bank = get_question_bank()
                        if not question_bank:
                            print("[WARNING] 未检测到题库，请先导入题库")
                            continue

                        print("\n" + "=" * 60)
                        print("🚀 开始自动遍历所有题目")
                        print("=" * 60)

                        total_completed, total_failed = _auto_answer_items(
                            page, course_url, question_bank, skip_completed=True
                        )

                        print("\n" + "=" * 60)
                        print("[OK] 所有题目遍历完成")
                        print(f"📊 总计: 成功 {total_completed} 题, 失败 {total_failed} 题")
                        print("=" * 60)

                        # 退出内层循环，重新显示题目列表和菜单
                        break

                    elif choice == "2":
                        # 开始做题（API模式）- 只做未完成的题目
                        print("\n[OK] 选择了：开始做题（API模式）")
                        print("[INFO] 将自动遍历未完成的题目（API直接提交）")

                        # 检查是否已导入题库
                        question_bank = get_question_bank()
                        if not question_bank:
                            print("[WARNING] 未检测到题库，请先导入题库")
                            print("[INFO] 提示：在操作菜单选择'5. 导入题库'功能")
                            continue

                        # 创建API做题器
                        api_answer = APICourseAnswer(access_token)

                        # 自动做题（跳过已完成的）
                        result = api_answer.auto_answer_course(ecourse_id, question_bank, skip_completed=True)

                        # 显示结果
                        print("\n" + "=" * 60)
                        print("[OK] API模式做题完成")
                        print("=" * 60)
                    elif choice == "3":
                        print("\n[OK] 选择了：重新作答（兼容模式）")
                        question_bank = get_question_bank()
                        if not question_bank:
                            print("[WARNING] 未检测到题库，请先导入题库")
                            continue

                        print("\n" + "=" * 60)
                        print("🚀 开始重新作答所有题目")
                        print("=" * 60)

                        total_completed, total_failed = _auto_answer_items(
                            page, course_url, question_bank, skip_completed=False
                        )

                        print("\n" + "=" * 60)
                        print("[OK] 所有题目重新作答完成")
                        print(f"📊 总计: 成功 {total_completed} 题, 失败 {total_failed} 题")
                        print("=" * 60)

                        break
                    elif choice == "4":
                        # 重新作答（API模式）- 做所有题目（包括已完成的）
                        print("\n[OK] 选择了：重新作答（API模式）")
                        print("[INFO] 将自动遍历所有题目（包括已完成的题目）")

                        # 检查是否已导入题库
                        question_bank = get_question_bank()
                        if not question_bank:
                            print("[WARNING] 未检测到题库，请先导入题库")
                            print("[INFO] 提示：在操作菜单选择'5. 导入题库'功能")
                            continue

                        # 创建API做题器
                        api_answer = APICourseAnswer(access_token)

                        # 自动做题（包括已完成的）
                        result = api_answer.auto_answer_course(ecourse_id, question_bank, skip_completed=False)

                        # 显示结果
                        print("\n" + "=" * 60)
                        print("[OK] API模式重新作答完成")
                        print("=" * 60)
                    elif choice == "5":
                        # 导入题库
                        print("\n[OK] 选择了：导入题库")
                        print("=" * 60)
                        print("[INFO] 请输入题库JSON文件的路径")
                        print("提示：可以直接拖拽文件到此处")
                        print("=" * 60)

                        file_path = input("\n文件路径: ").strip().strip('"').strip("'")

                        if not file_path:
                            print("[ERROR] 文件路径不能为空")
                            continue

                        # 调用题库导入功能
                        success = import_question_bank(file_path)

                        if success:
                            print("\n[OK] 题库导入成功！")
                            print("[INFO] 现在可以选择'开始做题'或'重新作答'使用导入的题库")
                            # 重新显示操作菜单
                            show_operation_menu()
                        else:
                            print("\n[ERROR] 题库导入失败")
                            # 重新显示操作菜单
                            show_operation_menu()
                    elif choice == "0":
                        print("\n🔙 退出")
                        should_exit = True
                        break
                    else:
                        print("\n[ERROR] 无效的选择，请输入 1-5 或 0")
                        # 重新显示操作菜单
                        show_operation_menu()

    except KeyboardInterrupt:
        print("\n\n[WARNING] 用户中断")
    except Exception as e:
        print(f"[ERROR] 跳转页面异常: {str(e)}")
        import traceback
        traceback.print_exc()


class CourseAutoAnswer(BaseAnswer):
    """课程认证自动做题类（兼容模式）"""

    def __init__(self, page):
        self.page = page
        self.api_question_ids = []
        self.api_listener_active = False
        self.current_question_index = 0  # 当前题目索引（用于API模式）

    def _get_page(self):
        return self.page

    def _setup_api_listener(self):
        """设置API监听器，捕获题目ID"""
        def handle_route(route, request):
            # 监听 GetQuesionListByKPId API
            if "GetQuesionListByKPId" in request.url and self.api_listener_active:
                try:
                    # 继续请求并获取响应
                    response = route.fetch()
                    body = response.json()

                    if body.get('code') == 0 and 'data' in body:
                        # 提取题目ID
                        self.api_question_ids = [
                            q.get('questionID') for q in body.get('data', [])
                        ]
                        print(f"[OK] 监听到API，获取到 {len(self.api_question_ids)} 个题目ID")
                        # 打印前3个题目ID用于调试
                        if self.api_question_ids:
                            print(f"   题目ID: {self.api_question_ids[0]}...")

                except Exception as e:
                    print(f"[WARNING] API监听异常: {str(e)}")

                return route.continue_()

            return route.continue_()

        # 注册路由监听
        self.page.route('**/*', handle_route)

    def _start_api_listener(self):
        """启动API监听"""
        if not self.api_listener_active:
            self.api_listener_active = True
            self._setup_api_listener()
            print("[OK] API监听器已启动")

    def _stop_api_listener(self):
        """停止API监听"""
        self.api_listener_active = False
        print("[OK] API监听器已停止")

    def _normalize_text(self, text: str) -> str:
        """标准化文本"""
        return normalize_text(text)

    def _parse_question_type(self) -> tuple:
        """
        解析题目类型

        Returns:
            tuple: (题目类型代码, 题目类型名称)
                - 题目类型代码: 'single' (单选/判断), 'multiple' (多选)
                - 题目类型名称: '单选/判断', '多选'
        """
        try:
            # 检查是否存在单选组（单选或判断题）
            radio_group = self.page.query_selector(".el-radio-group")
            if radio_group:
                return "single", "单选/判断"

            # 检查是否存在多选组
            checkbox_group = self.page.query_selector(".el-checkbox-group")
            if checkbox_group:
                return "multiple", "多选"

            # 默认为单选
            return "single", "单选/判断"

        except Exception as e:
            print(f"[ERROR] 解析题目类型失败: {str(e)}")
            return "single", "单选/判断"

    def _parse_current_question(self) -> Optional[Dict]:
        """
        解析当前题目的信息

        Returns:
            Optional[Dict]: 题目信息字典，包含:
                {
                    'type': str,  # 题目类型: 'single', 'multiple'
                    'type_name': str,  # 题目类型名称
                    'title': str,  # 题目内容
                    'options': List[Dict],  # 选项列表
                        [
                            {
                                'label': str,  # 选项标签 (A, B, C, D)
                                'content': str,  # 选项内容
                                'value': str  # 选项value值
                            }
                        ]
                    'options_hash': str  # 选项内容的组合哈希，用于精确匹配
                }
        """
        try:
            # 解析题目类型
            question_type, type_name = self._parse_question_type()

            # 获取题目标题
            title_element = self.page.query_selector(".question-title")
            if not title_element:
                print("[ERROR] 未找到题目标题元素")
                return None

            title_text = title_element.inner_text().strip()

            # 获取选项
            options = []
            options_contents = []  # 存储选项内容用于生成哈希

            if question_type == "single":
                # 单选题或判断题 - 使用 el-radio
                radio_labels = self.page.query_selector_all(".el-radio")
                for label in radio_labels:
                    # 获取选项标签（A、B、C、D）
                    label_element = label.query_selector(".option-answer")
                    label_text = label_element.inner_text().strip() if label_element else ""

                    # 获取选项内容
                    content_element = label.query_selector(".option-content")
                    content_text = content_element.inner_text().strip() if content_element else ""

                    # 获取value值
                    input_element = label.query_selector("input[type='radio']")
                    value = input_element.get_attribute("value") if input_element else ""

                    if value:  # 只添加有value的选项
                        options.append({
                            'label': label_text,
                            'content': content_text,
                            'value': value
                        })
                        options_contents.append(content_text)

            elif question_type == "multiple":
                # 多选题 - 使用 el-checkbox
                checkbox_labels = self.page.query_selector_all(".el-checkbox")
                for label in checkbox_labels:
                    # 获取选项标签（A、B、C、D）
                    label_element = label.query_selector(".option-answer")
                    label_text = label_element.inner_text().strip() if label_element else ""

                    # 获取选项内容
                    content_element = label.query_selector(".option-content")
                    content_text = content_element.inner_text().strip() if content_element else ""

                    # 获取value值
                    input_element = label.query_selector("input[type='checkbox']")
                    value = input_element.get_attribute("value") if input_element else ""

                    if value:  # 只添加有value的选项
                        options.append({
                            'label': label_text,
                            'content': content_text,
                            'value': value
                        })
                        options_contents.append(content_text)

            # 生成选项哈希（将所有选项内容拼接并排序）
            options_hash = "|".join(sorted(options_contents))

            return {
                'type': question_type,
                'type_name': type_name,
                'title': title_text,
                'options': options,
                'options_hash': options_hash
            }

        except Exception as e:
            print(f"[ERROR] 解析当前题目失败: {str(e)}")
            return None

    def click_next_button(self) -> bool:
        """
        点击下一题按钮

        Returns:
            bool: 是否成功点击
        """
        try:
            # 查找"下一题"按钮
            next_button = self.page.wait_for_selector("button.el-button--success:has-text('下一题')", timeout=5000)

            if next_button:
                next_button.click()
                print("[OK] 已点击下一题按钮")
                time.sleep(1)  # 等待下一题加载
                return True
            else:
                print("[ERROR] 未找到下一题按钮")
                return False

        except Exception as e:
            print(f"[ERROR] 点击下一题按钮失败: {str(e)}")
            return False

    def _find_answer_from_bank(self, question: Dict, question_bank: Dict) -> Optional[List[str]]:
        """
        从题库中查找当前题目的答案（优先API模式，备用多维度匹配）

        Args:
            question: 当前题目信息
            question_bank: 题库数据

        Returns:
            Optional[List[str]]: 正确选项的字母列表（如 ['A'] 或 ['A', 'B', 'C']），如果未找到则返回None
        """
        if not question_bank:
            print("[WARNING] 题库未加载")
            return None

        try:
            question_title = question['title']
            question_options = question.get('options', [])

            # 方式1：优先使用API监听的questionID
            if self.api_question_ids and self.current_question_index < len(self.api_question_ids):
                current_question_id = self.api_question_ids[self.current_question_index]
                print(f"🎯 使用API模式，题目ID: {current_question_id}")

                # 在题库中查找匹配的questionID
                chapters = get_chapters(question_bank)

                for chapter in chapters:
                    for knowledge in chapter.get("knowledges", []):
                        for bank_question in knowledge.get("questions", []):
                            if bank_question.get("QuestionID") == current_question_id:
                                knowledge_name = knowledge.get("Knowledge", "")
                                print(f"[OK] API模式匹配成功（知识点: {knowledge_name}）")

                                # 获取正确答案的选项内容
                                bank_options = bank_question.get("options", [])
                                correct_answer_contents = []

                                for opt in bank_options:
                                    if opt.get("isTrue"):
                                        content = opt.get("oppentionContent", "")
                                        if content:
                                            correct_answer_contents.append(content)

                                if correct_answer_contents:
                                    print(f"   正确答案: {', '.join(correct_answer_contents)}")
                                    return correct_answer_contents

                print("[WARNING] API模式未找到匹配题目，降级到题库匹配")

            # 方式2：备用 - 多维度匹配（标题 + 选项评分）
            print("[DEBUG] 使用题库匹配模式...")

            # 标准化当前题目标题
            current_title_normalized = self._normalize_text(question_title)

            # 标准化当前选项内容
            current_option_contents = []
            for opt in question_options:
                content = self._normalize_text(opt.get('content', ''))
                if content:
                    current_option_contents.append(content)

            # 遍历题库查找匹配的题目
            chapters = get_chapters(question_bank)

            # 收集候选题目
            candidates = []

            for chapter in chapters:
                for knowledge in chapter.get("knowledges", []):
                    knowledge_id = knowledge.get("KnowledgeID", "")
                    knowledge_name = knowledge.get("Knowledge", "")

                    for bank_question in knowledge.get("questions", []):
                        # 标准化题库中的题目标题
                        bank_title_raw = bank_question.get("QuestionTitle", "")
                        bank_title_normalized = self._normalize_text(bank_title_raw)

                        # 检查标题是否匹配（使用包含匹配，提高容错率）
                        if (current_title_normalized == bank_title_normalized or
                            current_title_normalized in bank_title_normalized or
                            bank_title_normalized in current_title_normalized):

                            # 计算选项匹配评分
                            bank_options = bank_question.get("options", [])
                            bank_option_contents = []
                            for opt in bank_options:
                                content = opt.get("oppentionContent", "")
                                content_normalized = self._normalize_text(content)
                                if content_normalized:
                                    bank_option_contents.append(content_normalized)

                            # 计算匹配的选项数量
                            matched_count = 0
                            for curr_content in current_option_contents:
                                for bank_content in bank_option_contents:
                                    # 双向包含匹配
                                    if (curr_content == bank_content or
                                        curr_content in bank_content or
                                        bank_content in curr_content):
                                        matched_count += 1
                                        break

                            # 计算匹配得分
                            if current_option_contents:
                                match_score = matched_count / len(current_option_contents)
                            else:
                                match_score = 0

                            candidates.append({
                                'question': bank_question,
                                'knowledge_id': knowledge_id,
                                'knowledge_name': knowledge_name,
                                'match_score': match_score,
                                'matched_count': matched_count,
                                'total_count': len(current_option_contents)
                            })

            # 如果没有找到任何匹配的题目
            if not candidates:
                print("[WARNING] 在题库中未找到匹配的题目")
                return None

            # 按匹配评分排序，选择最佳匹配
            candidates.sort(key=lambda x: x['match_score'], reverse=True)

            best_match = candidates[0]

            if best_match['match_score'] >= 0.8:
                # 高匹配度（≥80%）
                print(f"[OK] 高匹配度题目（{best_match['match_score']:.1%}，知识点: {best_match['knowledge_name']}）")
            elif best_match['match_score'] >= 0.5:
                # 中等匹配度（50%-80%）
                print(f"[WARNING] 中等匹配度题目（{best_match['match_score']:.1%}，知识点: {best_match['knowledge_name']}）")
            else:
                # 低匹配度（<50%）
                print(f"[WARNING] 低匹配度题目（{best_match['match_score']:.1%}，知识点: {best_match['knowledge_name']}）")

            print(f"   选项匹配: {best_match['matched_count']}/{best_match['total_count']}")

            # 获取正确答案的选项内容（而不是ID）
            bank_options = best_match['question'].get("options", [])
            correct_answer_contents = []  # 存储正确答案的内容文本

            for opt in bank_options:
                if opt.get("isTrue"):
                    content = opt.get("oppentionContent", "")
                    if content:
                        correct_answer_contents.append(content)

            if correct_answer_contents:
                print(f"   正确答案: {', '.join(correct_answer_contents)}")
                return correct_answer_contents
            else:
                print("[WARNING] 题库中未标记正确答案")
                return None

        except Exception as e:
            print(f"[ERROR] 从题库查找答案失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def answer_with_bank(self, question_bank: Dict) -> Dict:
        """
        使用题库进行做题（兼容模式，支持API监听）

        Args:
            question_bank: 题库数据

        Returns:
            Dict: 做题结果统计
        """
        result = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0
        }

        try:
            print("🚀 开始自动做题（兼容模式 - 智能匹配）")
            print("=" * 60)

            # 启动API监听器
            self._start_api_listener()

            # 获取题目总数
            question_items = self.page.query_selector_all(".question-item")
            total_questions = len(question_items)
            print(f"[INFO] 总共 {total_questions} 道题")
            print("=" * 60)

            # 重置当前题目索引
            self.current_question_index = 0

            # 循环做题
            while True:
                # 获取当前题目序号
                current_num = self._get_current_question_number()

                if current_num == 0:
                    print("[WARNING] 无法获取当前题目序号，可能已完成")
                    break

                print(f"\n📌 第 {current_num}/{total_questions} 题")

                # 解析当前题目
                question = self._parse_current_question()
                if not question:
                    print("[ERROR] 解析题目失败")
                    result['failed'] += 1
                    # 点击下一题
                    if not self.click_next_button():
                        break
                    continue

                print(f"   题目类型: {question['type_name']}")
                print(f"   题目内容: {question['title'][:80]}...")
                print(f"   选项数量: {len(question['options'])}")

                # 从题库中查找答案（优先API模式）
                print("[DEBUG] 正在题库中查找答案...")
                answer_letters = self._find_answer_from_bank(question, question_bank)

                if not answer_letters:
                    print("[WARNING] 未在题库中找到答案，跳过该题")
                    result['skipped'] += 1
                    # 点击下一题
                    if not self.click_next_button():
                        break
                    # 更新题目索引
                    self.current_question_index += 1
                    continue

                # 将答案内容转换为选项value（通过选项内容匹配）
                correct_values = []
                for answer_content in answer_letters:
                    for option in question['options']:
                        # 标准化选项内容进行比较
                        option_content_normalized = self._normalize_text(option['content'])
                        answer_content_normalized = self._normalize_text(answer_content)

                        if option_content_normalized == answer_content_normalized:
                            correct_values.append(option['value'])
                            print(f"   匹配选项: {option['label']} - {option['content'][:30]}...")
                            break

                if not correct_values:
                    print(f"[ERROR] 未找到匹配的选项")
                    print(f"   题库答案: {answer_letters}")
                    print(f"   当前选项: {[opt['content'][:30] for opt in question['options']]}")
                    result['failed'] += 1
                    # 点击下一题
                    if not self.click_next_button():
                        break
                    self.current_question_index += 1
                    continue

                # 根据题目类型选择答案
                if question['type'] == "single":
                    success = self._select_single_answer(question, correct_values)
                elif question['type'] == "multiple":
                    success = self._select_multiple_answers(question, correct_values)
                else:
                    print(f"[ERROR] 未知的题目类型: {question['type']}")
                    success = False

                result['total'] += 1

                if success:
                    result['success'] += 1
                    print("[OK] 题目回答完成")
                else:
                    result['failed'] += 1
                    print("[ERROR] 题目回答失败")

                # 点击下一题
                if not self.click_next_button():
                    print("[WARNING] 未找到下一题按钮，可能已是最后一题")
                    break

                # 更新题目索引
                self.current_question_index += 1

            # 停止API监听器
            self._stop_api_listener()

            print("\n" + "=" * 60)
            print("[OK] 做题完成")
            print(f"📊 统计: 总计 {result['total']} 题, 成功 {result['success']} 题, 失败 {result['failed']} 题, 跳过 {result['skipped']} 题")
            print("=" * 60)

            return result

        except Exception as e:
            print(f"[ERROR] 做题流程失败: {str(e)}")
            import traceback
            traceback.print_exc()
            # 确保停止API监听器
            self._stop_api_listener()
            return result

    def answer_with_manual_answers(self, answers_dict: Dict) -> Dict:
        """
        使用手动提供的答案进行做题（兼容模式）

        Args:
            answers_dict: 答案字典，格式为:
                {
                    1: ["A"],  # 第1题答案是A
                    2: ["A", "B", "C"],  # 第2题答案是ABC（多选）
                    ...
                }

        Returns:
            Dict: 做题结果统计
            {
                'total': int,  # 总题数
                'success': int,  # 成功题数
                'failed': int,  # 失败题数
            }
        """
        result = {
            'total': 0,
            'success': 0,
            'failed': 0
        }

        try:
            print("🚀 开始自动做题（兼容模式）")
            print("=" * 60)

            # 获取题目总数
            question_items = self.page.query_selector_all(".question-item")
            total_questions = len(question_items)
            print(f"[INFO] 总共 {total_questions} 道题")
            print("=" * 60)

            # 循环做题
            while True:
                # 获取当前题目序号
                current_num = self._get_current_question_number()

                if current_num == 0:
                    print("[WARNING] 无法获取当前题目序号，可能已完成")
                    break

                # 检查是否超出答案字典范围
                if current_num not in answers_dict:
                    print(f"[WARNING] 第{current_num}题没有提供答案，跳过")
                    # 点击下一题
                    if not self.click_next_button():
                        break
                    continue

                print(f"\n📌 第 {current_num}/{total_questions} 题")

                # 解析当前题目
                question = self._parse_current_question()
                if not question:
                    print("[ERROR] 解析题目失败")
                    result['failed'] += 1
                    # 点击下一题
                    if not self.click_next_button():
                        break
                    continue

                print(f"   题目类型: {question['type_name']}")
                print(f"   题目内容: {question['title'][:80]}...")
                print(f"   选项数量: {len(question['options'])}")

                # 获取答案（字母）
                answer_letters = answers_dict[current_num]
                print(f"   正确答案: {''.join(answer_letters)}")

                # 将答案字母转换为选项value
                correct_values = []
                for letter in answer_letters:
                    for option in question['options']:
                        if option['label'] == f"{letter}、":
                            correct_values.append(option['value'])
                            break

                if not correct_values:
                    print(f"[ERROR] 未找到匹配的选项: {answer_letters}")
                    result['failed'] += 1
                    # 点击下一题
                    if not self.click_next_button():
                        break
                    continue

                # 根据题目类型选择答案
                if question['type'] == "single":
                    success = self._select_single_answer(question, correct_values)
                elif question['type'] == "multiple":
                    success = self._select_multiple_answers(question, correct_values)
                else:
                    print(f"[ERROR] 未知的题目类型: {question['type']}")
                    success = False

                result['total'] += 1

                if success:
                    result['success'] += 1
                    print("[OK] 题目回答完成")
                else:
                    result['failed'] += 1
                    print("[ERROR] 题目回答失败")

                # 点击下一题
                if not self.click_next_button():
                    print("[WARNING] 未找到下一题按钮，可能已是最后一题")
                    break

            print("\n" + "=" * 60)
            print("[OK] 做题完成")
            print(f"📊 统计: 总计 {result['total']} 题, 成功 {result['success']} 题, 失败 {result['failed']} 题")
            print("=" * 60)

            return result

        except Exception as e:
            print(f"[ERROR] 做题流程失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return result
