<div align="center">

# ZX Answering Assistant

### 智能答题助手系统

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE.txt)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Mac-lightgrey)]())
[![Version](https://img.shields.io/badge/Version-v2.3.0-green)]()

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
- **智能速率控制**：可配置的 API 请求速率限制（50ms-3秒）
- **自动重试**：网络错误自动重试机制（最多3次）
- **优雅退出**：按 Q 键随时停止，等待当前题目/知识点完成
- **进度监控**：实时显示答题进度和统计信息
- **题库管理**：支持题库导入/导出，支持 JSON 和 Excel 格式
- **自动保存**：提取的答案自动保存为 JSON 文件
- **可视化界面**：图形化操作流程，实时进度显示
- **统一配置**：CLI 模式支持配置文件管理账号和设置
- **浏览器自动恢复**：v2.3.0 新增 - 浏览器崩溃后可重新登录恢复
- **AsyncIO 兼容**：v2.3.0 新增 - GUI 模式完全兼容 Playwright 同步 API

---

## 功能特性

### 用户界面

| 界面类型           | 描述                         | 状态 |
| ------------------ | ---------------------------- | ---- |
| **GUI 模式** | 现代化图形界面，操作简单直观 | ✅   |
| **CLI 模式** | 传统命令行界面，功能完整     | ✅   |

### 学生端功能

| 功能                       | 描述                                       | 状态   |
| -------------------------- | ------------------------------------------ | ------ |
| 自动登录                   | 支持账户密码自动登录学生端                 | ✅     |
| 课程管理                   | 图形化显示课程列表和完成进度               | ✅     |
| 自动答题                   | 浏览器模拟点击，自动匹配答案               | ✅     |
| API 模式                   | 直接调用 API，无需浏览器操作               | ✅     |
| 网络重试                   | 连接失败自动重试（3次）                    | ✅     |
| 随时停止                   | 按 Q 键优雅退出                            | ✅     |
| 实时统计                   | 显示答题成功率和进度                       | ✅     |
| 题库加载                   | 支持导入 JSON 题库文件                     | ✅     |
| **浏览器崩溃恢复**   | v2.3.0 - 浏览器意外退出后可重新登录恢复    | ✅ NEW |
| **GUI AsyncIO 兼容** | v2.3.0 - 完美兼容 Flet 的 asyncio 事件循环 | ✅ NEW |

### 教师端功能

| 功能     | 描述                           | 状态 |
| -------- | ------------------------------ | ---- |
| 教师登录 | 图形化登录界面，紫色主题       | ✅   |
| 班级选择 | 左右分栏选择年级和班级         | ✅   |
| 课程选择 | 卡片化展示所有课程             | ✅   |
| 答案提取 | 一键提取课程答案，实时进度显示 | ✅   |
| 自动保存 | 提取完成自动保存为 JSON 文件   | ✅   |
| 提取统计 | 显示知识点、题目、选项数量     | ✅   |
| 文件管理 | 打开文件夹、复制文件路径       | ✅   |

### 答题模式对比

| 特性     | 浏览器兼容模式 | API 暴力模式 |
| -------- | -------------- | ------------ |
| 速度     | 较慢           | 极快         |
| 稳定性   | 中             | 中           |
| 资源占用 | 高（需浏览器） | 低           |
| 检测风险 | 一般           | 较高         |
| 推荐场景 | 网络不好       | 快速刷题     |

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
│   ┌───────────────────────────────────────────────────────┐ │
│   │                    GUI 模式 (Flet)                   │ │
│   │  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐ │ │
│   │  │  导航栏      │  │   答题模块   │  │   答案提取     │ │ │
│   │  │              │  │              │  │                 │ │ │
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
│   │           │  • 浏览器恢复   │     │  • 结果保存     │      │ │
│   │           │    (v2.3.0)    │     │                │      │ │
│   │           └─────────────────┘     └───────────────┘      │ │
│   │                                                           │ │
│   └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                     CLI 模式 (传统)                      │ │
│  │  ┌─────────────┐      ┌─────────────┐      ┌─────────┐  │ │
│  │  │   学生端    │      │   教师端    │      │  设置   │  │ │
│  │  │    模式     │      │    模式     │      │         │  │ │
│  │  └──────┬──────┘      └──────┬──────┘      └────┬────┘  │ │
│  │       │                    │                    │      │ │
│  │       ▼                    ▼                    │      │ │
│  │  ┌─────────────┐      ┌─────────────┐            │      │ │
│  │  │  兼容模式    │      │  答案提取    │            │      │ │
│  │  │             │      │             │            │      │ │
│  │  │  (浏览器)   │      │             │            │      │ │
│  │  │  • 自动恢复  │      │             │            │      │ │
│  │  └──────┬──────┘      └─────────────┘            │      │ │
│  │       │                                         │      │ │
│  │       ▼                                         │      │ │
│  │  ┌─────────────┐                                  │      │ │
│  │  │  API 模式   │                                  │      │ │
│  │  │  (暴力)     │                                  │      │ │
│  │  └──────┬──────┘                                  │      │ │
│  │       │                                         │      │ │
│  └───────┼─────────────────────────────────────────┼──────┘ │
│          │                                         │        │
│          ▼                                         ▼        │
│     ┌─────────────────┐                     ┌──────────────┐
│     │   题库管理系统    │                     │   设置系统    │
│     └─────────────────┘                     └──────────────┘
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### 浏览器健康监控机制 (v2.3.0)

```
┌─────────────────────────────────────────────────────────┐
│                  浏览器健康监控系统                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐         ┌──────────────┐            │
│  │  操作前检查   │────────▶│ 浏览器存活？ │            │
│  │              │         │              │            │
│  └──────┬───────┘         └──────┬───────┘            │
│         │                         │                    │
│         │                   ┌─────┴─────┐             │
│         │                   │           │             │
│         │                 是│          │否            │
│         │                   ▼           ▼             │
│         │           ┌──────────┐  ┌─────────┐        │
│         │           │ 继续执行  │  │ 清理资源 │        │
│         │           │          │  │         │        │
│         │           └──────────┘  └────┬────┘        │
│         │                              │             │
│         │                              ▼             │
│         │                     ┌──────────────┐      │
│         │                     │ 提示重新登录  │      │
│         │                     │              │      │
│         │                     └──────┬───────┘      │
│         │                            │              │
│         │                            ▼              │
│         │                   ┌──────────────┐       │
│         │                   │ 重启浏览器   │       │
│         │                   │              │       │
│         │                   └──────────────┘       │
│         │                                          │
│         ▼                                          │
│  ┌──────────────┐                                  │
│  │  操作中监控   │                                  │
│  │              │                                  │
│  └──────┬───────┘                                  │
│         │                                          │
│         ▼                                          │
│  ┌──────────────┐                                  │
│  │ 异常自动处理  │                                  │
│  │              │                                  │
│  └──────────────┘                                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**健康监控功能：**

- **自动检测**：每次操作前检查浏览器连接状态
- **智能清理**：发现崩溃时自动清理僵尸进程
- **用户提示**：GUI 模式弹出对话框提示重新登录
- **无缝恢复**：重新登录后自动重启浏览器继续操作

### 核心模块说明

**主程序**

- [main.py](main.py) - 双模式入口，GUI/CLI 切换
- [src/main_gui.py](src/main_gui.py) - GUI 主程序（Flet 框架）

**GUI 界面模块**

- [src/ui/views/answering_view.py](src/ui/views/answering_view.py) - 学生答题界面（含浏览器恢复）
- [src/ui/views/extraction_view.py](src/ui/views/extraction_view.py) - 答案提取界面
- [src/ui/views/settings_view.py](src/ui/views/settings_view.py) - 设置管理界面

**学生端模块**

- [src/student_login.py](src/student_login.py) - 学生端登录、浏览器健康监控、AsyncIO 兼容
- [src/auto_answer.py](src/auto_answer.py) - 浏览器兼容模式答题
- [src/api_auto_answer.py](src/api_auto_answer.py) - API 暴力模式答题

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

- [build.py](build.py) - PyInstaller 打包脚本（支持双版本编译）
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
git clone https://github.com/TianJiaJi/ZX-Answering-Assistant-python.git
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

#### 浏览器崩溃恢复 (v2.3.0)

当浏览器意外退出时：

1. **GUI 模式**：

   - 系统自动检测浏览器状态
   - 弹出提示对话框："浏览器已断开连接"
   - 点击"重新登录"按钮
   - 系统自动重启浏览器并继续操作
2. **CLI 模式**：

   - 系统提示"检测到浏览器已挂掉"
   - 询问是否重新登录
   - 输入 yes 确认后自动重新登录

**恢复特点：**

- 无需重启程序
- 自动清理僵尸进程
- 保留当前操作状态
- 支持多次恢复

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

#### 主题说明

- **学生端**：蓝色主题
- **教师端**：紫色主题
- **成功状态**：绿色
- **警告状态**：橙色
- **错误状态**：红色

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

**方式二：单课程答题**

1. 选择 `1. 开始答题`
2. 选择 `3. 单课程答题`
3. 输入课程 ID
4. 开始自动答题

#### 提取题目流程（教师端）

1. 选择 `2. 提取题目`
2. 选择 `1. 获取教师 Token`
3. 登录教师账户
4. 选择 `2. 提取所有课程` 或 `3. 提取单个课程`
5. 等待提取完成
6. 选择 `4. 导出结果`

### 操作快捷键

| 快捷键       | 功能             |
| ------------ | ---------------- |
| `Q`        | 停止当前答题操作 |
| `Ctrl + C` | 强制退出程序     |

### CLI 设置功能

CLI 模式支持通过配置文件管理账号密码和 API 设置，首次运行时会自动生成 `cli_config.json` 文件。

#### 可配置项

**账号管理**

- 学生端账号和密码
- 教师端账号和密码

**API 设置**

- **请求速率级别**：控制 API 请求之间的延迟
  - `low` - 50ms（快速，适合无限制的 API）
  - `medium` - 1秒（默认，平衡速度和稳定性）
  - `medium_high` - 2秒（较保守）
  - `high` - 3秒（最保守，适合严格限制的 API）
- **最大重试次数**：网络错误时的重试次数（默认 3 次）

#### 配置文件示例

```json
{
  "credentials": {
    "student": {
      "username": "your_student_username",
      "password": "your_password"
    },
    "teacher": {
      "username": "your_teacher_username",
      "password": "your_password"
    }
  },
  "api_settings": {
    "max_retries": 3,
    "rate_level": "medium"
  }
}
```

#### 速率级别选择建议

- **API 无速率限制**：选择 `low`（50ms）- 最大化速度
- **API 有轻微限制**：选择 `medium`（1秒）- 默认推荐
- **API 限制较严**：选择 `medium_high`（2秒）或 `high`（3秒）

---

## 打包与分发

### 编译可执行文件

项目支持使用 PyInstaller 打包成独立的可执行文件。

#### 基础编译

```bash
# 默认：编译两个版本（onedir + onefile）
python build.py

# 仅编译目录模式（推荐，启动快）
python build.py --mode onedir

# 仅编译单文件模式
python build.py --mode onefile
```

#### 输出文件名格式

编译后的文件名遵循规范命名格式：

**目录模式（installer）**：

```
ZX-Answering-Assistant-v2.3.0-windows-x64-installer/
```

- `installer` 表示目录模式
- 启动速度快（10-20倍）
- 推荐用于分发

**单文件模式（portable）**：

```
ZX-Answering-Assistant-v2.3.0-windows-x64-portable.exe
```

- `portable` 表示单文件模式
- 所有文件打包到一个可执行文件
- 便于携带，但首次启动较慢

#### 文件名组成

```
ZX-Answering-Assistant-<版本>-<平台>-<架构>-<模式>
```

**示例**：

- Windows x64: `ZX-Answering-Assistant-v2.3.0-windows-x64-installer`
- Linux x64: `ZX-Answering-Assistant-v2.3.0-linux-x64-portable`
- macOS ARM64: `ZX-Answering-Assistant-v2.3.0-macos-arm64-installer`

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

# 3. 仅压缩特定版本
python build.py --upx --mode onedir
python build.py --upx --mode onefile
```

**效果对比**：

| 方案     | 单文件     | 目录       | 分发（7z） |
| -------- | ---------- | ---------- | ---------- |
| 原始     | 262 MB     | 528 MB     | -          |
| UPX 压缩 | 130-180 MB | 260-360 MB | -          |
| UPX + 7z | -          | 260-360 MB | 150-200 MB |

#### 7z 二次压缩（分发用）

编译后使用 7z 压缩可进一步减小分发体积：

```bash
# Windows
7z a -t7z -m0=lzma2 -mx=9 ZX-Answering-Assistant-v2.3.0.7z dist/ZX-Answering-Assistant-v2.3.0-windows-x64-installer/

# Linux/Mac
7z a -t7z -m0=lzma2 -mx=9 ZX-Answering-Assistant-v2.3.0.7z dist/ZX-Answering-Assistant-v2.3.0-linux-x64-installer/
```

### 编译选项

```bash
# 查看所有编译选项
python build.py --help

# 可用选项：
#   --mode, -m        打包模式: onefile, onedir, both
#   --upx             启用 UPX 压缩（减小 30-50% 体积）
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
cd dist/ZX-Answering-Assistant-v2.3.0-windows-x64-installer/

# 2. 运行程序
# Windows:
ZX-Answering-Assistant-v2.3.0-windows-x64-installer.exe

# Linux:
./ZX-Answering-Assistant-v2.3.0-linux-x64-installer
```

**特点**：

- 首次启动几乎秒开（无需解压）
- 可以将整个文件夹分发给用户
- 占用磁盘空间较大

#### 单文件模式（portable）

```bash
# 直接运行可执行文件
# Windows:
ZX-Answering-Assistant-v2.3.0-windows-x64-portable.exe

# Linux:
./ZX-Answering-Assistant-v2.3.0-linux-x64-portable
```

**特点**：

- 单个文件，便于携带
- 首次运行需要 1-2 分钟解压
- 占用磁盘空间较小

### 首次运行

编译后的程序首次运行时：

1. Playwright 浏览器已内置，无需下载
2. Flet 可执行文件已内置，无需从 GitHub 下载
3. 会自动创建配置文件（CLI 模式）
4. 会自动创建日志目录

### 优化建议

**推荐方案（最佳用户体验）**：

```bash
# 1. 使用 UPX 压缩目录版本
python build.py --upx --mode onedir

# 2. 使用 7z 压缩分发
7z a -t7z -m0=lzma2 -mx=9 ZX-Answering-Assistant-v2.3.0.7z dist/ZX-Answering-Assistant-v2.3.0-windows-x64-installer/
```

最终分发体积：**~150-200 MB**（从 528 MB 减小约 60-70%）

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
│   │       ├── answering_view.py   # 答题界面（含浏览器恢复）
│   │       ├── extraction_view.py  # 答案提取界面
│   │       └── settings_view.py    # 设置界面
│   ├── student_login.py            # 学生端登录、浏览器健康监控
│   ├── teacher_login.py            # 教师端登录
│   ├── auto_answer.py              # 浏览器兼容模式
│   ├── api_auto_answer.py          # API 暴力模式
│   ├── extract.py                  # 答案提取
│   ├── export.py                   # 数据导出
│   ├── question_bank_importer.py   # 题库导入
│   ├── api_client.py               # API 客户端（速率限制）
│   ├── settings.py                 # 设置管理
│   ├── file_handler.py             # 文件处理
│   └── build_tools/                # 构建工具
│       ├── __init__.py
│       └── flet_handler.py         # Flet 可执行文件处理
├── logs/                          # 日志文件
├── tests/                         # 测试代码
├── venv/                          # 虚拟环境（不提交）
├── main.py                        # 主程序入口
├── src/main_gui.py                # GUI 主程序
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

| 依赖                 | 版本     | 用途           |
| -------------------- | -------- | -------------- |
| **flet**       | ≥0.80.0 | GUI 框架       |
| **playwright** | ≥1.57.0 | 浏览器自动化   |
| **requests**   | ≥2.31.0 | HTTP 请求      |
| **loguru**     | ≥0.7.0  | 日志管理       |
| **pandas**     | ≥2.0.0  | 数据处理       |
| **openpyxl**   | ≥3.1.0  | Excel 文件处理 |
| **keyboard**   | ≥0.13.5 | 键盘监听       |
| **aiohttp**    | ≥3.9.0  | 异步 HTTP      |
| **tqdm**       | ≥4.66.0 | 进度条显示     |

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

---

## 版本管理

### 版本信息

当前版本：**v2.3.0**

### 主要版本更新

**v2.3.0** (最新) - 版本信息与打包增强版本

- 新增 Windows EXE 版本信息属性支持
- 为编译后的 exe 添加完整的版本信息（文件说明、版本号、产品名称等）
- 版本信息中集成 Apache License 2.0 协议声明
- 添加作者信息（TianJiaJi）
- 版本信息管理模块化，统一在 version.py 中配置
- 支持自定义 EXE 文件属性（公司名、版权、备注等）
- 多语言版本信息支持（中文/英文）

**v2.2.0** - 浏览器健壮性与打包优化版本

- 新增浏览器崩溃自动恢复功能
- 新增浏览器健康状态监控机制
- 实现 AsyncIO 环境兼容性（解决 Playwright Sync API 在 GUI 模式的问题）
- 改进浏览器资源清理逻辑（多层清理策略）
- 添加浏览器连接状态检查函数
- GUI 模式：浏览器崩溃后弹出重新登录对话框
- CLI 模式：浏览器崩溃后提示用户重新登录
- 优化浏览器重启流程
- 改进错误提示信息

**打包优化**：

- 规范化编译输出文件名格式（版本-平台-架构-模式）
- 添加 UPX 压缩支持（减小 30-50% 体积）
- 改进打包脚本，支持灵活的编译选项
- 添加体积优化指南文档
- 优化分发流程（UPX + 7z 可减小 60-70% 体积）

**v2.1.0** - 打包优化版本

- 修复 Flet 可执行文件打包路径问题
- 修复 Windows GBK 编码导致的程序崩溃
- 改进打包脚本，默认编译两个版本（onedir + onefile）
- 优化 Flet 可执行文件复制逻辑
- 添加 UTF-8 控制台编码设置

**v2.0.0** - 架构重构版本

- 重构浏览器处理逻辑并模块化
- 新增统一 API 客户端（支持速率限制和自动重试）
- 实现 CLI 配置文件管理功能
- 添加 GUI 记住密码功能
- 改进系统架构，提升代码可维护性

**v1.2.1**

- 修复 API 客户端速率限制逻辑
- 实现可配置的 API 请求速率控制（50ms-3秒）
- 新增 CLI 配置文件管理（cli_config.json）
- 统一 API 请求处理
- 添加账号密码持久化存储

**v1.2.0**

- 新增现代化 GUI 界面（Flet 框架）
- 优化用户体验：图形化操作流程
- 实时进度显示和日志输出
- 答案提取进度可视化
- 自动保存 JSON 文件
- 文件路径一键复制和打开

**v1.1.0**

- 添加浏览器兼容模式
- 实现 API 暴力模式
- 支持题库导入/导出

### 版本号规范

遵循语义化版本控制（Semantic Versioning）：

- 主版本号.次版本号.修订号
- 例如：1.0.0, 1.0.1, 1.1.0, 2.0.0

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
  - 运行命令：`python main.py` 或 `python main.py --mode gui`
- **CLI 模式**：适合高级用户和自动化脚本

  - 完整功能访问
  - 可用于自动化脚本
  - 浏览器崩溃后可重新登录
  - 运行命令：`python main.py --mode cli`

### Q2: 两种答题模式有什么区别？

**A:**

| 特性     | 兼容模式             | API 模式             |
| -------- | -------------------- | -------------------- |
| 实现方式 | 浏览器模拟点击       | 直接调用 API         |
| 速度     | 较慢（需要页面加载） | 极快（纯 HTTP 请求） |
| 资源占用 | 高（需要浏览器）     | 低（仅网络请求）     |
| 稳定性   | 高                   | 高                   |
| 适用场景 | 验证答案、学习用途   | 快速刷题             |

**推荐**：日常使用选择 **API 模式**，验证答案选择 **兼容模式**。

### Q3: 浏览器崩溃了怎么办？(v2.3.0)

**A:** v2.3.0 版本已实现浏览器崩溃自动恢复：

**GUI 模式：**

1. 系统自动检测浏览器状态
2. 弹出对话框提示"浏览器已断开连接"
3. 点击"重新登录"按钮
4. 系统自动重启浏览器并继续

**CLI 模式：**

1. 系统提示"检测到浏览器已挂掉"
2. 询问是否重新登录
3. 输入 yes 确认
4. 系统自动重新登录并重启浏览器

**无需重启程序**，系统会自动清理僵尸进程。

### Q4: 提取的答案保存在哪里？

**A:** 答案提取完成后会自动保存在 `output/` 目录中，文件名格式为：

```
{班级名称}_{课程名称}_{时间戳}.json
```

例如：

```
24级大数据技术2班_Linux操作系统（云林选用2025）_20260121_225414.json
```

### Q5: 如何停止正在运行的答题？

**A:**

- **GUI 模式**：点击停止按钮或关闭窗口
- **CLI 模式**：按 `Q` 键优雅退出

### Q6: Token 过期了怎么办？

**A:** 系统会自动处理：

- Token 有效期：5 小时
- 提前检测并自动重新获取
- 无需手动干预

### Q7: 打包成可执行文件后如何使用？

**A:**

1. **打包项目**：

   ```bash
   python build.py  # 默认打包两个版本（onedir + onefile）
   python build.py --mode onedir  # 仅目录模式
   python build.py --mode onefile  # 仅单文件模式
   ```
2. **运行程序**：

   - **onedir 模式**：进入 `dist/ZX-Answering-Assistant/` 文件夹，双击 exe 文件
   - **onefile 模式**：直接双击 `dist/ZX-Answering-Assistant.exe`
3. **首次运行**：

   - Playwright 浏览器会自动下载（需要网络连接）
   - Flet 可执行文件已内置，无需从网络下载

### Q8: GUI 模式出现 Playwright 错误怎么办？(v2.3.0)

**A:** v2.3.0 已修复 AsyncIO 兼容性问题：

之前的错误：

```
Playwright Sync API inside the asyncio loop
```

现在系统会：

1. 自动检测 asyncio 事件循环
2. 在独立线程中创建新的事件循环
3. 隔离运行 Playwright 同步 API
4. 完美兼容 Flet 的异步架构

**如果仍有问题**，请确保：

- 使用最新版本（v2.3.0+）
- 安装了所有依赖：`pip install -r requirements.txt`
- 安装了 Playwright 浏览器：`python -m playwright install chromium`

### Q9: 如何调试日志？

**A:** 在 GUI 界面的"设置"页面中调整日志级别，选择 DEBUG 级别即可查看详细日志。

### Q10: 编译后的文件为什么这么大？(v2.3.0)

**A:** 编译后的文件较大（262-528 MB）是正常的，主要因为包含：

1. **Playwright 浏览器** (~170-200 MB) - Chromium 浏览器完整包
2. **Flet 框架** (~50-80 MB) - Flutter 引擎和 GUI 组件
3. **Python 运行时** (~50-100 MB) - Python 解释器和依赖库

**优化方案**：

- 使用 UPX 压缩：`python build.py --upx`（减小 30-50%）
- 使用 7z 二次压缩（分发时减小到 150-200 MB）

### Q11: 如何减小编译文件的体积？

**A:** 推荐使用以下优化方案：

**方案 1：UPX 压缩**

```bash
# 1. 安装 UPX: https://github.com/upx/upx/releases
# 2. 编译时启用压缩
python build.py --upx --mode onedir
```

**方案 2：7z 二次压缩（分发推荐）**

```bash
# 先用 UPX 压缩
python build.py --upx --mode onedir

# 再用 7z 打包
7z a -t7z -m0=lzma2 -mx=9 output.7z dist/ZX-Answering-Assistant-v2.3.0-windows-x64-installer/
```

**效果**：

- 原始：528 MB
- UPX 后：260-360 MB
- UPX + 7z：150-200 MB（减小 60-70%）

### Q12: 遇到问题如何获取帮助？

**A:**

1. 查看本文档
2. 查看 [CLAUDE.md](CLAUDE.md) 获取开发指导
3. 在 GitHub 提交 Issue

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
feat(recovery): 实现浏览器崩溃自动恢复功能

- 添加浏览器健康状态监控函数
- 实现多层清理策略清理僵尸进程
- GUI 模式：弹出重新登录对话框
- CLI 模式：提示用户重新登录
- 优化 AsyncIO 环境兼容性

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

- **问题反馈**: [GitHub Issues](https://github.com/TianJiaJi/ZX-Answering-Assistant-python/issues)
- **功能建议**: [GitHub Discussions](https://github.com/TianJiaJi/ZX-Answering-Assistant-python/discussions)
- **联系邮箱**: blog@mali.tianjiaji.top

---

<div align="center">

**如果这个项目对你有帮助，请给个 Star 支持一下！**

Made with ❤️ by TianJiaJi

</div>
