# 代码审计待办 — 第三梯队 + 第四梯队

> 来源：ponytail-audit 全仓库扫描（2026-07-05）
> 第一梯队 + 第二梯队已完成（-1,108 行），本文档记录剩余可优化项。

---

## 第三梯队 — 提取共享工具（消除重复）

预估精简：~800 行

### 3.1 `_normalize_text()` — 3 份近乎相同的副本

| 文件 | 行号 |
|------|------|
| `src/answering/browser_answer.py` | ~195 |
| `src/certification/workflow.py` | ~1299 |
| `src/certification/api_answer.py` | ~87 |

三个都做：`html.unescape` → 去 HTML 注释 → 去 HTML 标签 → 合并空白。`browser_answer.py` 版本稍复杂（额外保留尖括号内容、去除非 CJK/字母数字字符）。

**建议：** 在 `src/utils/text.py` 中写一个共享的 `normalize_text()`，三个文件改为调用它。

---

### 3.2 `CallbackHandler` + `_setup_log_handler` + `_cleanup_log_handler` — 复制粘贴 3 次

| 文件 | 行号 |
|------|------|
| `src/answering/api_answer.py` | ~56-87 |
| `src/answering/browser_answer.py` | ~67-97 |
| `src/certification/api_answer.py` | ~59-85 |

每个都定义了一个内部 `class CallbackHandler(logging.Handler)`，`emit` 实现几乎相同。

**建议：** 在 `src/utils/logging.py` 中写一个共享的 `CallbackHandler` 类 + `setup_callback_logging(callback)` / `cleanup_callback_logging(handler)`。

---

### 3.3 `get_chapters_from_bank()` — 5 行导航代码块重复 7 次

```python
chapters = []
if "class" in question_bank and "course" in question_bank["class"]:
    chapters = question_bank["class"]["course"].get("chapters", [])
elif "chapters" in question_bank:
    chapters = question_bank["chapters"]
```

| 文件 | 出现次数 |
|------|---------|
| `src/answering/browser_answer.py` | 2 |
| `src/answering/api_answer.py` | 1 |
| `src/certification/workflow.py` | 2 |
| `src/certification/api_answer.py` | 2 |

**建议：** 写一个 `get_chapters(bank) -> list` 函数，放在 `src/utils/` 或直接放在题库加载模块中。

---

### 3.4 硬编码浏览器指纹头 — 8+ 份副本，且版本不一致

| 文件 | Chromium 版本 |
|------|--------------|
| `src/answering/api_answer.py` | v138 |
| `src/extraction/extractor.py` | v143 |
| `src/certification/api_answer.py` | v144 |

每个 API 方法都内联了完整的 `headers` 字典（`sec-ch-ua`、`user-agent` 等）。

**建议：** 在 `src/core/` 中定义一个 `DEFAULT_HEADERS` 常量字典，所有文件引用它。顺便统一 Chromium 版本号。

---

### 3.5 `_cleanup_resource()` — 2 份完全相同的副本

| 文件 | 行号 |
|------|------|
| `src/core/plugin_context.py` | ~121 |
| `src/core/plugin_manager.py` | ~510 |

逻辑：遍历 `("cleanup", "dispose", "close")`，调用第一个存在的方法。

**建议：** 提取到 `src/core/plugin_context.py`（或 `src/utils/`）中作为共享函数。

---

### 3.6 `_get_browser_manager()` — 3 个相同的包装函数

| 文件 | 行号 |
|------|------|
| `src/auth/student.py` | ~85 |
| `src/auth/teacher.py` | ~27 |
| `src/certification/workflow.py` | ~110 |

全部是 `return get_browser_manager()`，零附加值。

**建议：** 直接调用 `get_browser_manager()`，删除这 3 个函数。

---

### 3.7 AnimatedSwitcher 样板代码 — 5 个视图中完全相同

`get_content()` 方法中的 `ft.AnimatedSwitcher` 包装在以下文件中重复：
- `answering_view.py`
- `extraction_view.py`
- `settings_view.py`
- `course_certification_view.py`
- （可能还有其他视图）

**建议：** 写一个 `cached_view_switcher(cache_dict, key, builder_fn)` 辅助函数放在 `components.py`。

---

### 3.8 AlertDialog 模式（图标 + 标题 + 内容 + 确定按钮）— 15+ 次

仅 `answering_view.py` 中就出现了 15+ 次，每次 10-15 行。`course_certification_view.py` 中也有大量重复。

**建议：** 在 `components.py` 中写一个 `def alert_dialog(page, icon, title, body, color=None)` 辅助函数。

---

## 第四梯队 — 结构性过度设计

预估精简：~2,500 行（长期）

### 4.1 `FileHandler` 类 — 300 行包装 `pathlib.Path`

**文件：** `src/extraction/file_handler.py`

`file_exists()`、`create_directory()`、`read_json()`、`write_json()` 等全是 `Path` 的一行操作加 print 语句。仅 2 个调用方（`exporter.py`、`extraction_view.py`）。

**建议：** 删除整个类，调用方直接使用 `pathlib.Path` + `json.load/dump`。

---

### 4.2 `QuestionBankCache` — 线程安全字典包装器，只用一个 key

**文件：** `src/certification/workflow.py:36-103`

只用 `'current'` 一个 key。GIL 已保护简单 dict 读写。

**建议：** 替换为模块级变量 `_question_bank = None`。

---

### 4.3 `TokenManager` — 3 个 token 存储复制粘贴（229 行）

