# 评估出题插件问题分析计划

## Context
- 用户反馈 `plugins/evaluation/` 评估出题插件在第五个流程“AI生成”时没有真正触发 AI。
- 页面上的相关 AI 按钮也不可用，怀疑当前实现只是界面壳子。
- 产品要求：移除第一步上传考纲/大纲/样例题库等参考材料的功能；出题不读取本地参考资料，最多使用联网搜索作为可选辅助。
- 当前仅进行只读分析，不修改业务代码。

## Approach
- 梳理 manifest、入口、视图/组件和六步流程状态机，重新定义为不依赖本地参考材料的流程。
- 删除上传考纲/大纲/样例题库及“AI 提取候选”功能链路，确保这些材料不会进入提示词或生成器。
- 保留联网搜索作为可选辅助，仅在用户开启且模型判断知识点不确定时使用，不把搜索失败当成生成失败。
- 追踪剩余 AI 按钮事件从 UI 到 `ai_client.py` 的完整调用链，确认不存在未绑定、空实现、配置缺失或异常被吞掉。
- 对照项目现有配置、日志、后台任务和 Flet 事件处理模式，形成带文件/行号证据的问题结论。
- 将问题区分为“当前设计要求用户自行配置 API Key”与“真实运行中的可用性/反馈缺陷”，后续按优先级修复。

## Files to modify
- `plugins/evaluation/view.py`：移除第一步参考材料上传控件及“AI 提取候选”按钮/逻辑；在插件页面提供明确的 AI 设置/连接测试入口；统一剩余 AI 按钮的禁用、忙碌、成功/失败反馈；修正第五步生成生命周期和 UI 线程回调。
- `plugins/evaluation/manifest.json`：清理不再使用的本地参考材料相关声明（如存在），明确联网搜索为可选配置。
- `plugins/evaluation/ai_client.py`：必要时补充连接测试方法和更明确的 provider/响应格式错误信息，保持真实请求链路。
- `src/ui/components.py`：必要时修正通用后台任务的完成/失败回调调度，避免 worker 线程直接更新 Flet 控件；需要兼顾现有插件调用方。
- `tests/test_evaluation_view.py`：补充 AI 按钮、配置读取、连接测试、生成触发和失败反馈回归测试。
- `tests/test_evaluation_core.py`：补充客户端连接测试/响应兼容性测试（仅在实现需要时）。
- 当前阶段仅修改 `PLAN.md`，未修改上述实现文件。

## Reuse
- `plugins/evaluation/ai_client.py` 的 `StructuredAIClient.complete_json()` / `generate()`：真实 OpenAI 兼容 `/chat/completions` 请求，不能用假数据替代。
- `plugins/evaluation/generator.py` 的 `GenerationController.run()`：逐知识点生成、澄清、取消和进度语义。
- `src/core/plugin_context.py` 与 `src/core/config.py`：插件配置持久化和读取。
- `src/ui/components.py` 的 `build_plugin_settings_dialog()`、`run_background_task()`、`AnswerProgressDialog`：统一设置、后台任务和进度反馈。

## Steps
- [x] 读取插件入口、五步流程和 AI 相关模块：入口为 `plugins/evaluation/ui.py`，六步实际由 `plugins/evaluation/view.py` 编排。
- [x] 检查 AI 配置来源、客户端请求和错误传播：`ai_client.py` 存在真实请求；API Key 缺失会被 `_require_ai_config()` 拦截，且默认没有 Key。
- [x] 检查 AI 按钮及第五步事件绑定、线程/异步调用：AI 提取、AI 建议、开始生成均有回调并最终调用客户端；`run_background_task()` 的回调线程边界需要修正/验证；本地参考材料链路将删除。
- [x] 对照测试、依赖和运行配置：已有核心/视图测试和 Stub HTTP，但没有真实 UI 配置入口、连接测试及真实 provider 兼容性回归。
- [x] 补充根因、修复文件范围和端到端验证步骤。
- [x] 纳入产品调整：删除本地参考材料输入与 AI 提取候选功能，仅保留可选联网搜索。
- [x] 计划获批后实施修复并运行回归测试。

## Verification
- 当前分析结论：
  - 移除 `AI 提取候选`：`view.py::_extract_candidates` 及第一步考纲/样例题库上传控件不再保留；本地参考材料不得进入提示词。
  - `AI 建议考点`：若保留，改为仅依据课程名、章节名、知识点名和可选联网搜索，不读取上传材料。
  - 第五步：`view.py::_start_generation` → `GenerationController.run()` → `generate_point()` → `StructuredAIClient.generate()` → `/chat/completions`，不是空壳。
  - 主要可用性问题：API Key 是强制必填且默认空；插件页面本身没有设置按钮，配置入口依赖插件中心的设置齿轮或缺 Key 弹窗；没有独立“测试连接”按钮；`run_background_task()` 在 `page.run_thread()` 的 worker 中直接执行 `on_done/on_error`，而这些回调会 `_render()`、`show_snack()`、弹窗和保存，线程边界不稳，FakePage 测试无法暴露真实 Flet 的线程问题。
- 修复阶段（计划获批后）：
  1. 先从第一步和数据模型/提示词链路移除本地考纲、样例题库上传及 AI 提取候选功能，保证无参考材料依赖；
  2. 保留并明确联网搜索为可选辅助，搜索失败时继续使用模型自有知识出题；
  3. 修通用后台任务回调调度，并确保异常不会静默；
  4. 在评估插件页面增加可达的 AI 设置/连接测试入口，连接测试复用同一配置和真实客户端；
  5. 为剩余 AI 操作增加明确的状态/错误反馈，避免重复点击和“按钮无反应”；
  6. 验证第五步从按钮到 `/chat/completions` 的真实调用，保留逐知识点生成、澄清和取消语义。
- 运行 `python -m unittest tests.test_evaluation_core tests.test_evaluation_view` 或仓库对应测试命令；用 Stub 验证每个按钮实际发出请求；GUI 手动验证配置保存、连接测试、第五步开始/暂停/取消、失败提示、结果进入第六步和真实输出。
