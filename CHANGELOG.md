# 更新日志

## [v3.5.0] - 2026-04-27

### 🎨 优化项目

#### 清理项目结构
- ✅ 删除 `cache_template.py` 和 `cache_template.bat`（Flet 自动处理模板缓存）
- ✅ 删除多余文档（BUILD_CACHE_GUIDE.md、BUILD_FIXES.md 等）
- ✅ 整合文档结构，提高可维护性

#### 优化依赖
- ✅ 移除 `pyyaml` 和 `py7zr`（Flet 打包时自动安装）
- ✅ 移除 `keyboard`（代码中未使用）
- ✅ 保留所有运行时必需依赖

#### 更新版本号
- ✅ 版本号更新到 v3.5.0
- ✅ 更新所有文档和配置文件

### 📝 说明

本项目采用 Flet 构建系统，会自动处理以下内容：
- 模板自动下载和缓存到 `build/flutter`
- 无需手动管理模板缓存
- `build.bat` 提供一键清理并编译功能

所有功能保持不变，仅优化项目结构和依赖管理。

---

## [v3.4.1] - 2026-04-27

### 🎉 新增功能

#### 启动动画系统
- ✅ **运行时加载界面** - 应用启动时显示加载动画
  - 显示应用图标、标题和版本号
  - 进度条动画效果
  - 渐变背景色
  - 加载提示文字

