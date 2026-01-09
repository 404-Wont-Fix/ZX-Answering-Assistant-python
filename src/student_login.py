"""
学生端登录功能模块
用于获取学生端系统的access_token
"""

from playwright.sync_api import sync_playwright
from typing import Optional, List, Dict
import time
import json
import logging
import requests

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('student_login.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def get_student_access_token(username: str = None, password: str = None) -> Optional[str]:
    """
    使用Playwright模拟浏览器登录获取学生端access_token

    Args:
        username: 学生账户，如果为None则询问用户输入
        password: 学生密码，如果为None则询问用户输入

    Returns:
        Optional[str]: 获取到的access_token，如果失败则返回None
    """
    try:
        # 如果没有提供用户名和密码，则询问用户
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
        
        # 使用playwright启动浏览器
        with sync_playwright() as p:
            # 启动浏览器（显示浏览器窗口）
            browser = p.chromium.launch(headless=False)
            
            try:
                # 创建浏览器上下文
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
                )
                
                # 创建页面
                page = context.new_page()
                
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
                        # 等待一下确保完全获取到token
                        time.sleep(0.5)
                        return access_token
                    else:
                        # 检查是否登录成功
                        current_url = page.url
                        logger.info(f"当前页面URL: {current_url}")
                        if "home" in current_url or "home-2024" in current_url:
                            logger.warning("⚠️ 登录成功但未捕获到access_token")
                            return None
                        else:
                            logger.error("❌ 登录失败，未跳转到主页")
                            return None
                except Exception as e:
                    logger.error(f"登录过程中发生错误：{str(e)}")
                    return None
            finally:
                # 关闭浏览器
                browser.close()
                logger.info("浏览器已关闭")
    except Exception as e:
        logger.error(f"Playwright登录异常：{str(e)}")
        return None


def get_student_access_token_with_credentials() -> Optional[str]:
    """
    获取学生端access_token，使用用户输入的凭据

    Returns:
        Optional[str]: 获取到的access_token，如果失败则返回None
    """
    # 获取用户输入的用户名和密码
    username = input("请输入学生账户（直接回车使用默认账户）: ").strip()
    password = input("请输入学生密码（直接回车使用默认密码）: ").strip()

    # 如果用户没有输入，则使用默认账户
    if not username:
        username = None
    if not password:
        password = None

    return get_student_access_token(username, password)


def get_uncompleted_chapters(access_token: str, course_id: str) -> Optional[List[Dict]]:
    """
    使用access_token和课程ID获取未完成的知识点列表

    Args:
        access_token: 学生端的access_token
        course_id: 课程ID

    Returns:
        Optional[List[Dict]]: 未完成的知识点列表，如果失败则返回None
    """
    try:
        logger.info(f"正在获取课程 {course_id} 的未完成知识点列表...")

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

        logger.info(f"发送请求到: {url}")

        # 发送GET请求
        response = requests.get(url, headers=headers, timeout=30)

        # 检查响应状态
        if response.status_code == 200:
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

                # 打印知识点信息到屏幕
                if not all_knowledges:
                    print("✅ 没有未完成的知识点")
                else:
                    print(f"📝 未完成知识点: {len(all_knowledges)} 个\n")

                    current_chapter = None
                    for i, knowledge in enumerate(all_knowledges, 1):
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

                return all_knowledges

            except json.JSONDecodeError as e:
                logger.error(f"解析JSON响应失败: {str(e)}")
                logger.error(f"响应内容: {response.text[:500]}")
                return None
        else:
            logger.error(f"❌ 请求失败，状态码: {response.status_code}")
            logger.error(f"响应内容: {response.text[:500]}")
            return None

    except requests.exceptions.Timeout:
        logger.error("❌ 请求超时，请检查网络连接")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ 连接错误: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ 获取未完成知识点列表异常: {str(e)}")
        return None


def get_student_courses(access_token: str) -> Optional[List[Dict]]:
    """
    使用access_token获取学生端课程列表

    Args:
        access_token: 学生端的access_token

    Returns:
        Optional[List[Dict]]: 课程列表，如果失败则返回None
    """
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

        # 发送GET请求
        response = requests.get(url, headers=headers, timeout=30)

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

                # 打印课程信息到屏幕
                if not courses:
                    print("❌ 未找到任何课程")
                else:
                    print(f"📚 课程列表 (共 {len(courses)} 门):\n")

                    for i, course in enumerate(courses, 1):
                        course_name = course.get('courseName', 'N/A')
                        class_name = course.get('className', 'N/A')
                        teacher_name = course.get('teacherName', 'N/A')
                        print(f"{i}. 【{course_name}】({class_name}) - {teacher_name}")

                return courses

            except json.JSONDecodeError as e:
                logger.error(f"解析JSON响应失败: {str(e)}")
                logger.error(f"响应内容: {response.text[:500]}")
                return None
        else:
            logger.error(f"❌ 请求失败，状态码: {response.status_code}")
            logger.error(f"响应内容: {response.text[:500]}")
            return None

    except requests.exceptions.Timeout:
        logger.error("❌ 请求超时，请检查网络连接")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ 连接错误: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌ 获取课程列表异常: {str(e)}")
        return None