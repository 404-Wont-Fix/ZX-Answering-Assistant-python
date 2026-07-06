# 更新日志

## [v3.9.8] - 2026-07-06

本版本重点重构摸鱼速评助手的评分规则与批量评分能力，同时对设置界面进行了视觉重设计，并在全仓库完成了 Flet 0.83 弃用 API 的前置清理。

### 评分规则重构（摸鱼速评助手）

#### 三档严格度（保持 high=严格 / low=宽松 方向）

| 档位 | 分数范围 | 无附件扣分 | 日志不足扣分 |
|------|---------|-----------|-------------|
| 严格 | 76 ~ 90 | −5 分 | 0 条 −5 / 1 条 −4 / 2 条 −3 |
| 中等 | 76 ~ 90 | −5 分 | 同上 |
| 宽松 | 76 ~ 100 | −5 分 | 同上 |

- **保底分逻辑修正**：内容不达标（截图<3 且 字数<150）→ 固定 76 分 + 标注"混子"；满足最低要求 → 最低 77 分、不标注。修复了旧版以 `floor(77)` 判定标注导致 76 分学生漏标、77 分学生误标的 bug。
- **无附件改为固定扣分（−5）**：替代旧的封顶区间（high:77~80、medium/low:77~85）。解决了"学生截图多、字数高但无附件时分数被压到 ~79"的不合理问题，保证"内容越好→分数越高"的单调性。
- **日志<3 不再触发保底**：改为酌情扣 3~5 分（0 条 −5、1 条 −4、2 条 −3），扣完不低于 77 分、不触发标注。
- **日志质量因子扁平化**：移除旧版对每阶段>500 字的惩罚（0.5）；≥80 字/阶段一律 1.0，不再因"写得详细"反而降权。
- **`MINIMUM_NOT_MET_SCORE` 常量化**（76），标注逻辑统一由常量驱动。

#### 确认弹窗补齐

- 新增**免责声明**（AI 评分仅供参考、以教师复核为准），单项目/批量评分的确认弹窗均展示。
- 显示当前档位、分数范围、内容保底规则、日志/附件扣分规则。

### 批量评分（新功能）

- **项目列表新增复选框**：每张项目卡片左侧加 Checkbox（放在 GestureDetector 外部，避免双事件冲突），支持跨页勾选、"全选当前页" / "清空选择"。
- **批量评分按钮**：项目列表工具栏新增「批量评分」按钮（仅勾选≥1 个项目时启用），点击后后台汇总各项目的可评学生（进度≥100%）→ 确认弹窗（项目清单 + 学生总数 + 档位 + 规则 + 免责声明）→ 逐项目评分。
- **按项目独立应用分布上限**：评分核心重构为 `_grading_inner` 分组循环，每个项目的"满分≤2 人 / 95+≤7 人 / 90+≤12 人"独立计算，避免跨班级挤占名额。
- **完成弹窗保底名单增强**：保底 76 分学生名单附带"项目名（班级名）- 学生名"，批量后可快速定位；超 15 条截断显示"……等共 N 人"；每行 `max_lines=1` 防溢出。
- **工具栏设置按钮**：批量评分旁新增齿轮按钮，直接打开评语与严格度设置，无需进入学生列表。

### 设置界面重设计（摸鱼速评助手）

- **标题栏**：图标 +「评语与严格度设置」。
- **严格度**：紧凑卡片式（图标 + 说明文字 + 下拉框）。
- **评语模板分区**：短评语 / 长评语各为独立带边框卡片，顶部彩色标题栏（主色/强调色）显示图标 + 标题 + 用途说明 + 条数 + 建议字数 +「添加」按钮，下方可滚动 ListView（高度 150）。
- **评语卡片重做**：全文展示（可选中复制，不再截断 55 字）+ 字数状态徽标（绿✓达标 / 橙建议≥N字）+ 编辑/删除。
- **修复关闭按钮浮层遮挡**：内容区设固定高度（520px）+ 外层 Column 加 `scroll=AUTO`。

