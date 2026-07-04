"""
懒狗一键评分 — 评分算法与批语模板管理

三档严格度：
  HIGH（严格）：75 ~ 90
  MEDIUM（中等）：70 ~ 95
  LOW（宽松）：65 ~ 100

系统硬规则（所有档位均遵守）：
  截图 <3 且 字数 <150        → 不能超过 60
  截图 ≥3 或 字数 ≥150        → 可达 60+
  截图 ≥6 或 字数 ≥400        → 可达 80+
  截图 >9 或 字数 >500        → 可达 90+
  附件为空 → 有额外上限
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

STRICTNESS_CONFIG = {
    "high": {
        "label": "严格",
        "floor": 70,
        "no_att_cap": 80,
        "tier1": (70, 80),
        "tier2": (80, 85),
        "tier3": (85, 90),
    },
    "medium": {
        "label": "中等",
        "floor": 70,
        "no_att_cap": 85,
        "tier1": (70, 80),
        "tier2": (80, 88),
        "tier3": (85, 95),
    },
    "low": {
        "label": "宽松",
        "floor": 70,
        "no_att_cap": 90,
        "tier1": (70, 80),
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
    """综合质量因子 0.0 ~ 1.0。"""
    factors: list[float] = []
    factors.append(min(screenshot_count / 10.0, 1.0))
    factors.append(min(desc_char_count / 600.0, 1.0))

    if log_stage_count == 0:
        factors.append(0.0)
    elif log_stage_count < 3:
        # 一把梭哈：阶段不足3个，直接给极低分
        factors.append(0.08)
    else:
        # 3个阶段以上才正常评估
        stage_score = min(log_stage_count / 5.0, 1.0)
        avg = log_total_chars / log_stage_count
        if avg < 30:
            per_quality = 0.2
        elif avg < 80:
            per_quality = 0.6
        elif avg <= 350:
            per_quality = 1.0
        elif avg <= 500:
            per_quality = 0.8
        else:
            per_quality = 0.5
        factors.append(stage_score * per_quality)

    quality = sum(factors) / len(factors) if factors else 0.0

    # 阶段不足3个时，额外打折（不论其他维度多好）
    if log_stage_count < 3:
        quality *= 0.45

    return quality


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

    # ── 不满足最低要求 → 固定 70（无论严格度） ──
    meets_minimum = (screenshot_count >= 3) or (desc_char_count >= 150)
    if not meets_minimum:
        return 70

    quality = _quality_factor(
        screenshot_count, desc_char_count, log_stage_count, log_total_chars
    )

    if not has_attachment:
        floor = cfg["floor"]
        cap = cfg["no_att_cap"]
        return int(floor + quality * (cap - floor))

    can_90_plus = (screenshot_count > 9) or (desc_char_count > 500)
    can_80_plus = (screenshot_count >= 6) or (desc_char_count >= 400)

    if can_90_plus:
        low, high = cfg["tier3"]
    elif can_80_plus:
        low, high = cfg["tier2"]
    else:
        low, high = cfg["tier1"]

    score = max(low, min(high, int(low + quality * (high - low))))

    # 阶段不足3个 → 不能进入最高分段（tier3），上限卡死到 tier2 顶部
    if log_stage_count < 3:
        score = min(score, cfg["tier2"][1])

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
