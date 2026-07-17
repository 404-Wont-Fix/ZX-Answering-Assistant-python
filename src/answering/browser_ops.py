"""
共享浏览器操作

提取 browser_answer 和 certification/workflow 中重复的 Playwright 操作，
如"点击开始测评按钮"、"等待成功提示"等。
"""

import time
import logging
from typing import Optional

from playwright.sync_api import Page

logger = logging.getLogger(__name__)


def wait_for_success_hint(page: Page, timeout: float = 10) -> bool:
    """等待考评成功提示（.eva-success 元素）。

    browser_answer 和 certification/workflow 共用的"轮询成功标记"逻辑。

    Args:
        page: Playwright Page 对象
        timeout: 最长等待秒数（默认 10）

    Returns:
        True 如果检测到成功提示，False 如果超时
    """
    start = time.time()
    while time.time() - start < timeout:
        try:
            el = page.query_selector(".eva-success")
            if el:
                return True
            time.sleep(0.5)
        except Exception:
            time.sleep(0.5)
    return False