### 跨仓库维护

- **全仓库 `ft.border.all()` → `ft.Border.all()`**（8 个文件、20 处）：Flet 0.80 标注 `ft.border.all` 弃用、0.83 移除；提前清理，消除 DeprecationWarning。
- 触及文件：`components.py`、`view.py`（摸鱼速评）、`answering_view.py`、`course_certification_view.py`、`extraction_view.py`、`plugin_center_view.py`、`settings_view.py`、`weban_view.py`。

---

## [v3.9.7] - 2026-07-06

本版本主要包含摸鱼速评助手的成绩导出功能、答题/提取/认证模块的大规模代码重构（净删减约 2,000 行）、文档整理，以及学生列表勾选卡顿的性能修复。

### 新增功能

#### 摸鱼速评助手：成绩导出

- 新增「导出成绩」按钮，可将已评分学生成绩导出为 Excel（.xlsx）
- 仅导出已评分数据，按分数降序排列，自动清理文件名非法字符
- 新增 openpyxl 依赖，适配 Flet 文件保存对话框

### 性能优化

#### 摸鱼速评助手勾选卡顿（plugin v2.5.0）

- 修复学生列表勾选时的「顿一下」卡顿。根因：Flet 0.82 在每个事件处理器返回后会自动触发一次 `page.update()`，对整棵控件树（~750 节点）做全量 diff（实测 ~370ms），阻塞事件循环、把定向推送的 patch 卡在发送队列里迟迟不发。
- 改为在每个选择 handler 开头调用 `ft.context.disable_auto_update()`（事件级隔离，事件结束自动恢复，不污染其它视图/事件）跳过冗余的全树 diff，并对真正改动的控件定向 `control.update()`。
- 单卡点击从 ~370ms 降到 ~2.5ms；批量勾选（50 人）从 ~718ms 降到 ~85ms。

### 重构（净删减约 2,000 行）

- **提取答题公共基类**：新增 `src/answering/base_answer.py`，抽离答题/认证流程的公共逻辑；新增停止请求标志，实现答题过程的优雅停止（`browser_answer.py`、`certification/workflow.py` 等，净删减约 330 行）
- **重构提取器**：`src/extraction/extractor.py` 抽离公共流程和通用 API 请求方法，单文件净减约 410 行
- **移除 FileHandler 类**：简化配置/token/导出逻辑（`config.py`、`token_manager.py`、`exporter.py` 等），净删减约 620 行
- **统一请求头管理**：新增 `src/core/headers.py` 集中管理浏览器指纹与请求头配置，替换 `auth`、`answering`、`certification`、`extraction`、`cloud_exam` 等多处重复的手动构造代码
- **代码复用与规范化**：跨 17 个文件统一重复逻辑（`student.py`、`teacher.py`、`api_answer.py` 等）

### 文档

- 整理文档结构：移除 `AUDIT_TODO.md`、`REPOSITORY_REVIEW_CONCLUSION.md`、`BUILD_QUICKREF.md` 等冗余/过时文档
- 新增 `docs/BROWSER_SETUP.md` 浏览器配置指南
- 更新 `README.md`、`CLAUDE.md` 同步当前项目结构

---

## [v3.9.6] - 2026-07-05

### 代码清理与瘦身

通过全仓库审计，移除 4 个废弃模块和大量死代码，净删减约 1,100 行。

#### 删除废弃模块（-737 行）

- 移除 `src/utils/retry.py`：259 行重试装饰器，从未被任何代码调用
- 移除 `src/core/constants.py`：113 行常量定义，全部废弃或与 `config.py` 重复
- 移除 `src/core/ssl_helper.py`：239 行 SSL 配置模块，核心逻辑已内联到 `main.py`
- 移除 `src/core/app_state.py`：127 行全局状态管理器，仅被导入但从未实际读写

