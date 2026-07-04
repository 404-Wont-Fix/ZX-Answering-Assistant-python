"""
懒狗一键评分 — 评分算法与批语模板管理

评分范围：75 ~ 90
  截图 <3 且 字数 <150     → 75（保底）
  满足最低，无附件          → 75 ~ 80
  满足最低，有附件          → 80 ~ 82
  截图 ≥6 或 字 ≥400，有附件 → 80 ~ 84
  截图 ≥9 或 字 ≥500，有附件 → 85 ~ 90

段内微调由 _quality_factor 综合截图数、心得字数、日志阶段数/质量决定。
"""

import json
import os
import random
from pathlib import Path
from typing import List

# ────────────────────────────────────────────────
# 批语模板持久化
# ────────────────────────────────────────────────

_TEMPLATES_FILE = Path(__file__).parent / "comment_templates.json"

_DEFAULT_TEMPLATES: List[str] = [
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


def load_templates() -> List[str]:
    """从 JSON 文件加载批语模板；文件不存在则用默认模板初始化。"""
    if _TEMPLATES_FILE.exists():
        try:
            with open(_TEMPLATES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                return data
        except (json.JSONDecodeError, OSError):
            pass
    # 兜底：写入默认模板
    save_templates(_DEFAULT_TEMPLATES)
    return list(_DEFAULT_TEMPLATES)


def save_templates(templates: List[str]) -> None:
    """将批语模板列表写入 JSON 文件。"""
    with open(_TEMPLATES_FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f, ensure_ascii=False, indent=2)


class CommentPicker:
    """循环选取批语的辅助类（实例存活于一次评分会话内）。"""

    def __init__(self):
        self._templates: List[str] = load_templates()
        self._index: int = 0
        # 用 shuffle 打乱顺序，避免每轮完全相同
        random.shuffle(self._templates)

    def reload(self) -> None:
        """用户在设置界面修改后重新加载。"""
        self._templates = load_templates()
        random.shuffle(self._templates)
        self._index = 0

    def next(self, min_len: int = 0) -> str:
        """
        取下一条批语。

        Args:
            min_len: 最低字数要求（80+ 分 ≥20）。若当前模板不足则拼接补齐。
        """
        if not self._templates:
            return "项目实训已完成，基本符合要求。阅"
        tpl = self._templates[self._index % len(self._templates)]
        self._index += 1
        # 确保满足最低字数
        if min_len > 0 and len(tpl) < min_len:
            tpl = tpl + "整体表现值得肯定，望继续努力提升专业技能。"
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
    """
    综合质量因子，返回 0.0 ~ 1.0。
    用于在分段范围内微调具体分数。

    截图和心得字数权重最高；日志阶段数/质量次之。
    """
    factors: list[float] = []

    # 截图因子（10张以上满分）
    factors.append(min(screenshot_count / 10.0, 1.0))

    # 心得字数因子（600字以上满分）
    factors.append(min(desc_char_count / 600.0, 1.0))

    # 日志因子（需综合阶段数 + 每阶段质量）
    if log_stage_count > 0:
        # 阶段数：5段以上满分
        stage_score = min(log_stage_count / 5.0, 1.0)
        # 每阶段平均字数：100~350 为理想区间
        avg = log_total_chars / log_stage_count
        if avg < 30:
            per_quality = 0.2  # 太短，敷衍
        elif avg < 80:
            per_quality = 0.6
        elif avg <= 350:
            per_quality = 1.0  # 理想区间
        elif avg <= 500:
            per_quality = 0.8  # 偏长但可接受
        else:
            per_quality = 0.5  # 太长，可能拉满/抄袭
        factors.append(stage_score * per_quality)
    else:
        factors.append(0.0)

    return sum(factors) / len(factors) if factors else 0.0


def calculate_score(
    screenshot_count: int,
    desc_char_count: int,
    has_attachment: bool,
    log_stage_count: int = 0,
    log_total_chars: int = 0,
) -> int:
    """
    根据评分规则计算最终分数（75 ~ 90）。

    Args:
        screenshot_count: 实际截图数（不含封面）
        desc_char_count: 心得正文纯文字字数
        has_attachment: 是否提交了附件
        log_stage_count: 阶段日志条数（可选，需先调详情接口）
        log_total_chars: 阶段日志总字数（可选）

    Returns:
        75 ~ 90 之间的整数分数
    """
    # ── 不满足最低要求 → 保底 75 ──
    meets_minimum = (screenshot_count >= 3) or (desc_char_count >= 150)
    if not meets_minimum:
        return 75

    quality = _quality_factor(
        screenshot_count, desc_char_count, log_stage_count, log_total_chars
    )

    # ── 无附件：最高卡死 80 ──
    if not has_attachment:
        return int(75 + quality * 5)  # 75 ~ 80

    # ── 有附件，按内容质量分段 ──
    is_excellent = (screenshot_count >= 9) or (desc_char_count >= 500)
    is_good = (screenshot_count >= 6) or (desc_char_count >= 400)

    if is_excellent:
        return min(90, int(85 + quality * 5))  # 85 ~ 90
    elif is_good:
        return min(84, int(80 + quality * 4))  # 80 ~ 84
    else:
        # 满足最低 + 有附件 → 80 起步
        return min(82, int(80 + quality * 2))  # 80 ~ 82