**文件：** `src/auth/token_manager.py`

学生、教师、认证三套 `set/get/clear/validate` 方法，逻辑完全相同，仅 key 名不同。

**建议：** 写一个 `_TokenSlot` 数据类 × 3 实例，约 80 行。

---

### 4.4 `SettingsManager` 凭据方法 — 9 个方法复制粘贴

**文件：** `src/core/config.py:194-343`

`get_student_credentials`、`set_student_credentials`、`clear_student_credentials` × 3 角色 = 9 个方法，逻辑相同仅 key 路径不同。

**建议：** 一个 `_get_cred(role)`、`_set_cred(role, data)`、`_clear_cred(role)` 替代全部。

---

### 4.5 `Extractor` API 方法 — 6 个方法模板完全相同

**文件：** `src/extraction/extractor.py`

`get_class_list`、`get_course_list`、`get_chapter_list`、`get_knowledge_list`、`get_question_list`、`get_question_options` 全部重复：构建 headers → debug 打印 → `api_client.get()` → 检查状态码 → 解析 JSON。headers 字典复制了 5 次。

**建议：** 一个 `_api_get(url)` 私有方法 + headers 作为类属性。

---

### 4.6 `exporter.py` — `export_single_course` / `export_all_courses` 内部循环相同

**文件：** `src/extraction/exporter.py`

遍历 chapters → knowledges → questions → options 构建嵌套字典的代码逐字节相同。

**建议：** 提取 `_build_course_data(course)` 辅助函数。

> ⚠️ **已知 Bug：** `export_all_courses` 第315行读取 `"oppotionOrder"`（拼写错误），应为 `"oppentionOrder"`。导致所有选项的排序值永远为 `0`。

---

### 4.7 `importer.py` — 两个统计方法 90% 相同

**文件：** `src/extraction/importer.py:132-201`

`_calculate_single_course_statistics` 和 `_calculate_multiple_courses_statistics` 内部循环完全相同。

**建议：** 一个方法，加可选 `course_list` 参数。

---

### 4.8 `extractor.py` — 3 个提取方法重复登录→选课序列

**文件：** `src/extraction/extractor.py`

`extract()`、`extract_single_course()`、`extract_course_answers()` 都重复 登录→获取班级→选年级→选班级→获取课程 序列。"按课程分组章节" 和 "按章节分组知识点" 的字典构建代码在三处逐字重复。

**建议：** 一个参数化的 `_extract(courses=None, interactive=True)`。

---

### 4.9 `CourseAutoAnswer` 从 `AutoAnswer` 复制了 5 个方法

| 方法 | `browser_answer.py` | `workflow.py` |
|------|---------------------|---------------|
| `_normalize_text` | ~195 | ~1299 |
| `_parse_current_question` | ? | ? |
| `_select_single_answer` | ~854 | ~1481 |
| `_select_multiple_answers` | ~891 | ~1519 |
| `_get_current_question_number` | ? | ? |

**建议：** 提取共享基类或 mixin。

---

### 4.10 `navigate_to_course_page` — 600+ 行，选择 "1" 和 "3" 共享 200 行

**文件：** `src/certification/workflow.py:623-1240`

"兼容模式" 和 "重做兼容模式" 分支包含约 200 行相同的 Playwright 自动跳转检测逻辑。

**建议：** 提取共享检测逻辑为辅助函数。

---

### 4.11 `answering_view.py`（2809 行）+ `course_certification_view.py`（1387 行）共享 ~500 行

重复内容：
- JSON 导入处理 `_process_selected_json_file()`（~200 行 × 2）
- 课程不匹配弹窗（~70 行 × 3 处）
- 进度对话框 `_create_answer_log_dialog()`
- 停止逻辑 `_on_stop_answering()`
- 进度更新 `_update_progress()`
- AnimatedSwitcher 样板

**建议：** 提取共享基类或把公共逻辑放入 `components.py`。

---

## ⚠️ 已知 Bug（审计中发现）

| 严重程度 | 问题 | 位置 |
|---------|------|------|
| **Bug** | `export_all_courses` 读取 `"oppotionOrder"`（拼写错误）而非 `"oppentionOrder"`，所有选项排序值永远为 `0` | `src/extraction/exporter.py:315` |
| **异味** | `sec-ch-ua` 头在 3 个文件中有不同 Chromium 版本（v138/v143/v144），可能触发反爬检测 | `api_answer.py`、`extractor.py`、`certification/api_answer.py` |
| **异味** | `weban_view.py` 在 UI 线程用 `time.sleep(0.5)` 轮询，阻塞整个 Flet 页面 | `src/ui/views/weban_view.py:595` |
| **异味** | `browser_answer.py` 中 `_check_stop()` 始终返回 `False`，所有停止检查调用都是死代码 | `src/answering/browser_answer.py` |

---

## 附：已完成的第一梯队 + 第二梯队摘要

- 删除 4 个文件：`retry.py`（259 行）、`constants.py`（113 行）、`ssl_helper.py`（239 行）、`app_state.py`（127 行）
- 清理 `api_client.py` 缓存子系统和未使用方法（-159 行）
- 清理 `browser.py` 12 个未使用包装函数（-68 行）
- 清理 `answering_view.py` 死代码（-133 行）
- 清理 `workflow.py` 测试桩和未使用导入（-10 行）
- 清理未使用导入（`browser_answer.py`、`extractor.py`、`workflow.py`）
- **总计净删减：-1,108 行**
