# ZX Answering Assistant v3.6.1 发布说明

## 🎉 版本概览

**发布日期**: 2026-05-14
**版本号**: v3.6.1
**构建模式**: 稳定修复版本

---

## 🐛 主要修复

### 1. Flet版本兼容性修复
**问题**: Flet 0.82.0+版本API变化导致应用程序无法启动
**解决方案**:
- 修复`window_center`方法调用
- 更新`ft.app()` → `ft.run()`
- 固定Flet版本至0.82.2确保稳定性
- 更新所有相关API调用

### 2. 系统浏览器自动检测优化
**改进**: 完全自动化的系统浏览器支持
**特性**:
- ✅ 自动检测系统Chrome浏览器
- ✅ 自动检测系统Edge浏览器
- ✅ 智能选择优先级：Chrome > Edge > Playwright内置
- ✅ 无需手动配置，无需下载额外浏览器

### 3. Greenlet线程切换错误修复
**问题**: GUI模式下出现"cannot switch to a different thread"错误
**解决方案**:
- 完善BrowserManager工作线程机制
- 修复`Extractor`类的浏览器初始化
- 统一所有模块使用BrowserManager
- 确保所有Playwright操作在同一线程中执行

### 4. Windows编码问题修复
**问题**: emoji字符在Windows GBK编码下报错
**解决方案**:
- 替换所有emoji为文本标记
- `[OK]` 替代 ✅
- `[INFO]` 替代 💡/📋
- `[WARNING]` 替代 ⚠️
- `[ERROR]` 替代 ❌

---

## 🚀 部署改进

### 最小化部署
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行应用
python main.py
```

### 核心优势
- **零额外配置**: 无需下载Playwright浏览器（~300MB）
- **完全自动化**: 自动检测并使用系统Chrome/Edge
- **统一管理**: 所有模块通过BrowserManager统一管理
- **兼容性**: 支持GUI和CLI模式，完全兼容Windows系统

---

## 📝 技术细节

### 依赖版本固定
```txt
flet==0.82.2
flet-desktop==0.82.2
playwright>=1.57.0
```

### 文件变更
- `src/main_gui.py` - Flet API修复
- `src/core/browser.py` - 浏览器管理优化
- `src/extraction/extractor.py` - 重构使用BrowserManager
- `src/certification/workflow.py` - emoji字符修复
- `requirements.txt` - 版本固定

---

## 🔧 升级指南

### 从v3.6.0升级
1. 拉取最新代码: `git pull`
2. 重新安装依赖: `pip install -r requirements.txt`
3. 直接运行: `python main.py`

### 新环境安装
1. 克隆仓库: `git clone https://github.com/TianJiaJi/ZX-Answering-Assistant-python.git`
2. 安装依赖: `pip install -r requirements.txt`
3. 运行应用: `python main.py`

---

## ⚠️ 已知问题
- 无重大问题

## 📋 下一步计划
- 继续优化用户体验
- 完善插件系统
- 增强错误处理机制

---

## 💬 反馈与支持
- **问题报告**: [GitHub Issues](https://github.com/TianJiaJi/ZX-Answering-Assistant-python/issues)
- **功能建议**: [GitHub Discussions](https://github.com/TianJiaJi/ZX-Answering-Assistant-python/discussions)

---

**感谢使用ZX Answering Assistant！** 🎯
