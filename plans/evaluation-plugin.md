# 评估出题助手（`plugins/evaluation`）开发计划

> 状态：**v2 — 待评审**（4 个决策点已由用户确认）

## Context

**问题**：`plugins/` 下已有 `evaluation` 插件空壳（`manifest.json` / `__init__.py` / `requirements.txt` / `ui.py`），
但 `ui.py` 导入的 `src/ui/views/evaluation_view.py` 只是一张「敬请期待」占位页；
插件中心「插件管理」卡片上的设置齿轮 `plugin_center_view._on_plugin_settings` 是
`# TODO: 实现插件设置对话框` 空实现。

**目标**：按 PRD v1.0 + v1.1（模板对齐修订）交付**六步向导式 AI 出题**插件，
并顺带补齐一个 **manifest 驱动的通用插件设置组件**（其他插件可零成本复用）。

### 已确认的平台事实（**以实际模板文件为准**）

`kp-question-excel.xlsx` → 工作簿含 `Sheet1 / Sheet2 / Sheet3`（Sheet1 有内容）：

| 行 | 实际内容 |
|---|---|
| R1 | `A1:L1` 合并 = 注意事项 4 行（**保留原文，含 "Eceel" 笔误**） |
| R2 | `A2:D2`=知识点名称 ｜ `E2:H2`=知识点等级（对口、高质量、明星） ｜ `I2:L2`=知识点类型(了解、理解、掌握)；另有空合并区 `N3:Q3` |
| R3 | 上述三值的填写位置 |
| R4 | 13 列表头：`序号｜题目｜难度(简单、一般、困难)｜类型（单选、多选、判断）｜正确答案项｜答案A..答案H`（F..M） |
| R5+ | 数据行（模板自带 3 道示例题 → **导出时不写示例、不写"删除示例"提示行**） |

样式：宋体 11pt；R2 加粗居中；R1 自动换行、行高 75；A 列序号为数字。

`kp-import-template.docx` → **必须用模板做基底克隆段落 XML**，不能从零拼：

| 部位 | 实际结构 |
|---|---|
| 页眉 `word/header1.xml` | `\t\t“{知识点名}”知识点评估题`（加粗 sz21/22） |
| 正文首段 | `知识点{序号}：{知识点名}。【{等级}】【{类型}】`（加粗 sz22=11pt） |
| 题干段 | `numPr(numId=1, ilvl=0)` **自动编号**（不写字面 `1.`）；`spacing before=218(70行) after=62(20行)`；宋体 sz20=10pt |
| 选项段 | `A.xxx`；`ind left=426`、`spacing line=360 auto`、sz20 |
| 答案段 | `答案：【B】` / `答案：【BC】` |
| 页脚 `word/footer1.xml` | `第 {PAGE} 页 共 {NUMPAGES} 页`（真实域代码，非静态文本） |

### 用户已确认的决策

1. **「0 配置模式」= 仅 Exa 联网检索**：默认连 Exa 托管 MCP（`https://mcp.exa.ai/mcp`，免 key 有 IP 限额）；
   额度不足再提示填 `exa_api_key`；检索彻底失败 → 不带检索上下文，**降级为模型自有知识出题**
   （即「降级成模型自己输出」）。AI 主通道的 key 仍由用户在插件设置里填。
2. **AI 通道默认预填 DeepSeek**：`base_url=https://api.deepseek.com/v1`、`model=deepseek-chat`（OpenAI 兼容 `/chat/completions`）。
3. **向导 UI 移入插件**：`plugins/evaluation/view.py`；删除 `src/ui/views/evaluation_view.py`；`ui.py` 改 `from .view import EvaluationView`。
4. **交付 PRD v1.1 全量**（含澄清队列三档、局部暂停、逐题审核+红色阻断、按题数/按比例双视图、模板导出+zip、澄清记录留痕）。

---

## Approach

三层结构：**通用设置组件（进主程序）** → **插件领域层（纯逻辑、可单测）** → **模板驱动导出**。

### A. 通用插件设置组件（用户明确要求，其他插件可复用）

`src/core/plugin_settings.py`
```python
SCHEMA_FIELD_TYPES = ("text", "password", "number", "switch", "select")

def setting_value(schema: dict, stored) -> Any
    # stored is None → schema["default"]；switch→bool；number→int（失败回落 default/0）；其余→str(None→"")

def validate_settings(schema: list[dict], values: dict) -> list[str]
    # 仅校验 required 字段为空 → ["{label}不能为空", ...]
```

