# -*- coding: utf-8 -*-
"""
浏览器管理器测试脚本（简化版）

测试多浏览器同时运行的功能
"""

import sys
import time
from pathlib import Path

# 设置 UTF-8 编码输出
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.browser_manager import (
    get_browser_manager,
    BrowserType
)


def print_header(title):
    print("\n" + "=" * 60)
    print(f"TEST: {title}")
    print("=" * 60)


def print_success(msg):
    print(f"[PASS] {msg}")


def print_info(msg):
    print(f"[INFO] {msg}")


def print_warning(msg):
    print(f"[WARN] {msg}")


def test_multi_context():
    """测试1: 多上下文同时创建"""
    print_header("多上下文创建测试")

    try:
        manager = get_browser_manager()

        print_info("启动浏览器...")
        browser = manager.start_browser(headless=False)
        print_success("浏览器启动成功")

        # 创建三个上下文和页面（使用管理器的方法）
        print_info("创建学生端上下文和页面...")
        student_page = manager.create_page(BrowserType.STUDENT)
        student_ctx = manager.get_context(BrowserType.STUDENT)

        print_info("创建教师端上下文和页面...")
        teacher_page = manager.create_page(BrowserType.TEACHER)
        teacher_ctx = manager.get_context(BrowserType.TEACHER)

        print_info("创建课程认证上下文和页面...")
        course_page = manager.create_page(BrowserType.COURSE_CERTIFICATION)
        course_ctx = manager.get_context(BrowserType.COURSE_CERTIFICATION)

        # 验证
        contexts_count = len(manager._contexts)
        pages_count = len(manager._pages)
        print_info(f"当前上下文数量: {contexts_count}")
        print_info(f"当前页面数量: {pages_count}")

        # 验证浏览器实例共享
        same_browser = (student_ctx.browser == teacher_ctx.browser == course_ctx.browser)
        if same_browser:
            print_success("所有上下文共享同一个浏览器实例")
        else:
            print_warning("浏览器实例不一致")

        print_success("多上下文创建测试通过")
        return True

    except Exception as e:
        print_warning(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_isolation():
    """测试2: 上下文隔离"""
    print_header("上下文隔离测试")

    try:
        manager = get_browser_manager()

        student_ctx, student_page = manager.get_context_and_page(BrowserType.STUDENT)
        teacher_ctx, teacher_page = manager.get_context_and_page(BrowserType.TEACHER)

        if not student_ctx or not teacher_ctx:
            print_warning("上下文未创建")
            return False

        # 设置不同的 Cookie
        print_info("学生端: 设置 Cookie = student_value")
        student_page.goto("https://example.com")
        student_ctx.add_cookies([{
            'name': 'test_cookie',
            'value': 'student_value',
            'domain': '.example.com',
            'path': '/'
        }])

        print_info("教师端: 设置 Cookie = teacher_value")
        teacher_page.goto("https://example.com")
        teacher_ctx.add_cookies([{
            'name': 'test_cookie',
            'value': 'teacher_value',
            'domain': '.example.com',
            'path': '/'
        }])

        # 验证
        student_cookies = student_ctx.cookies()
        teacher_cookies = teacher_ctx.cookies()

        student_val = next((c['value'] for c in student_cookies if c['name'] == 'test_cookie'), None)
        teacher_val = next((c['value'] for c in teacher_cookies if c['name'] == 'test_cookie'), None)

        print_info(f"学生端 Cookie: {student_val}")
        print_info(f"教师端 Cookie: {teacher_val}")

        if student_val == 'student_value' and teacher_val == 'teacher_value':
            print_success("上下文隔离验证通过")
            return True
        else:
            print_warning("上下文隔离验证失败")
            return False

    except Exception as e:
        print_warning(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_health_check():
    """测试3: 健康检查"""
    print_header("健康检查测试")

    try:
        manager = get_browser_manager()

        # 检查浏览器
        browser_alive = manager.is_browser_alive()
        print_info(f"浏览器存活: {browser_alive}")

        # 检查各上下文
        for btype in [BrowserType.STUDENT, BrowserType.TEACHER, BrowserType.COURSE_CERTIFICATION]:
            alive = manager.is_context_alive(btype)
            print_info(f"  {btype.value}: {alive}")

        if browser_alive:
            print_success("健康检查测试通过")
            return True
        else:
            print_warning("浏览器未存活")
            return False

    except Exception as e:
        print_warning(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cleanup():
    """测试4: 清理功能"""
    print_header("清理功能测试")

    try:
        manager = get_browser_manager()

        initial_count = len(manager._contexts)
        print_info(f"初始上下文数: {initial_count}")

        # 关闭学生端上下文
        print_info("关闭学生端上下文...")
        manager.close_context(BrowserType.STUDENT)

        after_count = len(manager._contexts)
        print_info(f"关闭后上下文数: {after_count}")

        # 验证其他上下文仍存活
        teacher_alive = manager.is_context_alive(BrowserType.TEACHER)
        course_alive = manager.is_context_alive(BrowserType.COURSE_CERTIFICATION)

        if teacher_alive and course_alive:
            print_success("其他上下文未受影响")
        else:
            print_warning("其他上下文可能被错误关闭")
            return False

        # 重新创建学生端上下文和页面
        print_info("重新创建学生端上下文和页面...")
        manager.create_page(BrowserType.STUDENT)
        print_success("清理测试通过")
        return True

    except Exception as e:
        print_warning(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_navigate():
    """测试5: 同时导航到不同网站"""
    print_header("多网站导航测试")

    try:
        manager = get_browser_manager()

        _, student_page = manager.get_context_and_page(BrowserType.STUDENT)
        _, teacher_page = manager.get_context_and_page(BrowserType.TEACHER)
        _, course_page = manager.get_context_and_page(BrowserType.COURSE_CERTIFICATION)

        if not all([student_page, teacher_page, course_page]):
            print_warning("页面未创建")
            return False

        # 导航到不同网站
        print_info("学生端 -> example.com")
        student_page.goto("https://example.com")
        s_title = student_page.title()

        print_info("教师端 -> example.org")
        teacher_page.goto("https://example.org")
        t_title = teacher_page.title()

        print_info("课程认证 -> example.net")
        course_page.goto("https://example.net")
        c_title = course_page.title()

        print_info(f"学生端: {s_title}")
        print_info(f"教师端: {t_title}")
        print_info(f"课程认证: {c_title}")

        print_success("多网站导航测试通过")
        return True

    except Exception as e:
        print_warning(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "=" * 60)
    print("  浏览器管理器功能测试")
    print("=" * 60)

    tests = [
        ("多上下文创建", test_multi_context),
        ("上下文隔离", test_isolation),
        ("健康检查", test_health_check),
        ("清理功能", test_cleanup),
        ("多网站导航", test_navigate),
    ]

    results = []

    for name, func in tests:
        try:
            result = func()
            results.append((name, result))
            time.sleep(1)
        except KeyboardInterrupt:
            print_warning("\n用户中断")
            break
        except Exception as e:
            print_warning(f"测试异常: {e}")
            results.append((name, False))

    # 汇总
    print_header("测试结果")
    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {name}")

    print("\n" + "=" * 60)
    print(f"总计: {passed}/{total} 通过")
    print("=" * 60 + "\n")

    # 清理
    try:
        manager = get_browser_manager()
        manager.close_browser()
        print("[INFO] 已清理所有资源")
    except:
        pass


if __name__ == "__main__":
    main()