#### 清理存活文件中的死代码（-368 行）

- `api_client.py`：移除从未被使用的缓存子系统（`use_cache` 从未传入 `True`）和未被调用的方法（`put`、`delete`、`get_json`、`post_json`、`reset_api_client`）
- `browser.py`：移除 12 个无人调用的模块级包装函数（`start_browser`、`get_browser` 等）和从未被调用的 `_is_in_asyncio_context` 方法
- `answering_view.py`：移除 `_on_json_file_selected()` 死代码（已被 `_process_selected_json_file()` 取代）
- `workflow.py`：移除 `hello_world()` 测试桩
- 清理 `browser_answer.py`、`extractor.py`、`workflow.py` 中未使用的导入（`sys`、`os`、`sync_playwright`、`asyncio`、`requests`）

#### SSL 配置简化

原 `ssl_helper.py` 的 239 行模块替换为 `main.py` 中 12 行的 `_setup_ssl()` 内联函数，通过 `certifi` 设置环境变量实现同等功能。

#### 文档同步

- 更新 `README.md`：删除对已移除模块的引用，补全插件列表（新增摸鱼速评助手）
- 更新 `CLAUDE.md`：同步项目结构和 SSL 配置说明
- 更新 `docs/SSL_SETUP.md`：指向新的内联配置方式

---

## [v3.9.5] - 2026-07-05

### 维护

- 关闭 GitHub Actions release 打包时的自动归档

---

## [v3.9.0] - 2026-07-05

### 新增功能

#### 摸鱼速评助手插件（v2.4.0）

- 新增学生项目成果查看与批量评分功能
- 实现完整一键评分功能，支持自动计算分数和批语
- 重构评分系统，新增多严格度配置与长评语模板

### 改进

- 统一按钮字体为系统字体，优化文案显示
- 重构进程清理逻辑，统一子进程树强制终止方案
- 修复 Flet 版本升级后的图标和边框渲染问题

---

## [v3.8.0] - 2026-06-28

### 新增功能

#### 摸鱼速评助手插件

- 新增懒狗一键 AI 评分插件，支持自动批改产教融合项目
- 后续调整插件名称，移除 AI 相关字样

### 重构

#### 云考试模块插件化

- 将云考试模块重构为独立插件 `plugins/cloud_exam/`
- 简化题库查找逻辑并优化 UI 线程处理
- 修复线程安全问题

#### 插件系统优化

- 重构插件系统，优化上下文与加载流程
- 完成插件系统资源管理与导入路径优化

### 维护

- 重构 WeBan 模块安装与 CI 缓存策略

---

## [v3.7.4] - 2026-06-04

### 新增功能

#### GitHub Actions 桌面发布

- 新增 Windows、macOS Intel、macOS Apple Silicon 三平台自动构建与发布工作流
- 配置 Flet 打包排除项和构建参数

### 改进

- 添加跨平台适配的字体配置，改善 macOS 渲染效果
- 优化应用退出流程

### 维护

- 更新 macOS runner 版本并修复 Windows 打包逻辑
- 调整 macOS 构建平台为 arm64

---

## [v3.7.2] - 2026-05-26

### 界面统一与修复

- 统一评估答题、答案提取、插件中心和课程认证页面的工作台设计风格
- 修复侧边栏折叠后缺少恢复入口的问题
- 调整状态标签配色，提升文字对比度和可读性
- 为评估答题详情列表提供独立布局与滚动范围，避免列表内容改变主页面结构

### 文档维护

- 同步 README、开发说明和应用版本元数据至 v3.7.2
- 修复 Flet 与浏览器安装文档的失效入口
- 移除由现行指南和本更新日志替代的历史临时文档

---

## [v3.7.0] - 2026-05-26

### 现代界面基础

- 引入共享主题与 UI 组件，统一导航、页面标题、卡片和状态展示
- 重构主工作台、设置、关于、评估答题与答案提取视图
- 为后续内置插件页面统一视觉规范奠定基础