`src/ui/components.py` 新增
```python
def build_plugin_settings_dialog(page, plugin_id, plugin_name, schema,
                                 settings_manager, on_saved=None) -> ft.AlertDialog
```
- 按 `schema` 渲染控件：`switch→ft.Switch`、`select→ft.Dropdown(ft.DropdownOption(key,text))`、
  `password→ft.TextField(password=True, can_reveal_password=True)`、
  `number→ft.TextField(keyboard_type=ft.KeyboardType.NUMBER)`、其余 `ft.TextField`。
- 初始值 `setting_value(field, settings_manager.get_plugin_config(plugin_id, field["key"]))`。
- 「保存」→ `validate_settings` 不通过则 `show_snack` 错误并保留弹窗；通过则逐项 `set_plugin_config`，
  关闭弹窗、`on_saved(values)` 回调。
- 「取消」→ `page.pop_dialog()`。

`src/ui/views/plugin_center_view.py::_on_plugin_settings(plugin_id)`
- 读 `plugin_info.path / "manifest.json"` 的 **`settings_schema`** 字段（缺失/空 → `show_snack("该插件没有可配置项", color=GREY_700)` 并返回）；
- 调 `build_plugin_settings_dialog(...)` → `page.show_dialog(dialog)`。

> 效果：以后任何插件只要在 `manifest.json` 里写 `settings_schema`，齿轮自动生效，无需改主程序。

### B. 插件领域层（`plugins/evaluation/`，纯逻辑、无 Flet 依赖）

| 模块 | 关键 API |
|---|---|
| `models.py` | `QUESTION_TYPES=("单选","多选","判断")`、`DIFFICULTIES=("简单","一般","困难")`、`KNOWLEDGE_LEVELS=("对口","高质量","明星")`、`KNOWLEDGE_TYPES=("了解","理解","掌握")`、`TYPE_CODES={"单选":"X","多选":"D","判断":"P"}`；`Question`/`KnowledgePoint`/`Chapter`/`CourseDraft`(dataclass + `to_dict/from_dict` + `total_questions`)；`allocate_by_largest_remainder(total, weights)` |
| `state.py` | `DraftStore(project_root)`（`output/evaluation/draft.json` 落盘/恢复，**带脏标记 + 防抖**）、`WizardValidator.validate_step(draft, step)->list[str]`（§7 六步校验）、`pending_clarifications(draft)`、`apply_global_defaults(draft)` |
| `prompts.py` | `build_system_prompt(course_name, knowledge_context, web_context)`、`QUESTION_SCHEMA`、`build_generation_request(...)->{"system","user","response_schema"}` |
| `ai_client.py` | `StructuredAIClient(config)`（`/chat/completions`, `response_format={"type":"json_object"}`, JSON 解析失败重试）、`HttpMcpSearchClient(config)`（JSON-RPC `tools/call`→`web_search_exa`，**流式读 + SSE 兼容解析**）、`should_search(uncertainty, online_search)` |
| `importers.py` | `import_knowledge_points_xlsx(path)->list[str]`、`import_question_examples(path)->list[dict]`（**仅对齐格式/难度**）；`_import_docx` / `_import_xlsx` 供考纲本地取文本（考纲仅支持 `.docx` / `.xlsx`，PDF 不支持则提示） |
| `clarification.py` | `Clarification(kind, level, chapter, point, question_no, question, basis, options, recommended, choice, scope, status, timestamp)`；`ClarificationQueue`：`add / pending / answer / defer / skip / record`，内建 `resolved_by_kind` 实现「同类都按此处理」 |
| `quality.py` | `duplicate_pairs()`、`answer_distribution_warning()`、`coverage()`、`estimate_cost()` |
| `validators.py` | `validate_question(q)->list[str]`（FR6.9）、`validate_questions(qs)`、`sort_questions(qs)`（题型 单→多→判，题号升序） |
| `exporter.py` | `EvaluationExporter(templates)`：`export_excel → bytes`、`export_word → bytes`、`export_zip(points, course_name, date) → bytes`、`_safe_stem()`（**非法字符 + 保留名清洗**） |
| `template_manager.py` | `TemplateResource(kind, path, source, version)`；`TemplateManager(plugin_dir)`：`get(kind)`、`install_override(kind, path)`、`reset_override(kind)`；内置 `templates/`、覆盖 `template_overrides/` + `metadata.json` |
| `generator.py` | `GenerationController(ai_client, search_client, ...)`：`generate_point(point, request, on_question, on_clarification)`、`pause/resume/cancel`（逐知识点独立挂起） |
| `review.py` | `assign_internal_ids / review_summary / ready_for_export / mark_reviewed / replace_question / append_generated / export_blockers`；`GenerationRun`（`pause/resume/cancel/should_skip/completed`） |

