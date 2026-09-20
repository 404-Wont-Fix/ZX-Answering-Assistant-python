"""
评估出题向导的领域模型 - Domain models for the evaluation question wizard.

这一层完全不依赖 Flet / 网络 / 文件系统，便于单测。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# ---------------------------------------------------------------- 平台枚举
# 取值以平台模板为准（见 kp-question-excel.xlsx / kp-import-template.docx）
QUESTION_TYPES = ("单选", "多选", "判断")
QUESTION_TYPE_ORDER = {"单选": 0, "多选": 1, "判断": 2}

DIFFICULTIES = ("简单", "一般", "困难")

KNOWLEDGE_LEVELS = ("对口", "高质量", "明星")

KNOWLEDGE_TYPES = ("了解", "理解", "掌握")

# 题号里的题型码：X=单选 D=多选 P=判断
TYPE_CODES = {"单选": "X", "多选": "D", "判断": "P"}

# 正确答案项最多可用的选项字母（平台最多 8 个选项）
OPTION_LETTERS = "ABCDEFGH"
MAX_OPTIONS = len(OPTION_LETTERS)

JUDGE_OPTIONS = ("正确", "错误")

# ---------------------------------------------------------------- 默认值
DEFAULT_QUESTION_COUNT = 10
DEFAULT_TYPE_RATIO = {"单选": 70, "多选": 20, "判断": 10}
DEFAULT_DIFFICULTY_RATIO = {"简单": 20, "一般": 60, "困难": 20}
SENSITIVITY_LEVELS = ("宽松", "标准", "严格")
DEFAULT_SENSITIVITY = "标准"

# 澄清级别
CLARIFICATION_LEVELS = ("阻断", "确认", "自决")


@dataclass
class Question:
    """一道评估题。"""

    stem: str = ""
    question_type: str = "单选"
    difficulty: str = "一般"
    options: list[str] = field(default_factory=list)
    answer: str = "A"
    confidence: float = 1.0
    rationale: str = ""
    reviewed: bool = False
    internal_id: str = ""
    # 生成失败/被跳过时标记，Step6 显示灰行 + ［补生成］
    skipped: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.options, tuple):
            self.options = list(self.options)
        if self.options is None:
            self.options = []

    @property
    def answer_letters(self) -> list[str]:
        """答案字母升序列表（如 'BC' → ['B', 'C']）。"""
        return sorted({ch for ch in (self.answer or "").upper() if ch.isalpha()})

    @property
    def confidence_color(self) -> str:
        """AI 置信度色标：绿 ≥0.8；黄 0.6~0.8；红 <0.6。"""
        if self.confidence >= 0.8:
            return "green"
        if self.confidence >= 0.6:
            return "amber"
        return "red"

    def question_no(self, chapter_order: int, point_order: int, index: int) -> str:
        """题号 {章}-{知识点}-{题型码}-{序号}。"""
        code = TYPE_CODES.get(self.question_type, "X")
        return f"{chapter_order}-{point_order}-{code}-{index}"


@dataclass
class KnowledgePoint:
    """一个知识点及其出题配置与产出。"""

    name: str = ""
    order: int = 0
    chapter_order: int = 0
    chapter_name: str = ""
    # v1.1：知识点等级 / 知识点类型
    level: str = KNOWLEDGE_LEVELS[0]
    knowledge_type: str = KNOWLEDGE_TYPES[0]
    # 教师填写的考点 tag
    tags: list[str] = field(default_factory=list)
    special_requirements: str = ""
    # 题量与题型配置
    #   question_count —— 该知识点总题数
    #   type_counts    —— 各题型**题数**（规范存储，合计应当等于 question_count）
    #   type_ratio     —— 各题型**比例**（「按比例」视图的输入，有效题型合计 100）
    question_count: int = DEFAULT_QUESTION_COUNT
    type_counts: dict[str, int] = field(default_factory=dict)
    type_ratio: dict[str, int] = field(default_factory=dict)
    difficulty_ratio: dict[str, int] = field(
        default_factory=lambda: dict(DEFAULT_DIFFICULTY_RATIO)
    )
    questions: list[Question] = field(default_factory=list)
    skipped: bool = False
    # 自推考点（FR3.3：全部未填写时按 课程名+章节名+知识点名 自推）
    inferred_tags: list[str] = field(default_factory=list)
    inferred_tags_reviewed: bool = False
    # 该行是否被教师手动覆盖过默认配置（Step4 灰标「默认」/ 高亮「已覆盖」）
    overridden: bool = False

    def __post_init__(self) -> None:
        if isinstance(self.tags, tuple):
            self.tags = list(self.tags)
        if not self.type_ratio:
            self.type_ratio = dict(DEFAULT_TYPE_RATIO)
        if not self.type_counts:
            self.type_counts = allocate_with_floor(self.question_count, self.type_ratio)
        elif sum(self.type_counts.values()) == 100 and self.question_count != 100:
            # 兼容把「比例」直接写进 type_counts 的数据
            self.type_ratio = {
                name: max(int(self.type_counts.get(name, 0) or 0), 0)
                for name in QUESTION_TYPES
            }
            self.type_counts = allocate_with_floor(self.question_count, self.type_ratio)
        if not self.difficulty_ratio:
            self.difficulty_ratio = dict(DEFAULT_DIFFICULTY_RATIO)

    @property
    def effective_tags(self) -> list[str]:
        """实际用于出题的考点：教师填写优先，否则用自推清单。"""
        return list(self.tags) if self.tags else list(self.inferred_tags)

    @property
    def selected_types(self) -> dict[str, int]:
        """被勾选的题型（比例 > 0）——教师预期的题型集合。"""
        return {
            name: max(int(self.type_ratio.get(name, 0) or 0), 0)
            for name in QUESTION_TYPES
            if max(int(self.type_ratio.get(name, 0) or 0), 0) > 0
        }

    @property
    def has_pending_clarification(self) -> bool:
        return any(getattr(q, "_pending", False) for q in self.questions)

    @property
    def active_types(self) -> dict[str, int]:
        """实际有题数的题型（题数 > 0）。"""
        return {
            name: int(self.type_counts.get(name, 0) or 0)
            for name in QUESTION_TYPES
            if int(self.type_counts.get(name, 0) or 0) > 0
        }

    @property
    def active_type_total(self) -> int:
        return sum(self.active_types.values())

    @property
    def selected_ratio_total(self) -> int:
        return sum(self.selected_types.values())

    def set_type_ratio(self, ratio: dict[str, int], *, question_count: int | None = None) -> None:
        """写入题型比例并用带保底的最大余数法同步题数（比例视图编辑入口）。"""
        self.type_ratio = {
            name: max(int(ratio.get(name, 0) or 0), 0) for name in QUESTION_TYPES
        }
        total = self.question_count if question_count is None else int(question_count)
        self.type_counts = allocate_with_floor(total, self.type_ratio)

    def set_type_counts(self, counts: dict[str, int]) -> None:
        """写入题型题数并回算比例（题数视图编辑入口）。"""
        self.type_counts = {
            name: max(int(counts.get(name, 0) or 0), 0) for name in QUESTION_TYPES
        }
        self.type_ratio = ratio_from_counts(self.type_counts)

    def set_question_count(self, total: int) -> None:
        """改总题数后按当前比例重算各题型题数（FR4.3 题数↔比例联动）。"""
        self.question_count = max(int(total or 0), 0)
        self.type_counts = allocate_with_floor(self.question_count, self.type_ratio)


@dataclass
class Chapter:
    """一个章节，含有序知识点列表。"""

    name: str = ""
    order: int = 0
    knowledge_points: list[KnowledgePoint] = field(default_factory=list)

    def __post_init__(self) -> None:
        if isinstance(self.knowledge_points, tuple):
            self.knowledge_points = list(self.knowledge_points)

    def renumber(self, chapter_order: int | None = None) -> None:
        """重排章节内知识点序号，并回填 chapter_order/chapter_name。"""
        order = self.order if chapter_order is None else chapter_order
        self.order = order
        for index, point in enumerate(self.knowledge_points, start=1):
            point.order = index
            point.chapter_order = order
            point.chapter_name = self.name


@dataclass
class CourseDraft:
    """整份向导草稿（可 JSON 序列化，用于续填）。"""

    course_name: str = ""
    target: str = ""
    tool_version: str = ""
    # 考纲/大纲/教材目录（本地路径）与样例题库（仅对齐格式/难度）
    syllabus_path: str = ""
    course_examples: list[dict[str, Any]] = field(default_factory=list)
    online_search: bool = False
    chapters: list[Chapter] = field(default_factory=list)
    current_step: int = 1
    sensitivity: str = DEFAULT_SENSITIVITY
    # 是否强制教师过目自推考点清单（FR3.4，默认否）
    force_review_inferred_tags: bool = False
    review_mode: str = "逐题"
    export_word: bool = True
    export_excel: bool = True
    clarification_records: list[dict[str, Any]] = field(default_factory=list)
    generation_status: str = "idle"
    generation_run_id: str = ""
    # 上一次成功生成时的「生成输入指纹」；与当前草稿不一致 = 草稿已改需重新生成
    generation_fingerprint: str = ""
    cost_estimate: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.sensitivity not in SENSITIVITY_LEVELS:
            self.sensitivity = DEFAULT_SENSITIVITY

    # ------------------------------------------------------------ 序列化
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "CourseDraft":
        payload = payload or {}
        draft = cls(
            course_name=payload.get("course_name", ""),
            target=payload.get("target", ""),
            tool_version=payload.get("tool_version", ""),
            syllabus_path=payload.get("syllabus_path", ""),
            course_examples=list(payload.get("course_examples") or []),
            online_search=bool(payload.get("online_search", False)),
            current_step=int(payload.get("current_step", 1) or 1),
            sensitivity=payload.get("sensitivity", DEFAULT_SENSITIVITY),
            force_review_inferred_tags=bool(payload.get("force_review_inferred_tags", False)),
            review_mode=payload.get("review_mode", "逐题"),
            export_word=bool(payload.get("export_word", True)),
            export_excel=bool(payload.get("export_excel", True)),
            clarification_records=list(payload.get("clarification_records") or []),
            generation_status=payload.get("generation_status", "idle"),
            generation_run_id=payload.get("generation_run_id", ""),
            generation_fingerprint=payload.get("generation_fingerprint", ""),
            cost_estimate=dict(payload.get("cost_estimate") or {}),
        )

        for chapter_payload in payload.get("chapters") or []:
            chapter = Chapter(
                name=chapter_payload.get("name", ""),
                order=int(chapter_payload.get("order", 0) or 0),
            )
            for point_payload in chapter_payload.get("knowledge_points") or []:
                point = KnowledgePoint(
                    name=point_payload.get("name", ""),
                    order=int(point_payload.get("order", 0) or 0),
                    chapter_order=int(point_payload.get("chapter_order", 0) or 0),
                    chapter_name=point_payload.get("chapter_name", chapter.name),
                    level=point_payload.get("level", KNOWLEDGE_LEVELS[0]),
                    knowledge_type=point_payload.get(
                        "knowledge_type", KNOWLEDGE_TYPES[0]
                    ),
                    tags=list(point_payload.get("tags") or []),
                    special_requirements=point_payload.get("special_requirements", ""),
                    question_count=int(
                        point_payload.get("question_count", DEFAULT_QUESTION_COUNT)
                        or DEFAULT_QUESTION_COUNT
                    ),
                    type_counts=dict(point_payload.get("type_counts") or {}),
                    type_ratio=dict(
                        point_payload.get("type_ratio") or DEFAULT_TYPE_RATIO
                    ),
                    difficulty_ratio=dict(
                        point_payload.get("difficulty_ratio") or DEFAULT_DIFFICULTY_RATIO
                    ),
                    skipped=bool(point_payload.get("skipped", False)),
                    inferred_tags=list(point_payload.get("inferred_tags") or []),
                    inferred_tags_reviewed=bool(
                        point_payload.get("inferred_tags_reviewed", False)
                    ),
                    overridden=bool(point_payload.get("overridden", False)),
                )
                for question_payload in point_payload.get("questions") or []:
                    point.questions.append(
                        Question(
                            stem=question_payload.get("stem", ""),
                            question_type=question_payload.get("question_type", "单选"),
                            difficulty=question_payload.get("difficulty", "一般"),
                            options=list(question_payload.get("options") or []),
                            answer=question_payload.get("answer", "A"),
                            confidence=float(question_payload.get("confidence", 1.0) or 0.0),
                            rationale=question_payload.get("rationale", ""),
                            reviewed=bool(question_payload.get("reviewed", False)),
                            internal_id=question_payload.get("internal_id", ""),
                            skipped=bool(question_payload.get("skipped", False)),
                        )
                    )
                chapter.knowledge_points.append(point)
            draft.chapters.append(chapter)

        draft.renumber()
        return draft

    # ------------------------------------------------------------ 便捷访问
    @property
    def total_questions(self) -> int:
        return sum(
            point.question_count
            for chapter in self.chapters
            for point in chapter.knowledge_points
        )

    @property
    def all_points(self) -> list[KnowledgePoint]:
        return [point for chapter in self.chapters for point in chapter.knowledge_points]

    def renumber(self) -> None:
        for chapter_index, chapter in enumerate(self.chapters, start=1):
            chapter.renumber(chapter_index)

    def find_point(self, chapter_order: int, point_order: int) -> KnowledgePoint | None:
        for point in self.all_points:
            if point.chapter_order == chapter_order and point.order == point_order:
                return point
        return None


def ratio_from_counts(
    counts: dict[str, Any],
    *,
    active_keys: Iterable[str] | None = None,
) -> dict[str, int]:
    """
    把题型题数换算成整数比例（合计 100），用于「按比例」视图回显。

    同样用最大余数法，保证有效题型占比合计恰好 100；
    题数全为 0 时返回全 0（视图层负责提示）。
    """
    values = {key: max(int(counts.get(key, 0) or 0), 0) for key in counts}
    keys = list(active_keys) if active_keys is not None else [
        key for key, value in values.items() if value > 0
    ]
    if not keys:
        return {key: 0 for key in values}

    shares = allocate_by_largest_remainder(100, {key: values.get(key, 0) for key in keys})
    return {key: shares.get(key, 0) for key in values}


def allocate_with_floor(
    total: int,
    weights: dict[str, Any],
    *,
    floor: int = 1,
) -> dict[str, int]:
    """
    题型题数分配（FR4.3 + FR4.5）。

    优先**纯最大余数法**（题量充足时就是比例的直接换算，例如 10 题 / 70-20-10 → 7/2/1）；
    只有当某个**勾选题型**因此拿到 0 题时（例如总题数 3、70-20-10 会得到 2/1/0），
    才降级为「每个勾选题型先保底 ``floor`` 个，剩余名额再按比例分配」。

    当总题数连保底都不够时（``total < 勾选题型数``），回退到纯最大余数分配，
    由 WizardValidator 报「题数不足以覆盖已选题型」阻断。
    """
    keys = list(weights)
    counts = {key: 0 for key in keys}
    if not keys:
        return counts

    total = max(int(total or 0), 0)
    positive = {key: max(int(weights.get(key, 0) or 0), 0) for key in keys}
    selected = [key for key in keys if positive[key] > 0]
    if not selected or total <= 0:
        return counts

    plain = allocate_by_largest_remainder(total, positive)
    if all(plain.get(key, 0) > 0 for key in selected):
        return plain

    floor = max(int(floor or 0), 0)
    if floor <= 0 or total < len(selected) * floor:
        return plain

    rest = total - len(selected) * floor
    extra = allocate_by_largest_remainder(rest, {key: positive[key] for key in selected})
    for key in selected:
        counts[key] = floor + extra.get(key, 0)
    return counts


def allocate_by_largest_remainder(total: int, weights: dict[str, Any]) -> dict[str, int]:
    """
    最大余数法分配题数，保证各项之和 **恰好等于** ``total``。

    - 权重非正的项直接得 0 且不参与分配；
    - 权重全为 0 或没有可分配项时，返回全 0（调用方负责提示）；
    - 余数相同者按 key 名升序稳定分配，保证结果可复现。

    Args:
        total: 总题数（负数按 0 处理）
        weights: {名称: 权重}

    Returns:
        {名称: 分配到的题数}，与 weights 同键集
    """
    total = max(int(total or 0), 0)
    keys = list(weights)
    counts = {key: 0 for key in keys}

    positive = {key: max(int(weights.get(key, 0) or 0), 0) for key in keys}
    weight_sum = sum(positive.values())
    if total <= 0 or weight_sum <= 0:
        return counts

    quotas = {key: total * value / weight_sum for key, value in positive.items()}
    for key, quota in quotas.items():
        counts[key] = int(quota)

    assigned = sum(counts.values())
    remainder = total - assigned
    if remainder > 0:
        order = sorted(keys, key=lambda key: (-(quotas[key] - counts[key]), key))
        for key in order[:remainder]:
            counts[key] += 1

    return counts
