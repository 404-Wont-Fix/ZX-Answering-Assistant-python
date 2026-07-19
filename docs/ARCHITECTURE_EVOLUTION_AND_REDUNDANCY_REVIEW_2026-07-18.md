# ZX Answering Assistant v4.0.0 架构演进与冗余代码深度 Review

> - 审查日期：2026-07-18
> - 审查对象：`origin/main` 远端提交 `ad6e80ce9ae73b944cd88fc7cc32ccd89fe82dae`
> - 对比基线：v3.9.8 提交 `1d6e88d`
> - 审查方式：只读代码审查、提交演进对比、静态调用关系检查、可执行复现、Python 3.10 完整依赖测试
> - 审查结论：**BLOCK，不建议按当前状态发布或合并为稳定版本**

## 1. 执行摘要

v4.0.0 的架构治理方向总体正确，而且多处改善是真实的：学生认证模块、浏览器管理器、一键评分业务服务、通用 UI 组件和题库工具都完成了职责迁移，测试代码量也明显增加。

但当前版本仍存在三个必须修复的问题：

1. 云考试后台任务会被执行两次，是本轮统一后台调度重构直接引入的运行时回归。
2. 多个插件在 manifest 中公开的 `entry_core` 已与真实业务 API 脱节，出现必然失败、失败返回成功以及“功能开发中”等失真实现。
3. 完整测试套件仍有一项失败，而唯一发布工作流完全不运行测试，导致上述问题可以直接进入 v4.0.0 发布产物。

维护状态评定为 **CRITICAL**，风险等级为 **HIGH**。这里的 CRITICAL 不代表需要推倒重写，而是表示当前存在可执行契约漂移和发布门禁失效，必须先修正再继续发布。

## 2. 仓库同步状态与审查边界

审查开始时，本地 `main` 位于 `6bc58b4`，原先跟踪同名远端分支。执行 `git fetch --prune origin` 后发现远端发生过 force-push：

```text
local main:   6bc58b4b27bad2e6f8c88aae043af81c0d34bd81
origin/main:  ad6e80ce9ae73b944cd88fc7cc32ccd89fe82dae
divergence:   ahead 166 / behind 246
```

由于这不是 fast-forward，未擅自覆盖本地 `main`。本次审查通过隔离 worktree 检出远端最新提交进行，结束前再次 fetch，确认审查提交仍与 `origin/main` 完全一致。

本报告中的代码行号均以 `ad6e80c` 为准。

## 3. 架构演进对比

### 3.1 规模变化

从 v3.9.8 到 v4.0.0：

```text
55 files changed
5,800 insertions
5,911 deletions
Python 总行数：33,177 -> 33,010
测试总行数：668 -> 1,515
Python 文件数：79 -> 79
```

约 1.17 万行发生变化，但 Python 总量只减少 167 行。这说明本轮价值主要来自职责迁移、兼容 façade 和测试补充，而不是简单删除代码。评价本轮架构质量时，不应把改动规模或净删行量当作主要指标。

### 3.2 明显改善

#### 学生认证模块：显著改善

`src/auth/student.py` 从约 1,141 行下降到 165 行，并拆分为：

- `_student_courses.py`：课程和 HTTP 数据访问；
- `_student_browser_health.py`：浏览器健康检查；
- `_student_browser_ops.py`：页面操作；
- `_student_login.py`：登录和令牌获取；
- `student.py`：兼容 façade。

同时新增 `tests/test_student_facade.py`，用于保护原有导入路径和公共符号。该部分是本轮最完整的职责拆分之一。

#### 浏览器管理器：明显改善

`src/core/browser.py` 从 1,113 行下降到 622 行，安装逻辑和 worker 引擎分别迁移到：

- `src/core/_browser_installer.py`；
- `src/core/_worker_engine.py`。

浏览器生命周期、Context/Page 管理、worker 恢复的责任比基线清晰。但后文提到的共享 Context helper 尚未真正接入调用方。

#### 一键评分：业务与 UI 开始分离

`plugins/one_click_rating_for_projects/view.py` 从 2,698 行下降到 1,971 行，并新增：

- `grading_service.py`：评分编排；
- `template_service.py`：批语模板维护；
- `excel_exporter.py`：成绩导出；
- `widgets.py`：UI 构建；
- `tests/test_lazy_grading_services.py`：服务层测试。

这不是单纯移动代码：评分服务已经不依赖 Flet，可以独立测试，属于有效的边界改善。

#### 通用能力复用：方向正确

本轮新增或强化了以下共享能力：