### C. 向导 UI（`plugins/evaluation/view.py`）

顶部步骤节点条（已完成可点击回跳、未到达置灰）＋ 中间操作区 ＋ 底部固定
`［上一步］［下一步／继续生成／导出］`。

- **Step1 课程信息**：课程名称\*、授课对象、软件/工具版本、考纲/大纲/教材目录上传、样例题库上传、联网检索开关（默认关）。
  v1.1 起**无**「课程标签」字段。
- **Step2 章节与知识点**：左章节 / 右知识点主从（`Row` 两栏）；新建/编辑/删除 + **`ft.ReorderableListView` 真拖拽排序**（`on_reorder` 用 `e.old_index/e.new_index`）；
  「未选章节」时右侧置灰提示「请先创建章节」；知识点 Excel 批量导入；［AI 提取候选］（未上传考纲则 `disabled=True`）。
- **Step3 出题详情**：考点 tag 清单（`ft.Chip` + `TextField` 回车添加）、知识点等级（默认对口）、知识点类型（默认了解）、
  特殊要求（placeholder 明示「平台不支持图片题，请描述为文字」）；［AI 建议考点］给 8~10 候选供勾选；
  全局填写栏 + ［应用到全部未填写知识点］；自推考点只读 `ft.ExpansionTile` 折叠区（可展开改）。
  全部未填写时的自推规则 = `课程名 + 章节名 + 知识点名`（§FR3.3），在 Step5 生成前展示并允许改写。
- **Step4 题量与题型**：全局默认区（10 题 / 三题型全开 / 70-20-10 / 难度 20-60-20 / ［应用到全部知识点］）；
  明细 `ft.DataTable` 每行灰标「默认」、被编辑转「已覆盖」高亮 + ［↺］恢复；
  **`ft.SegmentedButton`［按题数｜按比例］** 双向联动，`allocate_by_largest_remainder` 保证合计＝总题数；
  取消题型 → 题数比例归零 + 其余比例归一化；底部实时汇总条（知识点数/总题数/各题型合计）；
  弹窗敏感度（宽松／标准／严格，默认标准）。
- **Step5 AI 生成与澄清**：`AnswerProgressDialog(show_log_panel=True, on_stop=...)` 复用；模态澄清队列（一次一个，右上「澄清 n/m」）；
  进度区［待澄清 n］可随时重开队列；局部暂停（只挂起出问题的知识点）；自决项只记入澄清记录不弹窗；
  队列清空且生成完成 → 自动进 Step6。
  **跨线程握手（见 §H-1）：worker 线程只 `event.wait()`，弹窗生命周期一律由 Flet 事件循环线程经 `page.run_task` 持有。**
- **Step6 结果与导出**：树形列表（课程→章节→知识点，**即导出顺序**）；每知识点 预览/编辑/重生成；
  跳过者灰行 +［补生成］；置信度色标（绿≥0.8／黄0.6~0.8／红<0.6）；逐题审核默认开（红色必须人工确认）；
  ［查看澄清记录］；导出格式多选（Word+Excel 默认全选）；导出 zip。

### D. 澄清弹窗（§5）

结构：级别图标＋标题 → 关联定位（章节/知识点/题号）→ 问题描述 → ［查看依据］`ft.ExpansionTile`
→ 2~4 快捷选项（推荐项高亮 `bgcolor=Palette.PRIMARY_SOFT`）→ 自由输入框
→ `ft.Checkbox("本批次同类问题都按此处理")` → ［由AI自行决定］／［确认并继续］。
关闭(×)= `defer()` 保持挂起（**`event.set()` 也要唤醒 worker，避免线程泄漏**）+ 进度区［待澄清 n］。

敏感度门控（`should_ask(level, sensitivity)`）：

| 敏感度 | 弹窗级别 |
|---|---|
| 宽松 | 仅 `阻断` |
| **标准（默认）** | `阻断` + `确认` |
| 严格 | 全部（含 `自决` 也弹） |

`阻断` 级场景：知识点名称多义/跨领域、教师考点与通用知识冲突、考点数＞总题数、答案不唯一或无正确答案。
「跳过该知识点」→ 标记缺失、结果页灰行［补生成］。
「同类都按此处理」→ 写入 `ClarificationQueue.resolved_by_kind`，同类不再弹窗、复用本次答案。

### E. 导出规范（逐行实现，§10 修订）