---

## [v3.6.5] - 2026-05-26

### 维护与配置

- 调整插件、浏览器与配置相关实现，整理安全微伴接入结构
- 更新系统托盘和平台运行说明，并补充配置与插件加载测试覆盖

---

## [v3.6.1] - 2026-05-14

### 🐛 重要修复

#### Flet版本兼容性修复
- ✅ **修复Flet 0.82.0+ API兼容性问题**
  - 修复`window_center`方法调用（属性→方法）
  - 修复`ft.app()`废弃API（`ft.app()` → `ft.run()`）
  - 修复窗口属性访问问题
  - 固定Flet版本至0.82.2确保稳定性

#### 系统浏览器自动检测优化
- ✅ **完全自动化系统浏览器支持**
  - 自动检测系统Chrome浏览器
  - 自动检测系统Edge浏览器
  - 智能选择优先级：Chrome > Edge > Playwright内置
  - 无需手动配置，无需下载额外浏览器

#### Greenlet线程切换错误修复
- ✅ **修复AsyncIO环境下的线程安全问题**
  - 完善BrowserManager工作线程机制
  - 修复`Extractor`类的浏览器初始化
  - 统一所有模块使用BrowserManager
  - 解决GUI模式下的greenlet错误

#### Windows编码问题修复
- ✅ **修复emoji字符导致的GBK编码错误**
  - 替换所有emoji为文本标记
  - `[OK]` 替代 ✅
  - `[INFO]` 替代 💡/📋
  - `[WARNING]` 替代 ⚠️
  - `[ERROR]` 替代 ❌

### 🔧 技术改进
- 📝 更新依赖版本固定（flet==0.82.2, flet-desktop==0.82.2）
- 📝 优化BrowserManager线程安全机制
- 📝 统一日志输出格式，避免编码问题
- 📝 完善系统浏览器检测逻辑

### 📝 文件修改
- `src/main_gui.py` - Flet API修复
- `src/core/browser.py` - 浏览器管理优化，日志格式统一
- `src/extraction/extractor.py` - 重构使用BrowserManager
- `src/certification/workflow.py` - emoji字符修复
- `requirements.txt` - 版本固定
- `version.py` - 版本号更新至3.6.1

### 🚀 部署改进
- **最小化部署**: `pip install -r requirements.txt` → `python main.py`
- **零额外配置**: 无需下载Playwright浏览器，无需手动配置
- **完全兼容**: 支持GUI和CLI模式，Windows系统Chrome/Edge

---

## [v3.5.1] - 2026-04-30

### 🎉 用户体验改进

#### 安全微伴插件优化
- ✅ **修复学校验证提示问题**
  - 问题：验证学校按钮点击后没有用户反馈提示
  - 原因：后台线程中的UI更新未正确执行
  - 解决：使用AlertDialog替代SnackBar，提供明确的视觉反馈

- ✅ **改进用户界面交互**
  - 添加加载状态对话框（带进度条）
  - 添加明确的结果反馈对话框
  - 视觉优化：
    - ✅ 成功：绿色对勾图标
    - ❌ 失败：红色错误图标
    - 🔄 加载：蓝色刷新图标和进度条

#### 技术改进
- 📝 重写 `_on_validate_school()` 方法
- 📝 新增 `_show_validation_dialog()` 方法
- 🐛 修复图标引用错误 (`LOADING` → `REFRESH`)
- 🔧 后台线程处理验证逻辑，主线程更新UI确保Flet兼容性

### 📝 文件修改
- `plugins/weban_plugin/weban_view.py` (+78行, -8行)

---

## [v3.5.0] - 2026-04-27

### 🎨 优化项目

#### 清理项目结构
- ✅ 删除 `cache_template.py` 和 `cache_template.bat`（Flet 自动处理模板缓存）
- ✅ 删除多余文档（BUILD_CACHE_GUIDE.md、BUILD_FIXES.md 等）
- ✅ 整合文档结构，提高可维护性

