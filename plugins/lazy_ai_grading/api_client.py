"""
懒狗一键评分插件 API 客户端

封装产教融合项目列表接口 GetTeacherClassProject，
复用主程序的统一 HTTP 客户端（含速率限制/重试）。
"""

from typing import List, Tuple

from src.core.api_client import get_api_client

from .models import ClassProject

# 产教融合项目列表接口（教师端 admin 站点下的 prodedu 模块）
PROJECT_LIST_URL = "https://admin.cqzuxia.com/prodedu/api/Admin/GetTeacherClassProject"


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

        # rate_limit=False：默认 very_high 档为 10s/请求，翻页/搜索会非常卡；
        # 此处均为用户主动触发的单次请求，无突发风险，故对该接口关闭限流。
        # use_cache 保持默认 False：分页不可缓存。
        response = get_api_client().get(
            PROJECT_LIST_URL,
            headers=headers,
            params=params,
            rate_limit=False,
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