**Excel**：`load_workbook(模板)` → **合并区防御性写入（见 §H-3）** 写 `A3/E3/I3`
→ `ws.delete_rows(5, ws.max_row-4)` 清掉模板示例题 → 从 R5 逐行写
`序号(int)｜题目｜难度｜类型｜正确答案项｜答案A..H`；判断固定 `正确/错误`、答案 `A/B`；`Sheet2/Sheet3` 原样保留。
写完必须断言 R4 表头仍是 13 列期望值、R5 起首行 A 列为 `1`（防止 WPS 另存导致的静默错位）。

**Word**：`Document(模板)` → 页眉文本改 `“{知识点名}”知识点评估题` → 首段改
`知识点 {序号}：{知识点名}。【{等级}】【{类型}】` → **节点级 XML 克隆（见 §H-2）** 模板中「题干/选项/答案」
三种段落原型（保住 `numPr`/`ind`/`spacing`/`rFonts 宋体`/`sz`，且不引入新关系）后逐题替换 `w:t` 文本
→ 删除模板残留段落（保留 `sectPr`）。

**命名与排列（固定不可配置）**：
文件名 `{课程名}_{章节序号}_{章节名}_{知识点序号}_{知识点名}.docx/.xlsx`；
zip `{课程名}_评估题库_{日期}.zip`，包内按 章节序→知识点序；
题目排列 题型（单→多→判）→ 题号；题号 `{章}-{知识点}-{题型码}-{序号}`，题型码 `X/D/P`。

**落盘**：先写入 `output/evaluation/`（`output/` 已在 .gitignore），
再用 `ft.FilePicker().save_file(initial_directory=..., file_name=..., src_bytes=zip_bytes)` 提供另存；
用户取消也不丢产物。

### F. 生成约束与提示词（用户强调「题不要太难」）

系统提示词（已锁定文案）：
> 你是一位资深的职业教育教师，正在为学生编制【{course_name}】的课后评估题。
> 核心目标：巩固基础知识、检验常规操作掌握情况。
> 严格禁忌：不要出偏题、怪题、冷门版本特有题、有争议或答案不唯一的题、文字游戏题。
> 错误选项必须来自学生常见的易错点或混淆概念，不能使用荒谬、搞笑或明显凑数的选项。
> 难度定义：简单考查单一概念/界面元素/快捷键；一般考查常规操作流程或工具基本属性；
> 困难考查基础范围内的多步骤综合操作、易混淆概念或常见报错排查，绝不刁钻冷门。
> 题目必须是纯文本。只能依据教师提供的考点 Tag 和通用知识；样例题库只用于对齐格式和难度风格，不得照抄内容。
> 必须严格输出 JSON，不要 Markdown，不要额外解释。答案字母按升序排列。

`QUESTION_SCHEMA` 强约束：`questions[]` 每项 required `stem/type/difficulty/options/answer/confidence/rationale`；
`type ∈ {单选,多选,判断}`、`difficulty ∈ {简单,一般,困难}`、`answer` 正则 `^[A-H]+$`、`confidence ∈ [0,1]`。
**出题依据优先级**：教师考点清单 ＞ 考纲/大纲 ＞ AI 通用知识；样例题库仅作格式参考。

### G. 配置项（写入 `manifest.json` 的 `settings_schema`）

```json
"settings_schema": [
  {"key": "api_key",     "label": "AI API Key",   "type": "password", "default": "", "required": true},
  {"key": "base_url",    "label": "AI Base URL",  "type": "text",     "default": "https://api.deepseek.com/v1", "required": true},
  {"key": "model",       "label": "AI 模型",       "type": "text",     "default": "deepseek-chat", "required": true},
  {"key": "exa_mcp_url", "label": "Exa MCP 地址",  "type": "text",     "default": "https://mcp.exa.ai/mcp", "required": false},
  {"key": "exa_api_key", "label": "Exa API Key（选填，仅额度不足时需要）", "type": "password", "default": "", "required": false}
]
```

AI 调用：key 为空 → Step5 弹「未配置 AI API Key」并直接打开插件设置弹窗（非静默失败）。
Exa 检索：`exa_api_key` 为空 → 用 keyless `https://mcp.exa.ai/mcp`；非空 → URL 追加 `?exaApiKey=...`
（并带 `Authorization: Bearer ...` 兜底）。请求头需含 `Accept: application/json, text/event-stream`，
响应解析见 **§H-5**；任何异常 → 记入澄清记录（自决级）＋ 日志提示「已降级为模型自有知识」，继续生成。

### H. 防御性设计（评审补充，开工前必须落地）

