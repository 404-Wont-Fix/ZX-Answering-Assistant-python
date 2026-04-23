# Playwright 浏览器安装指南

## 问题说明

在某些情况下，特别是打包后的可执行文件，Playwright 浏览器可能无法自动下载安装。本指南提供多种备选方案来解决此问题。

## 自动安装（推荐）

### 方案1：命令行自动安装

打开命令行（终端），执行以下命令：

```bash
# Windows
python -m playwright install chromium

# Linux/Mac
python3 -m playwright install chromium
```

### 方案2：程序启动时自动安装

程序会在启动时自动检测并安装 Playwright 浏览器。如果自动安装失败，请参考以下手动方案。

## 手动安装方案

### 方案3：使用系统已安装的 Chromium 浏览器

如果您已经安装了 Chromium 或 Chrome 浏览器，可以让程序使用它：

#### Windows 系统

```json
// 编辑 cli_config.json，添加本地浏览器路径
{
  "browser_settings": {
    "headless": false,
    "local_browser_path": "C:\\Program Files\\Chromium\\chrome.exe"
  }
}
```

常见的 Windows Chrome/Chromium 路径：
- `C:\Program Files\Google\Chrome\Application\chrome.exe`
- `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`
- `C:\Users\YourName\AppData\Local\Chromium\Application\chrome.exe`
- `C:\Program Files\Chromium\chrome.exe`

#### Linux 系统

```json
{
  "browser_settings": {
    "headless": false,
    "local_browser_path": "/usr/bin/chromium"
  }
}
```

常见的 Linux Chrome/Chromium 路径：
- `/usr/bin/chromium`
- `/usr/bin/chromium-browser`
- `/usr/bin/google-chrome`
- `/usr/bin/google-chrome-stable`

#### macOS 系统

```json
{
  "browser_settings": {
    "headless": false,
    "local_browser_path": "/Applications/Chromium.app/Contents/MacOS/Chromium"
  }
}
```

常见的 macOS Chrome/Chromium 路径：
- `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
- `/Applications/Chromium.app/Contents/MacOS/Chromium`
- `/Users/YourName/Applications/Chromium.app/Contents/MacOS/Chromium`

### 方案4：手动下载 Playwright 浏览器

#### 步骤1：确定需要下载的浏览器版本

查看您的 Playwright 版本：

```bash
python -m playwright --version
```

#### 步骤2：手动下载浏览器

访问 Playwright 官方文档获取下载链接：

https://playwright.dev/docs/browsers

或使用以下命令查看需要下载的版本：

```bash
python -m playwright install --dry-run chromium
```

#### 步骤3：下载并放置到正确位置

**Windows 系统：**
```bash
# 创建目录
mkdir "%USERPROFILE%\AppData\Local\ms-playwright\chromium-1234"

# 下载浏览器并解压到上述目录
# （具体版本号根据 Playwright 版本而定）
```

**Linux 系统：**
```bash
# 创建目录
mkdir -p ~/.cache/ms-playwright/chromium-1234

# 下载浏览器并解压到上述目录
```

**macOS 系统：**
```bash
# 创建目录
mkdir -p ~/Library/Caches/ms-playwright/chromium-1234

# 下载浏览器并解压到上述目录
```

### 方案5：使用便携版 Chromium

1. 下载便携版 Chromium 浏览器
2. 解压到任意目录（如 `C:\Chromium\`）
3. 在 `cli_config.json` 中配置路径：

```json
{
  "browser_settings": {
    "local_browser_path": "C:\\Chromium\\chrome.exe"
  }
}
```

## 打包版本的浏览器处理

### 打包前准备

如果您需要打包应用程序，建议在打包前预先下载好浏览器：

```bash
# 开发环境中安装浏览器
python -m playwright install chromium

# 打包应用程序
python build.py
```

### 打包后手动安装

如果打包后的程序无法自动安装浏览器：

1. **在目标机器上安装 Python**
2. **手动安装 Playwright 浏览器：**
   ```bash
   python -m playwright install chromium
   ```
3. **配置本地浏览器路径**（如方案3所述）

### 离线安装

对于完全离线的环境：

1. **在有网络的机器上下载浏览器：**
   ```bash
   python -m playwright install chromium --with-deps
   ```

2. **复制浏览器文件夹：**
   - Windows: `%USERPROFILE%\AppData\Local\ms-playwright\`
   - Linux/Mac: `~/.cache/ms-playwright/`

3. **在离线机器上放置到相同位置**

## 验证安装

运行以下命令验证浏览器是否正确安装：

```bash
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); print(p.chromium.executable_path)"
```

应该显示浏览器可执行文件的完整路径。

## 常见问题

### Q1: 提示 "Executable doesn't exist"

**解决方案：**
- 确保浏览器已正确安装
- 检查 `local_browser_path` 配置是否正确
- 尝试重新安装：`python -m playwright install chromium --force`

### Q2: 网络问题导致下载失败

**解决方案：**
- 使用镜像源：`set PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/`
- 手动下载（方案4）
- 使用便携版浏览器（方案5）

### Q3: 权限问题

**解决方案：**
- 以管理员权限运行安装命令
- 检查目标目录的写权限
- 选择用户目录作为安装路径

### Q4: 版本不兼容

**解决方案：**
- 更新 Playwright：`pip install --upgrade playwright`
- 重新安装浏览器：`python -m playwright install chromium --force`

## 配置示例

完整的 `cli_config.json` 配置示例：

```json
{
  "credentials": {
    "student": {
      "username": "",
      "password": ""
    },
    "teacher": {
      "username": "",
      "password": ""
    }
  },
  "api_settings": {
    "max_retries": 3,
    "rate_level": "high"
  },
  "browser_settings": {
    "headless": false,
    "local_browser_path": "C:\\Program Files\\Chromium\\chrome.exe"
  }
}
```

## 获取帮助

如果以上方案都无法解决问题：

1. 检查系统日志查看详细错误信息
2. 确认网络连接正常
3. 尝试在不同的网络环境下安装
4. 查看项目 GitHub Issues 寻求帮助

## 相关链接

- [Playwright 官方文档](https://playwright.dev/python/)
- [Playwright 浏览器下载](https://playwright.dev/docs/browsers)
- [项目文档](../README.md)
