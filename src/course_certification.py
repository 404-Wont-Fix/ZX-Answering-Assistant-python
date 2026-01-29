"""
课程认证模块

用于处理课程相关的认证功能
"""

from playwright.sync_api import sync_playwright
from typing import Optional
import time


def hello_world():
    """测试函数 - 打印 Hello World"""
    print("\n" + "=" * 50)
    print("🎉 Hello World!")
    print("=" * 50)
    print("✅ 课程认证模块运行成功！")
    print("=" * 50)


def get_access_token() -> Optional[str]:
    """
    使用Playwright模拟浏览器登录获取课程认证access_token

    Returns:
        Optional[str]: 获取到的access_token，如果失败则返回None
    """
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
                    # 获取用户输入的用户名和密码
                    username = input("请输入课程认证账户：").strip()
                    password = input("请输入课程认证密码：").strip()
            else:
                # 获取用户输入的用户名和密码
                username = input("请输入课程认证账户：").strip()
                password = input("请输入课程认证密码：").strip()
        except Exception:
            # 如果读取配置失败，继续手动输入
            username = input("请输入课程认证账户：").strip()
            password = input("请输入课程认证密码：").strip()

        if not username or not password:
            print("❌ 用户名或密码不能为空")
            return None

        # 使用playwright启动浏览器
        with sync_playwright() as p:
            # 启动浏览器（显示浏览器窗口）
            browser = p.chromium.launch(headless=False)

            try:
                # 创建浏览器上下文
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0"
                )

                # 创建页面
                page = context.new_page()

                # 用于存储捕获的 access_token
                captured_data = None

                # 设置网络请求监听器（在打开页面之前就设置）
                def handle_response(response):
                    nonlocal captured_data
                    if 'token' in response.url:
                        print(f"🔍 捕获到 token 响应")
                        try:
                            # 立即解析并保存
                            data = response.json()
                            captured_data = data
                            print(f"✅ 成功捕获响应数据")
                        except Exception as e:
                            print(f"解析失败: {e}")

                page.on('response', handle_response)

                # 打开课程认证登录页面
                login_url = "https://zxsz.cqzuxia.com/#/login/index"
                print(f"正在打开登录页面: {login_url}")
                page.goto(login_url)

                # 等待页面加载完成
                print("等待登录表单加载...")
                page.wait_for_selector("input[placeholder='登录账号']", timeout=10000)

                # 输入用户名
                print(f"正在填写账户: {username}")
                page.fill("input[placeholder='登录账号']", username)

                # 输入密码
                print("正在填写密码")
                page.fill("input[placeholder='登录密码']", password)

                # 点击登录按钮
                print("正在点击登录按钮...")
                page.click(".lic-clf-loginbut")

                # 等待页面跳转到 home（这意味着登录成功，请求已完成）
                print("等待登录成功...")
                try:
                    page.wait_for_url("**/home", timeout=15000)
                    print("✅ 页面已跳转到 home，登录成功")

                    # 等待一下确保响应处理器完全处理完毕
                    time.sleep(1)
                except Exception as e:
                    print(f"⚠️ 等待页面跳转超时: {e}")
                    print("继续检查是否捕获到 token...")

                # 处理捕获的数据
                if captured_data and 'access_token' in captured_data:
                    access_token = captured_data['access_token']
                    print("\n" + "=" * 50)
                    print("✅ 登录成功！")
                    print("=" * 50)
                    print(f"access_token: {access_token}")
                    print(f"token类型: Bearer")
                    print(f"有效期: 5小时 (18000秒)")
                    print("=" * 50)
                    return access_token
                else:
                    print("❌ 未能在响应中捕获到 access_token")
                    if captured_data:
                        print(f"响应内容: {captured_data}")
                    return None

            finally:
                # 等待一下让用户看到结果
                time.sleep(2)
                # 关闭浏览器
                browser.close()

    except Exception as e:
        print(f"❌ Playwright登录异常：{str(e)}")
        import traceback
        traceback.print_exc()
        return None
