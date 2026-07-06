"""
懒狗一键评分插件数据模型

- ClassProject：GetTeacherClassProject 列表项
- ProjectResult：GetClassProjectResult 学生成果列表项
"""

from dataclasses import dataclass, field
from typing import Optional
import json as _json
import re as _re
import html as _html


def _truncate_date(value: Optional[str]) -> str:
    """把 '2026-06-20T00:00:00' 之类的 ISO 时间截断到 '2026-06-20'。"""
    if not value:
        return ""
    return value.split("T", 1)[0]


@dataclass
class ClassProject:
    """
    产教融合项目列表项（GetTeacherClassProject）。

    字段命名说明
    - source_id：GetClassProjectResult 接口的 sourceid 入参（班级项目记录ID）
    - project_id：GetClassProjectResult 接口的 projectID 入参（项目库ID）
    - class_id：GetClassProjectResult 接口的 classID 入参
    """

    source_id: int  # raw["id"] → GetClassProjectResult.sourceid
    project_id: int  # raw["projiectLibID"] / projectLib.id → GetClassProjectResult.projectID
    class_id: str
    class_name: str
    fb_name: str  # 指导老师姓名（GetTeacherClassProject.fbName）
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
        project_lib = raw.get("projectLib") or {}
        return cls(
            source_id=raw.get("id", 0) or 0,
            # 响应字段名是 projiectLibID（后端拼写错误），回退到 projectLib.id
            project_id=raw.get("projiectLibID") or project_lib.get("id") or 0,
            class_id=raw.get("classID", "") or "",
            class_name=raw.get("className", "") or "",
            fb_name=raw.get("fbName", "") or "",
            # 优先用顶层 proName，缺失时回落到 projectLib.name
            pro_name=(
                raw.get("proName")
                or project_lib.get("name")
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


# 审核状态码 → 可读文案（仅在无法确认时给出合理默认值）
_AUDIT_STATUS_TEXT: dict[int, str] = {
    0: "未提交",
    1: "待评审",
    2: "已通过",
    3: "未通过",
}


@dataclass
class ProjectResult:
    """
    学生项目成果（GetClassProjectResult 列表项）。

    包含学生提交的实训报告、截图、附件、评分等全部字段。
    """

    id: int  # 成果记录ID
    project_id: int
    student_id: str
    student_name: str
    project_progress: int  # 项目进度 0-100
    submit_time: str  # ISO 格式
    pro_score: int  # 教师评分（0=未评分）
    audit_status: int  # 审核状态码
    review_comments: Optional[str]
    result_description: str  # HTML 实训报告正文
    screenshot_raw: str  # 截图 JSON 字符串（项目截图列表）
    enclosure_raw: str  # 附件 JSON 字符串
    # 来自 GetStudentResultWithLogsByRid 时才有值（基础列表接口为空列表）
    commit_logs_raw: list = field(default_factory=list)

    # ---------- 计算属性 ----------

    @property
    def submit_date(self) -> str:
        """'2026-06-24T20:43:54' → '2026-06-24 20:43'。"""
        if not self.submit_time:
            return ""
        return self.submit_time.replace("T", " ")[:16]

    @property
    def status_text(self) -> str:
        """审核状态可读文案。"""
        return _AUDIT_STATUS_TEXT.get(self.audit_status, "未知")

    @property
    def is_graded(self) -> bool:
        """是否已被教师评分（pro_score > 0）。"""
        return self.pro_score > 0

    @property
    def initial(self) -> str:
        """学生姓名首字（用于列表头像占位）。"""
        return (self.student_name or "?")[:1]

    # ---------- 评分辅助属性 ----------

    @property
    def screenshot_count(self) -> int:
        """实际截图数（第一张封面不算）。"""
        try:
            items = _json.loads(self.screenshot_raw) if self.screenshot_raw else []
            return max(0, len(items) - 1)
        except (_json.JSONDecodeError, TypeError):
            return 0

    @property
    def desc_char_count(self) -> int:
        """心得正文字数（去 HTML 标签后的纯文本长度）。"""
        text = _re.sub(r'<[^>]+>', '', self.result_description or "")
        text = _html.unescape(text)
        return len(text.strip())

    @property
    def has_attachment(self) -> bool:
        """enclosure 是否包含真实文件（非空对象）。"""
        raw = (self.enclosure_raw or "").strip()
        if not raw or raw == "{}":
            return False
        try:
            d = _json.loads(raw)
            return bool(d.get("id") or d.get("fileName"))
        except (_json.JSONDecodeError, TypeError):
            return False

    @property
    def log_stage_count(self) -> int:
        """commitLogs 阶段数（需先通过详情接口填充 commit_logs_raw）。"""
        return len(self.commit_logs_raw)

    @property
    def log_total_chars(self) -> int:
        """commitLogs 所有 note 的总字数。"""
        return sum(len((log.get("note") or "").strip()) for log in self.commit_logs_raw)

    # ---------- 反序列化 ----------

    @classmethod
    def from_api(cls, raw: dict) -> "ProjectResult":
        """从后端原始 item dict 解析出 ProjectResult。"""
        return cls(
            id=raw.get("id", 0) or 0,
            project_id=raw.get("projectID", 0) or 0,
            student_id=raw.get("studentID", "") or "",
            student_name=raw.get("studentName", "") or "",
            project_progress=raw.get("projectProgress", 0) or 0,
            submit_time=raw.get("submitTime", "") or "",
            pro_score=raw.get("proScore", 0) or 0,
            audit_status=raw.get("auditStatus", 0) or 0,
            review_comments=raw.get("reviewComments"),
            result_description=raw.get("resultDescription", "") or "",
            screenshot_raw=raw.get("projectScreenshot", "") or "",
            enclosure_raw=raw.get("enclosure", "") or "",
            # 仅 GetStudentResultWithLogsByRid 响应才包含此字段
            commit_logs_raw=raw.get("commitLogs") or [],
        )
