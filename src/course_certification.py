"""
课程认证模块

用于处理课程相关的认证功能
"""

from playwright.sync_api import sync_playwright
from typing import Optional, List, Dict
import time
import requests
from src.api_client import get_api_client
from src.course_api_answer import APICourseAnswer

# 全局变量，保存浏览器实例
_global_browser = None
_global_page = None
_global_playwright = None

# 全局变量，保存导入的题库
_global_question_bank = None


def import_question_bank(file_path: str) -> bool:
    """
    导入题库文件

    Args:
        file_path: 题库JSON文件路径

    Returns:
        bool: 导入是否成功
    """
    global _global_question_bank

    try:
        from src.question_bank_importer import QuestionBankImporter

        print(f"\n正在导入题库文件: {file_path}")

        # 创建题库导入器
        importer = QuestionBankImporter()

        # 导入题库
        success = importer.import_from_file(file_path)

        if not success:
            print("❌ 题库文件导入失败")
            return False

        # 保存到全局变量
        _global_question_bank = importer.data

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
        print(f"✅ 题库已保存到全局变量")

        return True

    except Exception as e:
        print(f"❌ 导入题库异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def get_question_bank() -> Optional[Dict]:
    """
    获取全局题库数据

    Returns:
        Optional[Dict]: 题库数据，如果未导入则返回None
    """
    global _global_question_bank
    return _global_question_bank


def hello_world():
    """测试函数 - 打印 Hello World"""
    print("\n" + "=" * 50)
    print("🎉 Hello World!")
    print("=" * 50)
    print("✅ 课程认证模块运行成功！")
    print("=" * 50)


def close_browser():
    """关闭全局浏览器实例"""
    global _global_browser, _global_page, _global_playwright

    # 尝试多种方法关闭浏览器
    success = False

    # 方法1: 逐个关闭所有 pages 和 contexts
    if _global_browser:
        try:
            # 获取所有 contexts
            contexts = list(_global_browser.contexts)
            for context in contexts:
                try:
                    # 获取所有 pages
                    pages = list(context.pages)
                    for page in pages:
                        try:
                            page.close()
                        except:
                            pass
                    context.close()
                except:
                    pass
        except:
            pass

    # 方法2: 关闭全局 page
    if _global_page:
        try:
            _global_page.close()
            print("✅ Page 已关闭")
            success = True
        except Exception as e:
            pass

    # 方法3: 关闭 browser
    if _global_browser:
        try:
            _global_browser.close()
            print("✅ Browser 已关闭")
            success = True
        except Exception as e:
            print(f"⚠️ Browser.close() 失败: {e}")

    # 方法4: 停止 playwright
    if _global_playwright:
        try:
            _global_playwright.stop()
            print("✅ Playwright 已停止")
            success = True
        except Exception as e:
            print(f"⚠️ Playwright.stop() 失败: {e}")

    # 清空全局变量
    _global_browser = None
    _global_page = None
    _global_playwright = None

    if not success:
        print("⚠️ 部分浏览器资源可能未完全释放，但已清空引用")


def get_access_token(keep_browser_open: bool = False, skip_prompt: bool = False) -> Optional[tuple]:
    """
    使用Playwright模拟浏览器登录获取课程认证access_token

    Args:
        keep_browser_open: 是否保持浏览器打开（用于后续操作）
        skip_prompt: 是否跳过交互式提示（GUI模式下使用，自动使用已保存的账号）

    Returns:
        Optional[tuple]: (access_token, browser, page, playwright_instance) 如果成功
                         如果 keep_browser_open=False，browser 和 page 为 None
    """
    global _global_browser, _global_page, _global_playwright

    try:
        print("正在启动浏览器进行课程认证登录...")

        # 尝试从配置文件读取凭据
        try:
            from src.settings import get_settings_manager
            settings = get_settings_manager()
            config_username, config_password = settings.get_teacher_credentials()

            if config_username and config_password:
                print("\n💡 检测到已保存的教师端账号")

                # 如果跳过提示（GUI模式），直接使用已保存的账号
                if skip_prompt:
                    print(f"✅ 使用已保存的账号: {config_username[:3]}****")
                    username = config_username
                    password = config_password
                else:
                    # CLI模式，询问用户是否使用已保存的账号
                    use_saved = input("是否使用已保存的账号？(yes/no，默认yes): ").strip().lower()

                    if use_saved in ['', 'yes', 'y', '是']:
                        print(f"✅ 使用已保存的账号: {config_username[:3]}****")
                        username = config_username
                        password = config_password
                    else:
                        print("💡 请手动输入账号密码")
                        username = input("请输入课程认证账户：").strip()
                        password = input("请输入课程认证密码：").strip()
            else:
                # 没有已保存的账号
                if skip_prompt:
                    print("❌ 未找到已保存的教师端账号")
                    return None
                else:
                    username = input("请输入课程认证账户：").strip()
                    password = input("请输入课程认证密码：").strip()
        except Exception:
            if skip_prompt:
                print("❌ 读取配置文件失败")
                return None
            else:
                username = input("请输入课程认证账户：").strip()
                password = input("请输入课程认证密码：").strip()

        if not username or not password:
            print("❌ 用户名或密码不能为空")
            return None

        # 启动playwright
        p = sync_playwright().start()
        browser = p.chromium.launch(headless=False)

        try:
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0"
            )

            page = context.new_page()
            captured_data = None

            def handle_response(response):
                nonlocal captured_data
                if 'token' in response.url:
                    print(f"🔍 捕获到 token 响应")
                    try:
                        data = response.json()
                        captured_data = data
                        print(f"✅ 成功捕获响应数据")
                    except Exception as e:
                        print(f"解析失败: {e}")

            page.on('response', handle_response)

            login_url = "https://zxsz.cqzuxia.com/#/login/index"
            print(f"正在打开登录页面: {login_url}")
            page.goto(login_url)

            print("等待登录表单加载...")
            page.wait_for_selector("input[placeholder='登录账号']", timeout=10000)

            print(f"正在填写账户: {username}")
            page.fill("input[placeholder='登录账号']", username)

            print("正在填写密码")
            page.fill("input[placeholder='登录密码']", password)

            print("正在点击登录按钮...")
            page.click(".lic-clf-loginbut")

            print("等待登录成功...")
            try:
                page.wait_for_url("**/home", timeout=15000)
                print("✅ 页面已跳转到 home，登录成功")
                time.sleep(1)
            except Exception as e:
                print(f"⚠️ 等待页面跳转超时: {e}")
                print("继续检查是否捕获到 token...")

            if captured_data and 'access_token' in captured_data:
                access_token = captured_data['access_token']
                print("\n" + "=" * 50)
                print("✅ 登录成功！")
                print("=" * 50)
                print(f"access_token: {access_token}")
                print(f"token类型: Bearer")
                print(f"有效期: 5小时 (18000秒)")
                print("=" * 50)

                if keep_browser_open:
                    # 保存到全局变量
                    _global_browser = browser
                    _global_page = page
                    _global_playwright = p
                    print("\n💡 浏览器保持打开状态，用于后续操作")
                    return (access_token, browser, page, p)
                else:
                    browser.close()
                    p.stop()
                    return (access_token, None, None, None)
            else:
                print("❌ 未能在响应中捕获到 access_token")
                if captured_data:
                    print(f"响应内容: {captured_data}")
                browser.close()
                p.stop()
                return None

        except Exception as e:
            print(f"❌ 登录过程异常：{str(e)}")
            browser.close()
            p.stop()
            return None

    except Exception as e:
        print(f"❌ Playwright登录异常：{str(e)}")
        import traceback
        traceback.print_exc()
        return None


