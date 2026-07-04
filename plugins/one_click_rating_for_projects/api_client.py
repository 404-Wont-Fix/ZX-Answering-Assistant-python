"""
懒狗一键评分插件 API 客户端

封装产教融合项目列表接口 GetTeacherClassProject，
复用主程序的统一 HTTP 客户端（含速率限制/重试）。
"""

from typing import List, Tuple

from src.core.api_client import get_api_client

from .models import ClassProject, ProjectResult

# 产教融合项目列表接口（教师端 admin 站点下的 prodedu 模块）
PROJECT_LIST_URL = "https://admin.cqzuxia.com/prodedu/api/Admin/GetTeacherClassProject"
# 学生项目成果接口
PROJECT_RESULT_URL = "https://admin.cqzuxia.com/prodedu/api/Admin/GetClassProjectResult"
# 学生详情接口（含阶段日志）
STUDENT_DETAIL_URL = "https://admin.cqzuxia.com/prodedu/api/Admin/GetStudentResultWithLogsByRid"
# 提交评分接口
AUDIT_RESULT_URL = "https://admin.cqzuxia.com/prodedu/api/Admin/AuditResult"


class LazyGradingAPIClient:
    """产教融合项目评分接口客户端。"""

    def __init__(self, access_token: str):
        """
        Args:
            access_token: 教师端 access_token（由 Extractor.login 取得）
        """
        self.access_token = access_token
        # 上一次已知的项目总数，作为 dataCount 入参回传（SqlSugar 分页惯例）；
        # 首次为 0，之后用响应里的真实 dataCount 更新。
        self._data_count = 0

    def get_class_projects(
        self,
        *,
        page_index: int = 1,
        page_size: int = 10,
        key_word: str = "",
        class_status: int = 0,
        source_type: int = 1,
    ) -> Tuple[List[ClassProject], int]:
        """
        获取教师名下的产教融合项目列表（分页 + 服务端搜索）。

        Args:
            page_index: 页码，从 1 开始
            page_size: 每页条数
            key_word: 搜索关键字（服务端按项目/班级名匹配）
            class_status: 班级项目状态过滤，0 表示全部
            source_type: 来源类型，1 为默认（与抓包一致）

        Returns:
            (items, total_count): 当前页项目列表与项目总数

        Raises:
            RuntimeError: 网络失败、HTTP 非 200 或业务信封标识失败时抛出
        """
        headers = {
            "accept": "application/json, text/plain, */*",
            "authorization": f"Bearer {self.access_token}",
            "referer": "https://admin.cqzuxia.com/",
        }
        params = {
            "pageIndex": page_index,
            "pageSize": page_size,
            "dataCount": self._data_count,
            "keyWord": key_word,
            "classStatus": class_status,
            "sourceType": source_type,
        }

        # 遵循主程序速率限制设置（由 cli_config.json api_settings.rate_level 控制）
        response = get_api_client().get(
            PROJECT_LIST_URL,
            headers=headers,
            params=params,
        )

        if response is None:
            raise RuntimeError("获取项目列表失败：网络错误或已超时，请重试或重新登录")
        if response.status_code != 200:
            raise RuntimeError(
                f"获取项目列表失败：服务器返回 {response.status_code}"
            )

        body = {}
        try:
            body = response.json() or {}
        except ValueError:
            raise RuntimeError("获取项目列表失败：响应不是合法的 JSON")

        # 兼容 code==0 与 success==true 两种成功标识
        if body.get("code") != 0 and not body.get("success"):
            raise RuntimeError(body.get("msg") or "获取项目列表失败")

        payload = body.get("data") or {}
        raw_items = payload.get("data") or []
        items = [ClassProject.from_api(item) for item in raw_items]
        self._data_count = payload.get("dataCount", self._data_count) or 0
        return items, self._data_count

    # ------------------------------------------------------------------
    # 学生项目成果
    # ------------------------------------------------------------------

    def get_class_project_result(
        self,
        *,
        source_id: int,
        class_id: str,
        project_id: int,
        key_word: str = "",
        source_type: int = 1,
    ) -> List[ProjectResult]:
        """
        获取某班级项目的学生成果列表（不分页，一次性返回全部提交记录）。

        Args:
            source_id: 班级项目记录ID（ClassProject.source_id，接口参数名 sourceid）
            class_id: 班级ID（ClassProject.class_id）
            project_id: 项目库ID（ClassProject.project_id，接口参数名 projectID）
            key_word: 搜索关键字（可选，按学生姓名匹配）
            source_type: 来源类型（1=产教融合）

        Returns:
            学生成果列表（按提交时间排序）

        Raises:
            RuntimeError: 网络/HTTP/业务失败
        """
        headers = {
            "accept": "application/json, text/plain, */*",
            "authorization": f"Bearer {self.access_token}",
            "referer": "https://admin.cqzuxia.com/",
        }
        params = {
            "sourceid": source_id,
            "classID": class_id,
            "projectID": project_id,
            "sourceType": source_type,
            "keyWord": key_word,
        }

        response = get_api_client().get(
            PROJECT_RESULT_URL,
            headers=headers,
            params=params,
        )

        if response is None:
            raise RuntimeError("获取学生成果失败：网络错误或已超时，请重试或重新登录")
        if response.status_code != 200:
            raise RuntimeError(
                f"获取学生成果失败：服务器返回 {response.status_code}"
            )

        body = {}
        try:
            body = response.json() or {}
        except ValueError:
            raise RuntimeError("获取学生成果失败：响应不是合法的 JSON")

        if body.get("code") != 0 and not body.get("success"):
            raise RuntimeError(body.get("msg") or "获取学生成果失败")

        # GetClassProjectResult 的 data 字段直接就是列表（非分页结构）
        raw_items = body.get("data") or []
        return [ProjectResult.from_api(item) for item in raw_items]

    # ------------------------------------------------------------------
    # 学生详情（含阶段日志）
    # ------------------------------------------------------------------

    def get_student_result_with_logs(self, rid: int) -> dict:
        """
        获取单个学生的完整成果详情（含 commitLogs 阶段日志）。

        Args:
            rid: 学生成果记录ID（ProjectResult.id）

        Returns:
            原始响应 dict，包含 commitLogs 等字段

        Raises:
            RuntimeError: 网络/HTTP/业务失败
        """
        headers = {
            "accept": "application/json, text/plain, */*",
            "authorization": f"Bearer {self.access_token}",
            "referer": "https://admin.cqzuxia.com/",
        }
        params = {"rid": rid}

        response = get_api_client().get(
            STUDENT_DETAIL_URL,
            headers=headers,
            params=params,
        )

        if response is None:
            raise RuntimeError(f"获取学生详情失败（rid={rid}）：网络错误")
        if response.status_code != 200:
            raise RuntimeError(
                f"获取学生详情失败（rid={rid}）：服务器返回 {response.status_code}"
            )

        body = {}
        try:
            body = response.json() or {}
        except ValueError:
            raise RuntimeError(f"获取学生详情失败（rid={rid}）：响应不是合法的 JSON")

        if body.get("code") != 0 and not body.get("success"):
            raise RuntimeError(body.get("msg") or f"获取学生详情失败（rid={rid}）")

        return body.get("data") or {}

    # ------------------------------------------------------------------
    # 提交评分
    # ------------------------------------------------------------------

    def audit_result(
        self,
        rid: int,
        pro_score: str,
        review_comments: str,
        audit_status: int = 3,
    ) -> dict:
        """
        提交学生项目评分。

        Args:
            rid: 学生成果记录ID
            pro_score: 分数（字符串，如 "86"）
            review_comments: 审核批语
            audit_status: 审核状态码（3 = 已评审）

        Returns:
            更新后的学生成果原始 dict

        Raises:
            RuntimeError: 网络/HTTP/业务失败
        """
        headers = {
            "accept": "application/json, text/plain, */*",
            "authorization": f"Bearer {self.access_token}",
            "content-type": "application/json",
            "origin": "https://admin.cqzuxia.com",
            "referer": "https://admin.cqzuxia.com/",
        }
        payload = {
            "rid": rid,
            "proScore": pro_score,
            "reviewComments": review_comments,
            "auditStatus": audit_status,
        }

        response = get_api_client().post(
            AUDIT_RESULT_URL,
            headers=headers,
            json=payload,
        )

        if response is None:
            raise RuntimeError(f"提交评分失败（rid={rid}）：网络错误")
        if response.status_code != 200:
            raise RuntimeError(
                f"提交评分失败（rid={rid}）：服务器返回 {response.status_code}"
            )

        body = {}
        try:
            body = response.json() or {}
        except ValueError:
            raise RuntimeError(f"提交评分失败（rid={rid}）：响应不是合法的 JSON")

        if body.get("code") != 0 and not body.get("success"):
            raise RuntimeError(body.get("msg") or f"提交评分失败（rid={rid}）")

        return body.get("data") or {}