**H-1 澄清弹窗跨线程握手（高风险，防死锁）**
- Step5 生成跑在 `page.run_thread` 的 **worker 线程**，而弹窗必须在 **Flet 事件循环线程**上创建/销毁。
- 协议：`Clarification` 携带 `threading.Event`（**非 `asyncio.Event`**，因为等待方是 OS 线程）：
  1. worker 线程 `queue.add(clar)` → `page.run_task(_show_next_clarification)`（**仅调度，不等待**）→ `clar.wait(timeout=…)`；
  2. `_show_next_clarification` 在事件循环里 `page.show_dialog(...)`；
  3. 用户点「确认并继续/由AI自行决定/跳过/关闭(×)」→ 事件循环里写回 `clar.choice` + `clar.status` → `page.pop_dialog()` + `page.update()` → **最后** `clar.event.set()`；
  4. worker 被唤醒后继续该知识点；`关闭(×)` 走 `defer()`（挂起）也同样 `set()`，避免 worker 永久阻塞。
- **红线**：worker 线程内**绝不**调用 `page.show_dialog / pop_dialog / update`；一切 UI 操作只经 `page.run_task`。
- 暂停/取消时对所有未决 `Clarification` 执行 `cancel` → `set()`，保证线程可退出；`view.cleanup()` 兜底 `set()` 全部事件。

**H-2 Word 节点级 XML 克隆（防关系丢失）**
- 不要 `copy.deepcopy(paragraph)`（`Paragraph` 是轻量包装，且对含隐藏关系的段落易丢 `rId`）。
- 正确做法：先从模板正文取三种段落原型 `proto = { 'stem': p._element, 'option': …, 'answer': … }`；
  生成新段落时 `new_el = copy.deepcopy(proto[kind])`，改写其中的 `w:t`（只保留首个 `w:r` 文本、删多余 run），
  再 `body.append(new_el)`（追加到 `document.element.body`，**在 `sectPr` 之前**）。
- 页眉/页脚同理：直接改 `section.header.paragraphs[0]` 内已有 run 的 `text`，**不新增 run、不改 `rId`**（页脚 PAGE/NUMPAGES 域保持原样）。
- 验收：必须用「含自动编号 + 页眉页脚域 + 宋体 rFonts hint」的真实模板做破坏性测试，并在 **Word 与 WPS 各开一次**确认无「内容有错误」提示、页码域正常显示。

**H-3 Excel 合并单元格防御性写入**
- 写入前检查目标是否真处于合并态：`any(rng.min_row==3 and rng.min_col==1 for rng in ws.merged_cells.ranges)`（E3/I3 同理）；
- 未合并则先 `ws.merge_cells('A3:D3')` 再写；已合并但期望不一致（WPS 另存偏移）则 `unmerge_cells` → `merge_cells` → 写，使状态绝对可控；
- 清除示例行用 `ws.delete_rows(5, max(ws.max_row - 4, 0))` 并做 `if ws.max_row >= 5` 守卫；
- 断言式自检（见 §E）不通过则抛错阻断导出，定位到具体单元格。

**H-4 `DraftStore` 脏标记 + 防抖落盘（性能）**
- `DraftStore` 内部维护 `_dirty: bool` 与 `_last_flush: float`；
- `mark_dirty()` 只置位，不落盘；`flush_if_due(min_interval=2.0, every_n_writes=5)` 满足「距上次 ≥2s」**或**「累计 ≥5 次变更」才真正 `json.dump`（`ensure_ascii=False`、先写 `*.tmp` 再 `os.replace` 保证原子性）；
- **强制落盘**：Step 切换、生成完成/取消/暂停/异常、导出前、`view.cleanup()` 各调一次 `flush(force=True)`；
- 启动时 `load()` 恢复草稿（含 `clarification_records`、`generation_status`）。

**H-5 Exa MCP 流式 + SSE 兼容解析**
- 用 `requests.Session.post(url, json=payload, stream=True, timeout=(5, 60))`（`requests` 已是根依赖，不新增依赖）；
- 按 `Content-Type` 分流：
  - 含 `text/event-stream` → `for line in resp.iter_lines(decode_unicode=True)`，累积 `line.startswith("data:")` 之后的内容，遇空行视为一条消息结束，逐条 `json.loads`；
  - 否则 → `resp.json()`；
- **不要**在 SSE 场景直接调 `.json()`（会抛解析异常）；对 `result.content[*].text` 再 `json.loads` 一次（Exa 把结果序列化成字符串），失败则把原文当纯文本切分；
- 全程 `try/except` 收敛为「无检索结果」返回值，绝不冒泡中断生成。