def start_answering():
    """
    开始做题功能
    登录并获取课程列表
    """
    global _global_browser, _global_page, _global_playwright

    try:
        print("\n" + "=" * 60)
        print("🎓 课程认证 - 开始做题")
        print("=" * 60)

        # 1. 获取 access_token（保持浏览器打开）
        print("\n步骤 1/2: 正在登录...")
        result = get_access_token(keep_browser_open=True)

        if not result:
            print("\n❌ 登录失败，无法继续")
            return

        access_token, browser, page, p = result

        print("\n步骤 2/2: 正在获取课程列表...")

        # 2. 请求课程列表API
        api_url = "https://zxsz.cqzuxia.com/teacherCertifiApi/api/ModuleTeacher/GetLessonListByTeacher"

        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'authorization': f'Bearer {access_token}',
            'dnt': '1',
            'priority': 'u=1, i',
            'referer': 'https://zxsz.cqzuxia.com/',
            'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Microsoft Edge";v="144"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'sec-gpc': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0'
        }

        try:
            # 使用 API 客户端以获得自动重试功能
            api_client = get_api_client()
            response = api_client.get(api_url, headers=headers)

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
                                print(f"❌ 无效的选择，请输入 0-{len(filtered_courses)} 之间的数字")
                        except ValueError:
                            print("❌ 请输入有效的数字")

                else:
                    print(f"❌ API返回错误: {data.get('message', '未知错误')}")
                    close_browser()
            else:
                print(f"❌ 请求失败，状态码: {response.status_code}")
                close_browser()

        except requests.exceptions.Timeout:
            print("❌ 请求超时")
            close_browser()
        except requests.exceptions.RequestException as e:
            print(f"❌ 请求异常: {str(e)}")
            close_browser()
        except Exception as e:
            print(f"❌ 处理响应异常: {str(e)}")
            close_browser()

    except Exception as e:
        print(f"❌ 开始做题异常: {str(e)}")
        import traceback
        traceback.print_exc()
        close_browser()


