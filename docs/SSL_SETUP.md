# SSL 证书配置说明

## 问题描述

在某些 Windows 环境（特别是新部署的环境）中，程序可能会遇到 SSL 证书验证失败的问题：

```
❌ 启动 Flet 失败: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED]
certificate verify failed: unable to get local issuer certificate (_ssl.c:1000)>
```

这个问题通常发生在：
1. Flet 首次运行时从 GitHub 下载可执行文件
2. Playwright 下载浏览器或驱动程序
3. 任何使用 HTTPS 的网络请求

## 解决方案

从版本 3.2.0 开始，程序内置了自动 SSL 证书配置功能。程序会在启动时自动配置 SSL 证书，无需手动干预。

### 自动配置过程

程序启动时会：

1. **检查并安装 certifi**
   - certifi 是 Python 的根证书包
   - 如果未安装，程序会自动安装

2. **配置全局 SSL 设置**
   - 设置 `SSL_CERT_FILE` 环境变量
   - 配置 Python 的 SSL 上下文
   - 配置 urllib 和 requests 的 SSL 设置

3. **验证配置**
   - 确保 SSL 证书正确配置

### 技术细节

自动配置位于：`src/core/ssl_helper.py`

主要功能：
- `setup_ssl_auto_config()` - 一步式自动配置
- `configure_ssl_certificate()` - 配置全局 SSL 证书
- `configure_urllib_ssl()` - 配置 urllib SSL（Flet 下载）
- `configure_requests_ssl()` - 配置 requests SSL
- `install_certifi_if_missing()` - 自动安装 certifi

### 手动配置（如果自动配置失败）

如果自动配置失败，您可以手动配置：

#### 方法 1: 更新 certifi

```bash
pip install --upgrade certifi
```

#### 方法 2: 设置环境变量（临时）

在 PowerShell 中：

```powershell
$env:SSL_CERT_FILE = python -c "import certifi; print(certifi.where())"
python main.py
```

在 CMD 中：

```cmd
for /f %i in ('python -c "import certifi; print(certifi.where())"') do set SSL_CERT_FILE=%i
python main.py
```

#### 方法 3: 设置环境变量（永久）

添加到系统环境变量：
1. 右键"此电脑" → 属性 → 高级系统设置 → 环境变量
2. 添加用户变量：
   - 变量名：`SSL_CERT_FILE`
   - 变量值：`python -c "import certifi; print(certifi.where())"` 的输出

例如：
```
C:\Users\YourName\AppData\Local\Programs\Python\Python312\Lib\site-packages\certifi\cacert.pem
```

#### 方法 4: 在代码中配置（开发环境）

在您的脚本开头添加：

```python
import ssl
import certifi

# 配置 SSL
ssl._create_default_https_context = ssl.create_default_context
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())

import urllib.request
urllib.request.ssl_context = ssl.create_default_context(cafile=certifi.where())
```

## 常见问题

### Q: 为什么会出现 SSL 证书问题？

A: Windows 默认不包含完整的根证书列表。Python 的 SSL 模块需要访问这些证书来验证 HTTPS 连接。certifi 包提供了 Mozilla 维护的根证书列表。

### Q: 这个配置会影响安全性吗？

A: 不会。我们使用的是 certifi 提供的官方根证书，这是业界标准做法。实际上，使用正确的根证书比忽略证书验证（`verify=False`）更安全。

### Q: 自动配置会影响性能吗？

A: 不会。SSL 配置只在程序启动时执行一次，对性能影响可以忽略不计。

### Q: 我需要为公司代理环境做什么特殊配置吗？

A: 如果您的公司使用代理服务器并有自己的 SSL 证书，您可能需要：

1. 获取公司的 CA 证书文件
2. 将其附加到 certifi 的证书包中，或
3. 设置环境变量指向公司的证书文件

### Q: 打包后的 exe 文件会出现这个问题吗？

A: 不会。打包后的程序已经包含了 SSL 配置代码，会在启动时自动配置。

## 验证 SSL 配置

您可以运行以下命令验证 SSL 配置是否正确：

```python
# 验证脚本
import ssl
import urllib.request
import certifi

try:
    cert_path = certifi.where()
    print(f"证书文件: {cert_path}")

    # 测试 HTTPS 连接
    response = urllib.request.urlopen(
        "https://www.google.com/",
        timeout=5,
        context=ssl.create_default_context(cafile=cert_path)
    )
    print(f"✓ SSL 配置正确（状态码: {response.status}）")
except Exception as e:
    print(f"✗ SSL 配置失败: {e}")
```

## 相关文件

- SSL 配置模块: `src/core/ssl_helper.py`
- 主入口: `main.py` (调用 SSL 配置)
- 依赖包: `requirements.txt` (包含 certifi)

## 更新日志

- **v3.2.0** - 添加自动 SSL 证书配置功能
- 初始版本
