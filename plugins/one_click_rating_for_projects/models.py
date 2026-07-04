"""
懒狗一键评分插件数据模型

封装产教融合项目（GetTeacherClassProject）列表项的字段映射，
避免视图层直接消费后端原始 dict。
"""

from dataclasses import dataclass
from typing import Optional


def _truncate_date(value: Optional[str]) -> str:
    """把 '2026-06-20T00:00:00' 之类的 ISO 时间截断到 '2026-06-20'。"""
    if not value:
        return ""
    return value.split("T", 1)[0]


@dataclass
class ClassProject:
    """产教融合项目列表项（仅保留展示所需字段）。"""

    id: int
    class_id: str
    class_name: str
    pro_name: str
    project_type_name: str
    pro_start_time: str
    pro_end_time: str
    class_count: int  # 班级总人数
    jing_xing_count: int  # 进行中
    to_sp_count: int  # 待审批
    has_ok_count: int  # 已完成
    status_str: str  # 进行中 / 已结束
    status_code: int  # 进行中=3 / 已结束=2

    @property
    def time_window(self) -> str:
        """格式化为 '开始 ~ 结束'（仅日期）。"""
        start = _truncate_date(self.pro_start_time)
        end = _truncate_date(self.pro_end_time)
        if not start and not end:
            return ""
        return f"{start} ~ {end}"

    @classmethod
    def from_api(cls, raw: dict) -> "ClassProject":
        """从后端原始 item dict 解析出 ClassProject。"""
        status_info = raw.get("statusStr") or {}
        return cls(
            id=raw.get("id", 0),
            class_id=raw.get("classID", "") or "",
            class_name=raw.get("className", "") or "",
            # 优先用顶层 proName，缺失时回落到 projectLib.name
            pro_name=(
                raw.get("proName")
                or (raw.get("projectLib") or {}).get("name")
                or ""
            ),
            project_type_name=raw.get("projectTypeName", "") or "",
            pro_start_time=raw.get("proStartTime", "") or "",
            pro_end_time=raw.get("proEndTime", "") or "",
            class_count=raw.get("classCount", 0) or 0,
            jing_xing_count=raw.get("jingXingCount", 0) or 0,
            to_sp_count=raw.get("toSPCount", 0) or 0,
            has_ok_count=raw.get("hasOkCount", 0) or 0,
            status_str=status_info.get("Str", "") or "",
            status_code=status_info.get("code", 0) or 0,
        )