- ✅ **编译时启动画面** - 配置启动画面（Splash Screen、Boot Screen、Startup Screen）
  - Splash Screen: 应用图标 + 品牌蓝色背景 (#0B6BFF)
  - Boot Screen: 首次启动解压提示
  - Startup Screen: Python 运行时初始化提示

#### 构建缓存系统
- ✅ **模板缓存脚本** - 自动下载并缓存 Flet 构建模板
  - `cache_template.py` - Python 缓存脚本
  - `cache_template.bat` - Windows 一键缓存
  - 避免每次编译都从 GitHub 下载模板

- ✅ **自动构建脚本** - 一键清理并编译
  - `build.bat` - Windows 自动构建脚本
  - 自动清理旧的构建文件和缓存
  - 确保干净的编译环境

### 🔧 修复问题

#### 修复 1: `__builtins__` 兼容性
- **问题**: 打包后运行时 `AttributeError: 'dict' object has no attribute 'exit'`
- **原因**: 在某些 Python 环境中，`__builtins__` 是字典而不是模块
- **修复**: 兼容字典和模块两种情况

#### 修复 2: Flet API 兼容性 (v0.82.2)
- **问题**: `AttributeError: module 'flet.controls.alignment' has no attribute 'center'`
- **原因**: Flet 0.82.2 版本的 API 与文档示例不完全一致
- **修复**:
  - `ft.alignment.center` → `ft.Alignment(0, 0)`
  - `ft.alignment.top_center` → `ft.Alignment(-1, -1)`
  - `ft.alignment.bottom_center` → `ft.Alignment(1, 1)`

#### 修复 3: 软件标题乱码
- **问题**: 编译后应用标题显示为乱码
- **原因**: `pyproject.toml` 中的 `product` 字段包含中文字符
- **修复**: 改为英文 `product = "ZX Answering Assistant"`
- **说明**: 应用内部的中文界面不受影响

#### 修复 4: 启动屏幕中文显示
- **问题**: 启动屏幕消息为英文
- **修复**: 改回中文，但使用单行文本（避免多行导致的编译错误）
  - `message = "正在准备首次启动"`
  - `message = "正在加载组件"`
  - `message = "正在初始化应用"`

#### 修复 5: 模板缓存 Windows 文件占用
- **问题**: 下载模板后解压失败 `[WinError 32] 另一个程序正在使用此文件`
- **原因**: Windows 系统临时文件被占用
- **修复**:
  - 使用自定义临时目录 `flet_template_cache`
  - 添加文件删除重试机制（最多 3 次）
  - 先删除旧缓存，避免解压冲突

#### 修复 6: ImportError: No module named main
- **问题**: 编译后运行时找不到主模块
- **原因**: 模板缓存损坏或构建配置不正确
- **修复**:
  - 添加 `build.bat` 自动清理并重建
  - 配置正确的文件包含规则
  - 提供手动清理缓存的说明

### 📝 配置优化

#### pyproject.toml 优化
```toml
[tool.flet]
# 产品名称（英文，避免乱码）
product = "ZX Answering Assistant"
# 描述（英文，避免乱码）
description = "Intelligent Answering Assistant System"

# 启动画面配置
[tool.flet.splash]
color = "#0B6BFF"          # 品牌蓝色
dark_color = "#1a1a1a"     # 深色模式

# 启动屏幕（中文，单行）
[tool.flet.app.startup_screen]
show = true
message = "正在加载组件"

# 排除不必要的文件
exclude = [
    "*.pyc", "__pycache__", ".git", ".venv", "venv",
    "tests", "docs", "*.md", ".gitignore", "CLAUDE.md", ".claude",
]
```

### 📚 新增文档

1. **BUILD_CACHE_GUIDE.md** - 构建模板缓存完整指南
   - 模板缓存原理和使用方法
   - 故障排除和最佳实践
   - 性能对比和优化建议

2. **BUILD_FIXES.md** - 编译问题修复指南
   - 三个主要问题的详细说明
   - pyproject.toml 配置规则
   - 验证修复的方法

3. **STARTUP_ANIMATION_GUIDE.md** - 启动动画配置指南
   - 编译时启动画面配置
   - 运行时加载界面自定义
   - 使用建议和故障排除

4. **BUILD_QUICK_START.md** - 快速编译指南
   - 首次编译步骤
   - 后续编译命令
   - 速度对比说明

### ⚡ 性能提升

| 项目 | 之前 | 现在 | 提升 |
|------|------|------|------|
| 首次编译 | 5-10 分钟（每次都下载） | 5-10 分钟（仅首次） | - |
| 后续编译 | 5-10 分钟（每次都下载） | 2-3 分钟（使用缓存） | **60-70%** |
| 启动体验 | 黑屏等待 | 启动动画 | **用户体验提升** |

### 🔨 开发者体验改进

1. **一键缓存模板** - `cache_template.bat` 双击运行
2. **一键构建** - `build.bat` 自动清理并编译
3. **详细文档** - 完整的故障排除指南
4. **配置验证** - pyproject.toml 配置规则说明

### ⚠️ 重要提示

**pyproject.toml 配置规则**:
- ✅ `product`、`description` 使用英文（避免编码问题）
- ✅ `message` 可以使用中文，但必须是单行
- ❌ 不要在 `message` 中使用 `\n` 换行符
- ❌ 避免使用 emoji 表情符号

### 🎯 下一步计划

- [ ] 添加应用图标（favicon.ico）
- [ ] 配置应用元数据（版本、版权等）
- [ ] 优化打包体积（排除更多不必要文件）
- [ ] 添加自动更新功能

---

## [v3.4.0] - 2026-04-27

### 🔒 新增功能
- 自动 SSL 证书配置功能
- 解决 Windows 环境下的 SSL 验证失败问题
- 新增 SSL 测试工具 (`test_ssl.py`)

### 🐛 修复问题
- Flet 首次下载时的 SSL 证书验证错误
- 添加 certifi 到 requirements.txt

---

## [v3.0.0] - 2026-04-21

### 🎉 重大更新
- 完成插件化架构重构
- 新增插件中心视图
- 支持插件动态加载和管理
- 新增依赖注入系统

### 🐛 修复问题
- 修复多个 UI 问题
- 完善插件开发文档

---

## 版本命名规则

- **主版本号** (Major): 重大架构变更
- **次版本号** (Minor): 新功能
- **修订号** (Patch): Bug 修复和小改进
- **构建号**: Git 提交哈希的前 7 位

---

## 相关链接

- [GitHub Releases](https://github.com/TianJiaJi/ZX-Answering-Assistant-python/releases)
- [问题追踪](https://github.com/TianJiaJi/ZX-Answering-Assistant-python/issues)
- [更新日志完整版](CHANGELOG_FULL.md)
