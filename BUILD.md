# ZX Answering Assistant - 构建系统说明

## 概述

本项目的构建系统使用 PyInstaller 将 Python 项目打包为独立的可执行文件。构建系统已简化，移除了复杂的构建工具模块，只保留核心功能。

## 快速开始

### 前置要求

1. Python 3.8+
2. pip 包管理器

### 基本构建

```bash
# 构建目录模式（推荐）
python build.py --mode onedir

# 构建单文件模式
python build.py --mode onefile

# 同时构建两种模式
python build.py --mode both
```

### 高级选项

```bash
# 源码预编译（减小体积，轻度保护源码）
python build.py --compile-src

# 启用 UPX 压缩（减小 30-50% 体积）
python build.py --upx

# 指定构建输出目录
python build.py --build-dir D:\BuildOutput

# 组合选项（推荐）
python build.py --mode onedir --compile-src --upx
```

### 仅复制依赖

```bash
# 仅复制 Playwright 浏览器（不打包）
python build.py --copy-browser

# 仅下载 Flet 可执行文件（不打包）
python build.py --copy-flet

# 复制所有依赖（浏览器 + Flet，不打包）
python build.py --copy-all
```

## 输出说明

### 目录模式 (onedir)

- **输出位置**: `dist/ZX-Answering-Assistant-v2.7.0-windows-x64-installer/`
- **优点**: 启动速度快（10-20倍），易于更新
- **推荐**: 用于日常使用和分发

### 单文件模式 (onefile)

- **输出位置**: `dist/ZX-Answering-Assistant-v2.7.0-windows-x64-portable.exe`
- **优点**: 单个文件，易于携带
- **缺点**: 首次启动慢（需要解压）
- **推荐**: 用于临时使用或快速测试

## 首次运行

如果使用默认构建选项，首次运行打包后的可执行文件时，会自动下载以下组件：

1. **Playwright 浏览器**: Chromium 浏览器（约 300MB）
2. **Flet 可执行文件**: GUI 框架依赖（约 100MB）

下载完成后，可执行文件会正常启动。

**提示**: 如果在构建时使用了 `--copy-all` 或正常打包流程，浏览器和 Flet 会被打包到可执行文件中，首次运行无需下载。

## 常见问题

### 1. UPX 压缩失败

如果启用 `--upx` 但系统未安装 UPX，构建会自动跳过压缩。

**安装 UPX**:
- 下载: https://upx.github.io/
- Windows: 下载 `upx-4.2.2-win64.zip`，解压后将 `upx.exe` 添加到 PATH

### 2. 构建失败

- 确保网络连接正常（需要下载依赖）
- 确保有足够的磁盘空间（至少 2GB）
- 检查 Python 版本是否 >= 3.8

### 3. 路径包含中文

如果项目路径包含中文字符，使用 `--build-dir` 参数指定无中文的输出目录：

```bash
python build.py --build-dir D:\BuildOutput
```

## 构建系统特性

### 源码预编译 (`--compile-src`)

将 Python 源码编译为 .pyc 字节码，提供以下好处：

1. **减小体积**: 编译后的字节码比源码小 20-30%
2. **轻度保护**: 字节码比明文源码难于阅读
3. **清理源码**: onedir 模式下会自动删除打包后的 .py 文件

**使用方法**:
```bash
python build.py --compile-src
```

**注意**:
- `__init__.py` 文件会被保留（Python 包导入需要）
- .pyc 字节码文件会被保留
- onefile 模式下不会删除源码（由于 PyInstaller 限制）

### 浏览器/Flet 打包

构建时会自动处理 Playwright 浏览器和 Flet 可执行文件：

1. **Playwright 浏览器**: 从系统安装的 Playwright 中复制到项目目录
2. **Flet 可执行文件**: 从 GitHub 下载（使用国内镜像加速）

**使用方法**:
```bash
# 正常打包（自动包含浏览器和 Flet）
python build.py

# 仅复制依赖（不打包）
python build.py --copy-all
```

**下载源**:
- 默认使用 monlor 镜像（国内加速）
- 失败自动回退到 GitHub 官方源

## 构建系统变更 (v2.7.0)

### 新增的功能

- ✅ 源码预编译 (`--compile-src`)
- ✅ 构建时浏览器/Flet 自动打包
- ✅ 简化的构建工具模块 (`src/build_tools/`)
- ✅ 仅复制依赖选项 (`--copy-all`)

### 移除的功能

- ❌ 增量构建、缓存、并行构建等高级功能
- ❌ 代码签名、构建验证等企业功能
- ❌ 复杂的进度可视化和日志系统

### 保留的功能

- ✅ 基本的 onedir/onefile 打包
- ✅ UPX 压缩支持
- ✅ 依赖自动安装
- ✅ 版本信息更新

### 简化的原因

1. **维护成本**: 移除不常用的复杂功能
2. **可靠性**: 简化后的构建系统更稳定
3. **性能**: 保留核心功能，提升构建效率

## 技术细节

### PyInstaller 参数

```python
# 核心参数
--onedir / --onefile     # 打包模式
--clean                  # 清理缓存
--noconfirm              # 不询问确认
--optimize 2             # 优化字节码

# 数据文件
--add-data src;src       # 包含源代码目录
--add-data version.py;.  # 包含版本信息

# 隐藏导入
--hidden-import playwright
--hidden-import flet
--collect-all playwright
--collect-all flet

# 排除模块
--exclude-module matplotlib
--exclude-module numpy
--exclude-module pandas
```

### 版本管理

版本信息在 `version.py` 中管理：

- `VERSION`: 主版本号（如 "2.7.0"）
- `VERSION_NAME`: 应用名称
- `BUILD_DATE/TIME`: 构建时自动更新
- `GIT_COMMIT`: 构建时自动获取

## 开发与构建

### 开发环境

直接运行 Python 脚本：

```bash
python main.py
```

### 生产构建

使用构建脚本打包：

```bash
python build.py --mode onedir
```

构建完成后，将 `dist/` 目录中的相应文件夹分发给用户。

## 支持

如有问题，请查看：

- [CLAUDE.md](CLAUDE.md) - 项目架构文档
- [README.md](README.md) - 项目说明
- GitHub Issues - 报告问题
