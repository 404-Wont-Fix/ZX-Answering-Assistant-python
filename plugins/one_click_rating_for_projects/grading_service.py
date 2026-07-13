"""评分编排服务（纯业务，无 UI 依赖）。

从 LazyAIGradingView._grading_inner 抽出，封装"分析→分布→提交"三阶段流程。
依赖 api_client（HTTP）、scoring（评分算法/批语选取器），均为纯业务模块，可独立单测。
"""

from typing import Callable, Optional

from .scoring import (
    MINIMUM_NOT_MET_SCORE,
    CommentPicker,
    calculate_score,
    enforce_distribution_limits,
)


class GradingService:
    """评分编排服务（纯业务，无 UI 依赖）。

    对每个 (label, targets) 分组独立执行 分析→分布→提交；分布上限按项目分别应用。
    stats 跨分组累加。进度通过 on_progress 文案回调通知（已是抽象，不耦合 UI）。
    """

    def __init__(self, api_client):
        self.api_client = api_client

    def grade_groups(
        self,
        groups,
        *,
        strictness: str,
        comment_picker: CommentPicker,
        on_progress: Optional[Callable[[str], None]] = None,
        stats: Optional[dict] = None,
    ) -> dict:
        """对每个 (label, targets) 分组执行 分析→分布→提交，stats 跨分组累加。

        Args:
            groups: [(label, [ProjectResult, ...]), ...]
            strictness: 严格度 "high"/"medium"/"low"；快照语义，评中途改设置不影响本轮。
            comment_picker: 批语选取器（scoring.CommentPicker）。
            on_progress: 进度文案回调（可选）。
            stats: 统计 dict（传入累加）；None 则自建。

        Returns:
            stats dict: {total, graded, failed, min_score_names, failed_names}
        """
        if stats is None:
            stats = {"total": 0, "graded": 0, "failed": 0,
                     "min_score_names": [], "failed_names": []}
        if on_progress is None:
            on_progress = lambda text: None  # noqa: E731

        needs_distribution = strictness != "high"

        for label, targets in groups:
            if not targets:
                continue
            n = len(targets)

            # ── 阶段一：逐个拉取详情 + 计算分数 ──
            analyzed = []
            for i, student in enumerate(targets, 1):
                name = student.student_name or "未知"
                on_progress(f"{label}：分析 {name}（{i}/{n}）")
                try:
                    detail = self.api_client.get_student_result_with_logs(student.id)
                    student.commit_logs_raw = detail.get("commitLogs") or []
                    score = calculate_score(
                        screenshot_count=student.screenshot_count,
                        desc_char_count=student.desc_char_count,
                        has_attachment=student.has_attachment,
                        log_stage_count=student.log_stage_count,
                        log_total_chars=student.log_total_chars,
                        strictness=strictness,
                    )
                    analyzed.append({"student": student, "score": score})
                except Exception as ex:
                    stats["failed"] += 1
                    stats["failed_names"].append(f"{label} - {name}（{ex}）")

            # ── 阶段二：应用分布限制（按本项目独立，中等/宽松档） ──
            if needs_distribution and analyzed:
                on_progress(f"{label}：调整分数分布...")
                analyzed = enforce_distribution_limits(analyzed)

            # ── 阶段三：逐个提交评分 ──
            m = len(analyzed)
            for i, item in enumerate(analyzed, 1):
                student = item["student"]
                score = item["score"]
                name = student.student_name or "未知"
                on_progress(f"{label}：提交 {name}（{i}/{m}）")
                try:
                    min_len = 100 if score >= 95 else 20 if score >= 80 else 0
                    comment = comment_picker.next(min_len=min_len)
                    self.api_client.audit_result(
                        rid=student.id,
                        pro_score=str(score),
                        review_comments=comment,
                    )
                    student.pro_score = score
                    student.review_comments = comment

                    stats["graded"] += 1
                    if score == MINIMUM_NOT_MET_SCORE:
                        stats["min_score_names"].append(f"{label} - {name}")
                except Exception as ex:
                    stats["failed"] += 1
                    stats["failed_names"].append(f"{label} - {name}（{ex}）")

        return stats
