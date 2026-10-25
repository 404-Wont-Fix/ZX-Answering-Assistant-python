# 当前架构与设计取舍

> 对照仓库 v4.1.0 源码整理。这是一份“现在代码怎么工作”的地图，不是把未来计划画成已经实现的功能。
>
> [返回 README](../README.md) · [阅读 API 实现手记](IMPLEMENTATION_NOTES.md) · [插件开发指南](PLUGIN_DEVELOPMENT.md)

## 1. 先说我们在做什么

ZX Answering Assistant 是一个本地桌面工作台：把登录、课程浏览、题库提取/导入、评估处理和插件操作放进同一个窗口。入口是 `python main.py`，主程序只有 GUI，不提供 CLI 菜单。

它不是新的教学平台，也没有自己的题目服务器。平台数据来自有权限的登录会话，题库来自授权提取或本地导入；应用负责组织流程，不负责赋予账号权限。本文只说明客户端实现，不把推测写成服务端协议保证。

### 设计目标与边界

| 目标 | 当前做法 | 不代表什么 |
| --- | --- | --- |
| 减少重复页面操作 | 浏览器交互与直接 API 请求并存 | 不保证页面或接口改版后仍然可用 |
| 登录会话互不串用 | 单浏览器、多 BrowserContext；token 分角色缓存 | 不是插件安全沙箱，也不是每个任务独立进程 |
| 避免阻塞窗口 | 耗时任务放后台，进度回到 UI 调度 | 不是所有旧路径都已完全统一 |
| 让扩展有落脚点 | `manifest.json` + `entry_ui` + `PluginContext` | 不再提供可自动加载的 core 入口 |
| 公共能力只维护一份 | 题库导入、ID 匹配、请求治理、进度组件复用 | 浏览器 DOM 匹配不必强行套用 API ID 匹配器 |

## 2. 总体关系：两条入口，不是层层套娃

这套结构不是一开始就规划好的。作者从有限的编程基础和浏览器自动化起步，第一次分析网页 JS 时将 HMAC-SHA256 误按普通 SHA256 理解，也没有弄懂硬编码 key 的用途，暂时退回浏览器方案。后来重新确认算法，通过断点取得签名前的原始变量值，计算结果与抓包签名一致，才将整理后的信息交给 AI 完成 API 模式开发。再经过多个版本的大更新与架构调整，形成当前分工。下面按现有源码说明结果，不为这段演进补造版本号或精确时间线。

内置页面不需要绕经插件才能调用业务。插件中心是另一条入口，两者共享基础服务。

```text
main.py
  └─ src/main_gui.py : MainApp
       ├─ 内置页面
       │    ├─ 评估答题 → src/auth/ + src/answering/
       │    ├─ 答案提取 → src/auth/ + src/extraction/
       │    └─ 系统设置 / 关于
       └─ 插件中心 → src/core/plugin_runtime.py
            └─ PluginManager → PluginContext → entry_ui
                 ├─ 云考试 → plugins/cloud_exam/ 内部实现
                 ├─ 课程认证 → 复用 src/ui/views/ 与 src/certification/
                 └─ 出题、评分、微伴、提醒等插件

上述业务按需使用：
  APIClient        → requests → 目标平台 API
  BrowserManager   → WorkerEngine → Playwright → 浏览器
  SettingsManager  → 用户目录中的配置 JSON
  TokenManager     → 进程内、分角色的 token 缓存
  共享题库/组件    → 文件导入、ID 匹配、进度与日志显示
```

这里用 Markdown 的 `text` 代码块画图。不需要 Mermaid、图片生成器或额外渲染环境，直接看源文件也能读。

### 从哪份代码开始看

| 文件/目录 | 主要责任 |
| --- | --- |
| [`main.py`](../main.py) | SSL、日志、版本、浏览器/Flet 环境准备、退出清理与启动 |
| [`src/main_gui.py`](../src/main_gui.py) | 导航、内置页面对象、视图内容缓存、托盘和退出调度 |
| [`src/ui/theme.py`](../src/ui/theme.py)、[`components.py`](../src/ui/components.py) | 主题、共享控件、题库提示、进度对话框与后台任务 helper |
| [`src/auth/student.py`](../src/auth/student.py) | 学生认证兼容 façade；实际修改应落到对应 `_student_*` 模块 |
| [`src/answering/api_answer.py`](../src/answering/api_answer.py) | 学生评估 API 编排、签名、保存答案与交卷 |
| [`src/answering/browser_answer.py`](../src/answering/browser_answer.py) | 浏览器兼容答题路径 |
| [`src/extraction/`](../src/extraction/) | 教师端提取、JSON 导出、题库导入服务 |
| [`src/core/`](../src/core/) | 配置、HTTP、浏览器、插件运行时与托盘等基础服务 |
| [`plugins/`](../plugins/) | 插件入口及插件自有业务模块 |

