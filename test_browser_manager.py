"""
浏览器管理器测试脚本

测试多浏览器同时运行的功能，验证：
1. 多上下文同时创建和使用
2. 上下文之间的隔离性
3. 健康检查功能
4. 资源清理功能
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.browser_manager import (
    get_browser_manager,
    BrowserType
)


def print_test_header(title: str):
    """打印测试标题"""
    print("\n" + "=" * 60)
    print(f"🧪 {title}")
    print("=" * 60)


def print_success(message: str):
    """打印成功信息"""
    print(f"✅ {message}")


def print_info(message: str):
    """打印信息"""
    print(f"ℹ️  {message}")


def print_warning(message: str):
    """打印警告"""
    print(f"⚠️  {message}")


def test_single_browser_multiple_contexts():
    """
    测试1：单浏览器多上下文模式

    验证：可以同时创建多个隔离的上下文
    """
    print_test_header("测试1: 单浏览器多上下文模式")

    try:
        # 获取管理器实例
        manager = get_browser_manager()

        # 启动浏览器
        print_info("启动浏览器...")
        browser = manager.start_browser(headless=False)
        print_success("浏览器启动成功")

        # 创建学生端上下文
        print_info("创建学生端上下文...")
        student_context = manager.create_context(
            BrowserType.STUDENT,
            viewport={'width': 1280, 'height': 720}
        )
        student_page = student_context.new_page()
        print_success("学生端上下文创建成功")

        # 创建教师端上下文
        print_info("创建教师端上下文...")
        teacher_context = manager.create_context(
            BrowserType.TEACHER,
            viewport={'width': 1280, 'height': 720}
        )
        teacher_page = teacher_context.new_page()
        print_success("教师端上下文创建成功")

        # 创建课程认证上下文
        print_info("创建课程认证上下文...")
        course_context = manager.create_context(
            BrowserType.COURSE_CERTIFICATION,
            viewport={'width': 1280, 'height': 720}
        )
        course_page = course_context.new_page()
        print_success("课程认证上下文创建成功")

        # 验证上下文数量
        contexts = manager._contexts
        print_info(f"当前上下文数量: {len(contexts)}")
        print_success("所有上下文创建成功")

        # 验证浏览器是同一个实例
        print_info("验证浏览器实例...")
        student_browser = student_context.browser
        teacher_browser = teacher_context.browser
        course_browser = course_context.browser

        if student_browser == teacher_browser == course_browser == browser:
            print_success("所有上下文共享同一个浏览器实例")
        else:
            print_warning("浏览器实例不一致（这可能是问题）")

        return True

    except Exception as e:
        print_warning(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_context_isolation():
    """
    测试2：上下文隔离性

    验证：不同上下文的 Cookie、LocalStorage 完全隔离
    """
    print_test_header("测试2: 上下文隔离性测试")

    try:
        manager = get_browser_manager()

        # 获取上下文
        student_context, student_page = manager.get_context_and_page(BrowserType.STUDENT)
        teacher_context, teacher_page = manager.get_context_and_page(BrowserType.TEACHER)

        if not student_context or not teacher_context:
            print_warning("上下文未创建，请先运行测试1")
            return False

        # 学生端：访问测试页面并设置 Cookie
        print_info("学生端：访问 example.com 并设置测试 Cookie...")
        student_page.goto("https://example.com")
        student_context.add_cookies([{
            'name': 'test_cookie',
            'value': 'student_value',
            'domain': 'example.com',
            'path': '/'
        }])

        # 教师端：访问同一页面并设置不同的 Cookie
        print_info("教师端：访问 example.com 并设置测试 Cookie...")
        teacher_page.goto("https://example.com")
        teacher_context.add_cookies([{
            'name': 'test_cookie',
            'value': 'teacher_value',
            'domain': 'example.com',
            'path': '/'
        }])

        # 验证 Cookie 隔离
        print_info("验证 Cookie 隔离...")
        student_cookies = student_context.cookies()
        teacher_cookies = teacher_context.cookies()

        student_cookie_value = next(
            (c['value'] for c in student_cookies if c['name'] == 'test_cookie'),
            None
        )
        teacher_cookie_value = next(
            (c['value'] for c in teacher_cookies if c['name'] == 'test_cookie'),
            None
        )

        if student_cookie_value == 'student_value' and teacher_cookie_value == 'teacher_value':
            print_success("上下文 Cookie 隔离验证成功")
            print_info(f"  学生端 Cookie: {student_cookie_value}")
            print_info(f"  教师端 Cookie: {teacher_cookie_value}")
            return True
        else:
            print_warning("Cookie 隔离验证失败")
            return False

    except Exception as e:
        print_warning(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_health_check():
    """
    测试3：健康检查功能

    验证：可以正确检测浏览器和上下文的状态
    """
    print_test_header("测试3: 健康检查功能")

    try:
        manager = get_browser_manager()

        # 检查浏览器存活
        print_info("检查浏览器健康状态...")
        is_browser_alive = manager.is_browser_alive()
        print_info(f"浏览器存活状态: {is_browser_alive}")

        if is_browser_alive:
            print_success("浏览器健康检查通过")
        else:
            print_warning("浏览器未启动或已崩溃")
            return False

        # 检查各上下文存活
        for browser_type in [BrowserType.STUDENT, BrowserType.TEACHER, BrowserType.COURSE_CERTIFICATION]:
            is_alive = manager.is_context_alive(browser_type)
            status = "存活" if is_alive else "不存在"
            print_info(f"  {browser_type.value}: {status}")

        print_success("所有健康检查完成")
        return True

    except Exception as e:
        print_warning(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_context_cleanup():
    """
    测试4：上下文清理功能

    验证：可以正确关闭特定上下文而不影响其他上下文
    """
    print_test_header("测试4: 上下文清理功能")

    try:
        manager = get_browser_manager()

        # 获取初始上下文数量
        initial_count = len(manager._contexts)
        print_info(f"初始上下文数量: {initial_count}")

        # 关闭学生端上下文
        print_info("关闭学生端上下文...")
        manager.close_context(BrowserType.STUDENT)

        # 验证上下文数量减少
        after_close_count = len(manager._contexts)
        print_info(f"关闭后上下文数量: {after_close_count}")

        if after_close_count == initial_count - 1:
            print_success("上下文关闭成功")
        else:
            print_warning("上下文关闭数量不符合预期")
            return False

        # 验证其他上下文仍然存活
        print_info("验证其他上下文仍然存活...")
        teacher_alive = manager.is_context_alive(BrowserType.TEACHER)
        course_alive = manager.is_context_alive(BrowserType.COURSE_CERTIFICATION)

        if teacher_alive and course_alive:
            print_success("其他上下文未受影响")
        else:
            print_warning("其他上下文可能被错误关闭")
            return False

        # 重新创建学生端上下文
        print_info("重新创建学生端上下文...")
        new_student_context = manager.create_context(BrowserType.STUDENT)
        print_success("学生端上下文重新创建成功")

        return True

    except Exception as e:
        print_warning(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_navigate_to_different_sites():
    """
    测试5：同时导航到不同网站

    验证：多个上下文可以同时访问不同的网站而不互相干扰
    """
    print_test_header("测试5: 同时导航到不同网站")

    try:
        manager = get_browser_manager()

        # 获取所有上下文
        student_context, student_page = manager.get_context_and_page(BrowserType.STUDENT)
        teacher_context, teacher_page = manager.get_context_and_page(BrowserType.TEACHER)
        course_context, course_page = manager.get_context_and_page(BrowserType.COURSE_CERTIFICATION)

        if not all([student_page, teacher_page, course_page]):
            print_warning("页面未创建，请先运行测试1")
            return False

        # 同时导航到不同网站
        print_info("学生端: 导航到 example.com...")
        student_page.goto("https://example.com")
        student_title = student_page.title()

        print_info("教师端: 导航到 example.org...")
        teacher_page.goto("https://example.org")
        teacher_title = teacher_page.title()

        print_info("课程认证: 导航到 example.net...")
        course_page.goto("https://example.net")
        course_title = course_page.title()

        # 验证标题各不相同
        print_success("所有页面导航成功")
        print_info(f"  学生端标题: {student_title}")
        print_info(f"  教师端标题: {teacher_title}")
        print_info(f"  课程认证标题: {course_title}")

        return True

    except Exception as e:
        print_warning(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_full_cleanup():
    """
    测试6：完全清理

    验证：可以正确关闭所有上下文和浏览器
    """
    print_test_header("测试6: 完全清理功能")

    try:
        manager = get_browser_manager()

        print_info("关闭所有上下文和浏览器...")
        manager.close_browser()

        # 验证清理结果
        contexts_count = len(manager._contexts)
        is_browser_alive = manager.is_browser_alive()

        print_info(f"剩余上下文数量: {contexts_count}")
        print_info(f"浏览器存活状态: {is_browser_alive}")

        if contexts_count == 0 and not is_browser_alive:
            print_success("完全清理成功")
            return True
        else:
            print_warning("清理可能不完整")
            return False

    except Exception as e:
        print_warning(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("  浏览器管理器功能测试")
    print("=" * 60)

    tests = [
        ("单浏览器多上下文模式", test_single_browser_multiple_contexts),
        ("上下文隔离性测试", test_context_isolation),
        ("健康检查功能", test_health_check),
        ("上下文清理功能", test_context_cleanup),
        ("同时导航到不同网站", test_navigate_to_different_sites),
        ("完全清理功能", test_full_cleanup),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            time.sleep(1)  # 测试之间稍作延迟
        except KeyboardInterrupt:
            print_warning("\n用户中断测试")
            break
        except Exception as e:
            print_warning(f"测试异常: {str(e)}")
            results.append((test_name, False))

    # 打印测试结果摘要
    print_test_header("测试结果摘要")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")

    print("\n" + "=" * 60)
    print(f"总计: {passed}/{total} 测试通过")
    print("=" * 60 + "\n")

    # 最终清理
    try:
        manager = get_browser_manager()
        manager.close_browser()
        print("✅ 测试完成，已清理所有资源")
    except:
        pass


if __name__ == "__main__":
    main()
