"""
懒狗一键评分 — 评分算法与批语模板管理

三档严格度（保持 high=严格 / low=宽松 的方向）：
  HIGH（严格）：76 ~ 90
  MEDIUM（中等）：76 ~ 90（中间档更宽松）
  LOW（宽松）：76 ~ 100

保底分规则：
  内容不达标（截图<3 且 字数<150）→ 固定保底 76 分（触发"混子"标注）
  其他情况 → 正常评分（最低 77 分）

酌情扣分（不触发标注，扣完不低于各档 floor 77）：
  无附件            → 扣 5 分
  提交日志不足 3 个 → 扣 3~5 分（0条扣5、1条扣4、2条扣3）

内容最低要求：
  截图 ≥ 3 或 描述字数 ≥ 150

系统硬规则（所有档位均遵守）：
  截图 ≥6 或 字数 ≥400        → 可达中间档
  截图 >9 或 字数 >500        → 可达最高档
  评语 ≥80分 不少于 20 字，≥95分 不少于 100 字
  分布上限：满分≤2人，95+≤7人，90+≤12人
"""

import json
import random
from pathlib import Path
from typing import Dict, List

# ────────────────────────────────────────────────
# 严格度配置
# ────────────────────────────────────────────────

# 不满足最低要求时的保底分；满足最低要求时各档最低 77 分（cfg["floor"]）。
MINIMUM_NOT_MET_SCORE = 76
# 无附件时的酌情扣分（不再用封顶区间压分，改扣固定分，
# 保证"内容质量越好→分数越高"的单调性，避免无附件学生被压进窄区间）。
NO_ATTACHMENT_DEDUCTION = 5

STRICTNESS_CONFIG = {
    "high": {
        "label": "严格",
        "floor": 77,
        "tier1": (77, 80),
        "tier2": (80, 85),
        "tier3": (85, 90),
    },
    "medium": {
        "label": "中等",
        "floor": 77,
        "tier1": (77, 80),
        "tier2": (80, 88),
        "tier3": (85, 90),  # 中档与严格同封顶 90，但 tier2 更宽
    },
    "low": {
        "label": "宽松",
        "floor": 77,
        "tier1": (77, 80),
        "tier2": (80, 92),
        "tier3": (88, 100),
    },
}

# ────────────────────────────────────────────────
# 设置持久化
# ────────────────────────────────────────────────

_SETTINGS_FILE = Path(__file__).parent / "settings.json"


def load_strictness() -> str:
    """加载严格度设置；默认 'high'。"""
    if _SETTINGS_FILE.exists():
        try:
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            val = data.get("strictness", "high")
            return val if val in STRICTNESS_CONFIG else "high"
        except (json.JSONDecodeError, OSError):
            pass
    return "high"


def save_strictness(level: str) -> None:
    """保存严格度设置。"""
    data = {}
    if _SETTINGS_FILE.exists():
        try:
            with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    data["strictness"] = level
    with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ────────────────────────────────────────────────
# 批语模板持久化（short / long 两个池）
# ────────────────────────────────────────────────

_TEMPLATES_FILE = Path(__file__).parent / "comment_templates.json"

_DEFAULT_SHORT: List[str] = [
    "基本的功能完成，与需求文档保持一致，细节上需要完善，基本符合要求。阅",
    "项目完成度较好，主要功能已实现，建议在细节处理上进一步优化完善。阅",
    "实训报告内容详实，操作步骤完整，整体完成质量不错，继续保持。阅",
    "能够按照要求完成项目实训，报告结构清晰，部分环节可进一步完善。阅",
    "项目整体完成情况良好，截图记录完整，建议加深理论分析与总结。阅",
    "实操过程记录详细，思路清晰，整体表现良好，继续保持学习态度。阅",
    "项目实训完成度较高，各环节衔接合理，建议补充更多分析总结内容。阅",
    "基本达到项目实训要求，报告内容较为完整，细节方面仍有提升空间。阅",
    "项目完成情况符合预期，技术操作规范，建议加强对原理的深入理解。阅",
    "实训过程记录较为完整，能够按步骤完成各项任务，整体表现不错。阅",
]