def navigate_to_course_page(ecourse_id: str, page, access_token: str):
    """
    使用已有的浏览器实例跳转到课程评估页面，并提取题目列表

    Args:
        ecourse_id: 课程ID
        page: Playwright page实例
        access_token: 访问令牌
    """

    def show_operation_menu():
        """显示操作菜单"""
        print("\n" + "=" * 60)
        print("📋 操作菜单")
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

        page.goto(course_url)

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
                print("⚠️ 未找到题目列表，页面可能加载失败")
                print("\n💡 浏览器将保持打开状态，你可以手动查看")
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

                                # 如果第一个图标不隐藏（显示✓），则已完成
                                if "display: none" not in first_icon_style:
                                    is_completed = True
                                # 如果第二个图标不隐藏（显示✕），则未完成
                                elif "display: none" not in second_icon_style:
                                    is_completed = False

                        # 状态标记
                        status_mark = "✅" if is_completed else "❌"

                        # 如果已完成，使用灰色显示
                        if is_completed:
                            print(f"{i}. {status_mark} {question_name} (已完成)")
                        else:
                            print(f"{i}. {status_mark} {question_name}")

                    except Exception as e:
                        print(f"{i}. ❌ 解析题目失败: {e}")

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
                        # 开始做题（兼容模式）- 自动遍历所有未完成的题目
                        print("\n✅ 选择了：开始做题（兼容模式）")
                        print("💡 将自动遍历所有未完成的题目")

                        # 检查是否已导入题库
                        question_bank = get_question_bank()
                        if not question_bank:
                            print("⚠️ 未检测到题库，请先导入题库")
                            print("💡 提示：在操作菜单选择'5. 导入题库'功能")
                            continue

                        # 自动遍历所有题目
                        print("\n" + "=" * 60)
                        print("🚀 开始自动遍历所有题目")
                        print("=" * 60)

                        # 获取所有章节（包括折叠的）
                        chapters = page.query_selector_all(".el-sub-menu")
                        print(f"📋 找到 {len(chapters)} 个章节")

                        total_completed = 0
                        total_failed = 0

                        # 遍历每个章节
                        for chapter_idx, chapter in enumerate(chapters):
                            try:
                                # 获取章节标题
                                chapter_title_elem = chapter.query_selector(".el-sub-menu__title span")
                                chapter_title = chapter_title_elem.inner_text().strip() if chapter_title_elem else f"第{chapter_idx+1}章"
                                print(f"\n📖 章节 {chapter_idx+1}: {chapter_title}")

                                # 检查章节是否折叠
                                chapter_title_div = chapter.query_selector(".el-sub-menu__title")
                                if chapter_title_div:
                                    chapter_class = chapter.get_attribute("class") or ""
                                    is_opened = "is-opened" in chapter_class

                                    if not is_opened:
                                        # 章节是折叠的，需要点击展开
                                        print(f"   ↕️  正在展开折叠的章节...")
                                        chapter_title_div.click()
                                        time.sleep(0.5)  # 等待展开动画
                                        print(f"   ✅ 章节已展开")
                                    else:
                                        print(f"   ✅ 章节已展开")

                                # 获取该章节下的所有题目
                                question_items_in_chapter = chapter.query_selector_all(".el-menu-item")
                                print(f"   📝 该章节有 {len(question_items_in_chapter)} 个题目")

                                # 检查每个题目的完成状态
                                for q_idx, item in enumerate(question_items_in_chapter):
                                    try:
                                        # 获取题目名称
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

                                        # 如果已完成，跳过
                                        if is_completed:
                                            print(f"      ⏭️  [{q_idx+1}] {question_name[:40]}... (已完成)")
                                            continue

                                        # 未完成，开始做题
                                        print(f"\n      🎯 开始做题: [{q_idx+1}] {question_name[:40]}...")

                                        # 创建自动做题器
                                        auto_answer = CourseAutoAnswer(page)

                                        # 点击题目进入答题界面
                                        item.click()
                                        time.sleep(2)

                                        # 点击"开始测评"按钮
                                        try:
                                            start_button = page.wait_for_selector("button.el-button--primary:has-text('开始测评')", timeout=5000)
                                            start_button.click()
                                            print("      ✅ 已点击开始测评按钮")
                                            time.sleep(2)  # 等待答题界面加载

                                            # 开始做题
                                            result = auto_answer.answer_with_bank(question_bank)

                                            if result['total'] > 0:
                                                success_rate = result['success'] / result['total']
                                                print(f"      ✅ 做题完成: 成功 {result['success']}/{result['total']} 题 ({success_rate:.1%})")
                                                total_completed += result['success']
                                                total_failed += result['failed']
                                            else:
                                                print(f"      ⚠️ 没有题目被回答")

                                            # 等待网站自动跳转（参考学生端逻辑）
                                            print(f"      ⏳ 等待网站显示成功提示并自动跳转...")

                                            # 检测成功提示（最多等待10秒）
                                            start_time = time.time()
                                            success_detected = False

                                            while time.time() - start_time < 10:
                                                try:
                                                    # 检查是否有成功提示（.eva-success）
                                                    success_element = page.query_selector(".eva-success")
                                                    if success_element and not success_detected:
                                                        print(f"      ✅ 检测到成功提示，等待5秒自动跳转...")
                                                        success_detected = True
                                                        break
                                                    time.sleep(0.5)
                                                except:
                                                    time.sleep(0.5)

                                            if success_detected:
                                                # 等待5秒倒计时+1秒缓冲
                                                time.sleep(6)

                                                # 检测是否成功跳转
                                                print(f"      🔍 检测是否自动跳转...")

                                                # 方法1：检测答题页面元素是否消失
                                                auto_jumped = False
                                                try:
                                                    page.wait_for_selector(".question-type", state="hidden", timeout=3000)
                                                    print(f"      ✅ 已自动跳转到题目列表")
                                                    auto_jumped = True
                                                except:
                                                    print(f"      ⚠️ 答题页面元素仍然存在")

                                                # 方法2：检测是否出现"开始测评"按钮
                                                if not auto_jumped:
                                                    try:
                                                        start_button = page.query_selector("button:has-text('开始测评')", timeout=2000)
                                                        if start_button:
                                                            print(f"      ✅ 检测到'开始测评'按钮，已自动跳转")
                                                            auto_jumped = True
                                                    except:
                                                        pass

                                                # 如果成功自动跳转，标记知识点处理完成
                                                if auto_jumped:
                                                    print(f"      🎉 网站已自动跳转，继续下一题")
                                                    # 重新获取章节和题目元素（因为页面可能变化了）
                                                    time.sleep(1)
                                                    chapters_list = page.query_selector_all(".el-sub-menu")
                                                    if chapter_idx < len(chapters_list):
                                                        chapter = chapters_list[chapter_idx]
                                                        question_items_in_chapter = chapter.query_selector_all(".el-menu-item")
                                                    continue
                                                else:
                                                    print(f"      ⚠️ 未检测到自动跳转，手动返回题目列表")
                                                    page.goto(course_url)
                                                    time.sleep(2)
                                                    # 重新获取章节和题目元素
                                                    chapter = page.query_selector_all(".el-sub-menu")[chapter_idx]
                                                    question_items_in_chapter = chapter.query_selector_all(".el-menu-item")
                                                    continue
                                            else:
                                                print(f"      ⚠️ 超时未检测到成功提示，手动返回题目列表")
                                                page.goto(course_url)
                                                time.sleep(2)
                                                # 重新获取章节和题目元素
                                                chapter = page.query_selector_all(".el-sub-menu")[chapter_idx]
                                                question_items_in_chapter = chapter.query_selector_all(".el-menu-item")
                                                continue

                                        except Exception as e:
                                            print(f"      ❌ 做题失败: {str(e)}")
                                            total_failed += 1
                                            # 出错时也要返回题目列表
                                            page.goto(course_url)
                                            time.sleep(2)
                                            # 重新获取章节和题目元素
                                            chapter = page.query_selector_all(".el-sub-menu")[chapter_idx]
                                            question_items_in_chapter = chapter.query_selector_all(".el-menu-item")
                                            continue

                                    except Exception as e:
                                        print(f"      ⚠️ 题目处理失败: {str(e)}")
                                        continue

                            except Exception as e:
                                print(f"   ⚠️ 章节处理失败: {str(e)}")
                                continue

                        # 所有题目处理完成
                        print("\n" + "=" * 60)
                        print("✅ 所有题目遍历完成")
                        print(f"📊 总计: 成功 {total_completed} 题, 失败 {total_failed} 题")
                        print("=" * 60)

                        # 退出内层循环，重新显示题目列表和菜单
                        break

                    elif choice == "2":
                        # 开始做题（API模式）- 只做未完成的题目
                        print("\n✅ 选择了：开始做题（API模式）")
                        print("💡 将自动遍历未完成的题目（API直接提交）")

                        # 检查是否已导入题库
                        question_bank = get_question_bank()
                        if not question_bank:
                            print("⚠️ 未检测到题库，请先导入题库")
                            print("💡 提示：在操作菜单选择'5. 导入题库'功能")
                            continue

                        # 创建API做题器
                        api_answer = APICourseAnswer(access_token)

                        # 自动做题（跳过已完成的）
                        result = api_answer.auto_answer_course(ecourse_id, question_bank, skip_completed=True)

                        # 显示结果
                        print("\n" + "=" * 60)
                        print("✅ API模式做题完成")
                        print("=" * 60)
                    elif choice == "3":
                        # 重新作答（兼容模式）- 自动遍历所有题目（包括已完成的）
                        print("\n✅ 选择了：重新作答（兼容模式）")
                        print("💡 将自动遍历所有题目（包括已完成的题目）")

                        # 检查是否已导入题库
                        question_bank = get_question_bank()
                        if not question_bank:
                            print("⚠️ 未检测到题库，请先导入题库")
                            print("💡 提示：在操作菜单选择'5. 导入题库'功能")
                            continue

                        # 自动遍历所有题目（包括已完成的）
                        print("\n" + "=" * 60)
                        print("🚀 开始重新作答所有题目")
                        print("=" * 60)

                        # 获取所有章节（包括折叠的）
                        chapters = page.query_selector_all(".el-sub-menu")
                        print(f"📋 找到 {len(chapters)} 个章节")

                        total_completed = 0
                        total_failed = 0

                        # 遍历每个章节
                        for chapter_idx, chapter in enumerate(chapters):
                            try:
                                # 获取章节标题
                                chapter_title_elem = chapter.query_selector(".el-sub-menu__title span")
                                chapter_title = chapter_title_elem.inner_text().strip() if chapter_title_elem else f"第{chapter_idx+1}章"
                                print(f"\n📖 章节 {chapter_idx+1}: {chapter_title}")

                                # 检查章节是否折叠
                                chapter_title_div = chapter.query_selector(".el-sub-menu__title")
                                if chapter_title_div:
                                    chapter_class = chapter.get_attribute("class") or ""
                                    is_opened = "is-opened" in chapter_class

                                    if not is_opened:
                                        # 章节是折叠的，需要点击展开
                                        print(f"   ↕️  正在展开折叠的章节...")
                                        chapter_title_div.click()
                                        time.sleep(0.5)  # 等待展开动画
                                        print(f"   ✅ 章节已展开")
                                    else:
                                        print(f"   ✅ 章节已展开")

                                # 获取该章节下的所有题目
                                question_items_in_chapter = chapter.query_selector_all(".el-menu-item")
                                print(f"   📝 该章节有 {len(question_items_in_chapter)} 个题目")

                                # 检查每个题目的完成状态（但不跳过）
                                for q_idx, item in enumerate(question_items_in_chapter):
                                    try:
                                        # 获取题目名称
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

                                        # 显示状态但不跳过
                                        status_text = "已完成" if is_completed else "未完成"
                                        print(f"\n      🎯 重新作答: [{q_idx+1}] {question_name[:40]}... ({status_text})")

                                        # 点击题目进入答题界面
                                        item.click()
                                        time.sleep(2)

                                        # 点击"开始测评"按钮
                                        try:
                                            start_button = page.wait_for_selector("button.el-button--primary:has-text('开始测评')", timeout=5000)
                                            start_button.click()
                                            print("      ✅ 已点击开始测评按钮")
                                            time.sleep(2)  # 等待答题界面加载

                                            # 创建自动做题器并开始做题
                                            auto_answer = CourseAutoAnswer(page)
                                            result = auto_answer.answer_with_bank(question_bank)

                                            if result['total'] > 0:
                                                success_rate = result['success'] / result['total']
                                                print(f"      ✅ 做题完成: 成功 {result['success']}/{result['total']} 题 ({success_rate:.1%})")
                                                total_completed += result['success']
                                                total_failed += result['failed']
                                            else:
                                                print(f"      ⚠️ 没有题目被回答")

                                            # 等待网站自动跳转（参考学生端逻辑）
                                            print(f"      ⏳ 等待网站显示成功提示并自动跳转...")

                                            # 检测成功提示（最多等待10秒）
                                            start_time = time.time()
                                            success_detected = False

                                            while time.time() - start_time < 10:
                                                try:
                                                    # 检查是否有成功提示（.eva-success）
                                                    success_element = page.query_selector(".eva-success")
                                                    if success_element and not success_detected:
                                                        print(f"      ✅ 检测到成功提示，等待5秒自动跳转...")
                                                        success_detected = True
                                                        break
                                                    time.sleep(0.5)
                                                except:
                                                    time.sleep(0.5)

                                            if success_detected:
                                                # 等待5秒倒计时+1秒缓冲
                                                time.sleep(6)

                                                # 检测是否成功跳转
                                                print(f"      🔍 检测是否自动跳转...")

                                                # 方法1：检测答题页面元素是否消失
                                                auto_jumped = False
                                                try:
                                                    page.wait_for_selector(".question-type", state="hidden", timeout=3000)
                                                    print(f"      ✅ 已自动跳转到题目列表")
                                                    auto_jumped = True
                                                except:
                                                    print(f"      ⚠️ 答题页面元素仍然存在")

                                                # 方法2：检测是否出现"开始测评"按钮
                                                if not auto_jumped:
                                                    try:
                                                        start_button = page.query_selector("button:has-text('开始测评')", timeout=2000)
                                                        if start_button:
                                                            print(f"      ✅ 检测到'开始测评'按钮，已自动跳转")
                                                            auto_jumped = True
                                                    except:
                                                        pass

                                                # 如果成功自动跳转，标记知识点处理完成
                                                if auto_jumped:
                                                    print(f"      🎉 网站已自动跳转，继续下一题")
                                                    # 重新获取章节和题目元素（因为页面可能变化了）
                                                    time.sleep(1)
                                                    chapters_list = page.query_selector_all(".el-sub-menu")
                                                    if chapter_idx < len(chapters_list):
                                                        chapter = chapters_list[chapter_idx]
                                                        question_items_in_chapter = chapter.query_selector_all(".el-menu-item")
                                                    continue
                                                else:
                                                    print(f"      ⚠️ 未检测到自动跳转，手动返回题目列表")
                                                    page.goto(course_url)
                                                    time.sleep(2)
                                                    # 重新获取章节和题目元素
                                                    chapter = page.query_selector_all(".el-sub-menu")[chapter_idx]
                                                    question_items_in_chapter = chapter.query_selector_all(".el-menu-item")
                                                    continue
                                            else:
                                                print(f"      ⚠️ 超时未检测到成功提示，手动返回题目列表")
                                                page.goto(course_url)
                                                time.sleep(2)
                                                # 重新获取章节和题目元素
                                                chapter = page.query_selector_all(".el-sub-menu")[chapter_idx]
                                                question_items_in_chapter = chapter.query_selector_all(".el-menu-item")
                                                continue

                                        except Exception as e:
                                            print(f"      ❌ 做题失败: {str(e)}")
                                            total_failed += 1
                                            # 出错时也要返回题目列表
                                            page.goto(course_url)
                                            time.sleep(2)
                                            # 重新获取章节和题目元素
                                            chapter = page.query_selector_all(".el-sub-menu")[chapter_idx]
                                            question_items_in_chapter = chapter.query_selector_all(".el-menu-item")
                                            continue

                                    except Exception as e:
                                        print(f"      ⚠️ 题目处理失败: {str(e)}")
                                        continue

                            except Exception as e:
                                print(f"   ⚠️ 章节处理失败: {str(e)}")
                                continue

                        # 所有题目处理完成
                        print("\n" + "=" * 60)
                        print("✅ 所有题目重新作答完成")
                        print(f"📊 总计: 成功 {total_completed} 题, 失败 {total_failed} 题")
                        print("=" * 60)

                        # 退出内层循环，重新显示题目列表和菜单
                        break
                    elif choice == "4":
                        # 重新作答（API模式）- 做所有题目（包括已完成的）
                        print("\n✅ 选择了：重新作答（API模式）")
                        print("💡 将自动遍历所有题目（包括已完成的题目）")

                        # 检查是否已导入题库
                        question_bank = get_question_bank()
                        if not question_bank:
                            print("⚠️ 未检测到题库，请先导入题库")
                            print("💡 提示：在操作菜单选择'5. 导入题库'功能")
                            continue

                        # 创建API做题器
                        api_answer = APICourseAnswer(access_token)

                        # 自动做题（包括已完成的）
                        result = api_answer.auto_answer_course(ecourse_id, question_bank, skip_completed=False)

                        # 显示结果
                        print("\n" + "=" * 60)
                        print("✅ API模式重新作答完成")
                        print("=" * 60)
                    elif choice == "5":
                        # 导入题库
                        print("\n✅ 选择了：导入题库")
                        print("=" * 60)
                        print("💡 请输入题库JSON文件的路径")
                        print("提示：可以直接拖拽文件到此处")
                        print("=" * 60)

                        file_path = input("\n文件路径: ").strip().strip('"').strip("'")

                        if not file_path:
                            print("❌ 文件路径不能为空")
                            continue

                        # 调用题库导入功能
                        success = import_question_bank(file_path)

                        if success:
                            print("\n✅ 题库导入成功！")
                            print("💡 现在可以选择'开始做题'或'重新作答'使用导入的题库")
                            # 重新显示操作菜单
                            show_operation_menu()
                        else:
                            print("\n❌ 题库导入失败")
                            # 重新显示操作菜单
                            show_operation_menu()
                    elif choice == "0":
                        print("\n🔙 退出")
                        should_exit = True
                        break
                    else:
                        print("\n❌ 无效的选择，请输入 1-5 或 0")
                        # 重新显示操作菜单
                        show_operation_menu()

    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
    except Exception as e:
        print(f"❌ 跳转页面异常: {str(e)}")
        import traceback
        traceback.print_exc()


