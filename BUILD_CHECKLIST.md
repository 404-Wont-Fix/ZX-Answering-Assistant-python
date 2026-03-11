# 浏览器和 Flet 打包功能验证清单

## 快速验证步骤

### 1. 安装 Playwright 浏览器

```bash
python -m playwright install chromium
```

预期输出：
```
Downloading Chromium 1200...
Chromium downloaded to C:\Users\<用户名>\AppData\Local\ms-playwright\chromium-1200
```

### 2. 测试浏览器复制功能

```bash
python build.py --copy-browser
```

预期输出：
```
============================================================
准备Playwright浏览器
============================================================
✅ 找到浏览器路径: C:\Users\...\AppData\Local\ms-playwright\chromium-1200\chrome-win\chrome.exe
✅ 浏览器根目录: C:\Users\...\AppData\Local\ms-playwright\chromium-1200

正在复制浏览器到: D:\...\playwright_browsers\chromium-1200
这可能需要几分钟...
✅ 浏览器复制完成！
📊 大小: XXX.XX MB
```

验证目录：
```bash
ls playwright_browsers/chromium-1200/chrome-win/chrome.exe
```

### 3. 测试 Flet 下载功能

```bash
python build.py --copy-flet
```

预期输出：
```
============================================================
准备Flet可执行文件
============================================================
============================================================
📥 正在下载 Flet v0.82.2 可执行文件
============================================================
📥 下载源: monlor
⏳ 这可能需要几分钟，请稍候...
✅ 下载完成！大小: XXX.XX MB
```

验证目录：
```bash
ls flet_browsers/unpacked/app/flet/flet/flet.exe
```

### 4. 测试完整打包流程

```bash
python build.py --mode onedir
```

预期输出：
```
[INFO] 正在准备 Playwright 浏览器...
✅ Playwright浏览器已存在且完整
[OK] 浏览器已准备就绪 (XXX.XX MB)

[INFO] 正在准备 Flet 可执行文件...
✅ Flet可执行文件已存在且完整
[OK] Flet已准备就绪 (XXX.XX MB)

[INFO] 将打包 Playwright 浏览器
[INFO] 将打包 Flet 可执行文件

[INFO] 开始构建 (onedir 模式)...
[CMD] pyinstaller --onedir ... --add-data playwright_browsers;playwright_browsers ... --add-data flet_browsers/unpacked;flet_browsers/unpacked ...
```

### 5. 验证打包结果

检查打包后的目录：
```bash
# onedir 模式
ls dist/ZX-Answering-Assistant-v2.7.0-windows-x64-installer/_internal/playwright_browsers/chromium-1200/chrome-win/chrome.exe

ls dist/ZX-Answering-Assistant-v2.7.0-windows-x64-installer/_internal/flet_browsers/unpacked/app/flet/flet/flet.exe
```

## 关键检查点

### ✅ 浏览器打包

- [ ] `playwright_browsers/` 目录已创建
- [ ] 里面有版本子目录（如 `chromium-1200/`）
- [ ] 版本子目录下有 `chrome-win/chrome.exe`
- [ ] 文件大小应该在 200-400 MB 之间
- [ ] 有 `INSTALLATION_COMPLETE` 标记文件

### ✅ Flet 打包

- [ ] `flet_browsers/unpacked/` 目录已创建
- [ ] 里面有 `app/flet/flet/flet.exe`
- [ ] 文件大小应该在 50-100 MB 之间
- [ ] 有 `FLET_CACHE_COMPLETE` 标记文件

### ✅ PyInstaller 命令

- [ ] 如果浏览器目录存在，命令中包含 `--add-data playwright_browsers;playwright_browsers`
- [ ] 如果 Flet 目录存在，命令中包含 `--add-data flet_browsers/unpacked;flet_browsers/unpacked`
- [ ] 如果目录不存在，会有警告信息但不会失败

## 常见问题

### Q1: 浏览器复制失败

**原因**: Playwright 浏览器未安装

**解决**:
```bash
python -m playwright install chromium
```

### Q2: Flet 下载失败

**原因**: 网络问题或镜像源不可用

**解决**:
- 等待自动回退到官方源
- 或者手动从 GitHub 下载后解压到 `flet_browsers/unpacked/`

### Q3: PyInstaller 失败

**原因**: 目录不存在或路径错误

**检查**:
```bash
# 检查目录是否存在
ls -la playwright_browsers/
ls -la flet_browsers/unpacked/

# 如果不存在，先运行：
python build.py --copy-all
```

### Q4: 编码问题

**原因**: Windows 控制台默认使用 GBK 编码

**解决**: 构建脚本已处理，如果仍有问题，在命令前加：
```bash
$env:PYTHONIOENCODING="utf-8"; python build.py
```

## 预期文件大小

| 项目 | 大小范围 | 说明 |
|------|---------|------|
| Playwright 浏览器 | 200-400 MB | 完整的 Chromium 浏览器 |
| Flet 可执行文件 | 50-100 MB | Flutter 桌面应用 |
| 打包后可执行文件 | 400-800 MB | 包含所有依赖 |

## 验证脚本

如果需要自动化验证，运行：
```bash
python test_build_tools.py
```

这会自动检查所有功能并生成报告。