- `src/utils/bank_matcher.py`；
- `src/extraction/bank_service.py`；
- `AnswerProgressDialog`；
- `run_background_task`；
- `APIClient.get_json()`；
- `AnswerMatcherMixin`。

这些抽象解决的都是已经出现多次的真实重复，而不是纯粹为了“看起来更架构化”而创建。

### 3.3 改善有限或基本未改善

#### `AnsweringView` 仍是高责任密度对象

`src/ui/views/answering_view.py:48` 的 `AnsweringView` 仍有 37 个方法，类体约 1,989 行，同时承担：

- 登录表单和凭据状态；
- 课程列表和课程详情；
- 题库选择和匹配；
- 浏览器/API 两种答题模式编排；
- 进度、停止、重登录和错误弹窗；
- 大量 Flet 控件构建。

文件已从 2,613 行下降到 2,036 行，但业务编排仍直接存在于 View 中。后续应按“登录会话、课程浏览、答题会话”三个用例边界渐进拆分，而不是按行数机械切文件。

#### 课程认证工作流基本没有实质改善

`src/certification/workflow.py` 仍有 1,572 行，本轮多次触碰后净减少约 23 行。该模块混合了：

- 题库全局状态；
- 教师认证；
- CLI 菜单；
- 浏览器导航；
- API 答题；
- 浏览器兼容答题类。

其中 `navigate_to_course_page()` 单个函数约 260 行，仍然是明显的维护热点。

#### 插件边界仍处于过渡状态

云考试已经完成插件自持有 UI、workflow、API client 和 models，但课程认证与评估插件仍只是宿主实现的薄包装：

- `plugins/course_certification/ui.py` 导入 `src.ui.views.course_certification_view`；
- `plugins/course_certification/core.py` 导入 `src.certification.workflow`；
- `plugins/evaluation/ui.py` 导入 `src.ui.views.evaluation_view`；
- `plugins/evaluation/core.py` 导入 `src.extraction`。

项目需要明确“插件是独立业务边界”还是“内置功能的可开关入口”。当前两种模型并存，已经造成 `entry_core` 契约漂移。

## 4. 必须修复

### 4.1 [必须修复] 云考试后台任务被执行两次

位置：`plugins/cloud_exam/view.py:858-866`

当前实现先通过统一 helper 调度任务：

```python
run_background_task(self.page, lambda: target(*args, **kwargs))
```

随后又保留了旧实现：

```python
thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
thread.start()
return thread
```

实际复现结果：

```text
task_execution_count=2 values=['ran', 'ran']
```

受影响的入口至少包括：

- `_perform_login()`；
- `capture_task()`；
- `load_task()`。

可能结果包括重复登录、重复网络监听、同一题库并发写入状态、重复弹窗以及 UI 竞争。

根因是提交 `b1d3b20` 在统一四个插件的 `_run_background` 时加入了新调度调用，但没有删除 cloud_exam 原有 fallback 线程块。

现有测试 `tests/test_cloud_exam_plugin.py:110-123` 只断言 `run_thread` 被登记一次，没有真正执行 runner 并统计业务回调次数，因此没有捕获问题。

最小修复：

1. 删除 `plugins/cloud_exam/view.py:862-866` 的旧线程实现；
2. 保持其他三个插件已经采用的一行委托模式；
3. 新增回归测试：执行 FakePage 收到的 runner，断言业务 target 恰好执行一次；
4. 分别验证登录、获取试卷和加载题库入口没有重复副作用。

### 4.2 [必须修复] `entry_core` 公开契约与真实实现脱节

`PluginManager.load_plugin_core()` 是真实存在的公共加载路径，插件开发文档也将 `entry_core` 描述为业务逻辑入口。但多个 manifest 仍公开 `core.Workflow`，实际实现却不可用。

#### 课程认证插件

位置：`plugins/course_certification/core.py`

- `src.certification.workflow.import_question_bank()` 返回 `bool`，core 却将其保存为题库对象，并在成功分支调用 `len(self.question_bank)`；
- `load_question_bank()` 使用 `self.question_bank is not None` 判断成功，因此底层返回 `False` 时，该方法仍返回 `True`；
- `start_answering_with_bank()` 调用 `start_answering(self.question_bank)`，但真实函数签名为 `start_answering()`。

可执行复现：

```text
course_start_result = {
  'success': False,
  'message': '答题失败: start_answering() takes 0 positional arguments but 1 was given'
}
course_load_false = True, stored = False
```

#### 评估插件

位置：`plugins/evaluation/core.py:47-75`

代码调用：