## 3. 为什么浏览器和 API 都留下了

浏览器模式与 API 模式不是“新旧版本二选一”，而是依赖不同。

- **浏览器兼容模式**依赖页面元素、选择器、选项内容以及页面提交反馈。页面布局变动容易影响它，但它能沿着页面交互走完整流程。
- **API 模式**依赖 token、题目/选项 ID、请求字段、签名及服务端业务状态。不必逐题点 DOM，但任何协议变化都需要重新核对。
- **登录仍借助浏览器**：学生登录模块监听 `/connect/token` 响应取得 `access_token`。因此“API 模式”指答题阶段，不是完全不启动浏览器。

GUI 里沿用的“暴力模式”是直接 API 模式的名称，不是暴力破解、并发轰炸或权限绕过。

## 4. 学生评估的数据流

### 正常路径

```text
学生登录 → 捕获 token → 选择课程
                          │
授权题库 JSON → 导入/预览 ─┘
                          ↓
                 创建 APIAutoAnswer
                          ↓
        读取课程详情 + 未完成章节/知识点
                          ↓
       按 isPass / times 预检查，排除已通过或次数用尽项
                          ↓
                  beginevaluate（签名）
                          ↓
                    questionList
                          ↓
                  按题目 ID 匹配题库
                    ├─ 无答案 → 记 skipped
                    └─ 有答案 → 选项 ID 用逗号拼接
                                      ↓
                           SaveEvaluateAnswer（签名）
                                      ↓
                          逐题记录 success / failed
                          ↓
               SaveTestMemberInfo（签名，questions=[]）
                          ↓
                   汇总日志与进度
                          ↓
                用户在平台核对最终业务状态
```

图中是非空题目列表的正常流程。开始评估失败、无题、次数用尽等会提前返回；保存和交卷异常的统计限制见第 9 节。

### 三种数据不要混成一份

| 数据 | 作用 | 来源 |
| --- | --- | --- |
| 登录 token | 表明当前账号会话身份 | 浏览器登录响应，交给 `TokenManager` 缓存 |
| 题库答案 | 题目 ID 对应的正确选项 ID | 导入 JSON 中的题目及 `isTrue` 选项标记 |
| 请求签名 | 按前端约定构造请求校验值 | `APIAutoAnswer.generate_sign()`，HMAC-SHA256 |

有签名不等于有登录权限；有登录权限不等于知道正确答案。签名细节、大小写陷阱和网页 JS 分析过程放在 [实现手记](IMPLEMENTATION_NOTES.md)，这里不再维护第二份完整算法说明。

### 题库为什么单独抽服务

[`bank_service.py`](../src/extraction/bank_service.py) 的 `load_question_bank()` 负责导入、预览和课程校验，返回 `BankLoadResult`。`apply_bank_result()` 决定是否替换视图里的题库：成功时替换，课程不匹配时清除，其他导入异常保留原值。

课程 ID 检查不是全覆盖校验：目前针对单课程题库，且双方 ID 均存在时才比较。不要把“导入成功”写成“所有题目都与当前课程一致”。

[`bank_matcher.py`](../src/utils/bank_matcher.py) 的 `find_correct_answer_ids()` 负责纯 API 路径的 ID 精确匹配：

- 支持 `class.course.chapters`、顶层 `chapters`、`courses[].chapters`、`course_list[].chapters` 四种题库组织方式；
- 兼容常见题目 ID 与选项 ID 字段名；
- 读取 `isTrue` 为真的选项，返回选项 ID；
- 不按标题模糊搜索，不调用 AI 猜答案。

学生评估、课程认证、云考试复用这个匹配器。浏览器模式要拿到页面可点击的 value/内容，继续使用自己的匹配逻辑，这是有意保留的差异。

## 5. 线程、浏览器与窗口

### 后台线程不是 Playwright 对象的“任意通行证”

同步 Playwright 有线程归属要求，不能拿到一个 `Page` 就在任意线程调用。项目用 `BrowserManager` 和专用 `WorkerEngine` 管理这些操作。

