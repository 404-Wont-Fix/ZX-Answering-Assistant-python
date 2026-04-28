# 编译快速参考

## ⚠️ 网络环境要求

**构建过程需要访问 Google/GitHub，请确保网络环境能访问这些服务！**

如果无法访问，请：
- 使用代理
- 或在良好网络环境下构建

---

## 最简构建流程

```bash
# 1. 激活虚拟环境
.venv\Scripts\activate

# 2. 运行构建脚本
build.bat
```

## 手动构建命令

```bash
# 标准 Flet 构建
flet build windows --project=ZX-Answering-Assistant

# 详细日志模式
flet build windows --project=ZX-Answering-Assistant --verbose
```

## 构建产物位置

```
build\windows\x64\runner\Release\ZX Answering Assistant.exe
```

## 前置要求

- ✅ Python 3.10+
- ✅ 虚拟环境已激活
- ✅ 依赖已安装（`pip install -r requirements.txt`）
- ✅ Flet 已安装（`pip install flet>=0.82.0 flet-desktop`）

## 常见问题快速修复

### 网络下载失败

**错误**：Failed to download, TimeoutError

**解决**：
```bash
# 使用代理
$env:HTTPS_PROXY = "http://127.0.0.1:7890"

# 或配置镜像
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

### Flet 未安装
```bash
pip install flet>=0.82.0 flet-desktop
```

### 构建体积过大
- 在干净目录中构建
- 确保没有包含测试文件、文档等

### 构建失败
```bash
# 查看详细日志
flet build windows --project=ZX-Answering-Assistant --verbose
```

## 配置文件

构建配置在 `pyproject.toml` 中：

```toml
[tool.flet]
project = "ZX-Answering-Assistant"
product = "ZX Answering Assistant"
org = "TianJiaJi"

[tool.flet.include]
assets = [
    "main.py",     # 主入口
    "version.py",  # 版本信息
]
```

## 完整文档

详细指南请查看：[BUILD_GUIDE.md](BUILD_GUIDE.md)
