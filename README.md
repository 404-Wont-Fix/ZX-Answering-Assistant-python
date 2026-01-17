<div align="center">

# 🎓 ZX Answering Assistant
### 智能答题助手系统

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Mac-lightgrey)]()

一个基于 Playwright 的自动化答题系统，支持学生端和教师端双模式操作，提供浏览器兼容模式和 API 暴力模式两种答题方式。

[功能特性](#功能特性) • [快速开始](#快速开始) • [使用指南](#使用指南) • [常见问题](#常见问题)

</div>

---

## 📋 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
- [配置说明](#配置说明)
- [项目结构](#项目结构)
- [技术栈](#技术栈)
- [版本管理](#版本管理)
- [常见问题](#常见问题)
- [开发规范](#开发规范)
- [免责声明](#免责声明)

---

## 🎯 项目简介

ZX Answering Assistant 是一个针对在线学习平台的自动化答题助手系统。通过浏览器自动化技术和 API 逆向分析，实现题目提取、答案匹配和自动答题等功能。

### 核心特点

- 🤖 **双模式支持**：浏览器兼容模式 + API 暴力模式
- 🎓 **双端支持**：学生端答题 + 教师端答案提取
- 🔄 **自动重试**：网络错误自动重试机制（最多3次）
- ⏸️ **优雅退出**：按 Q 键随时停止，等待当前题目/知识点完成
- 📊 **进度监控**：实时显示答题进度和统计信息
- 🗄️ **题库管理**：支持题库导入/导出，支持 JSON 和 Excel 格式

---

## ✨ 功能特性

### 学生端功能

| 功能 | 描述 | 状态 |
|------|------|------|
| 🔐 自动登录 | 支持账户密码自动登录学生端 | ✅ |
| 📚 课程管理 | 获取课程列表和进度信息 | ✅ |
| 📝 自动答题 | 浏览器模拟点击，自动匹配答案 | ✅ |
| ⚡ API 模式 | 直接调用 API，无需浏览器操作 | ✅ |
| 🔄 网络重试 | 连接失败自动重试（3次） | ✅ |
| ⏸️ 随时停止 | 按 Q 键优雅退出 | ✅ |
| 📊 实时统计 | 显示答题成功率和进度 | ✅ |

### 教师端功能

| 功能 | 描述 | 状态 |
|------|------|------|
| 🔐 教师登录 | 登录教师管理后台 | ✅ |
| 📖 答案提取 | 提取课程、章节、知识点的正确答案 | ✅ |
| 💾 数据导出 | 导出为 JSON 或 Excel 格式 | ✅ |
| 🔄 批量处理 | 支持批量提取多个课程 | ✅ |

### 答题模式对比

| 特性 | 浏览器兼容模式 | API 暴力模式 |
|------|----------------|--------------|
| 速度 | ⭐⭐⭐ 较慢 | ⭐⭐⭐⭐⭐ 极快 |
| 稳定性 | ⭐⭐⭐⭐ 高 | ⭐⭐⭐⭐ 高 |
| 资源占用 | ⭐⭐ 高（需浏览器） | ⭐⭐⭐⭐⭐ 低 |
| 检测风险 | ⭐⭐ 较高 | ⭐⭐⭐ 中等 |
| 推荐场景 | 验证答案准确性 | 快速刷题 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        ZX 智能答题助手                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │   主程序入口  │────────▶│   菜单系统   │                  │
│  │  (main.py)   │         │              │                  │
│  └──────────────┘         └──────┬───────┘                  │
│                                   │                          │
│              ┌────────────────────┼────────────────────┐    │
│              │                    │                    │    │
│              ▼                    ▼                    ▼    │
│     ┌─────────────┐      ┌─────────────┐      ┌─────────┐  │
│     │   学生端    │      │   教师端    │      │  设置   │  │
│     │    模式     │      │    模式     │      │         │  │
│     └──────┬──────┘      └──────┬──────┘      └────┬────┘  │
│            │                    │                    │      │
│            ▼                    ▼                    │      │
│     ┌─────────────┐      ┌─────────────┐            │      │
│     │  兼容模式    │      │  答案提取    │            │      │
│     │             │      │             │            │      │
│     │  (浏览器)   │      │             │            │      │
│     └──────┬──────┘      └─────────────┘            │      │
│            │                                         │      │
│            ▼                                         │      │
│     ┌─────────────┐                                  │      │
│     │  API 模式   │                                  │      │
│     │  (暴力)     │                                  │      │
│     └──────┬──────┘                                  │      │
│            │                                         │      │
└────────────┼─────────────────────────────────────────┼──────┘
             │                                         │
             ▼                                         ▼
    ┌─────────────────┐                     ┌──────────────┐
    │   题库管理系统    │                     │   配置系统    │
    └─────────────────┘                     └──────────────┘
```

### 核心模块说明

- **main.py** - 主程序入口，提供菜单系统
- **src/student_login.py** - 学生端登录和认证管理
- **src/teacher_login.py** - 教师端登录和认证管理
- **src/auto_answer.py** - 浏览器兼容模式答题
- **src/api_auto_answer.py** - API 暴力模式答题
- **src/extract.py** - 教师端答案提取
- **src/export.py** - 数据导出（JSON/Excel）
- **src/question_bank_importer.py** - 题库导入和管理

---

## 🚀 快速开始

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

### 4. 配置系统

```bash
# 复制配置文件模板
# Windows
copy config\config.example.yaml config\config.yaml

# Linux/Mac
cp config/config.example.yaml config/config.yaml
```

### 5. 运行程序

```bash
python main.py
```

---

## 📖 使用指南

### 主菜单

启动程序后，会显示主菜单：

```
╔══════════════════════════════════════════════════════╗
║         ZX Answering Assistant - 主菜单              ║
╠══════════════════════════════════════════════════════╣
║  1. 开始答题                                         ║
║  2. 提取题目（教师端）                               ║
║  3. 设置                                             ║
║  0. 退出                                             ║
╚══════════════════════════════════════════════════════╝
```

### 开始答题流程

#### 方式一：批量答题（推荐）

1. 选择 `1. 开始答题`
2. 选择 `1. 批量答题`
3. 登录学生账户（默认账户：`530XXXXXXXXXXXXXXXX` / `XXXXXX`）
4. 查看课程列表和完成进度
5. 选择要作答的课程
6. 选择答题模式：
   - **兼容模式**：浏览器模拟点击，稳定但较慢
   - **API 模式**：直接调用 API，速度快
7. 等待自动答题完成

#### 方式二：单课程答题

1. 选择 `1. 开始答题`
2. 选择 `3. 单课程答题`
3. 选择答题模式
4. 输入课程 ID
5. 开始自动答题

### 提取题目流程（教师端）

1. 选择 `2. 提取题目`
2. 选择 `1. 获取教师 Token`
3. 登录教师账户
4. 选择 `2. 提取所有课程` 或 `3. 提取单个课程`
5. 等待提取完成
6. 选择 `4. 导出结果`

### 题库导入

1. 选择 `1. 开始答题`
2. 选择 `4. 题库导入`
3. 选择题库文件（JSON 或 Excel 格式）
4. 确认导入

### 操作快捷键

| 快捷键 | 功能 |
|--------|------|
| `Q` | 停止当前答题操作（等待当前题目/知识点完成） |
| `Ctrl + C` | 强制退出程序 |

---

## ⚙️ 配置说明

### 配置文件 (config/config.yaml)

```yaml
app:
  name: "ZX Answering Assistant"
  version: "1.1.0"
  debug: false

logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  format: "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
  rotation: "100 MB"
  retention: "7 days"

data:
  input_dir: "data/input"
  output_dir: "data/output"
  temp_dir: "data/temp"

network:
  timeout: 30
  retry_delay: 2
  max_retries: 3

answer:
  mode: "compatible"  # compatible, api
  delay_between_questions: 1.5
  delay_between_knowledges: 3
```

### 环境变量 (.env)

```env
# 学生端默认账户
STUDENT_USERNAME=530XXXXXXXXXXXXXXX
STUDENT_PASSWORD=XXXXXX

# 教师端账户（需要手动输入）
TEACHER_USERNAME=
TEACHER_PASSWORD=

# API 配置
API_BASE_URL=https://ai.cqzuxia.com
```

---

## 📁 项目结构

```
ZX-Answering-Assistant-python/
├── data/                          # 数据目录
│   ├── input/                     # 输入文件（题库）
│   ├── output/                    # 输出文件（导出结果）
│   └── temp/                      # 临时文件
├── config/                        # 配置文件
│   ├── config.example.yaml        # 配置模板
│   └── config.yaml                # 用户配置（需创建）
├── src/                           # 源代码
│   ├── __init__.py
│   ├── student_login.py           # 学生端登录
│   ├── teacher_login.py           # 教师端登录
│   ├── auto_answer.py             # 浏览器兼容模式
│   ├── api_auto_answer.py         # API 暴力模式
│   ├── extract.py                 # 答案提取
│   ├── export.py                  # 数据导出
│   ├── question_bank_importer.py  # 题库导入
│   └── file_handler.py            # 文件处理
├── logs/                          # 日志文件
├── tests/                         # 测试代码
├── venv/                          # 虚拟环境（不提交）
├── main.py                        # 主程序入口
├── extract_answers.py             # 独立答案提取脚本
├── build.py                       # PyInstaller 打包脚本
├── version.py                     # 版本信息管理
├── VERSION.md                     # 版本管理文档
├── requirements.txt               # Python 依赖
├── .gitignore                     # Git 忽略文件
├── CLAUDE.md                      # Claude Code 指导文档
└── README.md                      # 项目说明文档
```

---

## 🛠️ 技术栈

### 核心依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| **playwright** | ≥1.57.0 | 浏览器自动化 |
| **requests** | ≥2.31.0 | HTTP 请求 |
| **loguru** | ≥0.7.0 | 日志管理 |
| **pyyaml** | ≥6.0 | YAML 配置解析 |
| **python-dotenv** | ≥1.0.0 | 环境变量管理 |
| **pandas** | ≥2.0.0 | 数据处理 |
| **openpyxl** | ≥3.1.0 | Excel 文件处理 |
| **keyboard** | ≥0.13.5 | 键盘监听 |
| **aiohttp** | ≥3.9.0 | 异步 HTTP |
| **tqdm** | ≥4.66.0 | 进度条显示 |

### API 端点

**学生端 (https://ai.cqzuxia.com/)**
- `/connect/token` - OAuth2 令牌获取
- `/evaluation/api/StuEvaluateReport/GetStuLatestTermCourseReports` - 课程列表
- `/studentevaluate/beginevaluate` - 开始测评
- `/StudentEvaluate/SaveEvaluateAnswer` - 保存答案
- `/StudentEvaluate/SaveTestMemberInfo` - 提交试卷

**教师端 (https://admin.cquxia.com/)**
- `/evaluation/api/TeacherEvaluation/GetClassByTeacherID` - 班级列表
- `/evaluation/api/TeacherEvaluation/GetEvaluationSummaryByClassID` - 课程摘要
- `/evaluation/api/TeacherEvaluation/GetChapterEvaluationByClassID` - 章节列表
- `/evaluation/api/TeacherEvaluation/GetEvaluationKnowledgeSummaryByClass` - 知识点
- `/evaluation/api/TeacherEvaluation/GetKnowQuestionEvaluation` - 题目列表
- `/evaluation/api/TeacherEvaluation/GetQuestionAnswerListByQID` - 答案选项

---

## 📦 版本管理

### 版本信息

项目使用 `version.py` 文件管理版本信息，包含以下内容：

- `VERSION`: 主版本号（当前：1.1.0）
- `VERSION_NAME`: 程序名称
- `BUILD_DATE`: 构建日期（打包时自动更新）
- `BUILD_TIME`: 构建时间（打包时自动更新）
- `GIT_COMMIT`: Git提交哈希（打包时自动更新）
- `BUILD_MODE`: 构建模式（development 或 release）

### 修改版本号

编辑 [version.py](version.py) 文件中的 `VERSION` 变量：

```python
VERSION = "1.1.0"  # 修改版本号
```

### 打包项目

```bash
# 查看打包选项
python build.py --help

# 目录模式（默认，启动快）
python build.py

# 单文件模式
python build.py --mode onefile
```

### 打包模式对比

| 特性 | onedir（默认）⭐ | onefile |
|-----|------------------|---------|
| 启动速度 | 快（1-3秒） | 慢（30秒-2分钟） |
| 文件形式 | 整个文件夹 | 单个exe |
| 分发方式 | 分发文件夹 | 分发单个文件 |
| 适用场景 | 追求快速启动 | 对启动速度要求不高 |

### 版本显示

程序启动时会自动显示版本信息：

```
============================================================
📦 ZX Answering Assistant v1.1.0 (Build 2026-01-17)
============================================================
版本号: 1.1.0
构建日期: 2026-01-17
构建时间: 18:30:45
Git提交: abc1234
构建模式: release
============================================================
```

### 版本号规范

遵循语义化版本控制（Semantic Versioning）：

- 主版本号.次版本号.修订号
- 例如：1.0.0, 1.0.1, 1.1.0

**版本更新规则：**

- **主版本号**：不兼容的API修改
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正

详细版本管理说明请查看 [VERSION.md](VERSION.md)

---

## ❓ 常见问题

### Q1: 如何处理网络连接错误？

**A:** 系统已内置自动重试机制：
- 最多重试 3 次
- 每次重试间隔 2 秒
- 仅对网络错误重试（ConnectionResetError、Connection aborted 等）

如果仍然失败，请检查：
- 网络连接是否稳定
- 防火墙是否阻止了请求
- 代理设置是否正确

### Q2: 如何停止正在运行的答题？

**A:** 按 `Q` 键可以优雅退出：
- 如果正在答题：等待当前题目完成
- 如果正在处理知识点：等待当前知识点完成
- 否则：立即停止

### Q3: 两种答题模式有什么区别？

**A:**

| 特性 | 兼容模式 | API 模式 |
|------|----------|----------|
| 实现方式 | 浏览器模拟点击 | 直接调用 API |
| 速度 | 较慢（需要页面加载） | 极快（纯 HTTP 请求） |
| 资源占用 | 高（需要浏览器） | 低（仅网络请求） |
| 稳定性 | 高 | 高 |
| 适用场景 | 验证答案、学习用途 | 快速刷题 |

### Q4: Token 过期了怎么办？

**A:** 系统会自动处理：
- Token 有效期：5 小时
- 提前 10 分钟过期检测
- 自动重新获取 Token
- 无需手动干预

### Q5: 如何打包成可执行文件？

**A:** 运行打包脚本：

```bash
# 查看打包选项
python build.py --help

# 目录模式（默认，启动快）
python build.py

# 单文件模式
python build.py --mode onefile
```

**打包模式对比：**

| 特性 | onedir（默认）⭐ | onefile |
|-----|------------------|---------|
| 启动速度 | 快（1-3秒） | 慢（30秒-2分钟） |
| 文件形式 | 整个文件夹 | 单个exe |
| 分发方式 | 分发文件夹 | 分发单个文件 |
| 适用场景 | 追求快速启动 | 对启动速度要求不高 |

**打包输出：**

- **onedir 模式**: `dist/ZX-Answering-Assistant/ZX-Answering-Assistant.exe`
- **onefile 模式**: `dist/ZX-Answering-Assistant.exe`

**版本信息：**

打包时会自动更新：
- 构建日期
- 构建时间
- Git 提交哈希
- 构建模式

程序启动时会显示完整的版本信息。

详细版本管理说明请查看 [VERSION.md](VERSION.md)

### Q6: Playwright 浏览器安装失败？

**A:** 尝试以下方法：

```bash
# 方法 1：手动安装
python -m playwright install chromium

# 方法 2：使用国内镜像
set PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/
python -m playwright install chromium

# 方法 3：清理缓存后重试
python -m playwright clean
python -m playwright install chromium
```

### Q7: 如何调试日志？

**A:** 修改配置文件 `config/config.yaml`：

```yaml
logging:
  level: "DEBUG"  # 改为 DEBUG 级别
```

或在代码中设置：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Q8: 支持多开吗？

**A:** 不支持。Playwright 浏览器实例无法在同一进程中并发运行。如需同时操作学生端和教师端，请使用 `extract_answers.py` 作为独立进程运行。

---

## 👨‍💻 开发规范

### 代码规范

1. **虚拟环境**: 所有开发工作必须在虚拟环境中进行
2. **测试优先**: 修改功能前先在独立测试文件中验证
3. **代码风格**:
   - 遵循 PEP 8 规范
   - 使用有意义的变量名和函数名
   - 添加必要的注释和文档字符串
4. **错误处理**: 所有异常必须被捕获并记录日志
5. **日志级别**:
   - DEBUG: 调试信息
   - INFO: 一般信息
   - WARNING: 警告信息
   - ERROR: 错误信息

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

**示例:**

```
feat(auto_answer): 添加 API 暴力模式答题功能

- 实现 APIAutoAnswer 类
- 添加网络重试机制
- 支持 Q 键优雅退出

Closes #123
```

### 贡献流程

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📜 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## ⚠️ 免责声明

本项目仅供学习和研究使用，请勿用于商业用途或任何违反服务条款的行为。使用本软件所产生的一切后果由使用者自行承担，作者不承担任何责任。

### 使用须知

1. ⚠️ 本工具仅用于个人学习和研究
2. ⚠️ 请遵守目标平台的使用条款
3. ⚠️ 禁止用于任何商业用途
4. ⚠️ 使用风险自负，作者不承担责任
5. ⚠️ 请勿过于频繁使用，避免账号异常

---

## 📞 联系方式

- **问题反馈**: [GitHub Issues](https://github.com/yourusername/ZX-Answering-Assistant-python/issues)
- **功能建议**: [GitHub Discussions](https://github.com/yourusername/ZX-Answering-Assistant-python/discussions)

---

## 🙏 致谢

感谢以下开源项目：

- [Playwright](https://playwright.dev/) - 浏览器自动化框架
- [Requests](https://requests.readthedocs.io/) - HTTP 库
- [Loguru](https://github.com/Delgan/loguru) - 日志库
- [Pandas](https://pandas.pydata.org/) - 数据处理库

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐️ Star 支持一下！**

Made with ❤️ by [Your Name]

</div>
