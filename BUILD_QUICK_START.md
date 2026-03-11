# Build System - Quick Start

快速入门指南 - 5 分钟构建你的第一个可执行文件

## 第一次使用

### 1. 安装依赖

```bash
pip install pyinstaller pyyaml
```

### 2. 安装 Playwright 浏览器（可选但推荐）

```bash
python -m playwright install chromium
```

### 3. 开始构建

```bash
# 目录模式（推荐）
python build.py

# 单文件模式
python build.py --mode onefile
```

## 输出位置

构建完成后，在 `dist/` 目录找到可执行文件：

**目录模式：**
```
dist/ZX-Answering-Assistant/ZX-Answering-Assistant.exe
```

**单文件模式：**
```
dist/ZX-Answering-Assistant.exe
```

## 常用命令

```bash
# 查看帮助
python build.py --help

# 启用 UPX 压缩（减小体积）
python build.py --upx

# 清理构建产物
python build.py --clean

# 构建两种模式
python build.py --mode both

# 不编译源代码（调试时使用）
python build.py --no-compile

# 自定义输出目录
python build.py --build-dir "C:\MyBuilds"
```

## 配置文件

编辑 `build_config.yaml` 自定义构建选项：

```yaml
# 启用源码编译（推荐用于生产）
compilation:
  enabled: true

# 启用浏览器打包
playwright:
  enabled: true

# 启用 UPX 压缩
upx:
  enabled: true
```

## 问题排查

### PyInstaller 找不到模块

```bash
pip install -r requirements.txt
```

### 构建体积太大

```bash
# 启用 UPX 压缩
python build.py --upx
```

### 可执行文件无法运行

1. 检查是否安装了所有依赖
2. 尝试目录模式而不是单文件模式
3. 查看详细文档：[BUILD.md](BUILD.md)

## 下一步

- 阅读 [BUILD.md](BUILD.md) 获取完整文档
- 查看 [README.md](README.md) 了解项目功能
- 检查 `build_config.yaml` 中的所有配置选项

---

**需要帮助？** 查看 [BUILD.md](BUILD.md) 中的故障排除章节