class CourseAutoAnswer:
    """课程认证自动做题类（兼容模式）"""

    def __init__(self, page):
        """
        初始化自动做题器

        Args:
            page: Playwright页面对象
        """
        self.page = page
        self.api_question_ids = []  # 存储从API获取的题目ID
        self.api_listener_active = False  # API监听器是否激活
        self.current_question_index = 0  # 当前题目索引（用于API模式）

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
                        print(f"✅ 监听到API，获取到 {len(self.api_question_ids)} 个题目ID")
                        # 打印前3个题目ID用于调试
                        if self.api_question_ids:
                            print(f"   题目ID: {self.api_question_ids[0]}...")

                except Exception as e:
                    print(f"⚠️ API监听异常: {str(e)}")

                return route.continue_()

            return route.continue_()

        # 注册路由监听
        self.page.route('**/*', handle_route)

    def _start_api_listener(self):
        """启动API监听"""
        if not self.api_listener_active:
            self.api_listener_active = True
            self._setup_api_listener()
            print("✅ API监听器已启动")

    def _stop_api_listener(self):
        """停止API监听"""
        self.api_listener_active = False
        print("✅ API监听器已停止")

    def _normalize_text(self, text: str) -> str:
        """
        标准化文本（参考学生端逻辑）

        Args:
            text: 原始文本

        Returns:
            str: 标准化后的文本
        """
        if not text:
            return ""

        import html
        import re

        # 解码HTML实体
        text = html.unescape(text)

        # 移除HTML注释
        text = re.sub(r'<!--.*?-->', '', text)

        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)

        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

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
            print(f"❌ 解析题目类型失败: {str(e)}")
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
                print("❌ 未找到题目标题元素")
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
            print(f"❌ 解析当前题目失败: {str(e)}")
            return None

    def _get_current_question_number(self) -> int:
        """
        获取当前题目序号

        Returns:
            int: 当前题目序号（1-based），如果获取失败返回0
        """
        try:
            # 查找所有题目序号元素
            question_items = self.page.query_selector_all(".question-item")

            for i, item in enumerate(question_items, 1):
                # 检查是否有"selected"类
                class_attr = item.get_attribute("class") or ""
                if "selected" in class_attr:
                    print(f"📍 当前题目序号: {i}/{len(question_items)}")
                    return i

            # 如果没有找到selected，返回0
            return 0

        except Exception as e:
            print(f"❌ 获取当前题目序号失败: {str(e)}")
            return 0

    def _select_single_answer(self, question: Dict, correct_values: List[str]) -> bool:
        """
        选择单选题/判断题的答案

        Args:
            question: 题目信息
            correct_values: 正确选项的value列表

        Returns:
            bool: 是否成功选择
        """
        try:
            if not correct_values:
                print("❌ 没有正确答案")
                return False

            correct_value = correct_values[0]  # 单选题只有一个正确答案

            # 查找对应的选项并点击
            for option in question['options']:
                if option['value'] == correct_value:
                    # 点击选项
                    option_label = option['label']
                    print(f"   选择答案: {option_label}")

                    # 点击label元素
                    selector = f".el-radio:has(input[value='{correct_value}'])"
                    self.page.click(selector, timeout=10000)
                    time.sleep(0.5)  # 等待选择完成
                    return True

            print(f"❌ 未找到value为 {correct_value} 的选项")
            return False

        except Exception as e:
            print(f"❌ 选择单选答案失败: {str(e)}")
            return False

    def _select_multiple_answers(self, question: Dict, correct_values: List[str]) -> bool:
        """
        选择多选题的答案

        Args:
            question: 题目信息
            correct_values: 正确选项的value列表

        Returns:
            bool: 是否成功选择
        """
        try:
            if not correct_values:
                print("❌ 没有正确答案")
                return False

            selected_count = 0

            # 查找对应的选项并点击
            for correct_value in correct_values:
                for option in question['options']:
                    if option['value'] == correct_value:
                        # 点击选项
                        option_label = option['label']
                        option_content = option['content'][:30]
                        print(f"   选择答案: {option_label} - {option_content}...")

                        # 点击label元素
                        selector = f".el-checkbox:has(input[value='{correct_value}'])"
                        self.page.click(selector, timeout=10000)
                        selected_count += 1

                        # 延迟，防止点击过快导致选择失败
                        time.sleep(0.3)
                        break

            if selected_count == len(correct_values):
                print(f"✅ 成功选择 {selected_count} 个答案")
                return True
            else:
                print(f"⚠️ 只选择了 {selected_count}/{len(correct_values)} 个答案")
                return False

        except Exception as e:
            print(f"❌ 选择多选答案失败: {str(e)}")
            return False

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
                print("✅ 已点击下一题按钮")
                time.sleep(1)  # 等待下一题加载
                return True
            else:
                print("❌ 未找到下一题按钮")
                return False

        except Exception as e:
            print(f"❌ 点击下一题按钮失败: {str(e)}")
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
            print("⚠️ 题库未加载")
            return None

        try:
            question_title = question['title']
            question_options = question.get('options', [])

            # 方式1：优先使用API监听的questionID
            if self.api_question_ids and self.current_question_index < len(self.api_question_ids):
                current_question_id = self.api_question_ids[self.current_question_index]
                print(f"🎯 使用API模式，题目ID: {current_question_id}")

                # 在题库中查找匹配的questionID
                chapters = []
                if "class" in question_bank and "course" in question_bank["class"]:
                    chapters = question_bank["class"]["course"].get("chapters", [])
                elif "chapters" in question_bank:
                    chapters = question_bank["chapters"]

                for chapter in chapters:
                    for knowledge in chapter.get("knowledges", []):
                        for bank_question in knowledge.get("questions", []):
                            if bank_question.get("QuestionID") == current_question_id:
                                knowledge_name = knowledge.get("Knowledge", "")
                                print(f"✅ API模式匹配成功（知识点: {knowledge_name}）")

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

                print("⚠️ API模式未找到匹配题目，降级到题库匹配")

            # 方式2：备用 - 多维度匹配（标题 + 选项评分）
            print("🔍 使用题库匹配模式...")

            # 标准化当前题目标题
            current_title_normalized = self._normalize_text(question_title)

            # 标准化当前选项内容
            current_option_contents = []
            for opt in question_options:
                content = self._normalize_text(opt.get('content', ''))
                if content:
                    current_option_contents.append(content)

            # 遍历题库查找匹配的题目
            chapters = []
            if "class" in question_bank and "course" in question_bank["class"]:
                chapters = question_bank["class"]["course"].get("chapters", [])
            elif "chapters" in question_bank:
                chapters = question_bank["chapters"]

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
                print("⚠️ 在题库中未找到匹配的题目")
                return None

            # 按匹配评分排序，选择最佳匹配
            candidates.sort(key=lambda x: x['match_score'], reverse=True)

            best_match = candidates[0]

            if best_match['match_score'] >= 0.8:
                # 高匹配度（≥80%）
                print(f"✅ 高匹配度题目（{best_match['match_score']:.1%}，知识点: {best_match['knowledge_name']}）")
            elif best_match['match_score'] >= 0.5:
                # 中等匹配度（50%-80%）
                print(f"⚠️ 中等匹配度题目（{best_match['match_score']:.1%}，知识点: {best_match['knowledge_name']}）")
            else:
                # 低匹配度（<50%）
                print(f"⚠️ 低匹配度题目（{best_match['match_score']:.1%}，知识点: {best_match['knowledge_name']}）")

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
                print("⚠️ 题库中未标记正确答案")
                return None

        except Exception as e:
            print(f"❌ 从题库查找答案失败: {str(e)}")
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
            print(f"📋 总共 {total_questions} 道题")
            print("=" * 60)

            # 重置当前题目索引
            self.current_question_index = 0

            # 循环做题
            while True:
                # 获取当前题目序号
                current_num = self._get_current_question_number()

                if current_num == 0:
                    print("⚠️ 无法获取当前题目序号，可能已完成")
                    break

                print(f"\n📌 第 {current_num}/{total_questions} 题")

                # 解析当前题目
                question = self._parse_current_question()
                if not question:
                    print("❌ 解析题目失败")
                    result['failed'] += 1
                    # 点击下一题
                    if not self.click_next_button():
                        break
                    continue

                print(f"   题目类型: {question['type_name']}")
                print(f"   题目内容: {question['title'][:80]}...")
                print(f"   选项数量: {len(question['options'])}")

                # 从题库中查找答案（优先API模式）
                print("🔍 正在题库中查找答案...")
                answer_letters = self._find_answer_from_bank(question, question_bank)

                if not answer_letters:
                    print("⚠️ 未在题库中找到答案，跳过该题")
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
                    print(f"❌ 未找到匹配的选项")
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
                    print(f"❌ 未知的题目类型: {question['type']}")
                    success = False

                result['total'] += 1

                if success:
                    result['success'] += 1
                    print("✅ 题目回答完成")
                else:
                    result['failed'] += 1
                    print("❌ 题目回答失败")

                # 点击下一题
                if not self.click_next_button():
                    print("⚠️ 未找到下一题按钮，可能已是最后一题")
                    break

                # 更新题目索引
                self.current_question_index += 1

            # 停止API监听器
            self._stop_api_listener()

            print("\n" + "=" * 60)
            print("✅ 做题完成")
            print(f"📊 统计: 总计 {result['total']} 题, 成功 {result['success']} 题, 失败 {result['failed']} 题, 跳过 {result['skipped']} 题")
            print("=" * 60)

            return result

        except Exception as e:
            print(f"❌ 做题流程失败: {str(e)}")
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
            print(f"📋 总共 {total_questions} 道题")
            print("=" * 60)

            # 循环做题
            while True:
                # 获取当前题目序号
                current_num = self._get_current_question_number()

                if current_num == 0:
                    print("⚠️ 无法获取当前题目序号，可能已完成")
                    break

                # 检查是否超出答案字典范围
                if current_num not in answers_dict:
                    print(f"⚠️ 第{current_num}题没有提供答案，跳过")
                    # 点击下一题
                    if not self.click_next_button():
                        break
                    continue

                print(f"\n📌 第 {current_num}/{total_questions} 题")

                # 解析当前题目
                question = self._parse_current_question()
                if not question:
                    print("❌ 解析题目失败")
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
                    print(f"❌ 未找到匹配的选项: {answer_letters}")
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
                    print(f"❌ 未知的题目类型: {question['type']}")
                    success = False

                result['total'] += 1

                if success:
                    result['success'] += 1
                    print("✅ 题目回答完成")
                else:
                    result['failed'] += 1
                    print("❌ 题目回答失败")

                # 点击下一题
                if not self.click_next_button():
                    print("⚠️ 未找到下一题按钮，可能已是最后一题")
                    break

            print("\n" + "=" * 60)
            print("✅ 做题完成")
            print(f"📊 统计: 总计 {result['total']} 题, 成功 {result['success']} 题, 失败 {result['failed']} 题")
            print("=" * 60)

            return result

        except Exception as e:
            print(f"❌ 做题流程失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return result