_DEFAULT_LONG: List[str] = [
    "本次项目实训完成质量优秀，报告整体结构完整规范，章节划分合理清晰，技术操作步骤记录详实准确，截图数量充足且关键步骤标注清楚，充分展现了扎实的专业基础知识和较强的实操动手能力，同时报告撰写语言流畅、表述准确，整体表现突出，望在后续学习中继续保持认真严谨的学习态度，不断提升专业技能水平。阅",
    "项目完成情况出色，实训报告撰写认真细致，内容涵盖理论分析与实操验证两大部分，截图记录完整详实且质量较高，阶段日志条理清晰、内容充实丰富，充分展示了良好的专业素养和严谨的实践态度，整体表现优秀，望继续保持这种认真的学习态度，争取更大进步。阅",
    "本次实训报告质量较高，正文内容充实丰富且论述有深度，实操截图完整清晰且质量较高，阶段日志记录详细规范，项目整体完成度好，充分体现了扎实的专业基础和认真负责的学习态度，整体表现突出，望在今后学习中继续发扬这种严谨务实的精神。阅",
    "项目整体完成度很高，实训报告内容详实丰富且分析深入透彻，截图记录完整清晰、关键步骤标注到位，各阶段操作衔接合理流畅，充分体现了扎实的专业功底和良好的综合实践能力，整体表现优秀，望继续努力提升，在后续项目中取得更好的成绩。阅",
    "本次项目实训表现优秀，报告结构严谨、内容充实完整，理论分析与实际操作结合紧密，截图数量充足且质量较高，阶段日志记录认真详细、条理清晰，整体完成质量突出，充分展现了较强的专业能力和良好的学习态度，值得肯定和表扬。阅",
]