```python
extractor.run_full_extraction()
exporter.export_full_data(...)
```

当前 `Extractor` 和 `DataExporter` 均不存在这些方法。实际执行立即得到：

```text
AttributeError: 'Extractor' object has no attribute 'run_full_extraction'
```

#### 一键评分插件

位置：`plugins/one_click_rating_for_projects/core.py:24-51`

manifest 公开 `core.Workflow`，但 `execute()` 始终返回 `success=False` 和“自动评分功能开发中”，与已经可用的 UI 评分能力不一致。

#### 为什么现有测试没有发现

`tests/test_plugin_entrypoints.py` 只验证 module 和属性可导入，不实例化 Workflow，也不执行约定方法。当前 `src/ui/views/plugin_runtime.py` 只加载 `entry_ui`，所以 core 错误在日常 GUI 路径中处于休眠状态。

最小修复需要先做架构选择：

- **方案 A：UI-only 插件模型。** 从 manifest 删除虚假的 `entry_core`，删除无调用方的 core 外壳；如果仓库没有真实 core 消费者，可进一步评估移除 `load_plugin_core()`。
- **方案 B：双入口插件模型。** 明确 Workflow 协议、让运行时真实装载 core、将 core 注入 UI，并为每个 manifest 增加实例化和最小行为测试。

该选择会改变公共插件契约，应由 Architecture Guardian 复核并记录 ADR。

### 4.3 [必须修复] 完整测试套件仍为红色

Python 3.10.20、完整 `requirements.txt` 环境执行：

```text
Ran 87 tests in 6.987s
FAILED (failures=1)
86 passed, 1 failed
```

失败项：`tests/test_api_client.py:72-102`

测试仍要求 `APIClient` 支持按认证上下文隔离的 `use_cache=True` 缓存，但缓存功能已经在提交 `0715d74` 中被主动删除。当前生产代码没有 `use_cache` 调用方，文档和函数签名也不再声明缓存能力。

根因是删除冗余实现时没有同步删除或更新契约测试。

最小修复：

1. 明确 APIClient 当前不提供缓存；
2. 删除或改写失效测试，不要只为让旧测试通过而重新引入无调用方缓存；
3. 如果仍需要缓存，必须重新定义失效策略、认证隔离、并发安全和响应对象生命周期后再实现。

## 5. 建议修改

### 5.1 [建议修改] 发布工作流没有测试门禁

`.github/workflows/release.yml` 是仓库唯一工作流。它在 Python 3.10 中安装依赖后直接构建 Windows 和 macOS 产物，没有执行：

- `unittest`；
- `compileall`；
- 静态检查；
- 插件 core 契约测试。

工作流还只在 `version.py` 变化时由 `push` 触发，所以普通业务提交没有持续验证。当前红测试和云考试双执行回归都能进入 v4.0.0，已经证明这不是理论风险。

建议增加独立 test job，在 PR 和普通 push 时运行；release build 必须依赖 test job 成功。

### 5.2 [建议修改] Browser 共享 helper 是零调用空抽象

位置：`src/core/browser.py:85-119`

提交 `5cc7c25` 新增：

- `DEFAULT_VIEWPORT`；
- `DEFAULT_USER_AGENT`；
- `create_browser_context()`。

但当前仓库只有定义，没有任何调用方。以下四处仍重复创建 Context/Page：

- `src/auth/_student_login.py`；
- `src/auth/teacher.py`；
- `src/extraction/extractor.py`；
- `src/certification/workflow.py`。

重复值还出现 Chrome 143、Chrome 144 和 Edge 144 三套 User-Agent，容易形成不可解释的运行差异。

建议真正迁移调用方，并对确实需要 Edge UA 的认证流程显式传 override；如果短期不迁移，应删除尚未产生价值的 helper，避免形成“文档说已统一、运行时仍分叉”的假象。

### 5.3 [建议修改] 删除失效的宿主 WeBan View

`src/ui/views/weban_view.py`：

- 没有运行时调用方；
- 插件入口实际使用 `plugins/weban_plugin/weban_view.py`；
- 仍引用已经不存在的 `src.modules.weban_adapter`；
- 文件约 801 行，并保留大量 DEBUG print 和旧 SnackBar 实现。

这是具备完整调用方证据的死代码，应优先删除，而不是继续维护或重构。

### 5.4 [建议修改] WeBan 专用输入框不应归宿主共享 UI 所有

`src/ui/dialogs/input_dialog.py` 中的 `WeBanInputDialog` 只被 WeBan 插件和上述失效 View 使用。插件当前通过 `src.ui.dialogs.input_dialog` 反向依赖宿主的插件专用实现。

