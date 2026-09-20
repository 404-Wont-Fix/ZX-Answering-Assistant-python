"""真实 AI 连通性 + 端到端出题验证（只读配置，不打印密钥）。

用途：用教师在插件设置里配置好的真实 AI，跑一遍「配置读取 → 连通性 → 出题 →
校验 → 逐题审核 → 导出 zip → 按平台格式回读核对」的完整链路。

用法：
    python scripts/e2e_evaluation_real_ai.py [知识点数] [每知识点题数]
    python scripts/e2e_evaluation_real_ai.py 2 5      # 2 个知识点 × 5 题

前置：已在「插件中心 → 评估出题助手 → 齿轮」里填好 AI API Key；
导出 Word 需要 python-docx（见 plugins/evaluation/requirements.txt）。

产物落在 output/evaluation/（zip 与 _e2e_extracted/ 解出的单文件）。
"""

import json
import os
import sys
import time
import zipfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugins"))
sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from plugins.evaluation.ai_client import StructuredAIClient
from plugins.evaluation.exporter import EvaluationExporter
from plugins.evaluation.generator import GenerationController
from plugins.evaluation.models import (
    Chapter,
    CourseDraft,
    KnowledgePoint,
    Question,
)
from plugins.evaluation.review import (
    assign_internal_ids,
    mark_reviewed,
    ready_for_export,
    review_summary,
)
from plugins.evaluation.validators import validate_question
from plugins.evaluation.clarification import ClarificationQueue
from plugins.evaluation.template_manager import TemplateManager
from src.core.config import SettingsManager

PLUGIN_ID = "evaluation"


def load_config() -> dict:
    manager = SettingsManager()
    cfg = {
        key: manager.get_plugin_config(PLUGIN_ID, key)
        for key in ("api_key", "base_url", "model", "exa_mcp_url", "exa_api_key")
    }
    return cfg


def banner(text: str) -> None:
    print("\n" + "=" * 72)
    print(text)
    print("=" * 72)


