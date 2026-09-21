# 评估出题助手 UX 修复计划

## Context
用户实际使用 `plugins/evaluation/` 评估出题助手时发现：第一步测试连接点击后缺少可靠反馈；第二步仍显示 Excel 导入；第三、四步全局卡片右侧留白且不自适应；AI 建议考点点击无运行状态；第五步 AI 生成弹窗长期停在 0% 且日志/进度条不刷新；第六步审核缺少批量确认，题目只显示答案未显示选项。

目标是在保留现有六步向导、真实 AI 请求、澄清/取消/导出逻辑的前提下，补齐反馈、响应式布局和审核效率。

## Approach
1. 在 `EvaluationView` 中为测试连接、AI 建议考点和生成任务增加明确的开始中/成功/失败状态，防止重复点击，并保证 UI 更新通过 Flet 事件循环线程执行。
2. 移除 Step2 的 Excel 导入入口及相关提示文案；保留文本批量添加和手动新增知识点。
3. 将 Step3/Step4 全局设置区域改成可占满父容器的自适应布局，避免固定宽度控件把内容挤在左侧后产生大片空白，并兼容窄窗口换行。
4. 复用 `AnswerProgressDialog.update_progress()` / `append_log()`，把生成控制器的知识点开始、题目完成、日志回调安全地调度到页面线程，确保百分比、计数、日志真实变化。
5. 在 Step6 增加批量确认入口，并在每道题下渲染 `Question.options` 与正确答案标识；继续保留单题勾选、编辑、重生成和现有导出拦截规则。
6. 为以上行为补充视图和核心回归测试，优先使用现有 FakePage、Stub AI 客户端和领域层方法，不引入新依赖。

## Files to modify
- `plugins/evaluation/view.py`：步骤二入口/文案、步骤三/四布局、AI 操作状态、生成进度调度、Step6 批量审核和选项渲染。
- `src/ui/components.py`：必要时修正 `run_background_task` 的完成/异常回调线程调度；确保不破坏现有插件调用方。
- `plugins/evaluation/review.py`：如视图需要批量审核领域操作，复用或补充 `mark_point_reviewed`/批量统计边界。
- `tests/test_evaluation_view.py`：连接测试、建议考点状态、生成进度刷新、Step2 无 Excel、批量确认、选项显示和布局约束测试。
- `tests/test_evaluation_core.py`：仅在新增/调整批量审核领域行为时补充纯逻辑测试。

## Reuse
- `plugins/evaluation/view.py::_test_ai_connection`：复用现有 `StructuredAIClient.test_connection()`，补充忙碌态和事件循环线程反馈。
- `plugins/evaluation/view.py::_suggest_tags`：复用现有 `complete_json()`、`build_tag_suggestion_prompt()` 和 `parse_tag_suggestion()`，增加运行提示/禁用状态/异常反馈。
- `plugins/evaluation/generator.py::GenerationController.progress`、`on_point_start`、`on_point_done`：使用现有逐知识点进度语义，避免重写生成循环。
- `src/ui/components.py::AnswerProgressDialog.update_progress`、`append_log`：统一更新进度条、百分比、计数和日志，避免直接操作内部控件。
- `src/ui/components.py::run_background_task`：作为后台工作入口；需要确认完成和错误回调都在页面线程调度后再让视图重建和弹窗。
- `plugins/evaluation/models.py::Question.options`、`answer_letters`：直接渲染已有选项数据和答案字母，不修改生成数据格式。
- `plugins/evaluation/review.py::mark_point_reviewed`、`review_summary`、`ready_for_export`：批量确认后继续由现有审核汇总和导出阻断逻辑判断状态。

## Steps
- [x] 明确批量确认范围和反馈交互决策：仅作用于当前展开的知识点；提供批量确认与取消全部确认；连接测试和 AI 建议考点使用 SnackBar + 按钮禁用/运行中文字样。
- [x] 修正 Step1 测试连接与 Step3 AI 建议考点的忙碌、成功、失败状态和事件循环更新。
- [x] 移除 Step2 Excel 导入按钮、文案和无用导入调用，保留文本批量添加。
- [x] 重排 Step3 全局填写与 Step4 全局默认卡片，使控件按可用宽度伸展并在窄窗口换行。
- [x] 修正 AI 生成进度与日志更新链路，覆盖知识点开始/完成、异常、取消和弹窗关闭。
- [x] 在 Step6 增加批量确认/取消确认能力，并显示每道题选项、选中答案标识和缺失选项的兼容提示。
- [x] 补充回归测试并运行评估插件核心与视图测试。

## Verification
- 运行 `python -m unittest tests.test_evaluation_core tests.test_evaluation_view`。
- 使用 FakePage 验证后台任务完成/失败回调通过 `run_task` 执行，且不会在 worker 线程直接重建控件或弹窗。
- 手动打开 GUI：测试连接时立即出现“正在测试”反馈，成功/失败均有结果；AI 建议考点显示运行中并在完成后展示候选。
- 手动检查 Step2 不再出现 Excel 导入；Step3/Step4 在宽窗口占满可用区域，在窄窗口自然换行且不溢出。
- 手动生成多知识点题目：进度百分比、`当前/总数`、日志内容随生成变化，取消后状态正确恢复。
- 手动进入 Step6：可以一键确认当前审核范围，题目显示全部选项并标识正确答案；单题审核、导出阻断和重生成行为保持正常。

## Confirmed Decisions
- Step6 批量确认范围为当前展开的知识点；未展开的知识点不受影响。
- Step6 同时提供“批量确认”和“取消全部确认”，两者都只作用于当前展开的知识点。
- 测试连接和 AI 建议考点启动时显示 SnackBar，并将按钮禁用且文字改为“测试中…”/“建议中…”；完成或失败后恢复按钮并显示结果。
