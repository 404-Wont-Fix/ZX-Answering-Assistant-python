# -*- coding: utf-8 -*-
"""
测试浏览器清理机制
"""

import sys
import time
from pathlib import Path

# Windows UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.browser_manager import get_browser_manager, BrowserType
import atexit


def cleanup_test():
    """测试清理函数"""
    print("\n" + "=" * 60)
    print("TEST: Browser cleanup on exit")
    print("=" * 60)

    try:
        manager = get_browser_manager()

        print("Step 1/4: Starting browser...")
        manager.start_browser(headless=False)

        print("Step 2/4: Creating contexts...")
        manager.create_page(BrowserType.STUDENT)
        manager.create_page(BrowserType.TEACHER)
        manager.create_page(BrowserType.COURSE_CERTIFICATION)
        print(f"Created {len(manager._contexts)} contexts")

        print("Step 3/4: Visiting test page...")
        _, student_page = manager.get_context_and_page(BrowserType.STUDENT)
        if student_page:
            student_page.goto("https://example.com")
            print("Visited example.com")

        print("Step 4/4: Waiting 2 seconds before exit...")
        print("INFO: Observe if program exits cleanly without EPIPE error")
        time.sleep(2)

        print("\n[SUCCESS] Test complete, program exiting...")
        print("INFO: Check cleanup logs above - no Node.js errors should appear\n")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("\n" + "=" * 60)
    print("  Browser Cleanup Mechanism Test")
    print("=" * 60)
    print("\nThis test verifies:")
    print("  1. Browser is cleaned up on exit")
    print("  2. No EPIPE errors occur")
    print("  3. Node.js process exits cleanly")
    print("\n" + "=" * 60)

    atexit.register(cleanup_test)

    print("\nTest starting in 1 second...")
    time.sleep(1)


if __name__ == "__main__":
    main()
