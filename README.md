<div align="center">

# ZX Answering Assistant
### 智能答题助手系统

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE.txt)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)](https://www.microsoft.com/windows)
[![Version](https://img.shields.io/badge/Version-v2.7.8-green)](https://github.com/yourusername/ZX-Answering-Assistant-python/releases)

**一个基于 Playwright 的在线学习平台自动化答题助手系统**

支持 **GUI 图形界面** 和 **CLI 命令行** 两种交互方式，提供浏览器兼容模式和 API 暴力模式两种答题方式。

[项目背景](#为什么制作这个程序) • [核心功能](#核心功能) • [技术架构](#技术架构) • [快速开始](#快速开始) • [使用指南](#使用指南) • [开发指南](#开发指南)

</div>

---

## 目录

- [为什么制作这个程序](#为什么制作这个程序)
- [核心功能](#核心功能)
- [技术架构](#技术架构)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
- [技术细节](#技术细节)
- [开发指南](#开发指南)
- [常见问题](#常见问题)
- [版本历史](#版本历史)
- [许可证](#许可证)

---

## 为什么制作这个程序

### 项目背景

在现代在线教育环境中，学生和教师经常面临以下挑战：

1. **重复性学习任务**: 学生需要完成大量的在线练习题来巩固知识，但手动答题效率低下
2. **答案提取困难**: 教师想要获取课程题库用于备课或分析，但缺少自动化工具
3. **学习进度管理**: 难以追踪课程完成情况和知识点掌握程度
4. **时间效率问题**: 重复性答题过程占用大量学习时间，影响学习效率

### 解决方案

ZX Answering Assistant 应运而生，旨在：

- **提高学习效率**: 自动化答题流程，节省时间用于理解重点知识
- **辅助教师工作**: 快速提取课程题库，便于教学准备和学情分析
- **智能化管理**: 实时追踪学习进度，智能匹配答案
- **降低学习成本**: 通过自动化工具减少重复劳动，提升学习体验

### 设计理念

- **用户友好**: 提供直观的 GUI 界面和传统 CLI 界面，满足不同用户需求
- **技术先进**: 采用最新的浏览器自动化技术和 API 逆向工程
- **安全可靠**: 智能速率控制，避免触发平台检测机制
- **开源共享**: 开源项目，欢迎社区贡献和改进

---

## 核心功能

### 双界面支持

| 界面类型 | 特点 | 适用场景 |
|---------|------|----------|
| **GUI 模式** | 现代化图形界面，操作简单直观，实时进度显示 | 普通用户日常使用 |
| **CLI 模式** | 命令行界面，支持脚本自动化 | 高级用户和自动化集成 |

### 学生端功能

#### 自动答题系统

- ✅ **自动登录**: 支持账户密码自动登录学生端，无需手动操作
- ✅ **课程管理**: 图形化显示课程列表和完成进度，一目了然
- ✅ **智能答题**: 两种模式可选
  - **浏览器兼容模式**: 模拟真实用户操作，点击选项完成答题
  - **API 暴力模式**: 直接调用 API 接口，速度极快
- ✅ **网络重试**: 连接失败自动重试（最多3次），确保答题成功率
- ✅ **优雅退出**: 按 Q 键随时停止，等待当前题目完成再退出
- ✅ **实时统计**: 显示答题成功率、完成进度、用时统计
- ✅ **题库导入**: 支持 JSON 格式题库导入，离线匹配答案
- ✅ **进度监控**: 实时追踪课程完成情况，显示完成百分比
- ✅ **浏览器崩溃恢复**: v2.2.0+ 浏览器意外退出后可自动重新登录恢复
- ✅ **统一浏览器管理**: v2.6.0+ 单浏览器实例多上下文，降低资源占用

#### 课程认证答题 (v2.6.0+)

- ✅ **题库导入**: 支持 JSON 格式题库导入
- ✅ **API 快速答题**: 直接调用 API 接口答题
- ✅ **文本智能匹配**: 基于文本相似度匹配答案
- ✅ **实时日志**: 显示答题进度和统计信息

### 教师端功能

#### 答案提取系统

- ✅ **教师登录**: 图形化登录界面，专业的紫色主题
- ✅ **智能选择**: 左右分栏设计，先选年级再选班级
- ✅ **课程卡片**: 卡片化展示所有课程，信息清晰
- ✅ **一键提取**: 点击课程卡片即可提取答案，实时进度显示
- ✅ **自动保存**: 提取完成自动保存为 JSON 文件
- ✅ **提取统计**: 显示知识点数量、题目数量、选项数量
- ✅ **文件管理**: 一键打开文件夹、复制文件路径

### 核心特性

#### 技术特性

| 特性 | 描述 | 版本 |
|------|------|------|
| **智能速率控制** | 可配置的 API 请求速率限制，避免触发检测 | v1.0 |
| **自动重试机制** | 网络错误自动重试，最多3次 | v1.0 |
| **浏览器崩溃恢复** | 自动检测浏览器崩溃并重新登录 | v2.2.0 |
| **AsyncIO 兼容** | GUI 模式完全兼容 Playwright 同步 API | v2.2.0 |
| **统一浏览器管理** | 单浏览器实例 + 多上下文隔离 | v2.6.0 |
| **源码自动清理** | 打包后自动删除 .py 源码，只保留 .pyc | v2.6.6 |
| **构建系统优化** | 配置文件化、自动化测试、增量构建 | v2.7.0 |

#### 答题模式对比

| 特性 | 浏览器兼容模式 | API 暴力模式 |
|------|----------------|--------------|
| **速度** | 较慢（约 2-3 题/秒） | 极快（约 10-20 题/秒） |
| **稳定性** | 高（模拟真实操作） | 高（API 调用） |
| **资源占用** | 高（需要浏览器） | 低（仅 HTTP 请求） |
| **检测风险** | 较低（模拟真人） | 中等（API 调用） |
| **推荐场景** | 验证答案准确性 | 快速刷题 |

---

## 技术架构

### 系统架构图

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
│   │           │  学生端界面   │     │  教师端界面   │      │ │
│   │           │                │     │                │      │ │
│   │           │  • 自动登录     │     │  • 班级选择     │      │ │
│   │           │  • 课程答题     │     │  • 答案提取     │      │ │
│   │           │  • 课程认证     │     │  • 数据导出     │      │ │
│   │           │  • 进度监控     │     │  • 统计信息     │      │ │
│   │           └─────────────────┘     └───────────────┘      │ │
│   │                                                           │
│   └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              浏览器管理器 (BrowserManager) v2.6.0+        │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  单浏览器实例 + 多上下文模式                        │ │ │
│  │  │                                                     │ │ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │ │ │
│  │  │  │ 学生端上下文  │  │ 教师端上下文  │  │ 认证上下文 │ │ │ │
│  │  │  │ (STUDENT)    │  │ (TEACHER)    │  │(COURSE_)  │ │ │ │
│  │  │  │              │  │              │  │  CERT)    │ │ │ │
│  │  │  └──────────────┘  └──────────────┘  └───────────┘ │ │ │
│  │  │                                                     │ │ │
│  │  │  完全隔离：Cookie、Session、LocalStorage            │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                   核心功能模块                          │ │
│  │  ┌──────────────┐  ┌─────────────┐  ┌───────────────┐  │ │
│  │  │  API 客户端   │  │  数据管理    │  │  配置管理     │  │ │
│  │  │  速率限制     │  │  导入/导出   │  │  持久化存储   │  │ │
│  │  └──────────────┘  └─────────────┘  └───────────────┘  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### 技术栈

#### 核心依赖

| 依赖 | 版本 | 用途 | 说明 |
|------|------|------|------|
| **flet** | ≥0.80.0 | GUI 框架 | 现代化跨平台桌面应用框架 |
| **playwright** | ≥1.57.0 | 浏览器自动化 | 用于登录、token提取、浏览器模式答题 |
| **requests** | ≥2.31.0 | HTTP 客户端 | API 调用、网络请求 |
| **keyboard** | ≥0.13.5 | 键盘监听 | 优雅退出功能 |

#### 开发依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| **pyinstaller** | ≥6.0.0 | 打包工具 |
| **pyyaml** | ≥6.0 | 配置文件解析 |
| **pytest** | ≥7.0.0 | 测试框架 |
| **pytest-cov** | ≥4.0.0 | 测试覆盖率 |

#### API 端点

**学生端 API**
- 基础地址: `https://ai.cqzuxia.com/`
- `/connect/token` - OAuth2 令牌获取
- 课程列表、进度、答题等接口

**教师端 API**
- 基础地址: `https://admin.cqzuxia.com/`
- `/evaluation/api/TeacherEvaluation/*` - 答案提取接口

**课程认证 API** (v2.6.0+)
- 基础地址: `https://zxsz.cqzuxia.com/teacherCertifiApi/api/TeacherCourseEvaluate`

### 核心模块

#### 1. 浏览器管理器 (BrowserManager)

**位置**: `src/browser_manager.py`

**核心功能**:
- 单浏览器实例管理
- 多上下文隔离（学生端、教师端、课程认证）
- 线程安全的工作队列
- AsyncIO 兼容性

**使用示例**:
```python
from src.browser_manager import get_browser_manager, BrowserType

# 获取单例实例
browser_manager = get_browser_manager()

# 启动浏览器
browser = browser_manager.start_browser(headless=False)

# 获取隔离的上下文
student_context = browser_manager.get_context(BrowserType.STUDENT)
teacher_context = browser_manager.get_context(BrowserType.TEACHER)

# 清理
browser_manager.stop_browser()
```

#### 2. API 客户端 (APIClient)

**位置**: `src/api_client.py`

**核心功能**:
- 统一的 HTTP 请求接口
- 智能速率限制（可配置）
- 自动重试机制
- 错误处理

**速率级别**:
- `low`: 50ms - 无速率限制的 API
- `medium`: 1s - 默认级别
- `medium_high`: 2s - 较严格限制
- `high`: 3s - 严格限制

**使用示例**:
```python
from src.api_client import get_api_client

api_client = get_api_client()
response = api_client.get(url, headers=headers)
```

#### 3. 答案提取器 (Extractor)

**位置**: `src/extract.py`

**数据流**:
```
class_list → filtered_classes → course_list → chapter_list
→ knowledge_list → knowledge_questions → question_options
```

**API 调用链**:
1. `GetClassByTeacherID` - 获取班级列表
2. `GetEvaluationSummaryByClassID` - 获取课程摘要
3. `GetChapterEvaluationByClassID` - 获取章节列表
4. `GetEvaluationKnowledgeSummaryByClass` - 获取知识点
5. `GetKnowQuestionEvaluation` - 获取题目
6. `GetQuestionAnswerListByQID` - 获取选项

#### 4. 自动答题模块

**浏览器模式** (`src/auto_answer.py`):
- 模拟真实用户操作
- 点击选项按钮
- 提交答案

**API 模式** (`src/api_auto_answer.py`):
- 直接调用 API
- 速度极快
- 网络重试机制

---

## 快速开始

### 环境要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows 10/11（推荐）
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

#### GUI 模式（推荐）

```bash
python main.py
# 或
python main.py --mode gui
```

#### CLI 模式

```bash
python main.py --mode cli
```

---

## 使用指南

### GUI 模式使用

#### 启动应用

 `main.py` 在命令行执行：

```bash
python main.py
```

#### 导航结构

```
┌──────────────────────────────────┐
│  首页                               │  - 欢迎页面
│  评估答题                           │  - 学生端答题
│  课程认证                           │  - 课程认证答题
│  答案提取                           │  - 教师端答案提取
│  设置                               │  - 配置管理
└──────────────────────────────────┘
```

#### 学生端答题流程

1. **登录**
   - 导航到"评估答题"页面
   - 输入学生端用户名和密码
   - 点击"登录"按钮

2. **导入题库（可选）**
   - 点击"导入题库"按钮
   - 选择 JSON 格式的题库文件
   - 系统会自动加载题库

3. **选择课程**
   - 查看课程列表和完成进度
   - 点击想要完成的课程卡片

4. **开始答题**
   - 点击"开始答题"按钮
   - 选择答题模式：
     - **API 模式**（推荐）：速度快，约 10-20 题/秒
     - **浏览器模式**：模拟真实操作，约 2-3 题/秒
   - 按 Q 键可随时停止

5. **查看进度**
   - 实时显示答题日志
   - 显示成功率和完成进度

#### 课程认证答题流程

1. **导航到"课程认证"页面**
2. **导入题库**：选择 JSON 题库文件
3. **开始答题**：点击"开始答题"按钮
4. **查看日志**：实时显示答题进度和统计

#### 教师端答案提取流程

1. **登录**
   - 导航到"答案提取"页面
   - 输入教师端用户名和密码
   - 点击"登录"按钮

2. **选择年级**
   - 左侧列表显示所有年级（如：2024、2025）
   - 点击选择目标年级

3. **选择班级**
   - 右侧列表显示该年级的所有班级
   - 点击选择目标班级

4. **提取答案**
   - 查看课程列表
   - 点击课程的"提取答案"按钮
   - 等待提取完成

5. **查看结果**
   - 显示提取统计（知识点、题目、选项数量）
   - 点击"打开文件夹"查看导出的 JSON 文件
   - 点击"复制路径"获取文件路径

### CLI 模式使用

#### 主菜单

```
========================================
     ZX 智能答题助手 - 主菜单
========================================

1. 开始答题
2. 提取问题
3. 设置
4. 退出

请选择功能 (1-4):
```

#### 答题子菜单

```
========================================
        开始答题 - 子菜单
========================================

1. 批量答题
2. 获取学生 access_token
3. 单课程答题
4. 题库导入
5. 返回

请选择功能 (1-5):
```

#### 提取问题子菜单

```
========================================
        提取问题 - 子菜单
========================================

1. 获取教师 access_token
2. 提取所有课程
3. 提取单课程
4. 导出结果
5. 返回

请选择功能 (1-5):
```

### 配置文件

程序运行时会自动生成 `cli_config.json` 配置文件：

```json
{
  "student_credentials": {
    "username": "",
    "password": ""
  },
  "teacher_credentials": {
    "username": "",
    "password": ""
  },
  "api_settings": {
    "rate_level": "medium",
    "max_retries": 3
  }
}
```

**配置说明**:
- `rate_level`: API 请求速率级别（low/medium/medium_high/high）
- `max_retries`: 最大重试次数

---

## 技术细节

### 速率限制机制

**为什么需要速率限制？**

1. **避免触发平台检测**: 过快的请求频率可能被识别为机器人
2. **保证系统稳定**: 避免因请求过快导致的服务器错误
3. **模拟真实用户**: 正常用户的答题速度是有限的

**实现方式**:

```python
class APIClient:
    def __init__(self, rate_level: APIRateLevel = APIRateLevel.MEDIUM):
        self.rate_delays = {
            APIRateLevel.LOW: 0.05,        # 50ms
            APIRateLevel.MEDIUM: 1.0,      # 1s
            APIRateLevel.MEDIUM_HIGH: 2.0, # 2s
            APIRateLevel.HIGH: 3.0         # 3s
        }

    def request(self, method, url, **kwargs):
        # 应用速率限制延迟
        delay = self.rate_delays[self.rate_level]
        time.sleep(delay)

        # 发送请求
        response = requests.request(method, url, **kwargs)

        # 处理错误和重试
        return self._handle_response(response)
```

### AsyncIO 兼容性

**问题**: Flet 框架使用 asyncio 事件循环，但 Playwright 的同步 API 无法在 asyncio 循环中运行。

**解决方案**: 检测 asyncio 环境，在独立线程中运行 Playwright：

```python
def login_in_asyncio_context():
    try:
        import asyncio
        asyncio.get_running_loop()
        # 检测到 asyncio 环境

        import threading
        result = [None]

        def run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            # 在新线程中运行 Playwright 代码
            result[0] = _do_login()

        thread = threading.Thread(target=run_in_new_loop)
        thread.start()
        thread.join()

        return result[0]

    except RuntimeError:
        # 没有 asyncio 循环，直接运行
        return _do_login()
```

### 浏览器崩溃恢复

**检测机制**:

```python
def check_browser_alive():
    """检查浏览器是否仍然连接"""
    global _browser_instance
    if _browser_instance is None:
        return False
    try:
        # 尝试访问浏览器上下文
        _browser_instance.contexts
        return True
    except Exception:
        return False
```

**恢复流程**:

1. 检测浏览器崩溃
2. 清理旧资源
3. 提示用户重新登录
4. 重启浏览器
5. 继续操作

### 数据结构

#### 单课程导出格式

```json
{
  "class": {
    "class_id": "123",
    "class_name": "2024级计算机1班",
    "course": {
      "course_id": "456",
      "course_name": "Python程序设计",
      "chapters": [
        {
          "chapter_id": "1",
          "chapter_name": "第一章",
          "knowledges": [
            {
              "knowledge_id": "1",
              "knowledge_name": "知识点1",
              "questions": [
                {
                  "question_id": "1",
                  "question_content": "题目内容",
                  "options": [
                    {
                      "id": "1",
                      "content": "选项A",
                      "is_correct": true
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  }
}
```

### 安全性考虑

1. **密码存储**: 配置文件中的密码以明文存储，建议不要将配置文件提交到版本控制
2. **Token 管理**: Token 有效期 5 小时，系统会自动刷新
3. **速率限制**: 默认使用 medium 级别，避免触发检测
4. **用户代理**: 使用真实的浏览器 User-Agent

---

## 开发指南

### 开发环境搭建

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/ZX-Answering-Assistant-python.git
cd ZX-Answering-Assistant-python

# 2. 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. 安装开发依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. 安装 Playwright 浏览器
python -m playwright install chromium

# 5. 运行测试
pytest tests/ -v
```

### 项目结构

```
ZX-Answering-Assistant-python/
├── src/                           # 源代码
│   ├── ui/                        # GUI 界面
│   │   └── views/                 # 视图组件
│   ├── browser_manager.py         # 浏览器管理器
│   ├── student_login.py           # 学生端登录
│   ├── teacher_login.py           # 教师端登录
│   ├── extract.py                 # 答案提取
│   ├── auto_answer.py             # 浏览器模式答题
│   ├── api_auto_answer.py         # API 模式答题
│   ├── api_client.py              # API 客户端
│   ├── settings.py                # 配置管理
│   └── ...
├── tests/                         # 测试代码
├── main.py                        # 主程序入口
├── build.py                       # 构建脚本
├── build_config.yaml              # 构建配置
├── version.py                     # 版本信息
├── requirements.txt               # 生产依赖
├── requirements-dev.txt            # 开发依赖
├── CLAUDE.md                      # Claude Code 指导文档
└── README.md                      # 项目文档
```

### 代码规范

#### 1. 命名规范

- **类名**: 大驼峰命名法 (PascalCase)
  ```python
  class BrowserManager:
      pass
  ```

- **函数/变量**: 小写加下划线 (snake_case)
  ```python
  def get_student_courses():
      pass
  ```

- **常量**: 全大写加下划线
  ```python
  MAX_RETRIES = 3
  ```

#### 2. 文档字符串

使用 Google 风格的文档字符串：

```python
def extract_course_answers(course_id: str, progress_callback=None) -> dict:
    """提取课程答案

    Args:
        course_id: 课程ID
        progress_callback: 进度回调函数

    Returns:
        包含课程信息和答案的字典
    """
    pass
```

#### 3. 错误处理

```python
try:
    result = api_client.get(url, headers=headers)
except requests.exceptions.ConnectionError:
    logger.error("网络连接失败")
    return None
except Exception as e:
    logger.error(f"未知错误: {e}")
    return None
```

### Git 提交规范

使用 Conventional Commits 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**类型 (type)**:
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建或辅助工具变动
- `gui`: GUI 相关功能
- `build`: 构建系统相关

**示例**:
```
feat(student_login): 添加记住密码功能

- 新增密码加密存储
- 添加"记住密码"选项
- 更新 GUI 界面

Closes #123
```

### 测试指南

#### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_api_client.py -v

# 生成覆盖率报告
pytest --cov=src --cov-report=html

# 查看报告
# 打开 htmlcov/index.html
```

#### 编写测试

```python
# tests/test_api_client.py
import pytest
from src.api_client import APIClient, APIRateLevel

def test_api_client_singleton():
    """测试 API 客户端单例模式"""
    client1 = get_api_client()
    client2 = get_api_client()
    assert client1 is client2

def test_rate_limit_levels():
    """测试速率限制级别"""
    client = APIClient(rate_level=APIRateLevel.MEDIUM)
    assert client.rate_level == APIRateLevel.MEDIUM
```

### 构建可执行文件

#### 快速构建

```bash
# 目录模式（推荐，启动快）
python build.py --mode onedir

# 单文件模式（便携，单个文件）
python build.py --mode onefile

# 同时构建两种模式
python build.py --mode both

# 启用 UPX 压缩（减小体积）
python build.py --upx

# 清理构建产物
python build.py --clean
```

#### 构建配置

编辑 `build_config.yaml` 自定义构建选项：

```yaml
build:
  mode: onedir                 # onedir, onefile, both
  output_dir: "dist"           # 输出目录

compilation:
  enabled: true                # 编译为 .pyc
  optimize: 2                  # 优化级别

playwright:
  enabled: true                # 打包浏览器

upx:
  enabled: false               # UPX 压缩
```

#### 构建输出

构建完成后，输出文件在 `dist/` 目录：

**目录模式**:
```
dist/
└── ZX-Answering-Assistant-v2.7.8-windows-x64-installer/
    ├── ZX-Answering-Assistant-v2.7.8-windows-x64-installer.exe
    └── [依赖文件...]
```

**单文件模式**:
```
dist/
└── ZX-Answering-Assistant-v2.7.8-windows-x64-portable.exe
```

### 贡献流程

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: add some amazing feature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 常见问题

### Q1: Token 过期了怎么办？

**A:** 系统会自动处理 Token 过期：

- Token 有效期：5 小时
- 系统会提前检测并自动重新获取
- 无需手动干预

如果遇到 Token 相关错误，尝试：
1. 重新登录
2. 检查网络连接
3. 清除缓存配置文件

### Q2: 如何调整答题速度？

**A:** 修改 `cli_config.json` 中的 `rate_level`：

```json
{
  "api_settings": {
    "rate_level": "medium"  // low/medium/medium_high/high
  }
}
```

- `low`: 最快（50ms），可能触发检测
- `medium`: 默认（1s），推荐
- `medium_high`: 较慢（2s）
- `high`: 最慢（3s），最安全

### Q3: 编译后的文件为什么这么大？

**A:** 正常现象，主要包含：

1. **Playwright 浏览器**: ~170-200 MB
2. **Flet 框架**: ~50-80 MB
3. **Python 运行时**: ~50-100 MB
4. **依赖库**: ~30-50 MB

**优化方案**：

```bash
# 启用 UPX 压缩（减小 30-50%）
python build.py --upx
```

### Q4: 运行打包后的程序提示"浏览器未安装"怎么办？

**A:** 这是 Playwright 浏览器未正确安装的问题。解决方法：

#### 方法 1: 自动安装（推荐）
首次运行程序时，程序会自动检测并提示安装浏览器。按照提示操作即可。

#### 方法 2: 手动安装
如果自动安装失败，请手动安装：

```bash
# Windows 用户
playwright install chromium

# 或者使用 Python
python -m playwright install chromium
```

浏览器将安装到：
- **Windows**: `C:\Users\<用户名>\AppData\Local\ms-playwright`
- **Linux/Mac**: `~/.cache/ms-playwright`

#### 方法 3: 使用开发环境（源码运行）
如果打包版本出现问题，建议直接使用源码运行：

```bash
# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
python -m playwright install chromium

# 运行程序
python main.py          # GUI 模式
python main.py --cli    # CLI 模式
```

**提示**: 源码运行比打包版本更稳定，推荐日常使用。

### Q5: 如何选择答题模式？

**A:** v2.2.0+ 版本支持自动恢复：

1. 系统会自动检测崩溃
2. 提示重新登录
3. 自动重启浏览器
4. 继续未完成的操作

如果频繁崩溃：
- 检查系统内存是否充足
- 关闭其他占用内存的程序
- 尝试使用 API 模式答题

### Q5: 如何选择答题模式？

**A:** 根据需求选择：

| 场景 | 推荐模式 |
|------|----------|
| 快速刷题 | API 模式 |
| 验证答案准确性 | 浏览器模式 |
| 网络不稳定 | API 模式（有重试） |
| 避免检测 | 浏览器模式 |

### Q6: 可以在没有网络的環境使用吗？

**A:** 部分功能可以：

- ✅ **题库导入**: 可以预先导入 JSON 题库
- ✅ **离线答题**: 使用导入的题库答题
- ❌ **答案提取**: 需要网络连接
- ❌ **首次登录**: 需要网络连接

### Q7: 如何参与开发？

**A:** 欢迎贡献！

1. 阅读 [开发指南](#开发指南)
2. 查看 [CLAUDE.md](CLAUDE.md) 了解架构细节
3. 选择一个 [Issue](https://github.com/yourusername/ZX-Answering-Assistant-python/issues)
4. Fork 并创建分支
5. 提交 Pull Request

---

## 版本历史

### v2.7.8 (最新) - 构建系统优化

**修改内容**:
- ✅ 移除自动创建压缩包功能
- ✅ 添加版本号到 exe 文件名和目录名
- ✅ 目录模式格式：`ZX-Answering-Assistant-v2.7.8-windows-x64-installer`
- ✅ 单文件模式格式：`ZX-Answering-Assistant-v2.7.8-windows-x64-portable`

### v2.7.0 - 构建系统优化

**新增功能**:
- ✅ 构建配置文件化（YAML）
- ✅ 自动化测试套件（pytest）
- ✅ 增量构建
- ✅ 依赖缓存
- ✅ 并行构建
- ✅ 进度可视化

**性能提升**:
- 构建时间从 ~12 分钟缩短到 ~4 分钟（~65% 提升）

### v2.6.6 - 源码自动清理

- ✅ 打包后自动删除 .py 源码
- ✅ 保留 .pyc 字节码
- ✅ 减小打包体积

### v2.6.0 - 架构升级（重大更新）

- ✅ 统一浏览器管理器（BrowserManager）
- ✅ 多上下文隔离
- ✅ 课程认证模块
- ✅ API 模式课程认证答题

### v2.2.0 - 浏览器健壮性

- ✅ 浏览器崩溃自动恢复
- ✅ 浏览器健康监控
- ✅ AsyncIO 兼容

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

---

<div align="center">

**如果这个项目对你有帮助，请给个 Star 支持一下！**

Made with ❤️ by ZX Project Team

[问题反馈](https://github.com/yourusername/ZX-Answering-Assistant-python/issues) • [功能建议](https://github.com/yourusername/ZX-Answering-Assistant-python/discussions)

</div>