#### 优化依赖
- ✅ 移除 `pyyaml` 和 `py7zr`（Flet 打包时自动安装）
- ✅ 移除 `keyboard`（代码中未使用）
- ✅ 保留所有运行时必需依赖

#### 更新版本号
- ✅ 版本号更新到 v3.5.0
- ✅ 更新所有文档和配置文件

### 📝 说明

本项目采用 Flet 构建系统，会自动处理以下内容：
- 模板自动下载和缓存到 `build/flutter`
- 无需手动管理模板缓存
- `build.bat` 提供一键清理并编译功能

所有功能保持不变，仅优化项目结构和依赖管理。

---

## [v3.4.1] - 2026-04-27

### 🎉 新增功能

#### 启动动画系统
- ✅ **运行时加载界面** - 应用启动时显示加载动画
  - 显示应用图标、标题和版本号
  - 进度条动画效果
  - 渐变背景色
  - 加载提示文字

- ✅ **编译时启动画面** - 配置启动画面（Splash Screen、Boot Screen、Startup Screen）
  - Splash Screen: 应用图标 + 品牌蓝色背景 (#0B6BFF)
  - Boot Screen: 首次启动解压提示
  - Startup Screen: Python 运行时初始化提示

#### 构建缓存系统
- ✅ **模板缓存脚本** - 自动下载并缓存 Flet 构建模板
  - `cache_template.py` - Python 缓存脚本
  - `cache_template.bat` - Windows 一键缓存
  - 避免每次编译都从 GitHub 下载模板

- ✅ **自动构建脚本** - 一键清理并编译
  - `build.bat` - Windows 自动构建脚本
  - 自动清理旧的构建文件和缓存
  - 确保干净的编译环境

### 🔧 修复问题

#### 修复 1: `__builtins__` 兼容性
- **问题**: 打包后运行时 `AttributeError: 'dict' object has no attribute 'exit'`
- **原因**: 在某些 Python 环境中，`__builtins__` 是字典而不是模块
- **修复**: 兼容字典和模块两种情况

#### 修复 2: Flet API 兼容性 (v0.82.2)
- **问题**: `AttributeError: module 'flet.controls.alignment' has no attribute 'center'`
- **原因**: Flet 0.82.2 版本的 API 与文档示例不完全一致
- **修复**:
  - `ft.alignment.center` → `ft.Alignment(0, 0)`
  - `ft.alignment.top_center` → `ft.Alignment(-1, -1)`
  - `ft.alignment.bottom_center` → `ft.Alignment(1, 1)`

#### 修复 3: 软件标题乱码
- **问题**: 编译后应用标题显示为乱码
- **原因**: `pyproject.toml` 中的 `product` 字段包含中文字符
- **修复**: 改为英文 `product = "ZX Answering Assistant"`
- **说明**: 应用内部的中文界面不受影响

#### 修复 4: 启动屏幕中文显示
- **问题**: 启动屏幕消息为英文
- **修复**: 改回中文，但使用单行文本（避免多行导致的编译错误）
  - `message = "正在准备首次启动"`
  - `message = "正在加载组件"`
  - `message = "正在初始化应用"`

#### 修复 5: 模板缓存 Windows 文件占用
- **问题**: 下载模板后解压失败 `[WinError 32] 另一个程序正在使用此文件`
- **原因**: Windows 系统临时文件被占用
- **修复**:
  - 使用自定义临时目录 `flet_template_cache`
  - 添加文件删除重试机制（最多 3 次）
  - 先删除旧缓存，避免解压冲突

#### 修复 6: ImportError: No module named main
- **问题**: 编译后运行时找不到主模块
- **原因**: 模板缓存损坏或构建配置不正确
- **修复**:
  - 添加 `build.bat` 自动清理并重建
  - 配置正确的文件包含规则
  - 提供手动清理缓存的说明

### 📝 配置优化

#### pyproject.toml 优化
```toml
[tool.flet]
# 产品名称（英文，避免乱码）
product = "ZX Answering Assistant"
# 描述（英文，避免乱码）
description = "Intelligent Answering Assistant System"

# 启动画面配置
[tool.flet.splash]
color = "#0B6BFF"          # 品牌蓝色
dark_color = "#1a1a1a"     # 深色模式

# 启动屏幕（中文，单行）
[tool.flet.app.startup_screen]
show = true
message = "正在加载组件"

# 排除不必要的文件
exclude = [
    "*.pyc", "__pycache__", ".git", ".venv", "venv",
    "tests", "docs", "*.md", ".gitignore", "CLAUDE.md", ".claude",
]
```

### 📚 新增文档

1. **BUILD_CACHE_GUIDE.md** - 构建模板缓存完整指南
   - 模板缓存原理和使用方法
   - 故障排除和最佳实践
   - 性能对比和优化建议

2. **BUILD_FIXES.md** - 编译问题修复指南
   - 三个主要问题的详细说明
   - pyproject.toml 配置规则
   - 验证修复的方法

3. **STARTUP_ANIMATION_GUIDE.md** - 启动动画配置指南
   - 编译时启动画面配置
   - 运行时加载界面自定义
   - 使用建议和故障排除

4. **BUILD_QUICK_START.md** - 快速编译指南
   - 首次编译步骤
   - 后续编译命令
   - 速度对比说明

### ⚡ 性能提升

| 项目 | 之前 | 现在 | 提升 |
|------|------|------|------|
| 首次编译 | 5-10 分钟（每次都下载） | 5-10 分钟（仅首次） | - |
| 后续编译 | 5-10 分钟（每次都下载） | 2-3 分钟（使用缓存） | **60-70%** |
| 启动体验 | 黑屏等待 | 启动动画 | **用户体验提升** |

### 🔨 开发者体验改进

1. **一键缓存模板** - `cache_template.bat` 双击运行
2. **一键构建** - `build.bat` 自动清理并编译
3. **详细文档** - 完整的故障排除指南
4. **配置验证** - pyproject.toml 配置规则说明

### ⚠️ 重要提示

**pyproject.toml 配置规则**:
- ✅ `product`、`description` 使用英文（避免编码问题）
- ✅ `message` 可以使用中文，但必须是单行
- ❌ 不要在 `message` 中使用 `\n` 换行符
- ❌ 避免使用 emoji 表情符号

### 🎯 下一步计划

- [ ] 添加应用图标（favicon.ico）
- [ ] 配置应用元数据（版本、版权等）
- [ ] 优化打包体积（排除更多不必要文件）
- [ ] 添加自动更新功能

---

## [v3.4.0] - 2026-04-27

### 🔒 新增功能
- 自动 SSL 证书配置功能
- 解决 Windows 环境下的 SSL 验证失败问题
- 新增 SSL 测试工具 (`test_ssl.py`)

### 🐛 修复问题
- Flet 首次下载时的 SSL 证书验证错误
- 添加 certifi 到 requirements.txt

---

## [v3.0.0] - 2026-04-21

### 🎉 重大更新
- 完成插件化架构重构
- 新增插件中心视图
- 支持插件动态加载和管理
- 新增依赖注入系统

### 🐛 修复问题
- 修复多个 UI 问题
- 完善插件开发文档

---

## 版本命名规则

- **主版本号** (Major): 重大架构变更
- **次版本号** (Minor): 新功能
- **修订号** (Patch): Bug 修复和小改进
- **构建号**: Git 提交哈希的前 7 位

---

## 相关链接

- [GitHub Releases](https://github.com/TianJiaJi/ZX-Answering-Assistant-python/releases)
- [问题追踪](https://github.com/TianJiaJi/ZX-Answering-Assistant-python/issues)
- [项目说明](README.md)
