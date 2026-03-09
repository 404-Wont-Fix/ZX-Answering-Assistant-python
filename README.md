<div align="center">

# ZX Answering Assistant
### 智能答题助手系统

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE.txt)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Mac-lightgrey)]())
[![Version](https://img.shields.io/badge/Version-v2.6.6-green)]()

一个基于 Playwright 的自动化答题系统，支持 **GUI 图形界面** 和 **CLI 命令行** 两种交互方式，提供浏览器兼容模式和 API 暴力模式两种答题方式。

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [使用指南](#-使用指南) • [常见问题](#-常见问题)

</div>

---

## 目录

- [项目简介](#-项目简介)
- [功能特性](#-功能特性)
- [系统架构](#-系统架构)
- [快速开始](#-快速开始)
- [使用指南](#-使用指南)
- [打包分发](#-打包分发)
- [项目结构](#-项目结构)
- [技术栈](#-技术栈)
- [版本管理](#-版本管理)
- [常见问题](#-常见问题)
- [开发规范](#-开发规范)
- [免责声明](#-免责声明)

---

## 项目简介

ZX Answering Assistant 是一个针对在线学习平台的自动化答题助手系统。通过浏览器自动化技术和 API 逆向分析，实现题目提取、答案匹配和自动答题等功能。

### 核心特点

- **双界面支持**：现代化 GUI 界面（Flet）+ 传统 CLI 命令行
- **双模式支持**：浏览器兼容模式 + API 暴力模式
- **双端支持**：学生端答题 + 教师端答案提取
- **智能速率控制**：可配置的 API 请求速率限制（1000ms-5000ms）
- **自动重试**：网络错误自动重试机制（最多3次）
- **优雅退出**：按 Q 键随时停止，等待当前题目/知识点完成
- **进度监控**：实时显示答题进度和统计信息
- **题库管理**：支持题库导入/导出，支持 JSON 和 Excel 格式
- **自动保存**：提取的答案自动保存为 JSON 文件
- **可视化界面**：图形化操作流程，实时进度显示
- **统一配置**：CLI 模式支持配置文件管理账号和设置
- **浏览器自动恢复**：v2.2.0 新增 - 浏览器崩溃后可重新登录恢复
- **AsyncIO 兼容**：v2.2.0 新增 - GUI 模式完全兼容 Playwright 同步 API
- **浏览器管理器**：v2.6.0 新增 - 统一的浏览器实例管理，支持多上下文隔离
- **课程认证模块**：v2.6.0 新增 - 支持课程认证题库导入和 API 答题
- **源码自动清理**：v2.6.6 新增 - 打包后自动删除 .py 源码，只保留 .pyc 字节码

---

## 功能特性

### 用户界面

| 界面类型 | 描述 | 状态 |
|---------|------|------|
| **GUI 模式** | 现代化图形界面，操作简单直观 | ✅ |
| **CLI 模式** | 传统命令行界面，功能完整 | ✅ |

### 学生端功能

| 功能 | 描述 | 状态 |
|------|------|------|
| 自动登录 | 支持账户密码自动登录学生端 | ✅ |
| 课程管理 | 图形化显示课程列表和完成进度 | ✅ |
| 自动答题 | 浏览器模拟点击，自动匹配答案 | ✅ |
| API 模式 | 直接调用 API，无需浏览器操作 | ✅ |
| 网络重试 | 连接失败自动重试（3次） | ✅ |
| 随时停止 | 按 Q 键优雅退出 | ✅ |
| 实时统计 | 显示答题成功率和进度 | ✅ |
| 题库加载 | 支持导入 JSON 题库文件 | ✅ |
| **浏览器崩溃恢复** | v2.2.0 - 浏览器意外退出后可重新登录恢复 | ✅ |
| **GUI AsyncIO 兼容** | v2.2.0 - 完美兼容 Flet 的 asyncio 事件循环 | ✅ |
| **统一浏览器管理** | v2.6.0 - 单浏览器实例 + 多上下文，降低资源占用 | ✅ NEW |
| **课程认证答题** | v2.6.0 - 支持课程认证题库导入和 API 答题 | ✅ NEW |

### 教师端功能

| 功能 | 描述 | 状态 |
|------|------|------|
| 教师登录 | 图形化登录界面，紫色主题 | ✅ |
| 班级选择 | 左右分栏选择年级和班级 | ✅ |
| 课程选择 | 卡片化展示所有课程 | ✅ |
| 答案提取 | 一键提取课程答案，实时进度显示 | ✅ |
| 自动保存 | 提取完成自动保存为 JSON 文件 | ✅ |
| 提取统计 | 显示知识点、题目、选项数量 | ✅ |
| 文件管理 | 打开文件夹、复制文件路径 | ✅ |

### 答题模式对比

| 特性 | 浏览器兼容模式 | API 暴力模式 |
|------|----------------|--------------|
| 速度 | 较慢 | 极快 |
| 稳定性 | 高 | 高 |
| 资源占用 | 高（需浏览器） | 低 |
| 检测风险 | 较高 | 中等 |
| 推荐场景 | 验证答案准确性 | 快速刷题 |

---

## 系统架构

### 核心架构

```
┌─────────────────────────────────────────────────────────────┐
│                        ZX 智能答题助手                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │   主程序入口  │────────▶│   模式选择   │                  │
│  │  (main.py)   │         │   (GUI/CLI)  │                  │
│  └──────┬───────┘         └──────┬───────┘                  │
│         │                       │                          │
│         ▼                       ▼                          │
│   ┌─────────────────────────────────────────────────────────┐ │
│   │                    GUI 模式 (Flet)                   │ │
│   │  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐ │ │
│   │  │  导航栏      │  │  答题/提取  │  │  设置管理     │ │ │
│   │  └──────────────┘  └──────┬───────┘  └───────────────┘ │ │
│   │                           │                              │ │
│   │                  ┌──────┴──────────────┐                 │ │
│   │                  │                      │                 │ │
│   │                  ▼                      ▼                 │ │
│   │           ┌───────────────┐     ┌───────────────┐      │ │
│   │           │  答题界面     │     │  提取界面     │      │ │
│   │           │                │     │                │      │ │
│   │           │  • 学生登录     │     │  • 教师登录     │      │ │
│   │           │  • 课程选择     │     │  • 年级选择     │      │ │
│   │           │  • 题库导入     │     │  • 班级选择     │      │ │
│   │           │  • 自动答题     │     │  • 课程选择     │      │ │
│   │           │  • 实时日志     │     │  • 进度显示     │      │ │
│   │           │  • 课程认证     │     │  • 结果保存     │      │ │
│   │           │    (v2.6.0)    │     │                │      │ │
│   │           └─────────────────┘     └───────────────┘      │ │
│   │                                                           │
│   └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                   浏览器管理器 (v2.6.0)                   │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  单浏览器实例 + 多上下文模式                        │ │ │
│  │  │                                                     │ │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │ │ │
│  │  │  │ 学生端上下文  │  │ 教师端上下文  │  │ 认证上下文 │ │ │ │
│  │  │  │ (STUDENT)    │  │ (TEACHER)    │  │(COURSE_)  │ │ │ │
│   │  │  │              │  │              │  │  CERT)    │ │ │ │
│   │  │  └──────────────┘  └──────────────┘  └───────────┘ │ │ │
│   │  │                                                     │ │ │
│   │  │  完全隔离：Cookie、Session、LocalStorage            │ │ │
│   │  └─────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### 核心模块说明

**主程序**
- [main.py](main.py) - 双模式入口，GUI/CLI 切换
- [src/main_gui.py](src/main_gui.py) - GUI 主程序（Flet 框架）

**浏览器管理** (v2.6.0)
- [src/browser_manager.py](src/browser_manager.py) - 统一浏览器实例管理，支持多上下文隔离
  - 单浏览器实例模式（降低资源占用）
  - 线程安全的工作队列机制
  - 自动清理和资源释放

**GUI 界面模块**
- [src/ui/views/answering_view.py](src/ui/views/answering_view.py) - 学生答题界面
- [src/ui/views/extraction_view.py](src/ui/views/extraction_view.py) - 答案提取界面
- [src/ui/views/settings_view.py](src/ui/views/settings_view.py) - 设置管理界面
- [src/ui/views/course_certification_view.py](src/ui/views/course_certification_view.py) - 课程认证界面 (v2.6.0)

**学生端模块**
- [src/student_login.py](src/student_login.py) - 学生端登录、浏览器健康监控、AsyncIO 兼容
- [src/auto_answer.py](src/auto_answer.py) - 浏览器兼容模式答题
- [src/api_auto_answer.py](src/api_auto_answer.py) - API 暴力模式答题

**课程认证模块** (v2.6.0)
- [src/course_certification.py](src/course_certification.py) - 课程认证题库管理
- [src/course_api_answer.py](src/course_api_answer.py) - 课程认证 API 答题

**教师端模块**
- [src/teacher_login.py](src/teacher_login.py) - 教师端登录
- [src/extract.py](src/extract.py) - 答案提取（带进度回调）

**数据管理**
- [src/export.py](src/export.py) - 数据导出（JSON）
- [src/question_bank_importer.py](src/question_bank_importer.py) - 题库导入

**系统配置**
- [src/api_client.py](src/api_client.py) - 统一 API 请求客户端（支持速率限制和重试）
- [src/settings.py](src/settings.py) - CLI 设置管理（账号、速率级别等）

**构建工具**
- [build.py](build.py) - PyInstaller 打包脚本（支持源码预编译、双版本编译）
  - `--compile-src` - 预编译源码为 .pyc 字节码
  - `--upx` - UPX 压缩支持
  - `--mode` - onedir/onefile/both
- [src/build_tools/flet_handler.py](src/build_tools/flet_handler.py) - Flet 可执行文件处理

---

## 快速开始

### 环境要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows / Linux / macOS
- **网络**: 稳定的互联网连接
- **浏览器**: Chromium（自动安装）

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/ZX-Answering-Assistant-python.git
cd ZX-Answering-Assistant-python
```

### 2. 创建虚拟环境

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器（必需）
python -m playwright install chromium
```

### 4. 运行程序

#### 方式一：GUI 模式（推荐）

```bash
python main.py
# 或
python main.py --mode gui
```

#### 方式二：CLI 模式

```bash
python main.py --mode cli
```

---

## 使用指南

### GUI 模式（推荐）

#### 启动应用

```bash
python main.py
```

#### 界面导航

应用启动后会显示左侧导航栏：

```
┌──────────────────────────────────┐
│  首页                               │
│  评估答题                           │
│  课程认证                           │
│  答案提取                           │
│  设置                               │
└──────────────────────────────────┘
```

#### 评估答题流程

1. **导航到"评估答题"页面**
2. **学生登录**：
   - 输入用户名和密码
   - 点击"登录"按钮
3. **加载题库**：
   - 点击"导入题库"按钮
   - 选择 JSON 文件导入
4. **选择课程**：
   - 查看课程列表和完成进度
   - 点击课程卡片
5. **开始答题**：
   - 点击"开始答题"按钮
   - 选择答题模式：
     - **API 模式**：极快速度，推荐
     - **兼容模式**：浏览器模式，较慢但更稳定
6. **查看进度**：
   - 实时显示答题日志
   - 显示完成统计

#### 课程认证答题流程 (v2.6.0)

1. **导航到"课程认证"页面**
2. **导入题库**：
   - 支持导入 JSON 题库
   - 自动解析题目和答案
3. **API 答题**：
   - 使用 API 模式快速答题
   - 文本相似度匹配答案
4. **实时日志**：
   - 显示答题进度
   - 记录成功/失败信息

#### 答案提取流程

1. **导航到"答案提取"页面**
2. **教师登录**：
   - 输入教师账号和密码
   - 点击"登录"按钮
3. **选择年级**：
   - 左侧列表显示所有年级
   - 点击年级卡片查看班级
4. **选择班级**：
   - 右侧列表显示该年级的所有班级
   - 点击班级卡片查看课程
5. **提取答案**：
   - 点击课程的"提取答案"按钮
   - 查看实时进度和日志
   - 等待提取完成
6. **查看结果**：
   - 显示提取统计（知识点、题目、选项数量）
   - 显示文件保存位置
   - 可选择"打开文件夹"或"复制路径"

### CLI 模式

#### 主菜单

```
============================================================
         ZX Answering Assistant - 主菜单
============================================================
  1. 开始答题
  2. 提取题目（教师端）
  3. 设置
  0. 退出
============================================================
```

#### 开始答题流程

**方式一：批量答题（推荐）**

1. 选择 `1. 开始答题`
2. 选择 `1. 批量答题`
3. 登录学生账户
4. 查看课程列表
5. 选择要作答的课程
6. 选择答题模式（兼容模式/API 模式）
7. 等待自动答题完成

### 操作快捷键

| 快捷键 | 功能 |
|--------|------|
| `Q` | 停止当前答题操作 |
| `Ctrl + C` | 强制退出程序 |

---

## 打包分发

### 编译可执行文件

项目支持使用 PyInstaller 打包成独立的可执行文件，并支持源码预编译和自动清理功能。

#### 基础编译

```bash
# 默认：编译两个版本（onedir + onefile）
python build.py

# 仅编译目录模式（推荐，启动快）
python build.py --mode onedir

# 仅编译单文件模式
python build.py --mode onefile
```

#### 源码预编译与清理 (v2.6.6)

启用源码预编译后，打包完成后会**自动删除所有业务逻辑的 .py 源码文件**，只保留编译后的 .pyc 字节码和必要的 `__init__.py`：

```bash
# 预编译 + 自动清理源码
python build.py --mode onedir --compile-src

# 预编译 + UPX 压缩
python build.py --mode onedir --compile-src --upx
```

**清理效果**：
- ✅ 自动删除所有 `.py` 源码文件（21+ 个业务逻辑文件）
- ✅ 保留 `__init__.py`（Python 包导入必需）
- ✅ 保留 `.pyc` 字节码文件（编译后的代码）
- ✅ 仅在 `onedir` 模式下生效（单文件模式会自动打包所有文件到 exe 内部）

**打包后的目录结构**：
```
dist/ZX-Answering-Assistant-v2.6.6-windows-x64-installer/
├── ZX-Answering-Assistant-v2.6.6-windows-x64-installer.exe
└── _internal/
    └── src/
        ├── __init__.py           ← 保留（包初始化）
        ├── ui/__init__.py        ← 保留
        ├── ui/views/__init__.py  ← 保留
        ├── build_tools/__init__.py ← 保留
        ├── __pycache__/          ← .pyc 字节码
        ├── ui/__pycache__/
        ├── ui/views/__pycache__/
        └── build_tools/__pycache__/
```

**注意事项**：
- `.pyc` 字节码可以被反编译（如使用 `uncompyle6`），不是强保护
- 如需更强的源码保护，需要使用 Cython 编译为 `.pyd` 二进制文件
- `__init__.py` 必须保留，否则 Python 无法导入包

#### 输出文件名格式

编译后的文件名遵循规范命名格式：

**目录模式（installer）**：
```
ZX-Answering-Assistant-v2.6.6-windows-x64-installer/
```
- `installer` 表示目录模式
- 启动速度快（10-20倍）
- 推荐用于分发

**单文件模式（portable）**：
```
ZX-Answering-Assistant-v2.6.6-windows-x64-portable.exe
```
- `portable` 表示单文件模式
- 所有文件打包到一个可执行文件
- 便于携带，但首次启动较慢

### 体积优化

编译后的文件较大（约 262-528 MB），主要因为包含：
- Playwright 浏览器（~170-200 MB）
- Flet 框架和 Flutter 引擎（~50-80 MB）
- Python 运行时和依赖库（~50-100 MB）

#### 使用 UPX 压缩（推荐）

UPX 可以减小 30-50% 的体积：

```bash
# 1. 安装 UPX
#    下载: https://github.com/upx/upx/releases
#    Windows: 下载 upx-4.2.2-win64.zip
#    解压后将 upx.exe 添加到系统 PATH

# 2. 启用 UPX 压缩编译
python build.py --upx

# 3. 源码预编译 + UPX
python build.py --upx --compile-src
```

**效果对比**：

| 方案 | 单文件 | 目录 | 分发（7z） |
|------|--------|------|------------|
| 原始 | 262 MB | 528 MB | - |
| 预编译+清理 | 255 MB | 510 MB | - |
| UPX 压缩 | 130-180 MB | 260-360 MB | - |
| 预编译+UPX | 125-170 MB | 250-350 MB | - |
| UPX + 7z | - | 260-360 MB | 150-200 MB |

### 编译选项

```bash
# 查看所有编译选项
python build.py --help

# 可用选项：
#   --mode, -m        打包模式: onefile, onedir, both
#   --upx             启用 UPX 压缩（减小 30-50% 体积）
#   --compile-src     预编译源码为 .pyc 字节码
#   --no-upx          禁用 UPX 压缩
#   --copy-browser    仅复制浏览器（不打包）
#   --copy-flet       仅下载 Flet（不打包）
#   --copy-all        复制所有依赖（不打包）
#   --force-copy      强制重新复制
```

### 编译后使用

#### 目录模式（installer）

```bash
# 1. 进入输出目录
cd dist/ZX-Answering-Assistant-v2.6.6-windows-x64-installer/

# 2. 运行程序
# Windows:
ZX-Answering-Assistant-v2.6.6-windows-x64-installer.exe
```

**特点**：
- 首次启动几乎秒开（无需解压）
- 可以将整个文件夹分发给用户
- 占用磁盘空间较大

---

## 项目结构

```
ZX-Answering-Assistant-python/
├── data/                          # 数据目录
│   ├── input/                     # 输入文件（题库）
│   ├── output/                    # 输出文件（导出结果）
│   └── temp/                      # 临时文件
├── src/                           # 源代码
│   ├── __init__.py
│   ├── ui/                        # GUI 界面模块
│   │   ├── __init__.py
│   │   └── views/                  # 视图
│   │       ├── answering_view.py           # 答题界面
│   │       ├── extraction_view.py          # 答案提取界面
│   │       ├── settings_view.py            # 设置界面
│   │       └── course_certification_view.py # 课程认证界面 (v2.6.0)
│   ├── build_tools/                # 构建工具
│   │   ├── __init__.py
│   │   ├── browser_handler.py              # 浏览器处理
│   │   └── flet_handler.py                # Flet 可执行文件处理
│   ├── browser_manager.py          # 浏览器管理器 (v2.6.0)
│   ├── student_login.py            # 学生端登录
│   ├── teacher_login.py            # 教师端登录
│   ├── auto_answer.py              # 浏览器兼容模式
│   ├── api_auto_answer.py          # API 暴力模式
│   ├── course_certification.py     # 课程认证管理 (v2.6.0)
│   ├── course_api_answer.py        # 课程认证 API 答题 (v2.6.0)
│   ├── extract.py                  # 答案提取
│   ├── export.py                   # 数据导出
│   ├── question_bank_importer.py   # 题库导入
│   ├── api_client.py               # API 客户端（速率限制）
│   ├── settings.py                 # 设置管理
│   ├── file_handler.py             # 文件处理
│   └── main_gui.py                 # GUI 主程序
├── logs/                          # 日志文件
├── venv/                          # 虚拟环境（不提交）
├── main.py                        # 主程序入口
├── extract_answers.py             # 独立答案提取脚本
├── build.py                       # PyInstaller 打包脚本
├── version.py                     # 版本信息管理
├── VERSION.md                     # 版本管理文档
├── requirements.txt               # Python 依赖
├── cli_config.json                # CLI 配置文件（自动生成）
├── .gitignore                     # Git 忽略文件
├── CLAUDE.md                      # Claude Code 指导文档
└── README.md                      # 项目说明文档
```

---

## 技术栈

### 核心依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| **flet** | ≥0.80.0 | GUI 框架 |
| **playwright** | ≥1.57.0 | 浏览器自动化 |
| **requests** | ≥2.31.0 | HTTP 请求 |
| **loguru** | ≥0.7.0 | 日志管理 |
| **pandas** | ≥2.0.0 | 数据处理 |
| **openpyxl** | ≥3.1.0 | Excel 文件处理 |
| **keyboard** | ≥0.13.5 | 键盘监听 |
| **greenlet** | ≥3.0.0 | 协程支持 |

### API 端点

**学生端**
- 基础地址: `https://ai.cqzuxia.com/`
- `/connect/token` - OAuth2 令牌获取
- 课程列表和进度接口
- 答题提交接口

**教师端**
- 基础地址: `https://admin.cqzuxia.com/`
- `/evaluation/api/TeacherEvaluation/GetClassByTeacherID` - 班级列表
- `/evaluation/api/TeacherEvaluation/GetEvaluationSummaryByClassID` - 课程摘要
- `/evaluation/api/TeacherEvaluation/GetChapterEvaluationByClassID` - 章节列表
- `/evaluation/api/TeacherEvaluation/GetEvaluationKnowledgeSummaryByClass` - 知识点
- `/evaluation/api/TeacherEvaluation/GetKnowQuestionEvaluation` - 题目列表
- `/evaluation/api/TeacherEvaluation/GetQuestionAnswerListByQID` - 答案选项

**课程认证** (v2.6.0)
- 基础地址: `https://zxsz.cqzuxia.com/teacherCertifiApi/api/TeacherCourseEvaluate`
- 不同于教师端和学生端的独立 API

---

## 版本管理

### 版本信息

当前版本：**v2.6.6**

### 主要版本更新

**v2.6.6** (最新) - 源码自动清理版本
- **自动清理源码**：打包完成后自动删除所有业务逻辑 .py 文件
  - 仅保留 `__init__.py`（包导入必需）
  - 仅保留 `.pyc` 字节码文件
  - 仅在 `onedir` 目录模式下生效
  - 使用 `--compile-src` 参数启用
- **改进预编译流程**：
  - 预编译时保留 .py 文件（确保打包稳定）
  - 打包后自动清理源码（删除 .py 文件）
  - 自动统计并显示删除的文件数量
- **优化打包脚本**：改进源码清理逻辑，确保不影响程序运行

**v2.6.5** - 打包优化版本
- **新增源码预编译功能**：支持将 .py 文件预编译为 .pyc 字节码
  - 减小打包体积
  - 轻度保护源码
  - 使用 `--compile-src` 参数启用
- **修复 Playwright 1.57.0 兼容性**：
  - 修复 headless 模式使用 chromium_headless_shell 导致的路径错误
  - 使用 `args=['--headless=new']` 参数强制使用完整 Chromium
- **优化打包脚本**：
  - 将 compile_src.py 功能集成到 build.py
  - 添加 `--optimize 2` PyInstaller 参数

**v2.6.4** - 浏览器路径优化版本
- 修复打包后程序中浏览器路径配置问题
- 优化浏览器健康检查机制
- 改进错误日志输出

**v2.6.3** - 编码修复版本
- 修复 Windows 平台剪贴板中文乱码问题
- 优化日志输出编码设置

**v2.6.0** - 架构升级版本（重大更新）
- **新增浏览器管理器**：统一的浏览器实例管理
  - 单浏览器实例 + 多上下文模式
  - 降低资源占用，提高稳定性
  - 支持学生端、教师端、课程认证三个独立上下文
- **新增课程认证模块**：
  - 支持课程认证题库导入
  - API 模式快速答题
  - 文本相似度匹配
  - 独立的认证界面
- **重构自动登录逻辑**：
  - 策略化登录按钮点击
  - 改进网络监听机制
- **优化速率控制**：
  - 统一 API 客户端速率限制
  - 可配置延迟级别

**v2.3.0 - v2.5.x** - 界面优化与功能增强
- GUI 设置重构
- API 速率优化
- 界面说明优化
- Flet API 兼容性修复

**v2.2.0** - 浏览器健壮性与打包优化版本
- 新增浏览器崩溃自动恢复功能
- 新增浏览器健康状态监控机制
- 实现 AsyncIO 环境兼容性
- 改进浏览器资源清理逻辑
- 规范化编译输出文件名格式
- 添加 UPX 压缩支持

### 版本号规范

遵循语义化版本控制（Semantic Versioning）：

- 主版本号.次版本号.修订号
- 例如：2.6.5

**版本更新规则：**

- **主版本号**：重大架构变更或不兼容的 API 修改
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正

---

## 常见问题

### Q1: 如何选择使用 GUI 还是 CLI 模式？

**A:**
- **GUI 模式**（推荐）：操作简单直观，适合大多数用户
  - 图形化界面，无需记忆命令
  - 实时进度显示
  - 可视化文件管理
  - 浏览器崩溃自动恢复
  - 运行命令：`python main.py`

- **CLI 模式**：适合高级用户和自动化脚本
  - 完整功能访问
  - 可用于自动化脚本
  - 运行命令：`python main.py --mode cli`

### Q2: v2.6.0 的浏览器管理器有什么优势？

**A:**
- **降低资源占用**：单浏览器实例运行多个上下文
- **提高稳定性**：统一的资源管理和清理
- **完全隔离**：学生端、教师端、课程认证互不干扰
- **线程安全**：专用工作线程处理所有 Playwright 操作

### Q3: 课程认证模块是什么？(v2.6.0)

**A:** 课程认证是一个独立的功能模块：
- 用于教师课程认证答题
- 支持导入 JSON 题库
- 使用 API 模式快速答题
- 文本相似度智能匹配答案

### Q4: 如何使用源码预编译和清理功能？(v2.6.6)

**A:** 在打包时添加 `--compile-src` 参数：

```bash
# 预编译 + 自动清理源码
python build.py --mode onedir --compile-src

# 预编译 + UPX 压缩
python build.py --mode onedir --compile-src --upx
```

**打包后的效果**：
- ✅ 自动删除所有 `.py` 源码文件（21+ 个业务逻辑文件）
- ✅ 保留 `__init__.py`（Python 包导入必需）
- ✅ 保留 `.pyc` 字节码文件（程序正常运行）
- ⚠️ 仅在 `onedir` 目录模式下生效
- ⚠️ `.pyc` 字节码可以被反编译（如 `uncompyle6`）

**保护级别**：
- **轻度保护**：源码清理可防止普通用户查看代码
- **中度保护**：如需更强保护，使用 Cython 编译为 `.pyd`
- **强度保护**：代码混淆 + Cython + 加壳保护

### Q5: 打包后浏览器无法启动怎么办？(v2.6.6)

**A:** 已修复 Playwright 1.57.0 兼容性问题：
- 使用 `args=['--headless=new']` 参数
- 强制使用完整 Chromium 而不是 chromium_headless_shell
- 如仍有问题，请确保使用最新版本

### Q6: 编译后的文件为什么这么大？

**A:** 编译后的文件较大（262-528 MB）是正常的，主要因为包含：

1. **Playwright 浏览器** (~170-200 MB)
2. **Flet 框架** (~50-80 MB)
3. **Python 运行时** (~50-100 MB)

**优化方案**：
- 使用 UPX 压缩：`python build.py --upx`
- 使用源码预编译：`python build.py --compile-src`
- 使用 7z 二次压缩（分发时）

### Q7: Token 过期了怎么办？

**A:** 系统会自动处理：
- Token 有效期：5 小时
- 提前检测并自动重新获取
- 无需手动干预

---

## 开发规范

### 代码规范

1. **虚拟环境**: 所有开发工作必须在虚拟环境中进行
2. **测试优先**: 修改功能前先在独立测试文件中验证
3. **代码风格**: 遵循 PEP 8 规范
4. **错误处理**: 所有异常必须被捕获并记录日志
5. **日志级别**: DEBUG/INFO/WARNING/ERROR

### Git 提交规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型 (type):**
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建或辅助工具变动
- `gui`: GUI 相关功能

**示例:**

```
feat(browser_manager): 实现统一浏览器管理器

- 单浏览器实例 + 多上下文模式
- 线程安全的工作队列机制
- 支持学生端、教师端、课程认证三个独立上下文
- 自动清理和资源释放

Closes #123
```

### 贡献流程

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 许可证

本项目采用 **Apache License 2.0** 许可证 - 详见 [LICENSE.txt](LICENSE.txt) 文件

---

## 免责声明

本项目仅供学习和研究使用，请勿用于商业用途或任何违反服务条款的行为。使用本软件所产生的一切后果由使用者自行承担，作者不承担任何责任。

### 使用须知

1. 本工具仅用于个人学习和研究
2. 请遵守目标平台的使用条款
3. 禁止用于任何商业用途
4. 使用风险自负，作者不承担责任
5. 请勿过于频繁使用，避免账号异常

---

## 联系方式

- **问题反馈**: [GitHub Issues](https://github.com/yourusername/ZX-Answering-Assistant-python/issues)
- **功能建议**: [GitHub Discussions](https://github.com/yourusername/ZX-Answering-Assistant-python/discussions)

---

<div align="center">

**如果这个项目对你有帮助，请给个 Star 支持一下！**

Made with ❤️ by [Your Name]

</div>
