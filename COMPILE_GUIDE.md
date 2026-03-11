# ZX Answering Assistant - 详细编译指南

## 准备工作

### 1. 确保环境准备就绪

```bash
# 激活虚拟环境（如果使用）
.\venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器（必需）
python -m playwright install chromium

# 安装 PyInstaller（如果还没有）
pip install pyinstaller
```

### 2. 验证环境

```bash
# 检查 Playwright 是否安装成功
python -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"

# 检查 Flet 是否安装成功
python -c "import flet; print('Flet OK')"
```

## 编译步骤

### 方案一：标准编译（推荐新手）

#### 步骤 1：准备依赖

```bash
# 下载 Flet 可执行文件（首次必需，约 50-100MB）
python build.py --copy-flet

# 复制 Playwright 浏览器（首次必需，约 300MB）
python build.py --copy-browser

# 或一次性完成两者
python build.py --copy-all
```

**预期输出**：
```
✅ Flet可执行文件已存在且完整
[OK] Flet已准备就绪 (XX.XX MB)
✅ Playwright浏览器已存在且完整
[OK] 浏览器已准备就绪 (XXX.XX MB)
```

#### 步骤 2：编译项目

```bash
# 基础编译（目录模式）
python build.py

# 或指定模式
python build.py --mode onedir
```

**编译过程**：
```
============================================================
ZX Answering Assistant - 构建工具
============================================================
[INFO] 构建模式: onedir

[INFO] 正在准备 Playwright 浏览器...
✅ Playwright浏览器已存在且完整
[OK] 浏览器已准备就绪 (327.45 MB)

[INFO] 正在准备 Flet 可执行文件...
✅ Flet可执行文件已存在且完整
[OK] Flet已准备就绪 (87.32 MB)

[INFO] 平台: windows x64
[INFO] 输出名称: ZX-Answering-Assistant-v2.7.0-windows-x64-installer

[INFO] 将打包 Playwright 浏览器
[INFO] 将打包 Flet 可执行文件

[INFO] 开始构建 (onedir 模式)...
[CMD] pyinstaller --onedir ...
（这里会持续几分钟，请耐心等待）

============================================================
[OK] 构建完成！
============================================================
[PATH] 可执行文件: dist\ZX-Answering-Assistant-v2.7.0-windows-x64-installer\ZX-Answering-Assistant-v2.7.0-windows-x64-installer.exe
[PATH] 分发目录: dist\ZX-Answering-Assistant-v2.7.0-windows-x64-installer
============================================================
```

#### 步骤 3：测试编译结果

```bash
# 进入输出目录
cd dist\ZX-Answering-Assistant-v2.7.0-windows-x64-installer

# 运行可执行文件
.\ZX-Answering-Assistant-v2.7.0-windows-x64-installer.exe
```

### 方案二：优化编译（推荐进阶用户）

#### 启用源码预编译（减小体积 20-30%）

```bash
# 编译 + 源码预编译
python build.py --mode onedir --compile-src
```

**效果**：
- 源码编译为 .pyc 字节码
- 打包后自动删除 .py 文件（onedir 模式）
- 提供轻度源码保护

#### 启用 UPX 压缩（减小体积 30-50%）

```bash
# 首先需要安装 UPX
# 下载：https://github.com/upx/upx/releases
# 解压后将 upx.exe 添加到系统 PATH

# 编译 + UPX 压缩
python build.py --mode onedir --upx
```

#### 完整优化（最佳效果）

```bash
# 源码预编译 + UPX 压缩
python build.py --mode onedir --compile-src --upx
```

**预期效果**：
- 原始大小：约 700-800 MB
- 预编译后：约 600-700 MB
- UPX 压缩后：约 350-400 MB

### 方案三：单文件模式

```bash
# 编译为单个 .exe 文件
python build.py --mode onefile

# 或优化版本
python build.py --mode onefile --compile-src --upx
```

**注意**：
- 单文件模式首次启动较慢（需要解压）
- 不支持删除源码（PyInstaller 限制）
- 文件更大但分发更方便

### 方案四：同时编译两种模式

```bash
# 编译目录模式和单文件模式
python build.py --mode both

# 或优化版本
python build.py --mode both --compile-src --upx
```

## 编译选项说明

| 参数 | 简写 | 说明 | 推荐度 |
|------|------|------|--------|
| `--mode onedir` | `-m onedir` | 目录模式（推荐） | ⭐⭐⭐⭐⭐ |
| `--mode onefile` | `-m onefile` | 单文件模式 | ⭐⭐⭐⭐ |
| `--mode both` | `-m both` | 两种模式都编译 | ⭐⭐⭐⭐⭐ |
| `--compile-src` | - | 源码预编译为 .pyc | ⭐⭐⭐⭐ |
| `--upx` | - | UPX 压缩 | ⭐⭐⭐ |
| `--build-dir` | `-b` | 指定输出目录 | ⭐⭐⭐ |

## 常见编译场景

