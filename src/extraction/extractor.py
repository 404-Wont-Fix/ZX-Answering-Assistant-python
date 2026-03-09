"""
题目提取模块
用于从系统中提取题目数据
"""

from playwright.sync_api import sync_playwright
from typing import Optional, List, Dict
import time
import requests
import asyncio


class Extractor:
    """题目提取器"""
    
    def __init__(self):
        self.access_token = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
    def login(self, username: str = None, password: str = None) -> bool:
        """
        使用用户名和密码登录系统

        Args:
            username: 用户名，如果为None则尝试从配置读取或询问用户
            password: 密码，如果为None则尝试从配置读取或询问用户

        Returns:
            bool: 登录是否成功
        """
        try:
            print("正在启动浏览器进行登录...")

            # 尝试从配置文件读取凭据
            if username is None or password is None:
                try:
                    from src.core.config import get_settings_manager
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
                            if username is None:
                                username = input("请输入账号：").strip()
                            if password is None:
                                password = input("请输入密码：").strip()
                except Exception:
                    # 如果读取配置失败，继续手动输入
                    if username is None:
                        username = input("请输入账号：").strip()
                    if password is None:
                        password = input("请输入密码：").strip()

            # 检查是否有正在运行的asyncio事件循环
            try:
                loop = asyncio.get_running_loop()
                has_loop = True
            except RuntimeError:
                has_loop = False
            
            # 从配置文件读取无头模式设置
            try:
                from src.core.config import get_settings_manager
                settings = get_settings_manager()
                headless = settings.get_browser_headless()
                print(f"💡 从配置文件读取无头模式设置: headless={headless}")
            except Exception:
                headless = False  # 默认显示浏览器
                print("⚠️ 无法读取配置文件，使用默认设置（显示浏览器）")

            # 使用playwright启动浏览器
            self.playwright = sync_playwright().start()

            # Playwright 1.57.0+ 使用 chromium_headless_shell
            # 为了兼容打包的完整 Chromium，使用 args 参数替代 headless
            launch_args = {
                'headless': headless,
            }
            # 如果需要 headless 模式，使用 args 参数以确保使用完整 Chromium
            if headless:
                launch_args['args'] = ['--headless=new']

            self.browser = self.playwright.chromium.launch(**launch_args)
            
            # 创建浏览器上下文
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
            )
            
            # 创建页面
            self.page = self.context.new_page()
            
            # 打开登录页面
            login_url = "https://admin.cqzuxia.com/#/login?redirect=%2F"
            self.page.goto(login_url)
            
            # 等待页面加载完成
            self.page.wait_for_selector("input[placeholder='请输入账户']", timeout=10000)
            
            # 输入用户名
            self.page.fill("input[placeholder='请输入账户']", username)
            
            # 输入密码
            self.page.fill("input[placeholder='请输入密码']", password)
            
            # 点击登录按钮
            self.page.click("button:has-text('登录')")
            
            # 等待登录成功
            try:
                self.page.wait_for_url("**/", timeout=15000)
                
                # 等待页面加载完成，确保cookies已经设置
                time.sleep(2)
                
                # 获取所有cookies
                cookies = self.context.cookies()
                
                # 查找包含access_token的cookie
                for cookie in cookies:
                    if cookie["name"] == "smartedu.admin.token":
                        self.access_token = cookie["value"]
                        break
                
                if self.access_token:
                    print("✅ 登录成功！")
                    return True
                else:
                    print("❌ 登录成功，但未找到access_token cookie")
                    return False
            except Exception as e:
                print(f"❌ 登录过程中发生错误：{str(e)}")
                return False
                
        except Exception as e:
            print(f"❌ Playwright登录异常：{str(e)}")
            return False
    
    def get_class_list(self) -> Optional[List[Dict]]:
        """
        从GetClassByTeacherID API获取班级列表

        Returns:
            Optional[List[Dict]]: 班级列表，如果失败则返回None
        """
        if not self.access_token:
            print("❌ 未登录，无法获取班级列表")
            return None

        try:
            from src.core.api_client import get_api_client

            url = "https://admin.cqzuxia.com/evaluation/api/TeacherEvaluation/GetClassByTeacherID"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            print("\n" + "="*60)
            print("📡 发送网络请求")
            print("="*60)
            print(f"请求方法: GET")
            print(f"请求URL: {url}")
            print(f"请求头:")
            print(f"  - Authorization: Bearer {self.access_token[:20]}...")
            print(f"  - Content-Type: {headers['Content-Type']}")
            print("="*60)

            start_time = time.time()
            api_client = get_api_client()
            response = api_client.get(url, headers=headers)
            elapsed_time = time.time() - start_time

            if response is None:
                print(f"\n❌ 请求失败（已达最大重试次数）")
                print("="*60)
                return None

            print(f"\n📥 收到响应")
            print(f"状态码: {response.status_code}")
            print(f"响应时间: {elapsed_time:.2f}秒")
            print(f"响应头:")
            print(f"  - Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            print(f"  - Content-Length: {response.headers.get('Content-Length', 'N/A')} bytes")

            if response.status_code == 200:
                data = response.json()
                print(f"响应数据: {data}")
                if data.get("success"):
                    class_list = data.get("data", [])
                    print(f"\n✅ 成功获取 {len(class_list)} 个班级")
                    print("="*60)
                    return class_list
                else:
                    print(f"\n❌ API返回错误：{data.get('message', '未知错误')}")
                    print("="*60)
                    return None
            else:
                print(f"\n❌ 请求失败，状态码：{response.status_code}")
                print(f"响应内容：{response.text[:200]}")
                print("="*60)
                return None

        except Exception as e:
            print(f"\n❌ 获取班级列表异常：{str(e)}")
            print("="*60)
            return None
    
    def filter_by_grade(self, class_list: List[Dict], grade: str) -> List[Dict]:
        """
        根据年级筛选班级列表，并过滤掉重复的班级
        
        Args:
            class_list: 班级列表
            grade: 年级（如"2024"或"2025"）
            
        Returns:
            List[Dict]: 筛选后的班级列表
        """
        filtered = []
        seen_class_names = set()
        
        for cls in class_list:
            class_grade = cls.get("grade", "")
            class_name = cls.get("className", "")
            
            # 只选择指定年级的班级
            if class_grade == grade:
                # 如果班级名称已经出现过，跳过重复的班级
                if class_name in seen_class_names:
                    continue
                
                # 添加班级到过滤列表
                filtered.append(cls)
                seen_class_names.add(class_name)
        
        return filtered
    
    def select_grade(self, class_list: List[Dict]) -> Optional[str]:
        """
        让用户选择年级
        
        Args:
            class_list: 班级列表
            
        Returns:
            Optional[str]: 选择的年级，如果取消则返回None
        """
        # 提取所有年级
        grades = set()
        for cls in class_list:
            grade = cls.get("grade", "")
            if grade:
                grades.add(grade)
        
        if not grades:
            print("❌ 未找到可用的年级")
            return None
        
        grades = sorted(grades, reverse=True)
        
        print("\n请选择年级：")
        for i, grade in enumerate(grades, 1):
            # 统计该年级的班级数量
            count = len(self.filter_by_grade(class_list, grade))
            print(f"{i}. {grade}级 ({count}个班级)")
        print("0. 取消")
        
        while True:
            choice = input("请输入选项：").strip()
            if choice == "0":
                return None
            
            try:
                choice_int = int(choice)
                if 1 <= choice_int <= len(grades):
                    selected_grade = grades[choice_int - 1]
                    print(f"✅ 已选择：{selected_grade}级")
                    return selected_grade
                else:
                    print("❌ 无效的选项，请重新输入")
            except ValueError:
                print("❌ 请输入数字")
    
    def get_course_list(self, class_id: str, max_retries: Optional[int] = None) -> Optional[List[Dict]]:
        """
        从GetEvaluationSummaryByClassID API获取课程列表

        Args:
            class_id: 班级ID
            max_retries: 最大重试次数，如果不提供则从配置读取

        Returns:
            Optional[List[Dict]]: 课程列表，如果失败则返回None
        """
        if not self.access_token:
            print("❌ 未登录，无法获取课程列表")
            return None

        try:
            from src.core.api_client import get_api_client

            url = f"https://admin.cqzuxia.com/evaluation/api/TeacherEvaluation/GetEvaluationSummaryByClassID?classID={class_id}"
            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                "authorization": f"Bearer {self.access_token}",
                "cache-control": "max-age=0",
                "dnt": "1",
                "if-modified-since": "0",
                "priority": "u=1, i",
                "referer": "https://admin.cqzuxia.com/",
                "sec-ch-ua": '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "sec-gpc": "1",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
            }

            print("\n" + "="*60)
            print("📡 发送网络请求")
            print("="*60)
            print(f"请求方法: GET")
            print(f"请求URL: {url}")
            print(f"请求头:")
            print(f"  - Authorization: Bearer {self.access_token[:20]}...")
            print(f"  - accept: {headers['accept']}")
            print(f"  - referer: {headers['referer']}")
            print("="*60)

            start_time = time.time()
            api_client = get_api_client()
            response = api_client.get(url, headers=headers, max_retries=max_retries)
            elapsed_time = time.time() - start_time

            if response is None:
                print(f"\n❌ 请求失败（已达最大重试次数）")
                print("="*60)
                return None

            print(f"\n📥 收到响应")
            print(f"状态码: {response.status_code}")
            print(f"响应时间: {elapsed_time:.2f}秒")
            print(f"响应头:")
            print(f"  - Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            print(f"  - Content-Length: {response.headers.get('Content-Length', 'N/A')} bytes")

            if response.status_code == 200:
                data = response.json()
                print(f"响应数据: {data}")
                if data.get("success"):
                    course_list = data.get("data", [])
                    print(f"\n✅ 成功获取 {len(course_list)} 门课程")
                    print("="*60)
                    return course_list
                else:
                    print(f"\n❌ API返回错误：{data.get('message', '未知错误')}")
                    print("="*60)
                    return None
            else:
                print(f"\n❌ 请求失败，状态码：{response.status_code}")
                print(f"响应内容：{response.text[:200]}")
                print("="*60)
                return None

        except Exception as e:
            print(f"❌ 获取课程列表异常：{str(e)}")
            return None

    def get_chapter_list(self, class_id: str, max_retries: Optional[int] = None) -> Optional[List[Dict]]:
        """
        从GetChapterEvaluationByClassID API获取章节列表

        Args:
            class_id: 班级ID
            max_retries: 最大重试次数，如果不提供则从配置读取

        Returns:
            Optional[List[Dict]]: 章节列表，如果失败则返回None
        """
        if not self.access_token:
            print("❌ 未登录，无法获取章节列表")
            return None

        try:
            from src.core.api_client import get_api_client

            url = f"https://admin.cqzuxia.com/evaluation/api/TeacherEvaluation/GetChapterEvaluationByClassID?classID={class_id}"
            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                "authorization": f"Bearer {self.access_token}",
                "cache-control": "max-age=0",
                "dnt": "1",
                "if-modified-since": "0",
                "priority": "u=1, i",
                "referer": "https://admin.cqzuxia.com/",
                "sec-ch-ua": '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "sec-gpc": "1",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
            }

            print("\n" + "="*60)
            print("📡 发送网络请求")
            print("="*60)
            print(f"请求方法: GET")
            print(f"请求URL: {url}")
            print(f"请求头:")
            print(f"  - Authorization: Bearer {self.access_token[:20]}...")
            print(f"  - accept: {headers['accept']}")
            print(f"  - referer: {headers['referer']}")
            print("="*60)

            start_time = time.time()
            api_client = get_api_client()
            response = api_client.get(url, headers=headers, max_retries=max_retries)
            elapsed_time = time.time() - start_time

            if response is None:
                print(f"\n❌ 请求失败（已达最大重试次数）")
                print("="*60)
                return None

            print(f"\n📥 收到响应")
            print(f"状态码: {response.status_code}")
            print(f"响应时间: {elapsed_time:.2f}秒")
            print(f"响应头:")
            print(f"  - Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            print(f"  - Content-Length: {response.headers.get('Content-Length', 'N/A')} bytes")

            if response.status_code == 200:
                data = response.json()
                print(f"响应数据: {data}")
                if data.get("code") == 0:
                    chapter_list = data.get("data", [])
                    print(f"\n✅ 成功获取 {len(chapter_list)} 个章节")
                    print("="*60)
                    return chapter_list
                else:
                    print(f"\n❌ API返回错误：{data.get('msg', '未知错误')}")
                    print("="*60)
                    return None
            else:
                print(f"\n❌ 请求失败，状态码：{response.status_code}")
                print(f"响应内容：{response.text[:200]}")
                print("="*60)
                return None

        except Exception as e:
            print(f"❌ 获取章节列表异常：{str(e)}")
            return None

    def get_knowledge_list(self, class_id: str, max_retries: Optional[int] = None) -> Optional[List[Dict]]:
        """
        从GetEvaluationKnowledgeSummaryByClass API获取知识点列表

        Args:
            class_id: 班级ID
            max_retries: 最大重试次数，如果不提供则从配置读取

        Returns:
            Optional[List[Dict]]: 知识点列表，如果失败则返回None
        """
        if not self.access_token:
            print("❌ 未登录，无法获取知识点列表")
            return None

        try:
            from src.core.api_client import get_api_client

            url = f"https://admin.cqzuxia.com/evaluation/api/TeacherEvaluation/GetEvaluationKnowledgeSummaryByClass?classID={class_id}"
            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                "authorization": f"Bearer {self.access_token}",
                "cache-control": "max-age=0",
                "dnt": "1",
                "if-modified-since": "0",
                "priority": "u=1, i",
                "referer": "https://admin.cqzuxia.com/",
                "sec-ch-ua": '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "sec-gpc": "1",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
            }

            print("\n" + "="*60)
            print("📡 发送网络请求")
            print("="*60)
            print(f"请求方法: GET")
            print(f"请求URL: {url}")
            print(f"请求头:")
            print(f"  - Authorization: Bearer {self.access_token[:20]}...")
            print(f"  - accept: {headers['accept']}")
            print(f"  - referer: {headers['referer']}")
            print("="*60)

            start_time = time.time()
            api_client = get_api_client()
            response = api_client.get(url, headers=headers, max_retries=max_retries)
            elapsed_time = time.time() - start_time

            if response is None:
                print(f"\n❌ 请求失败（已达最大重试次数）")
                print("="*60)
                return None

            print(f"\n📥 收到响应")
            print(f"状态码: {response.status_code}")
            print(f"响应时间: {elapsed_time:.2f}秒")
            print(f"响应头:")
            print(f"  - Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            print(f"  - Content-Length: {response.headers.get('Content-Length', 'N/A')} bytes")

            if response.status_code == 200:
                data = response.json()
                print(f"响应数据: {data}")
                if data.get("code") == 0:
                    knowledge_list = data.get("data", [])
                    print(f"\n✅ 成功获取 {len(knowledge_list)} 个知识点")
                    print("="*60)
                    return knowledge_list
                else:
                    print(f"\n❌ API返回错误：{data.get('msg', '未知错误')}")
                    print("="*60)
                    return None
            else:
                print(f"\n❌ 请求失败，状态码：{response.status_code}")
                print(f"响应内容：{response.text[:200]}")
                print("="*60)
                return None

        except Exception as e:
            print(f"❌ 获取知识点列表异常：{str(e)}")
            return None

    def get_question_list(self, class_id: str, knowledge_id: str, max_retries: Optional[int] = None) -> Optional[List[Dict]]:
        """
        从GetKnowQuestionEvaluation API获取知识点题目列表

        Args:
            class_id: 班级ID
            knowledge_id: 知识点ID
            max_retries: 最大重试次数，如果不提供则从配置读取

        Returns:
            Optional[List[Dict]]: 题目列表，如果失败则返回None
        """
        if not self.access_token:
            print("❌ 未登录，无法获取题目列表")
            return None

        try:
            from src.core.api_client import get_api_client

            url = f"https://admin.cqzuxia.com/evaluation/api/TeacherEvaluation/GetKnowQuestionEvaluation?classID={class_id}&knowledgeID={knowledge_id}"
            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                "authorization": f"Bearer {self.access_token}",
                "cache-control": "max-age=0",
                "dnt": "1",
                "if-modified-since": "0",
                "priority": "u=1, i",
                "referer": "https://admin.cqzuxia.com/",
                "sec-ch-ua": '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "sec-gpc": "1",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
            }

            print("\n" + "="*60)
            print("📡 发送网络请求")
            print("="*60)
            print(f"请求方法: GET")
            print(f"请求URL: {url}")
            print(f"请求头:")
            print(f"  - Authorization: Bearer {self.access_token[:20]}...")
            print(f"  - accept: {headers['accept']}")
            print(f"  - referer: {headers['referer']}")
            print("="*60)

            start_time = time.time()
            api_client = get_api_client()
            response = api_client.get(url, headers=headers, max_retries=max_retries)
            elapsed_time = time.time() - start_time

            if response is None:
                print(f"\n❌ 请求失败（已达最大重试次数）")
                print("="*60)
                return None

            print(f"\n📥 收到响应")
            print(f"状态码: {response.status_code}")
            print(f"响应时间: {elapsed_time:.2f}秒")
            print(f"响应头:")
            print(f"  - Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            print(f"  - Content-Length: {response.headers.get('Content-Length', 'N/A')} bytes")

            if response.status_code == 200:
                data = response.json()
                print(f"响应数据: {data}")
                if data.get("code") == 0:
                    question_list = data.get("data", [])
                    print(f"\n✅ 成功获取 {len(question_list)} 道题目")
                    print("="*60)
                    return question_list
                else:
                    print(f"\n❌ API返回错误：{data.get('msg', '未知错误')}")
                    print("="*60)
                    return None
            else:
                print(f"\n❌ 请求失败，状态码：{response.status_code}")
                print(f"响应内容：{response.text[:200]}")
                print("="*60)
                return None

        except Exception as e:
            print(f"❌ 获取题目列表异常：{str(e)}")
            return None

    def get_question_options(self, class_id: str, question_id: str, max_retries: Optional[int] = None) -> Optional[List[Dict]]:
        """
        从GetQuestionAnswerListByQID API获取题目选项列表

        Args:
            class_id: 班级ID
            question_id: 题目ID
            max_retries: 最大重试次数，如果不提供则从配置读取

        Returns:
            Optional[List[Dict]]: 选项列表，如果失败则返回None
        """
        if not self.access_token:
            print("❌ 未登录，无法获取题目选项")
            return None

        try:
            from src.core.api_client import get_api_client

            url = f"https://admin.cqzuxia.com/evaluation/api/TeacherEvaluation/GetQuestionAnswerListByQID?classID={class_id}&questionID={question_id}"
            headers = {
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                "authorization": f"Bearer {self.access_token}",
                "cache-control": "max-age=0",
                "dnt": "1",
                "if-modified-since": "0",
                "priority": "u=1, i",
                "referer": "https://admin.cqzuxia.com/",
                "sec-ch-ua": '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "sec-gpc": "1",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
            }

            print("\n" + "="*60)
            print("📡 发送网络请求")
            print("="*60)
            print(f"请求方法: GET")
            print(f"请求URL: {url}")
            print(f"请求头:")
            print(f"  - Authorization: Bearer {self.access_token[:20]}...")
            print(f"  - accept: {headers['accept']}")
            print(f"  - referer: {headers['referer']}")
            print("="*60)

            start_time = time.time()
            api_client = get_api_client()
            response = api_client.get(url, headers=headers, max_retries=max_retries)
            elapsed_time = time.time() - start_time

            if response is None:
                print(f"\n❌ 请求失败（已达最大重试次数）")
                print("="*60)
                return None

            print(f"\n📥 收到响应")
            print(f"状态码: {response.status_code}")
            print(f"响应时间: {elapsed_time:.2f}秒")
            print(f"响应头:")
            print(f"  - Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            print(f"  - Content-Length: {response.headers.get('Content-Length', 'N/A')} bytes")

            if response.status_code == 200:
                data = response.json()
                print(f"响应数据: {data}")
                if data.get("code") == 0:
                    options_list = data.get("data", [])
                    # 移除testQuestions字段，只保留选项信息
                    cleaned_options = []
                    for option in options_list:
                        cleaned_option = {
                            "id": option.get("id", ""),
                            "questionsID": option.get("questionsID", ""),
                            "oppentionContent": option.get("oppentionContent", ""),
                            "isTrue": option.get("isTrue", False),
                            "oppentionOrder": option.get("oppentionOrder", 0),
                            "tenantID": option.get("tenantID", 32)
                        }
                        cleaned_options.append(cleaned_option)
                    print(f"\n✅ 成功获取 {len(cleaned_options)} 个选项")
                    print("="*60)
                    return cleaned_options
                else:
                    print(f"\n❌ API返回错误：{data.get('msg', '未知错误')}")
                    print("="*60)
                    return None
            else:
                print(f"\n❌ 请求失败，状态码：{response.status_code}")
                print(f"响应内容：{response.text[:200]}")
                print("="*60)
                return None

        except Exception as e:
            print(f"❌ 获取题目选项异常：{str(e)}")
            return None

    def select_class(self, class_list: List[Dict]) -> Optional[Dict]:
        """
        让用户选择班级
        
        Args:
            class_list: 班级列表
            
        Returns:
            Optional[Dict]: 选择的班级信息，如果取消则返回None
        """
        if not class_list:
            print("❌ 没有可用的班级")
            return None
        
        print("\n请选择班级：")
        for i, cls in enumerate(class_list, 1):
            class_name = cls.get("className", "")
            class_id = cls.get("id", "")
            stats = cls.get("stats", 0)
            print(f"{i}. {class_name} (ClassID: {class_id})")
        print("0. 取消")
        
        while True:
            choice = input("请输入选项：").strip()
            if choice == "0":
                return None
            
            try:
                choice_int = int(choice)
                if 1 <= choice_int <= len(class_list):
                    selected_class = class_list[choice_int - 1]
                    print(f"✅ 已选择：{selected_class.get('className', '')}")
                    return selected_class
                else:
                    print("❌ 无效的选项，请重新输入")
            except ValueError:
                print("❌ 请输入数字")
    
    def extract(self) -> Optional[Dict]:
        """
        执行题目提取流程

        Returns:
            Optional[Dict]: 包含所有提取数据的字典，如果失败则返回None
        """
        # 1. 询问用户账号密码（如果不提供，login方法会尝试从配置读取）
        print("\n" + "="*50)
        print("题目提取功能")
        print("="*50)

        # 2. 登录（不传参数，让login方法自动处理）
        if not self.login():
            return None
        
        # 3. 获取班级列表
        class_list = self.get_class_list()
        if not class_list:
            return None
        
        # 4. 选择年级
        selected_grade = self.select_grade(class_list)
        if not selected_grade:
            print("❌ 已取消选择")
            return None
        
        # 5. 根据年级筛选班级
        filtered_classes = self.filter_by_grade(class_list, selected_grade)
        if not filtered_classes:
            print(f"❌ 未找到{selected_grade}级的班级")
            return None
        
        # 6. 选择班级
        selected_class = self.select_class(filtered_classes)
        if not selected_class:
            print("❌ 已取消选择")
            return None
        
        # 7. 获取班级ID
        class_id = selected_class.get("id", "")
        class_name = selected_class.get("className", "")
        
        # 8. 获取课程列表
        course_list = self.get_course_list(class_id)
        if not course_list:
            return None
        
        # 9. 获取章节列表
        chapter_list = self.get_chapter_list(class_id)
        if not chapter_list:
            return None
        
        # 10. 获取知识点列表
        knowledge_list = self.get_knowledge_list(class_id)
        if not knowledge_list:
            return None
        
        # 11. 按课程分组章节
        course_chapters = {}
        for chapter in chapter_list:
            course_id = chapter.get("courseID", "")
            if course_id not in course_chapters:
                course_chapters[course_id] = []
            course_chapters[course_id].append(chapter)
        
        # 12. 按章节分组知识点
        chapter_knowledges = {}
        for knowledge in knowledge_list:
            chapter_id = knowledge.get("ChapterID", "")
            if chapter_id not in chapter_knowledges:
                chapter_knowledges[chapter_id] = []
            chapter_knowledges[chapter_id].append(knowledge)
        
        # 13. 获取每个知识点的题目列表
        knowledge_questions = {}
        question_options = {}
        for knowledge in knowledge_list:
            knowledge_id = knowledge.get("KnowledgeID", "")
            print(f"\n正在获取知识点 {knowledge.get('Knowledge', '')} 的题目列表...")
            question_list = self.get_question_list(class_id, knowledge_id)
            if question_list:
                knowledge_questions[knowledge_id] = question_list

                # 获取每个题目的选项
                for question in question_list:
                    question_id = question.get("QuestionID", "")
                    print(f"正在获取题目 {question.get('QuestionTitle', '')} 的选项...")
                    options_list = self.get_question_options(class_id, question_id)
                    if options_list:
                        question_options[question_id] = options_list
                    else:
                        print(f"⚠️ 题目 {question.get('QuestionTitle', '')} 获取选项失败")
            else:
                print(f"⚠️ 知识点 {knowledge.get('Knowledge', '')} 获取题目列表失败")
        
        # 14. 打印班级和课程信息
        print("\n" + "="*50)
        print("✅ 题目提取完成")
        print("="*50)
        print(f"班级名称：{class_name}")
        print(f"班级ID (ClassID)：{class_id}")
        print(f"\n课程及章节列表：")
        
        for i, course in enumerate(course_list, 1):
            course_id = course.get("courseID", "")
            course_name = course.get("courseName", "未知课程")
            print(f"\n{i}. {course_name} (courseID: {course_id})")
            print(f"   知识点总数: {course.get('knowledgeSum', 0)}, 已完成: {course.get('shulian', 0)}")
            
            # 显示该课程的章节
            if course_id in course_chapters:
                chapters = course_chapters[course_id]
                print(f"   章节数量: {len(chapters)}")
                for j, chapter in enumerate(chapters, 1):
                    chapter_id = chapter.get("chapterID", "")
                    chapter_title = chapter.get("chapterTitle", "")
                    chapter_content = chapter.get("chapterContent", "")
                    knowledge_count = chapter.get("knowledgeCount", 0)
                    complet_count = chapter.get("completCount", 0)
                    pass_count = chapter.get("passCount", 0)
                    
                    print(f"   [{j}] {chapter_title} - {chapter_content} (ChapterID: {chapter_id})")
                    print(f"       知识点: {knowledge_count}, 完成: {complet_count}, 通过: {pass_count}")
                    
                    # 显示该章节的知识点
                    if chapter_id in chapter_knowledges:
                        knowledges = chapter_knowledges[chapter_id]
                        print(f"       知识点列表:")
                        for k, knowledge in enumerate(knowledges, 1):
                            knowledge_id = knowledge.get("KnowledgeID", "")
                            knowledge_name = knowledge.get("Knowledge", "")
                            order_number = knowledge.get("OrderNumber", 0)
                            k_complet_count = knowledge.get("completCount", 0)
                            k_pass_count = knowledge.get("passCount", 0)
                            
                            print(f"       [{k}] {knowledge_name} (KnowledgeID: {knowledge_id}, 顺序: {order_number}, 完成: {k_complet_count}, 通过: {k_pass_count})")
                            
                            # 显示该知识点的题目
                            if knowledge_id in knowledge_questions:
                                questions = knowledge_questions[knowledge_id]
                                print(f"           题目列表:")
                                for m, question in enumerate(questions, 1):
                                    question_id = question.get("QuestionID", "")
                                    question_title = question.get("QuestionTitle", "")
                                    sum_count = question.get("sumCount", 0)
                                    pass_count = question.get("PassCount", 0)
                                    
                                    print(f"           [{m}] {question_title} (QuestionID: {question_id}, 总数: {sum_count}, 通过: {pass_count})")
                                    
                                    # 显示该题目的选项
                                    if question_id in question_options:
                                        options = question_options[question_id]
                                        print(f"               选项列表:")
                                        for n, option in enumerate(options, 1):
                                            option_id = option.get("id", "")
                                            option_content = option.get("oppentionContent", "")
                                            is_true = option.get("isTrue", False)
                                            option_order = option.get("oppentionOrder", 0)
                                            
                                            # 标记正确答案
                                            correct_mark = "✅" if is_true else "❌"
                                            print(f"               [{n}] {option_content} (选项ID: {option_id}, 顺序: {option_order}) {correct_mark}")
                                    else:
                                        print(f"               暂无选项信息")
                            else:
                                print(f"           暂无题目信息")
                    else:
                        print("       暂无知识点信息")
            else:
                print("   暂无章节信息")
        
        print("="*50)
        
        # 返回完整的数据结构
        return {
            "class_info": selected_class,
            "course_list": course_list,
            "chapters": chapter_list,
            "knowledges": knowledge_list,
            "questions": knowledge_questions,
            "options": question_options
        }
    
    def select_course(self, course_list: List[Dict]) -> Optional[Dict]:
        """
        让用户选择课程
        
        Args:
            course_list: 课程列表
            
        Returns:
            Optional[Dict]: 选择的课程信息，如果取消则返回None
        """
        if not course_list:
            print("❌ 没有可用的课程")
            return None
        
        print("\n请选择课程：")
        for i, course in enumerate(course_list, 1):
            course_name = course.get("courseName", "")
            course_id = course.get("courseID", "")
            knowledge_sum = course.get("knowledgeSum", 0)
            shulian = course.get("shulian", 0)
            print(f"{i}. {course_name} (courseID: {course_id}, 知识点: {knowledge_sum}, 已完成: {shulian})")
        print("0. 取消")
        
        while True:
            choice = input("请输入选项：").strip()
            if choice == "0":
                return None
            
            try:
                choice_int = int(choice)
                if 1 <= choice_int <= len(course_list):
                    selected_course = course_list[choice_int - 1]
                    print(f"✅ 已选择：{selected_course.get('courseName', '')}")
                    return selected_course
                else:
                    print("❌ 无效的选项，请重新输入")
            except ValueError:
                print("❌ 请输入数字")
    
    def extract_single_course(self) -> Optional[Dict]:
        """
        执行单个课程题目提取流程

        Returns:
            Optional[Dict]: 包含所有提取数据的字典，如果失败则返回None
        """
        # 1. 询问用户账号密码（如果不提供，login方法会尝试从配置读取）
        print("\n" + "="*50)
        print("单个课程题目提取功能")
        print("="*50)

        # 2. 登录（不传参数，让login方法自动处理）
        if not self.login():
            return None
        
        # 3. 获取班级列表
        class_list = self.get_class_list()
        if not class_list:
            return None
        
        # 4. 选择年级
        selected_grade = self.select_grade(class_list)
        if not selected_grade:
            print("❌ 已取消选择")
            return None
        
        # 5. 根据年级筛选班级
        filtered_classes = self.filter_by_grade(class_list, selected_grade)
        if not filtered_classes:
            print(f"❌ 未找到{selected_grade}级的班级")
            return None
        
        # 6. 选择班级
        selected_class = self.select_class(filtered_classes)
        if not selected_class:
            print("❌ 已取消选择")
            return None
        
        # 7. 获取班级ID
        class_id = selected_class.get("id", "")
        class_name = selected_class.get("className", "")
        
        # 8. 获取课程列表
        course_list = self.get_course_list(class_id)
        if not course_list:
            return None
        
        # 9. 选择课程
        selected_course = self.select_course(course_list)
        if not selected_course:
            print("❌ 已取消选择")
            return None
        
        course_id = selected_course.get("courseID", "")
        course_name = selected_course.get("courseName", "")
        
        # 10. 获取章节列表
        chapter_list = self.get_chapter_list(class_id)
        if not chapter_list:
            return None
        
        # 11. 获取知识点列表
        knowledge_list = self.get_knowledge_list(class_id)
        if not knowledge_list:
            return None
        
        # 12. 按课程分组章节
        course_chapters = {}
        for chapter in chapter_list:
            chapter_course_id = chapter.get("courseID", "")
            if chapter_course_id not in course_chapters:
                course_chapters[chapter_course_id] = []
            course_chapters[chapter_course_id].append(chapter)
        
        # 13. 按章节分组知识点
        chapter_knowledges = {}
        for knowledge in knowledge_list:
            chapter_id = knowledge.get("ChapterID", "")
            if chapter_id not in chapter_knowledges:
                chapter_knowledges[chapter_id] = []
            chapter_knowledges[chapter_id].append(knowledge)
        
        # 14. 只获取选中课程的题目列表
        knowledge_questions = {}
        question_options = {}
        
        # 筛选出选中课程的章节
        selected_course_chapters = course_chapters.get(course_id, [])
        selected_chapter_ids = {chapter.get("chapterID", "") for chapter in selected_course_chapters}
        
        # 只处理选中课程的知识点
        for knowledge in knowledge_list:
            knowledge_id = knowledge.get("KnowledgeID", "")
            chapter_id = knowledge.get("ChapterID", "")
            
            # 只处理选中课程的章节下的知识点
            if chapter_id not in selected_chapter_ids:
                continue
            
            print(f"\n正在获取知识点 {knowledge.get('Knowledge', '')} 的题目列表...")
            question_list = self.get_question_list(class_id, knowledge_id)
            if question_list:
                knowledge_questions[knowledge_id] = question_list

                # 获取每个题目的选项
                for question in question_list:
                    question_id = question.get("QuestionID", "")
                    print(f"正在获取题目 {question.get('QuestionTitle', '')} 的选项...")
                    options_list = self.get_question_options(class_id, question_id)
                    if options_list:
                        question_options[question_id] = options_list
                    else:
                        print(f"⚠️ 题目 {question.get('QuestionTitle', '')} 获取选项失败")
            else:
                print(f"⚠️ 知识点 {knowledge.get('Knowledge', '')} 获取题目列表失败")

        # 15. 筛选出选中课程的章节和知识点
        selected_course_chapters = course_chapters.get(course_id, [])
        selected_chapter_ids = {chapter.get("chapterID", "") for chapter in selected_course_chapters}
        
        selected_course_knowledges = []
        for knowledge in knowledge_list:
            chapter_id = knowledge.get("ChapterID", "")
            if chapter_id in selected_chapter_ids:
                selected_course_knowledges.append(knowledge)
        
        # 16. 打印班级和课程信息
        print("\n" + "="*50)
        print("✅ 单个课程题目提取完成")
        print("="*50)
        print(f"班级名称：{class_name}")
        print(f"班级ID (ClassID)：{class_id}")
        print(f"\n课程信息：")
        print(f"{course_name} (courseID: {course_id})")
        print(f"知识点总数: {selected_course.get('knowledgeSum', 0)}, 已完成: {selected_course.get('shulian', 0)}")
        
        # 显示该课程的章节
        if course_id in course_chapters:
            chapters = course_chapters[course_id]
            print(f"\n章节数量: {len(chapters)}")
            for j, chapter in enumerate(chapters, 1):
                chapter_id = chapter.get("chapterID", "")
                chapter_title = chapter.get("chapterTitle", "")
                chapter_content = chapter.get("chapterContent", "")
                knowledge_count = chapter.get("knowledgeCount", 0)
                complet_count = chapter.get("completCount", 0)
                pass_count = chapter.get("passCount", 0)
                
                print(f"\n[{j}] {chapter_title} - {chapter_content} (ChapterID: {chapter_id})")
                print(f"    知识点: {knowledge_count}, 完成: {complet_count}, 通过: {pass_count}")
                
                # 显示该章节的知识点
                if chapter_id in chapter_knowledges:
                    knowledges = chapter_knowledges[chapter_id]
                    print(f"    知识点列表:")
                    for k, knowledge in enumerate(knowledges, 1):
                        knowledge_id = knowledge.get("KnowledgeID", "")
                        knowledge_name = knowledge.get("Knowledge", "")
                        order_number = knowledge.get("OrderNumber", 0)
                        k_complet_count = knowledge.get("completCount", 0)
                        k_pass_count = knowledge.get("passCount", 0)
                        
                        print(f"    [{k}] {knowledge_name} (KnowledgeID: {knowledge_id}, 顺序: {order_number}, 完成: {k_complet_count}, 通过: {k_pass_count})")
                        
                        # 显示该知识点的题目
                        if knowledge_id in knowledge_questions:
                            questions = knowledge_questions[knowledge_id]
                            print(f"        题目列表:")
                            for m, question in enumerate(questions, 1):
                                question_id = question.get("QuestionID", "")
                                question_title = question.get("QuestionTitle", "")
                                sum_count = question.get("sumCount", 0)
                                pass_count = question.get("PassCount", 0)
                                
                                print(f"        [{m}] {question_title} (QuestionID: {question_id}, 总数: {sum_count}, 通过: {pass_count})")
                                
                                # 显示该题目的选项
                                if question_id in question_options:
                                    options = question_options[question_id]
                                    print(f"            选项列表:")
                                    for n, option in enumerate(options, 1):
                                        option_id = option.get("id", "")
                                        option_content = option.get("oppentionContent", "")
                                        is_true = option.get("isTrue", False)
                                        option_order = option.get("oppentionOrder", 0)
                                        
                                        # 标记正确答案
                                        correct_mark = "✅" if is_true else "❌"
                                        print(f"            [{n}] {option_content} (选项ID: {option_id}, 顺序: {option_order}) {correct_mark}")
                                else:
                                    print(f"            暂无选项信息")
                        else:
                            print(f"        暂无题目信息")
                else:
                    print("    暂无知识点信息")
        else:
            print("暂无章节信息")
        
        print("="*50)
        
        # 返回完整的数据结构
        return {
            "class_info": selected_class,
            "course_info": selected_course,
            "chapters": selected_course_chapters,
            "knowledges": selected_course_knowledges,
            "questions": knowledge_questions,
            "options": question_options
        }
    
    def extract_course_with_progress(self, class_id: str, course_id: str, course_name: str,
                                     class_info: Dict, course_info: Dict,
                                     progress_callback=None) -> Optional[Dict]:
        """
        提取指定课程的答案（带进度回调）

        Args:
            class_id: 班级ID
            course_id: 课程ID
            course_name: 课程名称
            class_info: 班级信息字典
            course_info: 课程信息字典
            progress_callback: 进度回调函数，签名为 callback(message, current, total)

        Returns:
            Optional[Dict]: 包含所有提取数据的字典，如果失败则返回None
        """
        def log(msg, current=None, total=None):
            """内部日志辅助函数"""
            print(msg)
            if progress_callback:
                progress_callback(msg, current, total)

        try:
            # 获取章节列表
            log(f"📋 正在获取章节列表...")
            chapter_list = self.get_chapter_list(class_id)
            if not chapter_list:
                log("❌ 获取章节列表失败")
                return None

            # 获取知识点列表
            log(f"📚 正在获取知识点列表...")
            knowledge_list = self.get_knowledge_list(class_id)
            if not knowledge_list:
                log("❌ 获取知识点列表失败")
                return None

            # 按课程分组章节
            course_chapters = {}
            for chapter in chapter_list:
                chapter_course_id = chapter.get("courseID", "")
                if chapter_course_id not in course_chapters:
                    course_chapters[chapter_course_id] = []
                course_chapters[chapter_course_id].append(chapter)

            # 按章节分组知识点
            chapter_knowledges = {}
            for knowledge in knowledge_list:
                chapter_id = knowledge.get("ChapterID", "")
                if chapter_id not in chapter_knowledges:
                    chapter_knowledges[chapter_id] = []
                chapter_knowledges[chapter_id].append(knowledge)

            # 筛选出选中课程的章节
            selected_course_chapters = course_chapters.get(course_id, [])
            selected_chapter_ids = {chapter.get("chapterID", "") for chapter in selected_course_chapters}

            # 只处理选中课程的知识点
            selected_course_knowledges = []
            for knowledge in knowledge_list:
                chapter_id = knowledge.get("ChapterID", "")
                if chapter_id in selected_chapter_ids:
                    selected_course_knowledges.append(knowledge)

            # 获取题目和选项
            knowledge_questions = {}
            question_options = {}

            total_knowledges = len(selected_course_knowledges)
            log(f"📝 开始提取题目数据，共 {total_knowledges} 个知识点", 0, total_knowledges)

            for idx, knowledge in enumerate(selected_course_knowledges, 1):
                knowledge_id = knowledge.get("KnowledgeID", "")
                knowledge_name = knowledge.get("Knowledge", "")

                log(f"正在获取知识点 [{idx}/{total_knowledges}]: {knowledge_name}", idx, total_knowledges)

                question_list = self.get_question_list(class_id, knowledge_id)
                if question_list:
                    knowledge_questions[knowledge_id] = question_list

                    # 获取每个题目的选项
                    for question in question_list:
                        question_id = question.get("QuestionID", "")
                        question_title = question.get("QuestionTitle", "")
                        options_list = self.get_question_options(class_id, question_id)
                        if options_list:
                            question_options[question_id] = options_list
                else:
                    log(f"⚠️ 知识点 {knowledge_name} 获取题目列表失败", idx, total_knowledges)

            log(f"✅ 题目提取完成！", total_knowledges, total_knowledges)

            # 返回完整的数据结构
            return {
                "class_info": class_info,
                "course_info": course_info,
                "chapters": selected_course_chapters,
                "knowledges": selected_course_knowledges,
                "questions": knowledge_questions,
                "options": question_options
            }

        except Exception as e:
            log(f"❌ 提取过程发生错误：{str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def close(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
            self.browser = None
            self.context = None
            self.page = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
            print("浏览器已关闭")


def extract_questions() -> Optional[Dict]:
    """
    题目提取入口函数
    
    Returns:
        Optional[Dict]: 包含所有提取数据的字典，如果失败则返回None
    """
    extractor = Extractor()
    try:
        return extractor.extract()
    finally:
        extractor.close()


def extract_single_course() -> Optional[Dict]:
    """
    单个课程题目提取入口函数
    
    Returns:
        Optional[Dict]: 包含所有提取数据的字典，如果失败则返回None
    """
    extractor = Extractor()
    try:
        return extractor.extract_single_course()
    finally:
        extractor.close()


def extract_course_answers(course_id: str, username: str = None, password: str = None) -> Optional[Dict]:
    """
    直接提取指定课程的答案（使用教师端登录和班级选择逻辑）

    Args:
        course_id: 课程ID
        username: 教师账号（可选，如果不提供则从配置读取或询问）
        password: 教师密码（可选，如果不提供则从配置读取或询问）

    Returns:
        Optional[Dict]: 包含所有提取数据的字典，如果失败则返回None
    """
    extractor = Extractor()
    try:
        # 1. 登录（不传参数让login方法自动处理）
        if not extractor.login():
            return None
        
        # 2. 获取班级列表
        class_list = extractor.get_class_list()
        if not class_list:
            print("❌ 获取班级列表失败")
            return None
        
        # 3. 选择年级
        selected_grade = extractor.select_grade(class_list)
        if not selected_grade:
            print("❌ 未选择年级")
            return None
        
        # 4. 筛选该年级的班级
        filtered_classes = extractor.filter_by_grade(class_list, selected_grade)
        if not filtered_classes:
            print(f"❌ 未找到{selected_grade}级的班级")
            return None
        
        # 5. 选择班级
        selected_class = extractor.select_class(filtered_classes)
        if not selected_class:
            print("❌ 未选择班级")
            return None
        
        class_id = selected_class.get("id", "")
        print(f"✅ 已选择班级：{selected_class.get('name', '')}")
        
        # 6. 获取课程列表
        course_list = extractor.get_course_list(class_id)
        if not course_list:
            print("❌ 获取课程列表失败")
            return None
        
        # 7. 验证课程ID是否存在
        course_found = False
        for course in course_list:
            if course.get("courseID") == course_id:
                course_found = True
                print(f"✅ 找到课程：{course.get('courseName', '')}")
                break
        
        if not course_found:
            print(f"❌ 未找到课程ID: {course_id}")
            print("\n可用课程列表：")
            for course in course_list:
                print(f"  - {course.get('courseName', '')} (ID: {course.get('courseID', '')})")
            return None
        
        # 8. 获取章节列表
        chapter_list = extractor.get_chapter_list(class_id)
        if not chapter_list:
            return None
        
        # 9. 获取知识点列表
        knowledge_list = extractor.get_knowledge_list(class_id)
        if not knowledge_list:
            return None
        
        # 10. 按课程分组章节
        course_chapters = {}
        for chapter in chapter_list:
            chapter_course_id = chapter.get("courseID", "")
            if chapter_course_id not in course_chapters:
                course_chapters[chapter_course_id] = []
            course_chapters[chapter_course_id].append(chapter)
        
        # 11. 按章节分组知识点
        chapter_knowledges = {}
        for knowledge in knowledge_list:
            chapter_id = knowledge.get("ChapterID", "")
            if chapter_id not in chapter_knowledges:
                chapter_knowledges[chapter_id] = []
            chapter_knowledges[chapter_id].append(knowledge)
        
        # 12. 只获取指定课程的题目列表
        knowledge_questions = {}
        question_options = {}
        
        # 筛选出指定课程的章节
        selected_course_chapters = course_chapters.get(course_id, [])
        selected_chapter_ids = {chapter.get("chapterID", "") for chapter in selected_course_chapters}
        
        # 只处理指定课程的知识点
        for knowledge in knowledge_list:
            knowledge_id = knowledge.get("KnowledgeID", "")
            chapter_id = knowledge.get("ChapterID", "")
            
            # 只处理指定课程的章节下的知识点
            if chapter_id not in selected_chapter_ids:
                continue
            
            print(f"\n正在获取知识点 {knowledge.get('Knowledge', '')} 的题目列表...")
            question_list = extractor.get_question_list(class_id, knowledge_id)
            if question_list:
                knowledge_questions[knowledge_id] = question_list

                # 获取每个题目的选项
                for question in question_list:
                    question_id = question.get("QuestionID", "")
                    print(f"正在获取题目 {question.get('QuestionTitle', '')} 的选项...")
                    options_list = extractor.get_question_options(class_id, question_id)
                    if options_list:
                        question_options[question_id] = options_list
                    else:
                        print(f"⚠️ 题目 {question.get('QuestionTitle', '')} 获取选项失败")
            else:
                print(f"⚠️ 知识点 {knowledge.get('Knowledge', '')} 获取题目列表失败")

        # 13. 筛选出指定课程的章节和知识点
        selected_course_knowledges = []
        for knowledge in knowledge_list:
            chapter_id = knowledge.get("ChapterID", "")
            if chapter_id in selected_chapter_ids:
                selected_course_knowledges.append(knowledge)
        
        # 14. 打印提取信息
        print("\n" + "="*50)
        print("✅ 课程答案提取完成")
        print("="*50)
        print(f"课程ID: {course_id}")
        print(f"班级ID: {class_id}")
        print(f"班级名称: {selected_class.get('name', '')}")
        print(f"章节数量: {len(selected_course_chapters)}")
        print(f"知识点数量: {len(selected_course_knowledges)}")
        print(f"题目数量: {sum(len(questions) for questions in knowledge_questions.values())}")
        print("="*50)
        
        # 返回完整的数据结构
        return {
            "class_info": selected_class,
            "course_info": {"courseID": course_id},
            "chapters": selected_course_chapters,
            "knowledges": selected_course_knowledges,
            "questions": knowledge_questions,
            "options": question_options
        }
    finally:
        extractor.close()