建议将其迁移到 `plugins/weban_plugin/`，宿主 `src/ui` 只保留真正跨业务通用的组件。

### 5.5 [建议修改] 多个 package 的“延迟导入”名不副实

以下模块先声明“延迟导入以避免循环依赖”，随后又立即直接导入重依赖：

- `src/auth/__init__.py`；
- `src/extraction/__init__.py`；
- `src/certification/__init__.py`；
- `src/answering/__init__.py`。

只有 `src/core/__init__.py` 使用 `__getattr__` 真正实现按需加载。

这会导致导入纯数据或工具子模块时，也提前要求 Playwright/Flet 等运行时依赖。建议统一采用真实懒加载，或删除误导性的 getter 与注释，在完成调用方审计后收窄兼容导出。

### 5.6 [建议修改] 共享 UI helper 采用不完整

新增 `show_snack()` 后，以下三个区域仍保留 23 处原始 `ft.SnackBar` 样板：

- `plugins/warning_alert/ui.py`；
- `plugins/one_click_rating_for_projects/view.py`；
- `src/ui/views/settings_view.py`。

这不是立即故障，但 Flet API 频繁变动，继续并存会扩大兼容维护面。建议在下次触碰对应功能时逐块迁移，不需要为统一风格单独发动大改。

## 6. 仅供参考

### 6.1 [仅供参考] 两处 diff whitespace 问题

`git diff --check 1d6e88d..ad6e80c` 报告：

```text
plugins/one_click_rating_for_projects/view.py:1970: new blank line at EOF.
src/auth/student.py:159: new blank line at EOF.
```

不影响运行，可随下一次修复一起处理。

### 6.2 [仅供参考] Flet 控件弃用警告

测试构建 `AnswerProgressDialog` 时出现 `ElevatedButton` 已弃用警告。当前 Flet 0.82.2 仍可运行，但应在升级到 Flet 1.0 前迁移为 `Button`。

## 7. 建议处理顺序

### 第一阶段：恢复正确性和发布可信度

1. 修复 cloud_exam 双执行，并新增“业务回调只执行一次”的回归测试；
2. 解决 APIClient 缓存测试契约，使 87 项测试全绿；
3. 增加 CI test job，并让 release 依赖测试成功。

### 第二阶段：收束插件公共契约

1. 决定 UI-only 或 UI + core 双入口模型；
2. 记录 ADR；
3. 清理或修复 course_certification、evaluation、one_click_rating 的 `entry_core`；
4. 增加从 manifest 到 Workflow 最小行为的契约测试。

### 第三阶段：有证据地删除冗余

1. 删除 `src/ui/views/weban_view.py`；
2. 将 `WeBanInputDialog` 移入插件；
3. 完成或撤销零调用的 Browser Context helper；
4. 统一 package 懒加载策略；
5. 在下次触碰对应 UI 时迁移剩余 SnackBar 样板。

### 第四阶段：继续渐进式职责拆分

按用例边界拆分 `AnsweringView` 和 `certification/workflow.py`。每次只迁移一个责任，并用行为测试证明前后等价，避免把架构治理重新变成大规模无保护搬家。

## 8. 验证记录

```text
远端最新复核：reviewed HEAD == origin/main == ad6e80c
Python：3.10.20
完整依赖安装：成功，51 packages
unittest：87 tests，86 passed，1 failed
compileall：通过
cloud_exam 双执行复现：task_execution_count=2
插件 core 复现：课程认证参数错误、False 被报告成功、评估插件 AttributeError
git diff --check：2 个 EOF 空行问题
隔离审查 worktree：干净
本地 main：未覆盖，ahead 166 / behind 246
```

## 9. 最终门禁结论

```text
decision: BLOCK
risk_level: HIGH
maintenance_health: CRITICAL
adr_required: YES，仅针对插件 entry_core 公共契约选择
immediate_fix_scope:
  - cloud_exam 单任务单执行
  - APIClient 测试契约对齐
  - CI 测试门禁
required_follow_up:
  - debug-agent -> implementation-agent：修复双执行和红测试
  - architecture-guardian -> architecture-decision-recorder：决定插件 core 契约
  - refactor-agent：在契约明确后删除死代码和迁移插件专用 UI
```

总体评价：**这轮重构不是无效搬家，核心模块已经朝正确方向演进；但当前仍处于“结构改善明显、集成契约和发布纪律未跟上”的阶段。先修复运行错误和门禁，再继续做有限、可证明的清理。**