```text
Flet 事件 / 界面操作
  └─ 后台任务：HTTP、文件、业务编排
       ├─ APIClient → HTTP 请求
       └─ BrowserManager.submit_task(...)
            └─ WorkerEngine 队列
                 └─ 专用工作线程：Playwright 页面操作

业务进度 / 完成 / 异常
  └─ UI 调度 → 更新对话框、日志与页面
```

公共 helper `run_background_task()` 使用 `page.run_thread()` 执行工作，通过 `page.run_task()` 调度结束回调。`AnswerProgressDialog` 的进度与日志更新也回到 UI 调度。频繁进度回调不要直接在 worker 中调用 `page.update()`。

这描述的是公共机制和新增代码应遵循的边界，不意味着旧 View 中所有线程代码都已经迁移完成。

### 单浏览器、多上下文

```text
BrowserManager
  └─ 一个 Playwright Browser
       ├─ STUDENT               → 学生端 Context / Page
       ├─ TEACHER               → 教师端 Context / Page
       ├─ COURSE_CERTIFICATION  → 课程认证 Context / Page
       └─ CLOUD_EXAM            → 云考试 Context / Page
```

上下文隔离 Cookie、LocalStorage 等浏览器会话状态；应用层仍可按业务显式使用已有学生 token，因此不能把 Context 隔离理解成应用中所有凭据绝不共享。

通过 `get_browser_manager()` 获取全局管理器，不在各业务模块另建浏览器管理器。安装检测与通道选择在 `_browser_installer.py`，线程队列和恢复在 `_worker_engine.py`。

### 卡住以后怎么办

`WorkerEngine.submit_task()` 等待结果超时阈值为 300 秒。超时会触发 `reset_worker()`：终止相关进程树、提升 worker 代际、清空浏览器状态并处理待执行队列，后续提交任务时重建 worker。

这不是“把卡住的 Python 线程杀掉”，也不是透明续跑。原浏览器会话可能丢失，业务可能需要重新登录；新任务不会自动证明旧请求没有在服务器执行过。

主窗口则缓存内置视图内容，减少切换页面时的状态丢失。关闭到托盘与真正退出是两回事：托盘当前仅支持 Windows，真正退出才走资源清理路径。

<a id="配置与请求治理"></a>

## 6. 配置与请求治理

### 配置与 token 分开