def load_templates() -> Dict[str, List[str]]:
    """
    加载批语模板，返回 {'short': [...], 'long': [...]}。
    兼容旧格式（纯列表 → 全部归入 short）。
    """
    if _TEMPLATES_FILE.exists():
        try:
            with open(_TEMPLATES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 新格式
            if isinstance(data, dict) and "short" in data:
                return {
                    "short": data["short"] or list(_DEFAULT_SHORT),
                    "long": data.get("long") or list(_DEFAULT_LONG),
                }
            # 旧格式：纯列表 → 归入 short
            if isinstance(data, list) and data:
                return {"short": data, "long": list(_DEFAULT_LONG)}
        except (json.JSONDecodeError, OSError):
            pass
    default = {"short": list(_DEFAULT_SHORT), "long": list(_DEFAULT_LONG)}
    save_templates(default)
    return default


def save_templates(templates: Dict[str, List[str]]) -> None:
    """将批语模板写入 JSON 文件。"""
    with open(_TEMPLATES_FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)


class CommentPicker:
    """循环选取批语的辅助类（实例存活于一次评分会话内）。"""

    _PAD_TEXTS = [
        "整体表现值得肯定，望继续努力提升专业技能。",
        "在后续学习中要注重理论与实践的结合，不断提升自身的专业素养和实操能力，争取取得更好的成绩。",
        "同时建议加强对项目文档的整理和完善，提高报告的规范性和可读性，养成良好的技术文档撰写习惯。",
    ]

    def __init__(self):
        tpl = load_templates()
        self._short: List[str] = list(tpl["short"])
        self._long: List[str] = list(tpl["long"])
        self._short_idx: int = 0
        self._long_idx: int = 0
        random.shuffle(self._short)
        random.shuffle(self._long)

    def reload(self) -> None:
        """用户在设置界面修改后重新加载。"""
        tpl = load_templates()
        self._short = list(tpl["short"])
        self._long = list(tpl["long"])
        random.shuffle(self._short)
        random.shuffle(self._long)
        self._short_idx = 0
        self._long_idx = 0

    def next(self, min_len: int = 0) -> str:
        """
        取下一条批语。

        min_len >= 100 → 从 long 池取；
        否则 → 从 short 池取，不足时逐段拼接补齐。
        """
        if min_len >= 100 and self._long:
            tpl = self._long[self._long_idx % len(self._long)]
            self._long_idx += 1
            # 安全兜底：万一 long 模板也不够长
            for pad in self._PAD_TEXTS:
                if len(tpl) >= min_len:
                    break
                tpl += pad
            return tpl

        # short 池
        if not self._short:
            return "项目实训已完成，基本符合要求。阅"
        tpl = self._short[self._short_idx % len(self._short)]
        self._short_idx += 1
        if min_len > 0:
            for pad in self._PAD_TEXTS:
                if len(tpl) >= min_len:
                    break
                tpl += pad
        return tpl


# ────────────────────────────────────────────────
# 评分算法
# ────────────────────────────────────────────────


def _quality_factor(
    screenshot_count: int,
    desc_char_count: int,
    log_stage_count: int,
    log_total_chars: int,
) -> float:
    """综合质量因子 0.0 ~ 1.0。

    日志维度按"阶段数 × 阶段均字数质量"连续评估；阶段不足 3 个不再在此处
    一刀切压低（改由 calculate_score 的酌情扣分处理，避免把日志不足直接打成保底）。
    """
    factors: list[float] = []
    factors.append(min(screenshot_count / 10.0, 1.0))
    factors.append(min(desc_char_count / 600.0, 1.0))

    if log_stage_count == 0:
        factors.append(0.2)
    else:
        stage_score = min(log_stage_count / 5.0, 1.0)
        avg = log_total_chars / log_stage_count
        if avg < 30:
            per_quality = 0.3
        elif avg < 80:
            per_quality = 0.6
        else:
            # ≥80 字/阶段即视为认真记录，不再因"写得太详细"反而降权
            per_quality = 1.0
        factors.append(stage_score * per_quality)

    return sum(factors) / len(factors) if factors else 0.0


def meets_minimum_requirement(
    screenshot_count: int,
    desc_char_count: int,
) -> bool:
    """内容最低要求（触发保底76+"混子"标注）：截图 ≥3 或 描述字数 ≥150。

    日志不足3个不再算作不达标，改由 calculate_score 酌情扣分。
    """
    return (screenshot_count >= 3) or (desc_char_count >= 150)


def calculate_score(
    screenshot_count: int,
    desc_char_count: int,
    has_attachment: bool,
    log_stage_count: int = 0,
    log_total_chars: int = 0,
    strictness: str = "high",
) -> int:
    """
    根据评分规则和严格度计算最终分数。
    """
    cfg = STRICTNESS_CONFIG.get(strictness, STRICTNESS_CONFIG["high"])

    # ── 内容不达标 → 固定保底 76（触发"混子"标注） ──
    if not meets_minimum_requirement(screenshot_count, desc_char_count):
        return MINIMUM_NOT_MET_SCORE

    quality = _quality_factor(
        screenshot_count, desc_char_count, log_stage_count, log_total_chars
    )

    # 按内容丰富度选档、统一计算基础分（有无附件走同一套区间，保证单调性）
    can_90_plus = (screenshot_count > 9) or (desc_char_count > 500)
    can_80_plus = (screenshot_count >= 6) or (desc_char_count >= 400)
    if can_90_plus:
        low, high = cfg["tier3"]
    elif can_80_plus:
        low, high = cfg["tier2"]
    else:
        low, high = cfg["tier1"]
    score = max(low, min(high, int(low + quality * (high - low))))

    # ── 无附件：酌情扣分（不再用封顶压区间，内容质量仍主导分数） ──
    if not has_attachment:
        score = max(cfg["floor"], score - NO_ATTACHMENT_DEDUCTION)

    # ── 日志不足3个：酌情扣分（不低于各档 floor） ──
    if log_stage_count < 3:
        deduction = 5 - log_stage_count  # 0条→扣5，1条→扣4，2条→扣3
        score = max(cfg["floor"], score - deduction)

    return score


def enforce_distribution_limits(scored_items: list) -> list:
    """
    应用系统分布上限：满分≤2人，95+≤7人，90+≤12人。
    scored_items: [{'student': ..., 'score': int}, ...]，就地修改。
    """
    for item in scored_items:
        s = item["student"]
        item["_q"] = _quality_factor(
            s.screenshot_count, s.desc_char_count,
            s.log_stage_count, s.log_total_chars,
        )
    scored_items.sort(key=lambda x: x["_q"], reverse=True)

    for i, item in enumerate(scored_items):
        if i >= 12:
            item["score"] = min(item["score"], 89)
        elif i >= 7:
            item["score"] = min(item["score"], 94)
        elif i >= 2:
            item["score"] = min(item["score"], 99)
        del item["_q"]

    return scored_items
