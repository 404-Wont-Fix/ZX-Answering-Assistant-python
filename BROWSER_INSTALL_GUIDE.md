# Playwright 浏览器安装问题解决方案

## 🚨 常见问题

如果您在使用过程中遇到以下错误：
- "Executable doesn't exist"
- "Browser not found"
- "chromium not installed"

这是因为 Playwright 浏览器没有正确安装。

## ✅ 自动解决方案

### 方案1：程序自动安装（推荐）

程序会在启动时自动检测并安装浏览器，请耐心等待安装完成。

### 方案2：手动命令安装

打开命令行（Terminal/CMD），执行：

```bash
python -m playwright install chromium
```

**Windows 用户**：如果提示权限问题，请以管理员身份运行命令行

**Mac/Linux 用户**：可能需要使用 `sudo`（取决于 Python 安装位置）

## 🔧 使用本地浏览器

如果您已经安装了 Chrome 或 Chromium 浏览器，可以直接使用：

### 步骤1：找到浏览器路径

**Windows:**
- Chrome: `C:\Program Files\Google\Chrome\Application\chrome.exe`
- Chromium: `C:\Program Files\Chromium\chrome.exe`

**Mac:**
- Chrome: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`
- Chromium: `/Applications/Chromium.app/Contents/MacOS/Chromium`

**Linux:**
- Chrome: `/usr/bin/google-chrome`
- Chromium: `/usr/bin/chromium`

### 步骤2：配置程序

编辑项目目录下的 `cli_config.json` 文件，添加：

```json
{
  "browser_settings": {
    "local_browser_path": "您的浏览器路径"
  }
}
```

**示例 (Windows):**
```json
{
  "browser_settings": {
    "local_browser_path": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
  }
}
```

**示例 (Mac):**
```json
{
  "browser_settings": {
    "local_browser_path": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  }
}
```

## 🌐 网络问题解决

如果下载速度慢或无法下载：

### 使用国内镜像

```bash
# Windows PowerShell
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright/"; python -m playwright install chromium

# Linux/Mac
PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/ python3 -m playwright install chromium
```

### 离线安装

1. 在有网络的机器上下载浏览器
2. 复制到目标机器的相应目录
3. 详见：`docs/BROWSER_SETUP.md`

## 📦 打包版本特别说明

如果您使用的是打包后的 `.exe` 文件：

1. **首次运行时**：程序会自动下载浏览器（需要网络连接）
2. **如果自动下载失败**：
   - 手动安装：`python -m playwright install chromium`
   - 或使用本地浏览器（见上文）

## 🛠️ 故障排除

### 验证浏览器是否安装

运行以下命令检查：

```bash
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); print(p.chromium.executable_path)"
```

应该显示浏览器文件的完整路径。

### 重新安装

如果安装有问题，尝试强制重新安装：

```bash
python -m playwright install chromium --force
```

### 更新 Playwright

```bash
pip install --upgrade playwright
python -m playwright install chromium
```

## 📞 获取帮助

如果以上方案都无法解决问题：

1. 查看详细文档：`docs/BROWSER_SETUP.md`
2. 检查系统日志获取详细错误信息
3. 在 GitHub Issues 中寻求帮助

## 💡 快速解决方案汇总

| 问题类型 | 解决方案 |
|---------|---------|
| 首次运行 | 等待自动安装完成 |
| 自动安装失败 | 手动运行：`python -m playwright install chromium` |
| 网络问题 | 使用镜像源或本地浏览器 |
| 打包版本 | 手动安装或配置本地浏览器路径 |
| 权限问题 | 以管理员身份运行命令行 |

## 📋 配置文件示例

完整的 `cli_config.json` 示例：

```json
{
  "credentials": {
    "student": {
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
    "local_browser_path": ""
  }
}
```

**注意事项**：
- `local_browser_path` 留空则使用 Playwright 自带的浏览器
- 路径分隔符使用 `\\`（Windows）或 `/`（Mac/Linux）
- 配置后需要重启程序生效