**H-6 文件系统名清洗（防 `OSError` 中断导出）**
- `_safe_stem(name)`：`re.sub(r'[\\/*?:"<>|]', "_", name)` → 再去首尾空白与 `.` → 折叠连续下划线 → 空则回落 `"evaluation"`；
- 同时处理 Windows 保留名（`CON PRN AUX NUL COM1..9 LPT1..9`，加 `_` 前缀）与路径长度（单段截断到 80 字符，整路径预留余量）；
- **`课程名` / `章节名` / `知识点名` 三处都必须清洗**（zip 内文件名与 `save_file` 的 `file_name` 均用清洗后结果），并保证 `zipfile` 内不出现重复条目（重名自动加 `_2`）。

---

## Files to modify / create

**新增**
- `src/core/plugin_settings.py`
- `plugins/evaluation/models.py`
- `plugins/evaluation/state.py`
- `plugins/evaluation/prompts.py`
- `plugins/evaluation/ai_client.py`
- `plugins/evaluation/importers.py`
- `plugins/evaluation/clarification.py`
- `plugins/evaluation/quality.py`
- `plugins/evaluation/validators.py`
- `plugins/evaluation/exporter.py`
- `plugins/evaluation/template_manager.py`
- `plugins/evaluation/generator.py`
- `plugins/evaluation/review.py`
- `plugins/evaluation/view.py`（六步向导，`EvaluationView`）
- `plugins/evaluation/templates/kp-import-template.docx`（从仓库根拷入）
- `tests/test_evaluation_core.py`
- `tests/test_evaluation_view.py`

**修改**
- `src/ui/components.py`：新增 `build_plugin_settings_dialog`
- `src/ui/views/plugin_center_view.py`：实现 `_on_plugin_settings`
- `plugins/evaluation/manifest.json`：加 `settings_schema`，版本 → `1.0.0`→`1.0.0`（保留），描述更新
- `plugins/evaluation/requirements.txt`：`python-docx>=1.1.0`
- `plugins/evaluation/ui.py`：`from .view import EvaluationView`
- `requirements.txt`：补 `python-docx>=1.1.0`（内置插件运行依赖，PLUGIN_DEV_GUIDE 要求）
- `.gitignore`：加 `!plugins/evaluation/templates/*.xlsx`（否则 `*.xlsx` 会屏蔽模板）
  与 `plugins/evaluation/template_overrides/`

**删除**
- `src/ui/views/evaluation_view.py`（占位页，新位置 `plugins/evaluation/view.py`）

---

## Reuse（复用既有实现，不重复造轮子）

