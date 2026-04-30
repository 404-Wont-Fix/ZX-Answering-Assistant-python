<div align="center">

# ZX Answering Assistant

## 智能答题助手系统

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE.txt)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![Version](https://img.shields.io/badge/Version-v3.5.1-green.svg)](https://github.com/TianJiaJi/ZX-Answering-Assistant-python/releases)

**一个基于 Playwright 的在线学习平台自动化答题助手系统**

支持 **插件化架构**，提供浏览器兼容模式和 API 暴力模式两种答题方式。

[功能特性](#功能特性) • [技术架构](#技术架构) • [快速开始](#快速开始) • [插件开发](#插件开发) • [常见问题](#常见问题)

</div>

---

## 目录

- [程序介绍](#程序介绍)
- [功能特性](#功能特性)
- [技术架构](#技术架构)
- [快速开始](#快速开始)
- [打包构建](#打包构建可选)
- [使用指南](#使用指南)
- [插件开发](#插件开发)
- [常见问题](#常见问题)
- [许可证](#许可证)
- [致谢](#致谢)

---

## 程序介绍

**ZX Answering Assistant（智能答题助手）** 是一个专为在线学习平台设计的自动化工具，采用插件化架构设计，支持功能模块的动态加载和扩展。

### 核心定位

- **学生端**: 自动化答题、课程进度管理、学习数据统计
- **教师端**: 题库提取、教学辅助、学情分析
- **课程认证**: 快速完成课程认证要求
- **插件扩展**: 支持自定义插件开发和安装

### 设计目标

1. **插件化架构**: 核心功能与扩展功能分离，支持动态加载
2. **效率优先**: 通过自动化工具减少重复性劳动
3. **用户友好**: 提供直观的 GUI 界面
4. **安全可靠**: 智能速率控制、自动重试、崩溃恢复等机制

---

## 功能特性

### 插件化架构

| 特性 | 描述 |
|------|------|
| **动态加载** | 插件可独立开发、测试、部署 |
| **依赖注入** | 统一的服务接口，插件共享核心资源 |
| **状态持久化** | 插件配置和状态自动保存 |
| **一键管理** | 图形化插件管理界面，启用/禁用一键切换 |

### 内置插件

| 插件 | 功能 | 状态 |
|------|------|------|
| **云考试助手** | 云考试答题、题库匹配 | ✅ 可用 |
| **课程认证助手** | 教师课程认证答题 | ✅ 可用 |
| **评估出题助手** | 评估出题功能 | ✅ 可用 |

### 核心功能

#### 🌐 系统浏览器支持

- **智能检测**: 自动检测系统已安装的浏览器（Chrome/Edge）
- **零配置启动**: 无需下载 170MB 浏览器，直接使用系统浏览器
- **体积优化**: 打包体积减少 80%（200MB → 40MB）
- **自动降级**: 智能选择最佳浏览器，确保程序始终可用
- **详细文档**: 查看 [系统浏览器支持指南](docs/SYSTEM_BROWSER_SUPPORT.md)

#### 🎨 启动动画系统

- **启动画面**: 应用启动时显示品牌标识和渐变背景
- **加载界面**: 显示加载进度和组件初始化状态
- **用户体验**: 视觉反馈提升，缓解启动等待感
- **一键编译**: 使用 `build.bat` 自动清理并编译

#### 学生端功能

- **自动登录**: 支持账户密码自动登录学生端
- **课程管理**: 图形化显示课程列表和完成进度
- **智能答题**: 两种模式可选
  - **浏览器兼容模式**: 模拟真实用户操作（约 2-3 题/秒）
  - **API 暴力模式**: 直接调用 API 接口（约 10-20 题/秒）
- **网络重试**: 连接失败自动重试（最多 3 次）
- **题库导入**: 支持 JSON 格式题库导入
- **进度监控**: 实时追踪课程完成情况

#### 教师端功能

- **教师登录**: 图形化登录界面
- **答案提取**: 一键提取课程答案
- **自动保存**: 提取完成自动保存为 JSON 文件
- **文件管理**: 一键打开文件夹、复制文件路径

#### 安全微伴功能 (WeBan)

- **自动学习**: 自动完成必修课、推送课、自选课
- **智能考试**: 基于题库自动匹配正确答案
- **OCR 验证码**: 自动识别验证码（失败后手动输入）
- **实时进度**: 显示学习进度和考试统计

---

## 技术架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      用户界面层 (Flet)                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │
│  │  导航栏     │ │  内容区域   │ │     插件中心视图         │ │
│  └─────────────┘ └─────────────┘ └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      插件管理层                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              PluginManager (插件管理器)                  │ │
│  │  • 插件扫描  • 插件加载  • 生命周期管理  • 状态持久化   │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ 云考试插件  │ │ 课程认证插件│ │ 评估出题插件│            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      核心服务层                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ APIClient   │ │BrowserMgr   │ │ ConfigMgr   │            │
│  │ (API请求)   │ │ (浏览器管理)│ │ (配置管理)  │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      基础设施层                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ Playwright  │ │  Requests   │ │ 文件系统    │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

### 分层架构说明

| 层级 | 职责 | 主要组件 |
|------|------|----------|
| **用户界面层** | 用户交互和界面展示 | MainGUI, PluginCenterView |
| **插件管理层** | 插件发现、加载、生命周期管理 | PluginManager, PluginContext |
| **核心服务层** | 为插件提供共享的基础服务 | APIClient, BrowserManager, ConfigManager |
| **基础设施层** | 底层技术支撑 | Playwright, Requests, 文件系统 |

### 项目目录结构

```
ZX-Answering-Assistant-python/
├── main.py                          # 应用程序入口
├── version.py                       # 版本信息
├── requirements.txt                 # 依赖列表
│
├── plugins/                         # 插件目录
│   ├── cloud_exam/                  # 云考试插件
│   │   ├── manifest.json            # 插件元数据
│   │   ├── __init__.py
│   │   ├── ui.py                    # UI 入口
│   │   └── core.py                  # 业务逻辑
│   ├── course_certification/        # 课程认证插件
│   ├── evaluation/                  # 评估出题插件
│   └── README.md                    # 插件开发指南
│
├── src/
│   ├── core/                        # 核心服务层
│   │   ├── api_client.py            # API 客户端
│   │   ├── browser.py               # 浏览器管理器
│   │   ├── config.py                # 配置管理器
│   │   ├── plugin_manager.py        # 插件管理器
│   │   └── plugin_context.py        # 插件上下文
│   │
│   ├── auth/                        # 认证模块
│   │   ├── student.py               # 学生端登录
│   │   ├── teacher.py               # 教师端登录
│   │   └── token_manager.py         # Token 管理
│   │
│   ├── answering/                   # 答题模块
│   │   ├── api_answer.py            # API 模式答题
│   │   └── browser_answer.py        # 浏览器模式答题
│   │
│   ├── certification/               # 课程认证核心逻辑
│   │   ├── workflow.py
│   │   └── api_answer.py
│   │
│   ├── cloud_exam/                  # 云考试核心逻辑
│   │   ├── api_client.py
│   │   ├── models.py
│   │   └── workflow.py
│   │
│   ├── extraction/                  # 数据提取模块
│   │   ├── extractor.py
│   │   ├── exporter.py
│   │   └── importer.py
│   │
│   ├── ui/                          # UI 层
│   │   ├── main_gui.py              # 主 GUI 入口
│   │   └── views/                   # 视图组件
│   │       ├── answering_view.py
│   │       ├── cloud_exam_view.py
│   │       ├── course_certification_view.py
│   │       ├── plugin_center_view.py
│   │       └── settings_view.py
│   │
│   ├── modules/                     # 扩展模块
│   │   ├── WeBan/                   # 安全微伴模块
│   │   ├── weban_adapter.py
│   │   └── weban_runner.py
│   │
│   └── utils/                       # 工具模块
│       └── retry.py
│
├── CLAUDE.md                        # Claude Code 指导文档
├── PLUGIN_DEVELOPMENT.md            # 插件开发指南
└── README.md                        # 项目文档
```

---

## 技术栈

### 核心依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| **flet** | ≥0.82.0 | GUI 框架 |
| **playwright** | ≥1.57.0 | 浏览器自动化 |
| **requests** | ≥2.31.0 | HTTP 客户端 |

### WeBan 模块依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| **ddddocr** | 1.6.1 | OCR 验证码识别 |
| **loguru** | 0.7.3 | 日志处理 |
| **pycryptodome** | 3.23.0 | 加密解密 |

---

## 快速开始

### 环境要求

- Python 3.10+
- Windows 操作系统

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/TianJiaJi/ZX-Answering-Assistant-python.git
cd ZX-Answering-Assistant-python
```

2. **创建虚拟环境**

```bash
python -m venv .venv
.venv\Scripts\activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **安装 Playwright 浏览器**

**方法1: 自动安装（推荐）**
```bash
python -m playwright install chromium
```

**方法2: 使用本地浏览器**
```bash
# 编辑 cli_config.json，添加本地浏览器路径
# "browser_settings": {"local_browser_path": "C:\\Path\\To\\chrome.exe"}
```

**⚠️ 重要提示**: 如果遇到浏览器安装问题：
- 程序启动时会自动尝试安装浏览器
- 详见：[浏览器安装指南](BROWSER_INSTALL_GUIDE.md)

5. **运行程序**

```bash
python main.py
```

### 打包构建（可选）

如果你想将程序打包成独立的 Windows 可执行文件：

#### ⚠️ 网络环境要求

**重要：构建过程需要访问 Google 和 GitHub 服务，请确保网络环境能正常访问这些服务！**

构建过程会下载约 1.5-2 GB 资源（Flutter SDK、Flet 运行时、Playwright 浏览器等）。

**如果无法访问 Google/GitHub**：
- 使用代理（推荐）
- 配置国内镜像（详见 BUILD_GUIDE.md）
- 或在良好网络环境下构建

#### 快速构建

```bash
# 1. 激活虚拟环境
.venv\Scripts\activate

# 2. 运行构建脚本
build.bat
```

#### 构建产物

可执行文件位于：`build\windows\x64\runner\Release\ZX Answering Assistant.exe`

#### 详细文档

- **[编译打包指南](docs/BUILD_GUIDE.md)** - 详细步骤和配置说明
- **[快速参考](docs/BUILD_QUICKREF.md)** - 常用命令速查

---

## 使用指南

### 启动应用

```bash
python main.py
```

### 使用插件

1. 启动后点击左侧导航栏的"插件中心"
2. 在"我的插件"和"插件管理"之间切换
3. 使用开关启用/禁用插件
4. 点击信息图标查看插件详情

### 安装新插件

1. 点击"插件管理"视图中的"打开插件目录"按钮
2. 将插件文件夹复制到打开的目录中
3. 重启应用，新插件将自动被发现

---

## 插件开发

详细的插件开发指南请参阅 [PLUGIN_DEVELOPMENT.md](PLUGIN_DEVELOPMENT.md)。

### 快速开始

1. **创建插件目录**

```
plugins/
└── my_plugin/
    ├── manifest.json     # 插件元数据
    ├── __init__.py
    ├── ui.py             # UI 入口
    └── core.py           # 业务逻辑
```

2. **编写 manifest.json**

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
  "enabled": true
}
```

3. **实现 UI 入口**

```python
# plugins/my_plugin/ui.py
import flet as ft

def create_view(page, context):
    return ft.Column([
        ft.Text("我的插件"),
    ])
```

4. **重启应用**

新插件将自动被发现并显示在插件中心。

---

## 常见问题

### 1. SSL 证书验证失败

**问题**: 在新环境部署时出现 SSL 证书验证错误

**错误信息**:
```
<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
unable to get local issuer certificate (_ssl.c:1000)>
```

**解决方案**:

**✅ 自动配置 (v3.2.0+)**

从 v3.2.0 开始，程序内置了自动 SSL 证书配置功能，无需手动干预。

程序会在启动时：
1. 自动检查并安装 `certifi` 根证书包
2. 配置全局 SSL 证书设置
3. 配置 urllib 和 requests 的 SSL 上下文

**🔧 手动修复** (如果自动配置失败)

1. **更新 certifi**:
   ```bash
   pip install --upgrade certifi
   ```

2. **设置环境变量** (临时解决):
   ```powershell
   # PowerShell
   $env:SSL_CERT_FILE = python -c "import certifi; print(certifi.where())"
   python main.py
   ```

3. **运行测试脚本**:
   ```bash
   python test_ssl.py
   ```

**详细指南**: 查看 [SSL 证书配置指南](docs/SSL_SETUP.md)

### 2. Flet 库安装问题

**问题**: Flet GUI 库未安装或版本不兼容

**解决方案**:

1. **自动安装**: 程序启动时会自动检测并安装 Flet
2. **手动安装**:
   ```bash
   pip install flet>=0.82.0
   pip install flet-desktop
   ```
3. **使用项目依赖**:
   ```bash
   pip install -r requirements.txt
   ```
4. **国内镜像加速**:
   ```bash
   pip install flet -i https://pypi.tuna.tsinghua.edu.cn/simple
   pip install flet-desktop -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

**⚠️ 重要提示**:
- Flet 首次运行时会自动下载桌面运行时文件（约 50-100MB），可能需要 1-3 分钟，这是正常行为
- **Flet 0.8.0+ 需要同时安装 `flet` 和 `flet-desktop` 两个包**

**错误: `No module named 'flet_desktop'`**

如果看到这个错误，说明缺少 `flet-desktop` 包：

```bash
pip install flet-desktop
```

**📥 如果自动下载失败**：请查看 [Flet 可执行文件手动下载指南](FLET_MANUAL_DOWNLOAD.md)

**详细指南**: 查看 [Flet 安装指南](FLET_INSTALL_GUIDE.md)

### 3. 浏览器启动失败

**问题**: Playwright 浏览器未安装或无法下载

**解决方案**:

1. **自动安装**: 程序启动时会自动尝试安装浏览器
2. **手动安装**:
   ```bash
   python -m playwright install chromium
   ```
3. **使用本地浏览器**: 编辑 `cli_config.json`，添加浏览器路径
   ```json
   {
     "browser_settings": {
       "local_browser_path": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
     }
   }
   ```
4. **网络问题**: 使用国内镜像
   ```bash
   # Windows PowerShell
   $env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright/"
   python -m playwright install chromium
   ```

**详细指南**: 查看 [浏览器安装指南](BROWSER_INSTALL_GUIDE.md)

### 4. 插件无法加载

**问题**: manifest.json 格式错误或缺少必要字段

**解决方案**: 检查 manifest.json 格式，确保包含 `id`、`name`、`version`、`entry_ui` 字段。

### 5. API 请求失败

**问题**: 网络连接问题或 Token 过期

**解决方案**: 检查网络连接，重新登录获取新 Token。

---

## 版本历史

### v3.5.0 (2026-04-27)

- 🎨 **优化**: 清理项目结构，移除多余文件和文档
- 🔧 **优化**: 清理不必要的依赖（pyyaml、py7zr）
- 📝 **简化**: 整合文档，提高可维护性
- 🐛 **修复**: 保留所有 v3.4.1 的功能修复

### v3.4.1 (2026-04-27)

- 🎨 **新增**: 启动动画系统
- ⚡ **新增**: 一键构建脚本 (`build.bat`)
- 🐛 **修复**: `__builtins__` 兼容性问题
- 🐛 **修复**: Flet API 兼容性问题（v0.82.2）
- 🐛 **修复**: 软件标题乱码
- 🐛 **修复**: 启动屏幕中文显示
- 🐛 **修复**: ImportError: No module named main

### v3.2.0 (2026-04-23)

- 🔒 **新增**: 自动 SSL 证书配置功能
  - 解决 Windows 环境下的 SSL 验证失败问题
  - 自动安装和配置 certifi 根证书包
  - 配置 urllib、requests 的 SSL 上下文
  - 新增 SSL 测试工具 (`test_ssl.py`)
- 📝 **文档**: 新增 SSL 证书配置指南 (`docs/SSL_SETUP.md`)
- 🐛 **修复**: Flet 首次下载时的 SSL 证书验证错误
- 📦 **依赖**: 添加 certifi 到 requirements.txt

### v3.0.0 (2026-04-21)

- 🎉 完成插件化架构重构
- ✨ 新增插件中心视图
- ✨ 支持插件动态加载和管理
- ✨ 新增依赖注入系统
- 🐛 修复多个 UI 问题
- 📝 完善插件开发文档

### v2.9.0

- ✨ 集成 WeBan 安全微伴模块
- ✨ 支持 OCR 验证码识别
- 🐛 修复浏览器崩溃恢复问题

### v2.8.0

- ✨ 优化构建系统
- ✨ 新增配置文件化构建
- 🐛 修复多个已知问题

---

## 许可证

本项目采用 Apache 2.0 许可证，详见 [LICENSE.txt](LICENSE.txt)。

---

## 致谢

感谢以下开源项目和贡献者：

### 核心依赖

- **[Flet](https://github.com/flet-dev/flet)** - 现代化的 Python Flutter GUI 框架
- **[Playwright](https://github.com/microsoft/playwright)** - 微软开发的浏览器自动化框架
- **[Requests](https://github.com/psf/requests)** - 优雅的 Python HTTP 库

### 特别感谢

#### 🌟 WeBan 项目

本项目的安全微伴（WeBan）插件基于 **[WeBan](https://github.com/hangone/WeBan)** 项目开发。

**原项目作者**: [hangone](https://github.com/hangone)

**WeBan** 是一个优秀的**安全微伴学习平台自动化工具**，提供了：

- ✅ 自动学习课程功能
- ✅ 智能答题系统
- ✅ OCR 验证码识别
- ✅ 完善的 API 客户端
- ✅ 稳定的加密解密方案

本项目的 WeBan 插件在原项目基础上进行了：
- 🔧 插件化改造
- 🎨 GUI 界面集成
- 🚀 性能优化
- 📚 文档完善

**致谢原项目作者 hangone 的开源精神和优秀代码！**

### 其他开源项目

- **[ddddocr](https://github.com/sml2h3/ddddocr)** - 优秀的验证码识别库
- **[loguru](https://github.com/Delgan/loguru)** - 简单易用的 Python 日志库
- **[pycryptodome](https://github.com/Legrandin/pycryptodome)** - 强大的 Python 加密库

### 社区贡献

感谢所有为本项目提交 Issue、PR 和建议的开发者！

---

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 联系方式

- 作者: TianJiaJi
- 邮箱: notify@mail.tianjiaji.top
- GitHub: [https://github.com/TianJiaJi/ZX-Answering-Assistant-python](https://github.com/TianJiaJi/ZX-Answering-Assistant-python)