- `SettingsManager` 将配置保存到用户目录下的 `cli_config.json`，路径及覆盖环境变量见 [README 配置说明](../README.md#配置说明)。
- 配置通过临时文件替换写入，并尝试限制文件权限；**保存的账号密码仍是 JSON 明文**，不是加密凭据库。
- `TokenManager` 在进程内为学生、教师、认证分别维护带锁的缓存槽。默认本地有效期为 17400 秒，不是向服务器查询后保证的剩余有效期。
- 本地缓存未过期，服务端仍可能撤销会话；重新登录与权限错误不能用“再签一次”代替。

### 请求只走统一入口

学生评估等主业务请求通过 `get_api_client()` 取得 `APIClient`：

| 行为 | 当前实现 |
| --- | --- |
| 默认超时 | 未显式传入时为 30 秒 |
| 请求间隔 | `low` / `medium` / `medium_high` / `high` / `very_high` = 1 / 2 / 3 / 5 / 10 秒 |
| 默认配置 | `very_high`，总尝试次数 5 |
| 重试条件 | 指定网络异常、超时、HTTP 429、HTTP 5xx |
| 退避 | 按尝试轮次等待 `2 ** attempt` 秒，每次请求仍应用限速 |
| 最终返回 | 2xx 返回 Response；最终非 2xx 或请求异常通常返回 `None` |
| 业务成功 | 由具体接口继续检查 JSON 中的 `code`、`success`、`data` 等字段 |

`max_retries` 虽然叫“重试次数”，实现中是总尝试次数，0 也至少请求一次。配置加载还会把旧 `high` 升为 `very_high`、把不足 5 的次数升到 5；解释用户实际配置时要考虑迁移，不能只看写入值。

统一客户端并未消除所有历史等待：学生评估引擎还保留题间 1.5 秒、知识点间 3 秒等待和一层局部重试包装。新增业务不要继续堆 `sleep`。

尤其注意：当前客户端没有按 GET/POST 区分幂等重试。保存答案或交卷超时，不一定意味着服务端未处理；不要承诺“自动重试绝不会重复提交”。

## 7. 插件：入口统一，内部不强制长成一样

```text
plugins/<id>/manifest.json
  ↓ 扫描：ID、目录、入口格式、版本与依赖声明校验
用户配置决定 enabled
  ↓ 用户打开插件
open_plugin_ui()
  ↓ 创建 PluginContext，注入核心服务
load_plugin_ui() → entry_ui(page, context)
  ↓
插件自己调用 workflow / service / api_client 等模块
```

- `entry_ui` 是唯一运行入口；`entry_core` 废弃并保留为 `null`，不是另一条隐形工作流。
- `PluginContext` 提供 API、浏览器、设置、后台任务及资源登记；插件不要再造同名全局服务。
- 声明 `settings_schema` 后复用通用设置弹窗，配置存到 `plugins.plugin_specific_configs.<id>`。
- 扫描只提示额外 Python 依赖，不会自动 `pip install`。
- 插件运行在宿主 Python 进程中，只有可信代码才应安装；“插件系统”不等于“隔离沙箱”。

**边界现状**：云考试完整放在 `plugins/cloud_exam/`；课程认证和评估出题仍有复用宿主视图/业务的入口包装。新改动应尊重现有边界，不新增 `src/cloud_exam/` 这样的重复目录。

## 8. 教师端提取与其他平台

教师题库提取沿着“班级 → 课程 → 章节 → 知识点 → 题目 → 选项”组织数据，由 exporter 保存 JSON，再由 importer/bank_service 导入。层级是数据组织关系，不代表每个接口参数都沿用上一层 ID；实际参数以 `extractor.py` 为准。

学生评估、教师提取、课程认证与云考试是不同接口族。域名相近、都带 `Answer`，并不意味着可共用提交体或签名规则。特别是本文讨论的 HMAC-SHA256 来自学生评估引擎，不能原封不动搬给其他模块。

## 9. 已知限制：文档别比程序更乐观

以下是当前源码行为，不是本次文档更新已修复的问题：

1. **统计不等于成绩**：学生评估的 `success` 统计单题保存成功，不代表答案被判正确；`completed_knowledges` 对有题的已处理知识点计数，不能证明交卷成功或平台已通过。
2. **缺题仍可能交卷**：单题未匹配会跳过、保存失败会记失败；只要流程继续走完题目循环，仍会尝试 `SaveTestMemberInfo`。不是“全题成功才允许交卷”。
3. **错误归类不够细**：开始评估失败、无题、次数用尽都可能产生零题统计，上层会把其中一些情况归为跳过。返回值还没有完整表达这些差别。
4. **停止不是即时中断**：当前 `_check_stop()` 在题目/知识点处理标志仍为真时继续等待，通常在知识点处理结束后才退出；已发出的请求不会撤回。
5. **签名有格式约束**：JSON 字段顺序、大小写、空格、编码都会影响签名。现有实现不意味着已经覆盖未来前端的所有规范化规则。
6. **日志需要脱敏**：当前学生 API 引擎会记录签名原文、签名和请求体，不能直接把整份日志或 HAR 发到公开 Issue。
7. **测试覆盖有缺口**：现有测试涵盖 APIClient、题库、插件和部分 UI 等；目前未见专门覆盖学生评估签名协议三条请求的测试文件。不能以公共组件测试通过代替签名与线上业务验证。

后续优先考虑显式的交卷结果字段、可区分的失败状态、POST 重试策略和脱敏日志。这些是改进建议，当前没有在本文中宣称完成。

## 10. 如何验证与继续维护

本地基本检查：

```bash
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pytest tests/ -v
```

发布流程见 [`.github/workflows/release.yml`](../.github/workflows/release.yml)：测试是单独 job，构建依赖其成功后再分别生成 Windows、macOS Intel 与 Apple Silicon 产物。

维护学生评估协议时，建议增加纯离线测试：固定虚构 key 与 ID，检查签名原文、请求体和编码；通过 fake APIClient 覆盖保存失败、交卷失败、次数用尽与空列表，不能为跑测试消耗真实评估次数。

历史审查保留在 [`ARCHITECTURE_EVOLUTION_AND_REDUNDANCY_REVIEW_2026-07-18.md`](ARCHITECTURE_EVOLUTION_AND_REDUNDANCY_REVIEW_2026-07-18.md)，只代表其中标注的提交，不应用它推断当前仍有相同缺陷。当前架构以本页和源码为准。