def main() -> int:
    point_count = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    per_point = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    banner("① 读取真实配置")
    cfg = load_config()
    print(f"   base_url = {cfg.get('base_url')}")
    print(f"   model    = {cfg.get('model')}")
    print(f"   api_key  = {'已配置' if cfg.get('api_key') else '缺失'}"
          f" (len={len(cfg.get('api_key') or '')})")
    print(f"   exa_mcp  = {cfg.get('exa_mcp_url') or '(空 → 联网检索关闭)'}")

    client = StructuredAIClient(cfg, logger=lambda m: print(f"   [ai] {m}"))
    client.ensure_configured()

    banner("② AI 连通性测试（最小 JSON 请求）")
    started = time.time()
    try:
        probe = client.complete_json(
            system="你是JSON接口，只输出JSON。",
            user='输出严格 JSON：{"ok": true, "echo": "ping"}',
            retries=1,
            timeout=(10, 60),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"   ✖ 连通失败：{type(exc).__name__}: {exc}")
        return 2
    print(f"   ✔ 连通成功（{time.time() - started:.1f}s）→ {probe}")

    banner("③ 构造真实课程草稿")
    draft = CourseDraft(
        course_name="CorelDraw",
        target="24级大数据技术1班",
        tool_version="CorelDraw X4",
        online_search=False,
        review_mode="逐题",
        generation_status="running",
    )
    chapter = Chapter(name="CorelDraw界面介绍")
    chapter.knowledge_points = [
        KnowledgePoint(
            name="CorelDraw窗口界面",
            chapter_name=chapter.name,
            tags=["窗口组成", "工具栏", "属性栏", "标尺与网格"],
            level="对口",
            knowledge_type="了解",
        ),
        KnowledgePoint(
            name="文件基本操作",
            chapter_name=chapter.name,
            tags=["新建与打开", "保存与另存", "导入导出"],
            level="高质量",
            knowledge_type="掌握",
        ),
    ][:point_count]

    for point in chapter.knowledge_points:
        point.set_type_ratio({"单选": 70, "多选": 20, "判断": 10})
        point.set_question_count(per_point)
    draft.chapters = [chapter]
    draft.renumber()

    for point in draft.all_points:
        print(f"   {point.chapter_order}-{point.order} {point.name}"
              f" | 考点 {point.effective_tags} | {point.question_count} 题"
              f" → {point.type_counts}")

    banner("④ 真实调用 AI 出题（逐知识点）")
    queue = ClarificationQueue(
        sensitivity=draft.sensitivity,
        on_record=lambda record: draft.clarification_records.append(record),
    )
    controller = GenerationController(
        client, None, queue, logger=lambda m: print(f"   [gen] {m}")
    )

    pending_dialogs: list = []

    def on_clarification(clarification):
        # 无人值守：自动选择推荐项，等价于教师点「确认并继续」
        choice = clarification.recommended or (clarification.options or ["由AI自行决定"])[0]
        print(f"   [澄清] {clarification.level} / {clarification.kind} → 自动选：{choice}")
        queue.answer(clarification, choice, apply_to_kind=True)

    started = time.time()
    result = controller.run(
        draft,
        on_point_start=lambda p: print(f"   → 开始：{p.name}"),
        on_point_done=lambda p, qs: print(f"   ✔ 完成：{p.name}（{len(qs)} 题）"),
        on_clarification=on_clarification,
    )
    elapsed = time.time() - started
    draft.generation_status = "cancelled" if result["cancelled"] else "complete"
    print(f"   用时 {elapsed:.1f}s | 结果 {result}")

    banner("⑤ 校验生成结果（FR6.9 + 题型/难度配比）")
    assign_internal_ids(draft)
    total = 0
    for point in draft.all_points:
        print(f"   {point.name}：{len(point.questions)} 题 → {point.active_types}")
        for index, question in enumerate(point.questions, start=1):
            total += 1
            problems = validate_question(question)
            flag = "OK " if not problems else "!! "
            print(f"     {flag}{question.internal_id:>9} [{question.question_type}/{question.difficulty}]"
                  f" 答案={question.answer} 置信度={question.confidence:.2f}")
            print(f"          {question.stem}")
            for option_index, option in enumerate(question.options):
                print(f"            {'ABCDEFGH'[option_index]}. {option}")
            if problems:
                print(f"          ⚠ 校验问题：{'；'.join(problems)}")
    print(f"   合计 {total} 题")

    banner("⑥ 逐题审核 + 导出（Word + Excel → zip）")
    for question in [q for p in draft.all_points for q in p.questions]:
        mark_reviewed(question, True)
    summary = review_summary(draft)
    for line in summary.as_lines():
        print("   " + line)

    ok, blockers = ready_for_export(draft)
    print(f"   ready_for_export = {ok}")
    for blocker in blockers:
        print(f"     ✖ {blocker}")
    if not ok:
        return 3

    exporter = EvaluationExporter(TemplateManager(ROOT / "plugins" / "evaluation"))
    date_text = time.strftime("%Y%m%d")
    name, data = exporter.export_zip(draft, date_text=date_text)
    out_dir = ROOT / "output" / "evaluation"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / name).write_bytes(data)
    print(f"   zip = {name} ({len(data)} bytes)")
    print(f"   路径 = {out_dir / name}")

    banner("⑦ 产物核对（解出后按平台格式回读）")
    from plugins.evaluation import importers

    archive = zipfile.ZipFile(BytesIO(data))
    print("   包内条目：")
    for entry in archive.namelist():
        print(f"     - {entry}")

    extracted = out_dir / "_e2e_extracted"
    extracted.mkdir(parents=True, exist_ok=True)
    for entry in archive.namelist():
        (extracted / entry).write_bytes(archive.read(entry))

    for entry in sorted(archive.namelist()):
        path = extracted / entry
        parsed = importers.import_question_examples(path)
        print(f"   {entry.split('.')[-1]}: 回读 {len(parsed)} 题")
        for item in parsed:
            print(f"     [{item['type']}/{item['difficulty']}] 答案={item['answer']}"
                  f" 选项={len(item['options'])} | {item['stem'][:40]}")

    print("\n完成。zip：", out_dir / name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
