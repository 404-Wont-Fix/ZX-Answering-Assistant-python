<div align="center">

# ZX Answering Assistant

智能答题助手桌面工作台

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flet](https://img.shields.io/badge/Flet-0.82.2-0B6BFF.svg)](https://flet.dev/)
[![Playwright](https://img.shields.io/badge/Playwright-1.57%2B-green.svg)](https://playwright.dev/python/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg)](#预构建发布包)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE.txt)
[![Version](https://img.shields.io/badge/Version-v3.7.4-green.svg)](version.py)

一个基于 Flet、Playwright 和插件化架构构建的在线学习平台自动化辅助工具。

[快速开始](#快速开始) · [当前架构](#当前架构) · [插件系统](#插件系统) · [配置说明](#配置说明) · [构建发布](#构建发布) · [常见问题](#常见问题)

</div>

---

## 项目定位

ZX Answering Assistant 是一个桌面端自动化工作台，面向在线学习、课程认证、题库提取和扩展插件场景。当前版本以 GUI 模式为主，主界面由 Flet 驱动，自动化能力由 Playwright、HTTP API 客户端和插件工作流共同提供。

请在授权范围内使用本项目，并遵守目标平台、学校或组织的相关规则。

## 核心能力

| 能力 | 说明 |
| --- | --- |
| 工作台界面 | Flet 桌面应用，包含评估答题、答案提取、插件中心、系统设置和关于页面 |
| 插件化扩展 | 自动扫描 `plugins/`，通过 `manifest.json` 和入口点动态加载插件 UI 与核心逻辑 |
| 浏览器自动化 | `BrowserManager` 统一管理 Playwright，支持系统 Chrome、Edge、Playwright Chromium 和打包浏览器 |
| API 请求治理 | `APIClient` 提供限速、重试、GET 缓存和统一请求入口 |
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
┌────────────────────────────────────────────────────────────┐
│ GUI 工作台层                                                │
│ src/main_gui.py, src/ui/theme.py, src/ui/components.py      │
│ src/ui/views/*                                             │
└──────────────────────────────┬─────────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────┐
│ 插件层                                                      │
│ plugins/*/manifest.json, ui.py, core.py                    │
│ PluginManager + PluginContext                              │
└──────────────────────────────┬─────────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────┐
│ 核心服务层                                                  │
│ SettingsManager, APIClient, BrowserManager, AppState, Tray  │
└──────────────────────────────┬─────────────────────────────┘
                               │
┌──────────────────────────────▼─────────────────────────────┐
│ 业务与基础设施层                                            │
│ auth, answering, extraction, cloud_exam, certification      │
│ requests, Playwright, certifi, filesystem                   │
└────────────────────────────────────────────────────────────┘
```

### 主要目录

| 路径 | 职责 |
| --- | --- |
| `main.py` | 应用入口，负责启动前环境配置、版本输出、浏览器准备和 GUI 启动 |
| `version.py` | 应用版本、构建信息和可选 WeBan 模块版本读取 |
| `src/main_gui.py` | Flet 主工作台，负责导航、页面缓存、插件初始化和托盘调度 |
| `src/ui/` | 共享主题、组件和工作台内置视图 |
| `src/core/` | 核心单例服务：配置、API、浏览器、插件、托盘、SSL 和应用状态 |
| `src/auth/` | 学生端、教师端登录和 token 管理 |
| `src/answering/` | 学生端答题流程，包含浏览器模式和 API 模式 |
| `src/extraction/` | 教师端答案提取、导入导出和文件处理 |
| `src/cloud_exam/` | 云考试数据模型、API 客户端和工作流 |
| `src/certification/` | 课程认证工作流和 API 答题逻辑 |
| `src/utils/` | 通用工具，目前主要是重试辅助 |
| `plugins/` | 内置与外部插件目录 |
| `docs/` | 浏览器、SSL、Flet、构建和系统浏览器等专题文档 |
| `tests/` | 配置、插件和 API 客户端相关测试 |

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
| `plugins/cloud_exam` | 云考试助手 | `ui.create_view`, `core.Workflow` | 云考试试卷获取、题库匹配和答案注入 |
| `plugins/course_certification` | 课程认证助手 | `ui.create_view`, `core.Workflow` | 教师课程认证答题流程 |
| `plugins/evaluation` | 评估出题助手 | `ui.create_view`, `core.Workflow` | 评估出题、试题生成和编辑入口 |
| `plugins/weban_plugin` | 安全微伴 | `ui.create_view`, `core.WeBanPluginCore` | 安全微伴学习、考试和外部 WeBan 模块接入 |
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
git clone https://github.com/TianJiaJi/ZX-Answering-Assistant-python.git
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

请不要将真实账号、密码或个人配置提交到仓库。

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
       └─ 按需加载 UI 或核心类
```

### 插件目录结构

```text
plugins/
└─ my_plugin/
   ├─ manifest.json      # 必需，插件元数据
   ├─ __init__.py        # 必需，Python 包标识
   ├─ ui.py              # 必需，提供 create_view(page, context)
   ├─ core.py            # 可选，提供业务工作流类
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
  "entry_core": "core.Workflow",
  "min_app_version": "3.0.0",
  "dependencies": [],
  "enabled": true
}
```

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

更多细节见 [PLUGIN_DEVELOPMENT.md](PLUGIN_DEVELOPMENT.md) 和 [plugins/README.md](plugins/README.md)。

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
python -m pytest
```

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
- [编译快速参考](docs/BUILD_QUICKREF.md)
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

网络受限时可参考 [docs/BROWSER_SETUP.md](docs/BROWSER_SETUP.md) 和 [docs/SYSTEM_BROWSER_SUPPORT.md](docs/SYSTEM_BROWSER_SUPPORT.md)。

### SSL 证书校验失败

程序启动时会先执行 `src/core/ssl_helper.py` 中的 SSL 自动配置。若仍失败，先更新证书包：

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
| [PLUGIN_DEVELOPMENT.md](PLUGIN_DEVELOPMENT.md) | 插件开发完整指南 |
| [plugins/README.md](plugins/README.md) | 插件目录、安装和依赖说明 |
| [docs/BROWSER_SETUP.md](docs/BROWSER_SETUP.md) | Playwright 浏览器安装与排障 |
| [docs/SYSTEM_BROWSER_SUPPORT.md](docs/SYSTEM_BROWSER_SUPPORT.md) | 系统 Chrome/Edge 支持说明 |
| [docs/FLET_SETUP.md](docs/FLET_SETUP.md) | Flet 安装、运行时和常见问题 |
| [docs/SSL_SETUP.md](docs/SSL_SETUP.md) | SSL 证书配置说明 |
| [docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md) | Windows 打包完整指南 |
| [docs/BUILD_QUICKREF.md](docs/BUILD_QUICKREF.md) | 构建命令速查 |
| [SYSTEM_TRAY_README.md](SYSTEM_TRAY_README.md) | 系统托盘功能说明 |
| [CHANGELOG.md](CHANGELOG.md) | 版本更新记录 |

## 许可证

本项目使用 Apache License 2.0。详见 [LICENSE.txt](LICENSE.txt)。

## 致谢

感谢 Flet、Playwright、Requests、certifi、pystray、Pillow、ddddocr、DrissionPage、loguru 和 pycryptodome 等开源项目提供的基础能力。