| 需要 | 复用 |
|---|---|
| 卡片/标题/状态胶囊/区块标题 | `src/ui/components.py`：`surface_card / page_heading / status_chip / section_label / workflow_step` |
| 主次按钮 | `primary_button / secondary_button` |
| 提示与确认弹窗 | `show_snack / show_info_dialog / show_error_dialog / show_confirm_dialog / rich_dialog` |
| 生成进度与停止 | `AnswerProgressDialog(page, title, show_log_panel=True, on_stop=...)`（内部用 `page.run_task` 刷新，模态弹窗才不卡） |
| 后台任务 | `run_background_task(page, work_fn, on_done=, on_error=, progress_dialog=)` |
| 配色/圆角/**字体** | `src/ui/theme.py`：`Palette / Radius / Fonts.text()`（**CJK 必须走 `Fonts.text`**） |
| 插件配置持久化 | `PluginContext.get_plugin_config / set_plugin_config` → `SettingsManager`（落到 `cli_config.json → plugins.plugin_specific_configs.evaluation`） |
| 资源释放 | `context.register_resource(view)` + `view.cleanup()`（返回插件中心时 `PluginManager.unload_plugin` 自动调） |
| 文件选择/另存 | `ft.FilePicker().pick_files(...)` / `.save_file(..., src_bytes=...)`（参考 `plugins/one_click_rating_for_projects/view.py:1240`、`plugins/cloud_exam/view.py:698`、`src/ui/components.py:pick_json_file`） |
| 插件加载链路 | `src/core/plugin_runtime.open_plugin_ui`（不改） |

## Flet 0.82.2 API 红线（已对本机安装源码逐一核对）

- `ft.Dropdown` **无 `on_change`** → 必须用 **`on_select`**，选项用 `ft.DropdownOption(key=..., text=...)`。✔已验证
- `ft.Icon` 用 `.icon`，**没有** `.name`。
- 任何 `ft.TextStyle` 覆盖走 `Fonts.text(...)`，否则 Windows 中文发虚。
- `ft.SegmentedButton(segments=[ft.Segment(value=, label=)], selected={...}, on_change=)`；`ft.Segment` 无 on_*。
- `ft.ReorderableListView(controls=[...], on_reorder=...)`，事件为 `OnReorderEvent(old_index, new_index)`；
  默认已带拖拽手柄（`show_default_drag_handles=True`），无需 `ReorderableDragStartListener`（本版本不存在）。
- `ft.FilePicker.save_file(...) -> Optional[str]`，支持 `src_bytes` 直接落盘。
- `ft.AlertDialog` 无 `title_padding` 之外特殊项；开关弹窗用 `page.show_dialog() / page.pop_dialog()`。
- 频繁回调（生成进度）在 `page.run_task` 内更新 UI。
- `plugins/evaluation/ui.py` 会被 `tests/test_plugin_entrypoints.py` 导入 → **`view.py` 对 `docx` 的导入必须懒加载**
  （放在 `export_word()` 内部，缺失时抛 `RuntimeError("缺少 python-docx，请先安装插件依赖")`）。
- 包内统一用**相对导入**（`from .models import ...`），避免 `evaluation.models` 与 `plugins.evaluation.models`
  双模块身份导致 `isinstance` 失效。

---

## Steps

- [x] 1. `src/core/plugin_settings.py`（`setting_value` / `validate_settings`）
- [x] 2. `components.build_plugin_settings_dialog` + `plugin_center_view._on_plugin_settings`（读 manifest `settings_schema`）
- [x] 3. 模板就位：拷 `kp-import-template.docx` 到 `plugins/evaluation/templates/`；`.gitignore` 开例外；
      `manifest.json` 写 `settings_schema`；`requirements.txt` + 根 `requirements.txt` 补 `python-docx>=1.1.0`
- [x] 4. `models.py`（dataclass + 枚举 + `allocate_by_largest_remainder`）
- [x] 5. `state.py`（`DraftStore` + `WizardValidator.validate_step` 六步校验 + `apply_global_defaults`）
- [x] 6. `prompts.py`（系统提示词 + `QUESTION_SCHEMA`）+ `ai_client.py`（OpenAI 兼容 + Exa MCP + 降级链）
- [x] 7. `clarification.py`（三档分级 + 同类复用 + 跳过/挂起 + 留痕）
- [x] 8. `generator.py`（逐知识点 + 暂停/恢复/取消/局部挂起）+ `review.py` + `quality.py`
- [x] 9. `validators.py`（FR6.9）+ `sort_questions`（题型 单→多→判）
- [x] 10. `importers.py`（知识点 xlsx / 样例题库 / 考纲候选提取）
- [x] 11. `template_manager.py`（内置 + 覆盖 + 版本）
- [x] 12. `exporter.py`（Excel 合并区防御性覆写 / Word **节点级** XML 克隆 / 文件名清洗 / zip 命名与排列）
- [x] 13. `view.py` Step1–Step4（含拖拽排序、双视图联动、汇总条、敏感度设置）
- [x] 14. `view.py` Step5（生成 + 澄清模态队列 + 待澄清入口 + 局部暂停）
- [x] 15. `view.py` Step6（树形列表 + 预览/编辑/重生成 + 色标 + 逐题审核 + 澄清记录 + 导出）
- [x] 16. `ui.py` 接线；删除 `src/ui/views/evaluation_view.py`
- [x] 17. `tests/test_evaluation_core.py`：models（含 `allocate_by_largest_remainder` 合计恒等）/ validators（枚举、选项≤8、多选≥2字母、判断 A.正确 B.错误）/ `sort_questions`（单→多→判）/ state（六步 `validate_step` + 防抖落盘与原子写）/ clarification（同类复用、skip、defer、留痕）/ exporter（Excel 合并区+R5 起始+无示例行；Word 段落结构与页眉页脚域；zip 命名/排序/重名去重；`_safe_stem` 非法字符+保留名+超长）/ template_manager（内置/覆盖/版本/重置）
- [x] 18. `tests/test_evaluation_view.py`：FakePage 构建、步骤门控、澄清弹窗跨线程握手（`threading.Event` 唤醒、关闭=defer 不阻塞）、manifest `settings_schema` 设置弹窗
- [x] 19. 落 §H 全部 6 项防御性设计（跨线程握手 / 节点克隆 / 合并区校验 / 防抖落盘 / SSE 流式解析 / 文件名清洗）
- [x] 20. 端到端手测（见下）并出真实样例产物

## Verification

1. **单测**：`pytest -q`（全量，确认无回归；`test_plugin_entrypoints` 必须通过 → 证明 `docx` 是懒加载）
2. **设置组件**：启动 `python main.py` → 插件中心 → 管理视图齿轮 →
   能看到 5 个配置项 → 保存 → 检查 `%APPDATA%/ZX-Answering-Assistant/cli_config.json`
   的 `plugins.plugin_specific_configs.evaluation`；再对无 `settings_schema` 的插件点齿轮 → 应提示「该插件没有可配置项」
3. **六步向导（含线程安全压测）**：
   - 生成中反复触发/关闭澄清弹窗 20 次 → 无 UI 卡死、worker 线程全部退出、无「线程未结束」残留
     （`page.run_thread` 任务列表与 `threading.enumerate()` 计数回落）
   - 全程默认值时 Step1→触发生成点击 ≤6 次（§9 验收）
   - Step2 拖拽排序后知识点序号重排、Step3 自推考点折叠区可展开改
   - Step4 ［按题数｜按比例］互相换算合计**恒等于**总题数；取消某题型后其余比例归一化；
     总题数＜勾选题型数 → 红字「题数不足以覆盖已选题型」且下一步禁用
   - Step5 澄清弹窗：三档敏感度行为、「同类都按此处理」不再弹、关闭(×)→［待澄清 n］、
     「跳过该知识点」→ Step6 灰行［补生成］、局部暂停不影响其他知识点
   - Step6 红色置信度未确认 → 导出被阻断并定位到题
4. **模板一致性**：导出的 `.xlsx` 与 `kp-question-excel.xlsx` 逐行比对
   （R1 注意事项原文、R2/R3 合并区、R4 表头、R5 起无示例行）；
   `.docx` 与 `kp-import-template.docx` 比对
   （**页眉 `“{知识点名}”知识点评估题`**、正文首段、题干自动编号 `1.`、`答案：【BC】`、**页脚 `第 X 页 共 Y 页`**）
5. **降级链**：故意把 `exa_mcp_url` 指向无效地址 → 应记澄清记录并正常出题（不阻断）；
   清空 `api_key` → 应弹「未配置 AI API Key」并打开设置弹窗
6. **导出命名**：zip 名 `{课程名}_评估题库_{日期}.zip`，包内按 `{课程名}_{章节序号}_{章节名}_{知识点序号}_{知识点名}` 排序
7. **防御性设计专项**：
   - §H-1：生成中连点「确认/关闭」各轮 → 无卡死、`threading.enumerate()` 线程数回落
   - §H-2：导出 docx 用 `zipfile` 断言 `word/document.xml` 的题干段仍带 `numPr`、
     `word/header1.xml` 含知识点名、`word/footer1.xml` 仍含 `PAGE`/`NUMPAGES` 域；再用 Word/WPS 实开一次
   - §H-3：把模板复制一份用 WPS 重存后再导出 → 不出现合并区错位（断言 R4 表头与 R5 首行）
   - §H-4：连续 50 次 `mark_dirty()` 只产生少量落盘（用 monkeypatch 计数），且 `flush(force=True)` 必落盘
   - §H-5：用桩响应分别构造 SSE / 纯 JSON / 含 `result.content[0].text` 嵌套 JSON / 超时 四种情形
   - §H-6：课程名/章节名/知识点名填 `A/B:C*D?E"F<G>H|I` 与超长串 → 导出成功且文件名合规

## 已知风险 / 待办

- **Exa 托管 MCP 的响应形态未实证**（可能 SSE / 可能纯 JSON，keyless 限额未公开）→ 实现时双向容忍解析，
  并把 `exa_mcp_url` 做成可配置，便于换自建/第三方 MCP。
- **Word 模板克隆**依赖 python-docx 与 WPS 生成 XML 的兼容性 → 实现后必须用 Word/WPS 双开验证版式与页码域。
- `python-docx` 当前**未装在本机 system Python 3.13**（装在 `.venv`）→ 需补根 `requirements.txt`，
  否则打包/新环境会 Word 导出失败（Excel 不受影响）。
- 模板二进制进仓库需 `.gitignore` 例外，否则新克隆缺模板 → 已在 Steps 3 覆盖。
- `page.run_thread` 的 worker 阻塞在 `threading.Event.wait()` 时会占用一个线程 → 已用超时 + 暂停/取消/cleanup 兜底 `set()` 收敛；
  若 Flet 侧不支持长时 worker 阻塞，退化为「wait 超时后轮询队列状态并让 worker 让出」，行为不变。
- 破坏性测试依赖有权限在 WPS/Word 打开产物 → 若无 GUI 环境，至少完成 zip 内 XML 的 `zipfile` + `lxml` 结构断言。
- Windows 保留名/路径超长在真实长课程名下才暴露 → 已按 §H-6 统一清洗，并在测试里用超长 + 含 `\/:*?"<>|` 的名字做用例。
- 平台导入的最终校验只有真机才能确认 → 出口自检（枚举合规/选项≤8/多选≥2字母/答案字母与选项列一一对应）只能保证「格式合规」，
  不能替代平台侧验收。
