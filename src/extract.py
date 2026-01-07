"""
题目提取模块
用于从系统中提取题目数据
"""

from playwright.sync_api import sync_playwright
from typing import Optional, List, Dict
import time
import requests


class Extractor:
    """题目提取器"""
    
    def __init__(self):
        self.access_token = None
        self.browser = None
        self.context = None
        self.page = None
        
    def login(self, username: str, password: str) -> bool:
        """
        使用用户名和密码登录系统
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            bool: 登录是否成功
        """
        try:
            print("正在启动浏览器进行登录...")
            
            # 使用playwright启动浏览器
            p = sync_playwright().start()
            self.browser = p.chromium.launch(headless=False)
            
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
            url = "https://admin.cqzuxia.com/evaluation/api/TeacherEvaluation/GetClassByTeacherID"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            print("正在获取班级列表...")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    class_list = data.get("data", [])
                    print(f"✅ 成功获取 {len(class_list)} 个班级")
                    return class_list
                else:
                    print(f"❌ API返回错误：{data.get('message', '未知错误')}")
                    return None
            else:
                print(f"❌ 请求失败，状态码：{response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ 获取班级列表异常：{str(e)}")
            return None
    
    def filter_by_grade(self, class_list: List[Dict], grade: str) -> List[Dict]:
        """
        根据年级筛选班级列表
        
        Args:
            class_list: 班级列表
            grade: 年级（如"2024"或"2025"）
            
        Returns:
            List[Dict]: 筛选后的班级列表
        """
        filtered = []
        for cls in class_list:
            class_grade = cls.get("grade", "")
            if class_grade == grade:
                filtered.append(cls)
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
            print(f"{i}. {class_name} (ID: {class_id})")
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
    
    def extract(self) -> Optional[str]:
        """
        执行题目提取流程
        
        Returns:
            Optional[str]: 最终选择的班级ID，如果失败则返回None
        """
        # 1. 询问用户账号密码
        print("\n" + "="*50)
        print("题目提取功能")
        print("="*50)
        
        username = input("请输入账号：").strip()
        if not username:
            print("❌ 账号不能为空")
            return None
        
        password = input("请输入密码：").strip()
        if not password:
            print("❌ 密码不能为空")
            return None
        
        # 2. 登录
        if not self.login(username, password):
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
        
        # 7. 打印班级ID
        class_id = selected_class.get("id", "")
        class_name = selected_class.get("className", "")
        
        print("\n" + "="*50)
        print("✅ 题目提取完成")
        print("="*50)
        print(f"班级名称：{class_name}")
        print(f"班级ID：{class_id}")
        print("="*50)
        
        return class_id
    
    def close(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
            self.browser = None
            self.context = None
            self.page = None
            print("浏览器已关闭")


def extract_questions() -> Optional[str]:
    """
    题目提取入口函数
    
    Returns:
        Optional[str]: 最终选择的班级ID，如果失败则返回None
    """
    extractor = Extractor()
    try:
        return extractor.extract()
    finally:
        extractor.close()
