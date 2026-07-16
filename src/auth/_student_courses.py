"""学生端课程/章节 API（纯 HTTP，无 Playwright，无浏览器依赖）。

从 src/auth/student.py 抽出。课程/章节 API 根本不属于 auth 层，独立到此。
消除 get_student_courses 与 _get_student_courses_request 的重复（后者复用）。
"""

import json
import logging
from typing import Dict, List, Optional

from src.core.api_client import get_api_client
from src.core.headers import get_api_headers

logger = logging.getLogger(__name__)


def get_uncompleted_chapters(
    access_token: str, course_id: str, delay_ms: int = 600, max_retries: int = 3
) -> Optional[List[Dict]]:
    """使用 access_token 和课程 ID 获取未完成的知识点列表。

    Args:
        access_token: 学生端的 access_token。
        course_id: 课程 ID。
        delay_ms: 请求延迟（毫秒，已弃用，请使用设置菜单配置）。
        max_retries: 最大重试次数（已弃用，请使用设置菜单配置）。

    Returns:
        未完成的知识点列表，失败返回 None。
    """
    try:
        api_client = get_api_client()

        # API 端点
        url = f"https://ai.cqzuxia.com/evaluation/api/StuEvaluateReport/GetUnCompleteChapterList?CourseID={course_id}"

        # 请求头
        headers = get_api_headers(
            "chrome_138", access_token,
            referer="https://ai.cqzuxia.com/",
            extra_headers={"priority": "u=1, i"},
        )

        # 如果明确指定了 max_retries 且大于 0，使用它（向后兼容）
        actual_max_retries = max_retries if max_retries > 0 else None

        logger.info(f"正在获取课程 {course_id} 的未完成知识点列表...")
        logger.info(f"发送请求到: {url}")

        response = api_client.request("GET", url, headers=headers, max_retries=actual_max_retries)

        if response and response.status_code == 200:
            logger.info(f"✅ 请求成功，状态码: {response.status_code}")

            try:
                data = response.json()

                if isinstance(data, dict):
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

                logger.info(f"✅ 成功获取 {len(all_knowledges)} 个未完成知识点")
                return all_knowledges

            except Exception as e:
                logger.error(f"解析JSON响应失败: {str(e)}")
                logger.error(f"响应内容: {response.text[:500] if response else 'N/A'}")
                return None
        else:
            status_code = response.status_code if response else "N/A"
            logger.error(f"❌ 请求失败，状态码: {status_code}")
            logger.error(f"响应内容: {response.text[:500] if response else 'N/A'}")
            return None

    except Exception as e:
        logger.error(f"❌ 获取未完成知识点列表异常: {str(e)}")
        return None


def _get_student_courses_request(
    access_token: str, max_retries: Optional[int] = None
) -> Optional[List[Dict]]:
    """获取学生端课程列表的实际请求逻辑（内部方法）。

    Args:
        access_token: 学生端的 access_token。
        max_retries: 最大重试次数；None 走 APIClient 默认。

    Returns:
        课程列表，失败返回 None。
    """
    url = "https://ai.cqzuxia.com/evaluation/api/StuEvaluateReport/GetStuLatestTermCourseReports?"

    headers = get_api_headers(
        "chrome_138", access_token,
        referer="https://ai.cqzuxia.com/",
        extra_headers={"priority": "u=1, i"},
    )

    logger.info(f"发送请求到: {url}")
    logger.info("使用已认证的学生端会话获取课程列表")

    api_client = get_api_client()
    response = api_client.get(url, headers=headers, max_retries=max_retries)

    if response is None:
        return None

    if response.status_code == 200:
        logger.info(f"✅ 请求成功，状态码: {response.status_code}")

        try:
            data = response.json()
            logger.info(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")

            if isinstance(data, list):
                courses = data
            elif isinstance(data, dict):
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

            return courses

        except json.JSONDecodeError as e:
            logger.error(f"解析JSON响应失败: {str(e)}")
            logger.error(f"响应内容: {response.text[:500]}")
            return None
    else:
        logger.error(f"❌ 请求失败，状态码: {response.status_code}")
        logger.error(f"响应内容: {response.text[:500]}")
        return None


def get_student_courses(
    access_token: str, max_retries: Optional[int] = None, delay: int = 2
) -> Optional[List[Dict]]:
    """使用 access_token 获取学生端课程列表（带重试，复用 _get_student_courses_request）。

    Args:
        access_token: 学生端的 access_token。
        max_retries: 最大重试次数；None 从配置读取。
        delay: 重试延迟（秒，已弃用，保留向后兼容）。

    Returns:
        课程列表，失败返回 None。
    """
    try:
        logger.info("正在获取学生端课程列表...")
        return _get_student_courses_request(access_token, max_retries=max_retries)
    except Exception as e:
        logger.error(f"❌ 获取课程列表异常: {str(e)}")
        return None
