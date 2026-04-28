# 编译打包指南

本文档详细说明如何将 ZX Answering Assistant 编译打包为独立的 Windows 可执行文件。

## 目录

- [环境要求](#环境要求)
- [快速开始](#快速开始)
- [详细步骤](#详细步骤)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [高级选项](#高级选项)

---

## 环境要求

### 必需软件

- **Python**: 3.10 或更高版本
- **操作系统**: Windows 10/11
- **Git**: 用于克隆项目（可选）

### Python 依赖

所有依赖已列在 `requirements.txt` 中：

```txt
flet>=0.82.0
flet-desktop>=0.21.0
playwright>=1.57.0
requests>=2.31.0
certifi>=2024.0.0
pycryptodome>=3.19.0
loguru>=0.7.0
ddddocr>=1.5.0
```

---

## 快速开始

### ⚠️ 重要：网络环境要求

**构建过程需要访问 Google 和 GitHub 服务！**

构建会下载约 1.5 GB 资源（Flutter SDK、Flet、Playwright 浏览器等）。

**如果网络无法访问 Google/GitHub**：
- 使用代理（推荐）
- 配置国内镜像（PyPI、Playwright 等）
- 或在能访问 Google 的网络环境下构建

### 一键构建

```bash
# 1. 激活虚拟环境
.venv\Scripts\activate

# 2. 运行构建脚本
build.bat
```

构建产物位于：`build\windows\x64\runner\Release\`

---

## 详细步骤

### 步骤 1: 准备环境

#### 1.1 创建虚拟环境

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
.venv\Scripts\activate
```

#### 1.2 安装依赖

```bash
# 安装所有依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
python -m playwright install chromium
```

### 步骤 2: 构建配置

#### 2.1 pyproject.toml 配置说明

项目使用 `pyproject.toml` 进行 Flet 构建配置。主要配置项：

```toml
[tool.flet]
# 项目名称
project = "ZX-Answering-Assistant"
# 产品名称
product = "ZX Answering Assistant"
# 组织名称
org = "TianJiaJi"

# 启动画面配置
[tool.flet.splash]
color = "#0B6BFF"
dark_color = "#1a1a1a"

# 包含文件配置
[tool.flet.include]
assets = [
    "main.py",
    "version.py",
]
```

**重要说明**：

1. **assets 配置**：指定需要打包的资源文件
   - 只包含必需的入口文件
   - 其他 Python 文件会自动检测并包含

2. **排除文件**：
   - Flet 默认会排除 `build/`、`dist/` 等目录
   - 不支持在 `pyproject.toml` 中配置排除规则
   - 如需精确控制，建议在干净的环境中构建

### 步骤 3: 执行构建

#### 3.1 清理旧构建

```bash
# 删除旧的构建文件
rmdir /s /q build
rmdir /s /q dist
```

#### 3.2 运行构建命令

**方法 1: 使用 build.bat（推荐）**

```bash
build.bat
```

**方法 2: 手动执行 Flet 命令**

```bash
flet build windows --project=ZX-Answering-Assistant
```

**方法 3: 详细模式（调试用）**

```bash
flet build windows --project=ZX-Answering-Assistant --verbose
```

### 步骤 4: 验证构建

#### 4.1 检查构建产物

构建成功后，可执行文件位于：

```
build\windows\x64\runner\Release\ZX Answering Assistant.exe
```

#### 4.2 测试运行

```bash
# 运行打包后的程序
"build\windows\x64\runner\Release\ZX Answering Assistant.exe"
```

---

## 配置说明

### pyproject.toml 完整配置

```toml
[project]
name = "zx-answering-assistant"
version = "3.5.0"
description = "Intelligent Answering Assistant System"
requires-python = ">=3.10"

dependencies = [
    "flet>=0.82.0",
    "requests>=2.31.0",
    "certifi>=2024.0.0",
    "playwright>=1.57.0",
    "flet-desktop>=0.21.0",
    "pycryptodome>=3.19.0",
    "loguru>=0.7.0",
    "ddddocr>=1.5.0",
]

[tool.flet]
project = "ZX-Answering-Assistant"
product = "ZX Answering Assistant"
org = "TianJiaJi"
description = "Intelligent Answering Assistant System"
copyright = "Copyright © 2026 TianJiaJi"

# 启动画面配置
[tool.flet.splash]
color = "#0B6BFF"
dark_color = "#1a1a1a"

# Boot screen - 首次启动解压时显示
[tool.flet.app.boot_screen]
show = true
message = "正在准备首次启动"

# Startup screen - Python 运行时初始化时显示
[tool.flet.app.startup_screen]
show = true
message = "正在加载组件"

# Windows 平台特定配置
[tool.flet.windows.app.startup_screen]
show = true
message = "正在初始化应用"

# 包含必要的文件
[tool.flet.include]
assets = [
    "main.py",
    "version.py",
]
```

### 配置项说明

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| `project` | 项目名称 | `ZX-Answering-Assistant` |
| `product` | 产品名称（显示在窗口标题） | `ZX Answering Assistant` |
| `org` | 组织名称 | `TianJiaJi` |
| `description` | 应用描述 | `Intelligent Answering Assistant System` |
| `copyright` | 版权信息 | `Copyright © 2026 TianJiaJi` |
| `splash.color` | 启动画面背景色 | `#0B6BFF` |
| `include.assets` | 需要包含的资源文件 | `["main.py", "version.py"]` |

---

## 常见问题

### 1. 构建失败：网络下载问题 ⚠️

**症状**：
```
Failed to download Flet executable
TimeoutError: Download timeout
Connection refused
```

**原因**：构建需要下载 Flutter SDK（~1GB）和其他资源，需要访问 Google/GitHub

**解决方案**：

**方案 A：使用代理（推荐）**
```bash
# 设置代理
$env:HTTPS_PROXY = "http://127.0.0.1:7890"

# 重新构建
flet build windows --project=ZX-Answering-Assistant
```

**方案 B：配置镜像**
```bash
# PyPI 镜像
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# Playwright 镜像
$env:PLAYWRIGHT_DOWNLOAD_HOST = "https://npmmirror.com/mirrors/playwright/"
```

**方案 C：在良好网络环境构建**
- 使用能访问 Google 的网络
- 或在公司/学校外网环境构建

### 2. 构建失败：Flet 未安装

**错误信息**：
```
'flet' 不是内部或外部命令
```

**解决方案**：

```bash
# 安装 Flet
pip install flet>=0.82.0

# 安装 Flet Desktop（必需！）
pip install flet-desktop
```

#### 7. 构建失败：找不到模块

**错误信息**：
```
ModuleNotFoundError: No module named 'xxx'
```

**解决方案**：

```bash
# 确保所有依赖已安装
pip install -r requirements.txt

# 检查虚拟环境是否激活
where python
# 应该显示 .venv\python.exe
```

#### 8. 构建体积过大

**原因**：包含了不必要的文件

**解决方案**：

1. **在干净目录中构建**：
   ```bash
   # 创建新目录
   mkdir build_env
   cd build_env

   # 只复制必需文件
   mkdir src
   copy ..\main.py src\
   copy ..\version.py src\
   xcopy ..\src src\ /E /I
   xcopy ..\plugins plugins\ /E /I
   copy ..\requirements.txt .
   copy ..\pyproject.toml .

   # 安装依赖并构建
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   flet build windows
   ```

2. **使用 UPX 压缩**（Flet 默认启用）

### 4. 构建后程序无法运行

**可能原因**：

1. **缺少运行时依赖**：
   - 检查是否包含所有必要的资源文件
   - 确认 `pyproject.toml` 中 `assets` 配置正确

2. **Playwright 浏览器未打包**：
   ```bash
   # 程序首次运行时会自动下载浏览器
   # 或预先下载到 dist 目录
   python -m playwright install chromium
   ```

3. **SSL 证书问题**：
   - 程序内置自动配置功能（v3.2.0+）
   - 如仍有问题，查看 [SSL_SETUP.md](SSL_SETUP.md)

### 5. 构建时间过长

**正常情况**：
- 首次构建：5-10 分钟
- 后续构建：2-5 分钟

**优化建议**：

1. **使用缓存**：
   ```bash
   # 不清理 build 目录
   # Flet 会复用缓存
   ```

2. **减少依赖**：
   - 检查 `requirements.txt` 是否有冗余依赖

---

## 高级选项

### 自定义构建参数

#### 指定输出目录

```bash
flet build windows --project=ZX-Answering-Assistant --output=dist
```

#### 调试模式

```bash
# 保留调试符号
flet build windows --project=ZX-Answering-Assistant --debug

# 显示详细日志
flet build windows --project=ZX-Answering-Assistant --verbose
```

### 分发准备

#### 1. 创建安装包

使用 Inno Setup 或 NSIS 创建安装程序：

**Inno Setup 示例脚本**：

```iss
[Setup]
AppName=ZX Answering Assistant
AppVersion=3.5.0
DefaultDirName={pf}\ZX Answering Assistant
DefaultGroupName=ZX Answering Assistant
OutputDir=installer
OutputBaseFilename=ZX-Answering-Assistant-Setup

[Files]
Source: "build\windows\x64\runner\Release\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ZX Answering Assistant"; Filename: "{app}\ZX Answering Assistant.exe"
```

#### 2. 压缩分发

```bash
# 创建 ZIP 压缩包
powershell Compress-Archive -Path "build\windows\x64\runner\Release" -DestinationPath "ZX-Answering-Assistant-v3.5.0.zip"
```

---

## 构建脚本说明

### build.bat

项目提供的一键构建脚本：

```batch
@echo off
echo 正在清理旧的构建文件...
if exist "build\windows" rmdir /s /q "build\windows"
if exist "build\flutter" rmdir /s /q "build\flutter"
if exist "dist" rmdir /s /q "dist"

echo 正在编译应用...
flet build windows --project=ZX-Answering-Assistant --verbose

if %ERRORLEVEL% EQU 0 (
    echo 编译成功！
    echo 产物位置: build\windows\x64\runner\Release
) else (
    echo 编译失败，请检查错误信息
)
pause
```

---

## 最佳实践

### 1. 版本控制

- 在 `version.py` 中维护版本号
- 每次发布前更新版本号
- 在 Git 中打标签

### 2. 构建环境

- 使用独立的虚拟环境
- 定期清理缓存
- 在干净目录中测试构建

### 3. 测试流程

1. 本地运行测试
2. 构建可执行文件
3. 在干净 Windows 系统中测试
4. 检查所有功能是否正常

### 4. 持续集成

可以使用 GitHub Actions 自动构建：

```yaml
name: Build Windows

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Build
        run: |
          flet build windows --project=ZX-Answering-Assistant
      - name: Upload artifact
        uses: actions/upload-artifact@v2
        with:
          name: ZX-Answering-Assistant
          path: build\windows\x64\runner\Release\
```

---

## 相关文档

- [Flet 官方文档 - 发布应用](https://flet.dev/docs/publish/)
- [浏览器安装指南](BROWSER_SETUP.md)
- [SSL 证书配置](SSL_SETUP.md)
- [Flet 安装指南](FLET_SETUP.md)

---

## 更新日志

### v3.5.0 (2026-04-28)
- 📝 更新编译文档
- 🎨 优化 pyproject.toml 配置
- 🔧 简化构建流程
