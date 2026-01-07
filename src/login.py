"""
登录功能模块
用于获取系统的access_token
"""

from playwright.sync_api import sync_playwright
from typing import Optional
import time


def get_access_token() -> Optional[str]:
    """
    使用Playwright模拟浏览器登录获取access_token
    
    Returns:
        Optional[str]: 获取到的access_token，如果失败则返回None
    """
    try:
        print("正在启动浏览器进行登录...")
        
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
                
                # 打开登录页面
                login_url = "https://admin.cqzuxia.com/#/login?redirect=%2F"
                page.goto(login_url)
                
                # 等待页面加载完成
                page.wait_for_selector("input[placeholder='请输入账户']", timeout=10000)
                
                # 输入用户名
                page.fill("input[placeholder='请输入账户']", "wx2022")
                
                # 输入密码
                page.fill("input[placeholder='请输入密码']", "123456")
                
                # 点击登录按钮
                page.click("button:has-text('登录')")
                
                # 等待登录成功（URL变化或页面元素出现）
                try:
                    # 等待登录成功，最多等待15秒
                    page.wait_for_url("**/", timeout=15000)
                    
                    # 等待页面加载完成，确保cookies已经设置
                    time.sleep(2)
                    
                    # 获取所有cookies
                    cookies = context.cookies()
                    
                    # 查找包含access_token的cookie
                    access_token = None
                    for cookie in cookies:
                        if cookie["name"] == "smartedu.admin.token":
                            access_token = cookie["value"]
                            break
                    
                    if access_token:
                        return access_token
                    else:
                        print("登录成功，但未找到access_token cookie")
                        return None
                except Exception as e:
                    print(f"登录过程中发生错误：{str(e)}")
                    return None
            finally:
                # 关闭浏览器
                browser.close()
    except Exception as e:
        print(f"Playwright登录异常：{str(e)}")
        return None
