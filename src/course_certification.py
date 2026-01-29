"""
课程认证模块

用于处理课程相关的认证功能
"""

from playwright.sync_api import sync_playwright
from typing import Optional, List, Dict
import time
import requests

# 全局变量，保存浏览器实例
_global_browser = None
_global_page = None
_global_playwright = None


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
    try:
        if _global_browser:
            _global_browser.close()
            _global_browser = None
        if _global_playwright:
            _global_playwright.stop()
            _global_playwright = None
        _global_page = None
        print("✅ 浏览器已关闭")
    except Exception as e:
        print(f"⚠️ 关闭浏览器时出错: {e}")


def get_access_token(keep_browser_open: bool = False) -> Optional[tuple]:
    """
    使用Playwright模拟浏览器登录获取课程认证access_token

    Args:
        keep_browser_open: 是否保持浏览器打开（用于后续操作）

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
                username = input("请输入课程认证账户：").strip()
                password = input("请输入课程认证密码：").strip()
        except Exception:
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
            response = requests.get(api_url, headers=headers, timeout=10)

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
                                    navigate_to_course_page(ecourse_id, page)
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


def navigate_to_course_page(ecourse_id: str, page):
    """
    使用已有的浏览器实例跳转到课程评估页面，并提取题目列表

    Args:
        ecourse_id: 课程ID
        page: Playwright page实例
    """
    try:
        print(f"\n正在跳转到课程页面...")

        course_url = f"https://zxsz.cqzuxia.com/#/major-course/course-evaluate/{ecourse_id}"

        print(f"📖 正在打开课程页面...")
        print(f"🔗 URL: {course_url}")

        page.goto(course_url)

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
            print("\n" + "=" * 60)
            print("📋 操作菜单")
            print("=" * 60)
            print("1. 开始做题（兼容模式）")
            print("2. 开始做题（API模式）")
            print("3. 重新作答（兼容模式）")
            print("4. 重新作答（API模式）")
            print("5. 退出")
            print("=" * 60)

            while True:
                choice = input("\n请选择操作 (1-5): ").strip()

                if choice == "1":
                    print("\n✅ 选择了：开始做题（兼容模式）")
                    print("💡 功能开发中...")
                    # TODO: 实现兼容模式做题功能
                elif choice == "2":
                    print("\n✅ 选择了：开始做题（API模式）")
                    print("💡 功能开发中...")
                    # TODO: 实现API模式做题功能
                elif choice == "3":
                    print("\n✅ 选择了：重新作答（兼容模式）")
                    print("💡 功能开发中...")
                    # TODO: 实现兼容模式重新作答功能
                elif choice == "4":
                    print("\n✅ 选择了：重新作答（API模式）")
                    print("💡 功能开发中...")
                    # TODO: 实现API模式重新作答功能
                elif choice == "5":
                    print("\n🔙 退出")
                    break
                else:
                    print("\n❌ 无效的选择，请输入1-5之间的数字")

    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
    except Exception as e:
        print(f"❌ 跳转页面异常: {str(e)}")
        import traceback
        traceback.print_exc()