### 场景 1：日常使用（目录模式）

```bash
python build.py --mode onedir
```

### 场景 2：分发给用户（目录模式 + 优化）

```bash
python build.py --mode onedir --compile-src --upx
```

### 场景 3：快速测试（单文件模式）

```bash
python build.py --mode onefile
```

### 场景 4：发布所有版本

```bash
python build.py --mode both --compile-src --upx
```

## 编译后的目录结构

### onedir 模式

```
dist/
└── ZX-Answering-Assistant-v2.7.0-windows-x64-installer/
    ├── ZX-Answering-Assistant-v2.7.0-windows-x64-installer.exe  # 主程序
    └── _internal/                                               # 依赖文件
        ├── pythonXXX.dll
        ├── src/
        │   ├── *.pyc                                           # 编译后的字节码
        │   └── __init__.py                                     # 保留的包文件
        ├── playwright_browsers/
        │   └── chromium-1200/                                   # 内置浏览器
        │       └── chrome-win/chrome.exe
        ├── flet_browsers/
        │   └── unpacked/app/flet/flet/flet.exe                 # 内置 Flet
        └── ... (其他依赖)
```

### onefile 模式

```
dist/
└── ZX-Answering-Assistant-v2.7.0-windows-x64-portable.exe      # 单个文件
```

## 编译时间参考

| 配置 | 首次编译 | 后续编译 |
|------|---------|---------|
| 基础编译 | 5-10 分钟 | 3-5 分钟 |
| + 预编译 | 6-12 分钟 | 4-6 分钟 |
| + UPX 压缩 | 10-20 分钟 | 8-15 分钟 |

## 故障排除

### 问题 1：PyInstaller 找不到模块

```bash
# 确保在虚拟环境中
pip install pyinstaller

# 重新安装依赖
pip install -r requirements.txt --force-reinstall
```

### 问题 2：浏览器复制失败

```bash
# 确保安装了 Playwright 浏览器
python -m playwright install chromium

# 手动复制
python build.py --copy-browser
```

### 问题 3：Flet 下载失败

```bash
# 使用修复脚本
python fix_flet_download.py

# 或手动下载
python build.py --copy-flet
```

### 问题 4：编译失败，提示路径包含中文

```bash
# 使用自定义输出目录（无中文路径）
python build.py --build-dir D:\BuildOutput
```

### 问题 5：UPX 压缩失败

```bash
# 检查 UPX 是否安装
upx --version

# 如果未安装，跳过 UPX
python build.py --mode onedir --compile-src
```

## 编译检查清单

编译前：
- [ ] 已激活虚拟环境
- [ ] 已安装所有依赖 (`pip install -r requirements.txt`)
- [ ] 已安装 Playwright 浏览器 (`python -m playwright install chromium`)
- [ ] 已准备 Flet 可执行文件 (`python build.py --copy-flet`)
- [ ] 确认磁盘空间充足（至少 2GB）

编译后：
- [ ] 检查输出目录是否存在
- [ ] 验证可执行文件是否存在
- [ ] 运行可执行文件测试功能
- [ ] 检查文件大小是否符合预期

## 验证编译结果

```bash
# 1. 检查目录结构
ls dist\ZX-Answering-Assistant-v2.7.0-windows-x64-installer\

# 2. 检查可执行文件
ls dist\ZX-Answering-Assistant-v2.7.0-windows-x64-installer\*.exe

# 3. 检查内置浏览器
ls dist\ZX-Answering-Assistant-v2.7.0-windows-x64-installer\_internal\playwright_browsers\chromium-1200\chrome-win\chrome.exe

# 4. 检查内置 Flet
ls dist\ZX-Answering-Assistant-v2.7.0-windows-x64-installer\_internal\flet_browsers\unpacked\app\flet\flet\flet.exe

# 5. 测试运行
cd dist\ZX-Answering-Assistant-v2.7.0-windows-x64-installer\
.\ZX-Answering-Assistant-v2.7.0-windows-x64-installer.exe
```

## 清理编译产物

```bash
# 清理所有编译输出
rm -r -force build
rm -r -force dist
rm -r -force src_compiled

# 清理特定输出
rm -r -force dist\ZX-Answering-Assistant-v2.7.0-windows-x64-installer
```

## 下一步

编译成功后：

1. **测试功能**
   ```bash
   cd dist\ZX-Answering-Assistant-v2.7.0-windows-x64-installer
   .\ZX-Answering-Assistant-v2.7.0-windows-x64-installer.exe
   ```

2. **分发给用户**
   - 压缩整个目录为 ZIP 文件
   - 或使用安装程序打包工具（如 NSIS）

3. **版本管理**
   - 在 `version.py` 中更新版本号
   - 提交到 Git 仓库
   - 创建 GitHub Release

需要帮助？查看：
- `BUILD_CHECKLIST.md` - 验证清单
- `FLET_DOWNLOAD_FIX.md` - Flet 下载问题修复
- `BUILD.md` - 构建系统说明
