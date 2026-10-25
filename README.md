<div align="center">

# ZX Answering Assistant

智能答题助手桌面工作台

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flet](https://img.shields.io/badge/Flet-0.82.2-0B6BFF.svg)](https://flet.dev/)
[![Playwright](https://img.shields.io/badge/Playwright-1.57%2B-green.svg)](https://playwright.dev/python/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg)](#预构建发布包)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE.txt)
[![Version](https://img.shields.io/badge/Version-v4.1.0-green.svg)](version.py)

一个基于 Flet、Playwright 和插件化架构构建的在线学习平台自动化辅助工具。

[快速开始](#快速开始) · [实现原理手记](docs/IMPLEMENTATION_NOTES.md) · [架构设计](docs/ARCHITECTURE.md) · [插件系统](#插件系统) · [配置说明](#配置说明) · [常见问题](#常见问题) · [免责声明](#disclaimer)

</div>

---

## 项目定位

说白了，这个项目想做的事情很朴素：把登录、选课、导入题库、处理评估这些来回点鼠标的操作，收进一个桌面工作台。页面交互交给 Playwright，适合直接请求的流程交给 HTTP 客户端，扩展功能则放进插件。

我本身编程基础有限，最开始也是从浏览器自动化一点点做起。准确性和稳定性不太理想，才开始看请求、读网页 JS。第一次只认识 SHA256，没弄懂 HMAC-SHA256 和硬编码 key 的关系，算不对就暂时放弃，继续用浏览器自动化。后来不甘心又重新研究，查清算法，再打断点找到签名前的原始值，终于算出了与抓包完全一致的签名。把这些结果整理给 AI 后，才完成 API 模式的开发。又经过多个版本的大更新和架构调整，项目慢慢长成了现在的样子——并不是一开始就设计好了这一切。

当前版本为 **v4.1.0，主程序仅提供 Flet GUI**。运行 `python main.py` 即可打开窗口，不再提供 `--cli` 菜单；配置文件还叫 `cli_config.json`，只是沿用了旧名字。

它不是“凭空知道答案”的工具：学生评估 API 模式依赖已导入题库，按题目 ID 匹配正确选项，缺失的题目会跳过。签名解决的是请求如何组织，不会变出答案，也不会赋予账号额外权限。

想看源码背后的折腾过程，可以读 [《从点按钮到读 JS：学生评估 API 实现手记》](docs/IMPLEMENTATION_NOTES.md)；想改代码，先看 [当前架构与设计取舍](docs/ARCHITECTURE.md)。

请在授权范围内使用本项目，并遵守目标平台、学校或组织的相关规则。

<a id="disclaimer"></a>

## ⚠️ 免责声明

**本项目仅供技术学习、研究与交流用途。**

- 本项目与足下教育（以及其他任何相关平台、组织）**没有任何关联**，亦未获得其任何形式的授权、支持或认可；
- 使用者应遵守所在地区法律法规及目标平台的服务条款，因下载、部署、使用或滥用本项目所产生的一切后果，**均由使用者自行承担**，与本项目作者无关；
- 对于使用本项目可能导致的账号封禁、数据丢失、成绩异常、学业或法律纠纷等任何问题，**本作者概不负责**；
- 本项目按“现状”提供，不提供任何明示或默示的保证；
- 如本项目侵犯了任何组织或个人的合法权益，请提交 Issue，我们将及时处理。

继续使用本项目即视为已阅读并同意本声明。

## 核心能力

| 能力 | 说明 |
| --- | --- |
| 工作台界面 | Flet 桌面应用，包含评估答题、答案提取、插件中心、系统设置和关于页面 |
| 插件化扩展 | 自动扫描 `plugins/`，通过 `manifest.json` 的 `entry_ui` 动态加载插件 UI（`entry_core` 已废弃，插件统一为 UI-only 模型） |
| 浏览器自动化 | `BrowserManager` 统一管理 Playwright，支持系统 Chrome、Edge、Playwright Chromium 和打包浏览器 |
| API 请求治理 | `APIClient` 提供限速、重试和统一请求入口 |
| 配置持久化 | `SettingsManager` 将账号、浏览器、限速、插件和托盘设置保存到用户配置目录 |
| 题库与答案处理 | 支持学生端答题、教师端答案提取、题库导入导出等基础流程 |
| Windows 托盘 | Windows 环境下支持最小化到托盘和关闭到托盘 |
| 桌面打包 | 使用 Flet 构建 Windows 可执行程序和 macOS `.app` 应用包 |

## 当前架构

### 启动链路

```text
main.py
  ├─ 配置 SSL 证书环境
  ├─ 准备 Playwright 浏览器路径
  ├─ 准备 Flet 运行环境
  ├─ 注册退出清理逻辑
  └─ src.main_gui.run_app()
       └─ MainApp
            ├─ 初始化核心单例
            ├─ 扫描 plugins/
            ├─ 构建 Flet 工作台
            └─ 根据设置启用系统托盘
```

### 分层结构

```text
Flet 主工作台（src/main_gui.py）
  ├─ 内置视图（src/ui/views/）
  │    └─ 登录 / 学生评估 / 题库提取等业务模块
  └─ 插件中心
       └─ PluginManager + PluginContext + open_plugin_ui
            └─ plugins/<id>/ui.py → 插件视图与业务服务

两条路径按需复用：
  ├─ APIClient → HTTP 请求、限速与重试
  ├─ BrowserManager → 专用工作线程 → 单浏览器、多上下文
  ├─ SettingsManager / TokenManager → 配置与会话缓存
  └─ 题库导入、答案匹配、进度对话框与后台任务组件
```

### 主要目录

| 路径 | 职责 |
| --- | --- |
| `main.py` | 应用入口，负责启动前环境配置、版本输出、浏览器准备和 GUI 启动 |
| `version.py` | 应用版本、构建信息和可选 WeBan 模块版本读取 |
| `src/main_gui.py` | Flet 主工作台，负责导航、页面缓存、插件初始化和托盘调度 |
| `src/ui/` | 共享主题、组件和工作台内置视图 |
| `src/core/` | 核心单例服务：配置、API、浏览器、插件、托盘 |
| `src/auth/` | 学生端、教师端登录和 token 管理 |
| `src/answering/` | 学生端答题流程，包含浏览器模式和 API 模式 |
| `src/extraction/` | 教师端答案提取、导入导出和文件处理 |
| `src/certification/` | 课程认证工作流和 API 答题逻辑 |
| `src/utils/` | 通用工具函数 |
| `plugins/` | 内置与外部插件目录，云考试等插件的 UI 与业务逻辑都位于各自插件目录 |
| `docs/` | 架构设计、API 实现手记，以及浏览器、SSL、Flet、构建等专题文档 |
| `tests/` | API 客户端、题库匹配/导入、插件、UI 组件与发布流程等测试 |

## 工作台页面

| 页面 | 说明 |
| --- | --- |
| 评估答题 | 面向学生端课程/任务的答题入口，复用登录、题库和答题模块 |
| 答案提取 | 面向教师端课程答案提取，支持生成可复用题库文件 |
| 插件中心 | 展示已安装插件，支持启用、禁用、查看详情和进入插件 UI |
| 系统设置 | 管理账号、API 限速与重试、浏览器通道、本地浏览器路径和托盘行为 |
| 关于 | 展示版本、项目说明和相关信息 |

界面样式集中在 `src/ui/theme.py` 和 `src/ui/components.py`，内置页面和插件页面应优先复用这些主题令牌与组件，避免各自维护一套视觉风格。

## 内置插件

| 插件目录 | 显示名称 | 入口 | 说明 |
| --- | --- | --- | --- |
| `plugins/cloud_exam` | 云考试助手 | `ui.create_view` | 云考试试卷获取、题库匹配和答案注入 |
| `plugins/course_certification` | 课程认证助手 | `ui.create_view` | 教师课程认证答题流程 |
| `plugins/evaluation` | 评估出题助手 | `ui.create_view` | AI 生成课程评估题，并按平台模板导出 Word/Excel |
| `plugins/one_click_rating_for_projects` | 摸鱼速评助手 | `ui.create_view` | 产教融合项目一键评分、批语生成与成绩 Excel 导出 |
| `plugins/weban_plugin` | 安全微伴 | `ui.create_view` | 安全微伴学习、考试和外部 WeBan 模块接入（默认禁用，需手动启用） |
| `plugins/warning_alert` | 警告提示器 | `ui.create_view` | 自定义警告窗口和循环提醒 |

## 快速开始

### 环境要求

- Python 3.10 或更高版本
- Windows 和 macOS 为当前桌面发布目标
- Linux 可用于部分开发调试流程
- Chrome、Edge 或 Playwright Chromium 至少一种可用浏览器

### 预构建发布包

GitHub Release 工作流会构建并上传以下桌面包：

| 平台 | 产物 |
| --- | --- |
| Windows x86-64 | `ZX-Answering-Assistant-<version>-windows-x86_64.zip` |
| macOS Intel | `ZX-Answering-Assistant-<version>-macos-x86_64.zip` |
| macOS Apple Silicon | `ZX-Answering-Assistant-<version>-macos-arm64.zip` |

macOS 包内包含 `ZX Answering Assistant.app`。如遇到 macOS 首次打开的安全提示，请在系统设置中允许该应用；确认包来源可信时，也可以对解压后的 `.app` 移除 quarantine 标记：

```bash
xattr -dr com.apple.quarantine "ZX Answering Assistant.app"
```

### 从源码运行

```bash
git clone https://github.com/404-Wont-Fix/ZX-Answering-Assistant-python.git
cd ZX-Answering-Assistant-python
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

如果系统没有可用的 Chrome 或 Edge，安装 Playwright Chromium:

```bash
python -m playwright install chromium
```

### 第一次打开，先做什么？

1. 在「系统设置」确认浏览器与账号配置。默认浏览器通道是 Chrome，没有 Chrome 时可选 Edge 或安装 Chromium。
2. 进入「评估答题」，登录自己的学生账号，选择课程。
3. 导入有权使用、且与课程对应的 JSON 题库，检查导入预览；单课程题库在双方课程 ID 均存在时会校验是否一致。
4. 选择处理方式，观察日志和进度；不要把“请求已发送”当成“平台已通过”。
5. 完成后回到平台核对状态。缺题、保存失败或交卷失败，都需要单独处理。

| 界面中的模式 | 实际做什么 | 依赖什么 |
| --- | --- | --- |
| 兼容模式 | 通过浏览器查找页面控件、选择选项并提交 | 登录页面、DOM 结构、题库匹配 |
| 暴力模式 | 用 API 获取题目、匹配选项 ID、生成签名并提交 | 有效 token、正确题库、接口协议 |

“暴力模式”是沿用的界面名称，**不是密码破解，也不是无限并发请求**。API 路径同样受限速、权限和评估次数限制；登录阶段仍会使用浏览器。

需要教师端提取题库时，从「答案提取」进入，并使用有相应权限的教师账号。学生登录不会自动获得教师权限。

### 可选：启用安全微伴

该插件默认禁用，并依赖 WeBan 子模块。源码环境先执行：

```bash
git submodule update --init -- plugins/weban_plugin/modules/WeBan
python -m pip install -r plugins/weban_plugin/requirements.txt
```

再到插件中心启用。具体依赖与用法见 [安全微伴说明](plugins/weban_plugin/README.md)。

## 配置说明

配置由 `src/core/config.py` 中的 `SettingsManager` 管理。默认配置文件不会写入仓库，而是保存在当前用户配置目录：

| 平台 | 默认位置 |
| --- | --- |
| Windows | `%APPDATA%\ZX-Answering-Assistant\cli_config.json` |
| macOS | `~/Library/Application Support/ZX-Answering-Assistant/cli_config.json` |
| Linux | `$XDG_CONFIG_HOME/ZX-Answering-Assistant/cli_config.json` 或 `~/.config/ZX-Answering-Assistant/cli_config.json` |

也可以通过环境变量指定配置文件：

```bash
ZX_ASSISTANT_CONFIG_FILE=/path/to/cli_config.json python main.py
```

配置内容主要包含：

| 配置段 | 内容 |
| --- | --- |
| `credentials` | 学生端、教师端和安全微伴账号信息 |
| `api_settings` | 最大重试次数和请求限速等级 |
| `browser_settings` | 是否无头、本地浏览器路径、浏览器通道 |
| `gui_settings` | 最小化到托盘、关闭到托盘 |
| `plugins` | 禁用插件列表和插件私有配置 |

**保存的账号密码写入本地 JSON，不是加密保险箱。** 请不要将个人配置、token、Cookie、HAR 抓包文件或未脱敏日志提交到仓库。

默认限速为 `very_high`（请求间隔 10 秒），其余等级为 `low` / `medium` / `medium_high` / `high`（1 / 2 / 3 / 5 秒）。名字表示延迟档位，不是“越高越快”。当前学生评估引擎还保留题间与知识点间等待，因此实际耗时不只取决于这个配置。

`max_retries` 当前实现表示**总尝试次数**（默认 5），不是“首次之外再试 5 次”；设置为 0 仍会尝试一次。旧配置加载时还有自动迁移逻辑，详见 [配置与请求治理设计](docs/ARCHITECTURE.md#配置与请求治理)。

## 浏览器策略

浏览器能力集中在 `src/core/browser.py`：

- 使用单例 `BrowserManager` 管理浏览器生命周期。
- Playwright 操作统一调度到专用工作线程，降低 Flet/AsyncIO 场景下的线程切换问题。
- 使用“单浏览器实例 + 多上下文”模型隔离不同业务模块的 Cookie、Session 和 LocalStorage。
- 支持的业务上下文包括 `STUDENT`、`TEACHER`、`COURSE_CERTIFICATION` 和 `CLOUD_EXAM`。
- 浏览器通道支持 `chrome`、`msedge`、`chromium` 和空字符串代表的 Playwright 内置/打包 Chromium。

开发环境默认优先使用系统浏览器。打包环境会优先尝试使用随包浏览器；如果不存在，会回退到用户缓存目录并提示安装 Chromium。

## 插件系统

### 加载流程

```text
plugins/<plugin_id>/manifest.json
  └─ PluginManager.scan_plugins()
       ├─ 校验插件 ID、名称和入口格式
       ├─ 合并用户启用/禁用状态
       ├─ 提示缺失的 requirements.txt 依赖
       └─ 用户打开插件时，按需加载 entry_ui
```

### 插件目录结构

```text
plugins/
└─ my_plugin/
   ├─ manifest.json      # 必需，插件元数据
   ├─ __init__.py        # 必需，Python 包标识
   ├─ ui.py              # 必需，提供 create_view(page, context)
   ├─ workflow.py        # 可选，由插件 UI 显式调用的业务逻辑
   └─ requirements.txt   # 可选，声明额外 Python 依赖
```

### manifest 示例

```json
{
  "id": "my_plugin",
  "name": "我的插件",
  "version": "1.0.0",
  "description": "插件描述",
  "icon": "extension",
  "author": "作者",
  "entry_ui": "ui.create_view",
  "entry_core": null,
  "min_app_version": "3.0.0",
  "dependencies": [],
  "enabled": true
}
```

插件是 **UI-only 入口模型**：`entry_core` 已废弃，应为 `null`，宿主不会加载它。业务逻辑可以拆到 `workflow.py`、`service.py` 等模块，但由插件自己调用。声明 `settings_schema` 的插件还可以复用插件中心的通用设置弹窗。

### 插件可用服务

插件入口会收到 `PluginContext`，可访问：

| 属性/方法 | 说明 |
| --- | --- |
| `context.plugin_id` | 当前插件 ID |
| `context.api_client` | 全局 API 客户端 |
| `context.browser_manager` | 全局浏览器管理器 |
| `context.settings_manager` | 全局配置管理器 |
| `context.run_task()` | 后台线程执行耗时任务 |
| `context.get_plugin_config()` | 读取插件私有配置 |
| `context.set_plugin_config()` | 保存插件私有配置 |

插件依赖不会在扫描阶段自动安装。若插件包含 `requirements.txt`，请在当前虚拟环境中显式执行：

```bash
python -m pip install -r plugins/<plugin_id>/requirements.txt
```

更多细节见 [PLUGIN_DEVELOPMENT.md](docs/PLUGIN_DEVELOPMENT.md) 和 [plugins/README.md](plugins/README.md)。

## 开发命令

安装依赖：

```bash
python -m pip install -r requirements.txt
```

运行应用：

```bash
python main.py
```

运行测试：

```bash
python -m pip install pytest
python -m pytest tests/ -v
```

测试依赖需另行安装。发布工作流中的构建任务依赖测试任务通过；本地测试不等于线上接口可用性验证。

查看当前版本：

```bash
python -c "import version; print(version.get_version_string())"
```

## 构建发布

当前仓库支持 Windows 和 macOS 桌面包构建。GitHub Actions 会在 Windows、macOS Intel 和 macOS Apple Silicon runner 上分别构建并上传 zip 包。

### Windows 本地构建

仓库提供 Windows 一键构建脚本：

```powershell
.\.venv\Scripts\Activate.ps1
.\build.bat
```

构建产物默认位于：

```text
build\windows\x64\runner\Release\ZX Answering Assistant.exe
```

### macOS 本地构建

macOS 需要在 macOS 主机上构建：

```bash
source .venv/bin/activate
flet build macos --project=ZX-Answering-Assistant --verbose
```

构建完成后，`.app` bundle 位于 `build/macos/` 下。CI 发布流程会查找该 `.app`，并使用 `ditto --keepParent` 打包为对应架构的 zip：

```text
release-assets/ZX-Answering-Assistant-<version>-macos-x86_64.zip
release-assets/ZX-Answering-Assistant-<version>-macos-arm64.zip
```

构建过程可能下载 Flutter SDK、Flet 运行时、Playwright 浏览器等资源，需要稳定访问 Google、GitHub 和 Python 包源。构建配置见 `pyproject.toml`。

相关文档：

- [编译打包指南](docs/BUILD_GUIDE.md)
- [Flet 安装与运行时指南](docs/FLET_SETUP.md)

## 常见问题

### Flet 无法启动或缺少 `flet_desktop`

确认依赖已安装，并且版本与项目锁定一致：

```bash
python -m pip install -r requirements.txt
```

更多说明见 [docs/FLET_SETUP.md](docs/FLET_SETUP.md)。

### Playwright 浏览器不可用

优先在“系统设置”中选择系统 Chrome 或 Edge。若需要 Playwright Chromium：

```bash
python -m playwright install chromium
```

网络受限时可参考 [docs/BROWSER_SETUP.md](docs/BROWSER_SETUP.md)。

### SSL 证书校验失败

程序启动时会自动通过 `certifi` 配置 SSL 证书环境变量。若仍失败，先更新证书包：

```bash
python -m pip install --upgrade certifi
```

详细排查见 [docs/SSL_SETUP.md](docs/SSL_SETUP.md)。

### 插件没有显示或无法加载

检查以下内容：

- 插件目录位于 `plugins/<plugin_id>/`。
- `manifest.json` 存在且是合法 JSON。
- `id` 仅包含小写字母、数字和下划线。
- `entry_ui` 使用 `模块.函数` 格式，例如 `ui.create_view`。
- 插件额外依赖已经通过 `requirements.txt` 手动安装。
- 依赖的其他插件已经启用。

### 系统托盘不可用

系统托盘当前只在 Windows 平台启用，并依赖 `pystray` 和 `Pillow`。非 Windows 环境下相关设置会自动降级，不影响主窗口运行。

## 文档索引

| 文档 | 内容 |
| --- | --- |
| [docs/IMPLEMENTATION_NOTES.md](docs/IMPLEMENTATION_NOTES.md) | 开发手记：从浏览器 Network、网页 JS 到学生评估签名与请求流程 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 当前架构、设计取舍、数据流、线程边界与已知限制 |
| [docs/PLUGIN_DEVELOPMENT.md](docs/PLUGIN_DEVELOPMENT.md) | 插件开发完整指南 |
| [plugins/README.md](plugins/README.md) | 插件目录、安装和依赖说明 |
| [docs/BROWSER_SETUP.md](docs/BROWSER_SETUP.md) | 浏览器安装、系统浏览器支持与排障 |
| [docs/FLET_SETUP.md](docs/FLET_SETUP.md) | Flet 安装、运行时和常见问题 |
| [docs/SSL_SETUP.md](docs/SSL_SETUP.md) | SSL 证书配置说明 |
| [docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md) | Windows 打包专题（当前跨平台构建入口见本页「构建发布」） |
| [docs/SYSTEM_TRAY_README.md](docs/SYSTEM_TRAY_README.md) | 系统托盘功能说明 |
| [CHANGELOG.md](CHANGELOG.md) | 版本更新记录 |

## 许可证

本项目使用 Apache License 2.0。详见 [LICENSE.txt](LICENSE.txt)。

## 致谢

感谢 Flet、Playwright、Requests、certifi、pystray、Pillow、openpyxl、python-docx，以及 WeBan 和各插件所依赖的开源项目。这个项目也是我边学边做、借助 AI 不断理解和修改代码的过程；如果它对你有帮助，欢迎反馈问题或点个 Star。
