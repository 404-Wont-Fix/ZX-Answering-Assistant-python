# Flet 库安装指南

## 问题说明

Flet 是本项目的核心 GUI 框架，在首次运行时需要下载桌面运行时可执行文件。这可能导致以下问题：

1. **Flet 库未安装**：Python 环境中没有 flet 包
2. **Flet 可执行文件缺失**：首次运行时需要下载 `flet.exe` (Windows) 或 `flet` (Linux/Mac)
3. **网络下载失败**：运行时可执行文件下载失败或超时
4. **打包版本问题**：打包后的可执行文件无法下载 Flet 运行时

## Flet 运行时说明

**重要**: Flet 在首次运行时会自动下载桌面运行时文件（约 50-100MB）：

- **Windows**: `C:\Users\YourName\.flet\bin\flet.exe`
- **Linux/Mac**: `~/.flet/bin/flet`

这是 **正常行为**，程序会自动处理下载。如果下载失败，请参考以下解决方案。

## 自动安装（推荐）

### 方案1：程序自动处理

程序启动时会自动：
1. 检查 Flet 库是否安装
2. 检查 Flet 可执行文件是否存在
3. 自动下载缺失的组件

**注意**: 首次运行可能需要 1-3 分钟下载 Flet 运行时，请耐心等待。

### 方案2：预下载 Flet 运行时（推荐打包前执行）

在打包前或首次运行前，可以预先下载 Flet 运行时：

```bash
# 方法1: 使用 flet CLI（如果已安装）
pip install flet-cli
flet --version

# 方法2: 运行简单的 Flet 脚本触发下载
python -c "import flet; print('Flet 运行时下载中...')"

# 方法3: 运行一次程序
python main.py
```

下载完成后，Flet 运行时文件将存储在：
- **Windows**: `C:\Users\YourName\.flet\bin\flet.exe`
- **Linux/Mac**: `~/.flet/bin/flet`

## 手动安装方案

### 方案3：安装 Flet 库

如果 Flet 库未安装，使用 pip 安装：

```bash
# 安装推荐版本
pip install flet>=0.82.0

# 或安装项目要求的版本
pip install -r requirements.txt
```

### 方案4：手动下载 Flet 可执行文件

#### 如果自动下载失败，可以手动下载：

1. **找到 Flet 可执行文件存储位置**：
   - Windows: `C:\Users\YourName\.flet\bin\`
   - Linux/Mac: `~/.flet/bin/`

2. **从其他机器复制**：
   - 在有网络环境的机器上运行一次程序
   - 复制 `.flet/bin/` 目录到目标机器的相同位置

3. **设置可执行权限**（Linux/Mac）：
   ```bash
   chmod +x ~/.flet/bin/flet
   ```

### 方案5：使用国内镜像加速

如果官方源下载速度慢，可以使用国内镜像：

```bash
# 清华大学镜像
pip install flet -i https://pypi.tuna.tsinghua.edu.cn/simple

# 阿里云镜像
pip install flet -i https://mirrors.aliyun.com/pypi/simple/

# 中国科技大学镜像
pip install flet -i https://pypi.mirrors.ustc.edu.cn/simple/
```

## 离线安装

### 方案6：完全离线环境

#### 在有网络的机器上：

1. **安装 Flet 库和运行时**：
   ```bash
   pip install flet>=0.82.0
   python -c "import flet; print('触发运行时下载')"
   ```

2. **打包 Flet 相关文件**：
   - Python 库：`pip download flet -d ./flet_libs`
   - 运行时：复制 `~/.flet/` 目录

#### 在离线机器上：

1. **安装 Flet 库**：
   ```bash
   pip install --no-index --find-links=./flet_libs flet
   ```

2. **复制运行时文件**：
   - 将 `.flet/` 目录复制到用户目录
   - 确保可执行文件权限正确

## 验证安装

### 检查 Flet 库

```bash
python -c "import flet; print(f'Flet 版本: {flet.__version__}')"
```

### 检查 Flet 可执行文件

**Windows**:
```bash
dir C:\Users\YourName\.flet\bin\flet.exe
```

**Linux/Mac**:
```bash
ls -lh ~/.flet/bin/flet
```

### 运行测试

```bash
python main.py
```

如果程序正常启动，说明 Flet 已正确安装。

## 版本兼容性

### 支持的 Flet 版本

- **最低版本**: 0.80.0
- **推荐版本**: 0.82.0+
- **注意**: 0.8.0+ 版本有重大 API 变更，请确保使用兼容版本

### 版本检查

程序会自动检查 Flet 版本，如果版本过低会提示升级。

## 打包版本特别说明

### 打包前准备

如果您需要打包应用程序，建议：

1. **预下载 Flet 运行时**：
   ```bash
   python -c "import flet; print('触发运行时下载')"
   ```

2. **验证 Flet 安装**：
   ```bash
   python -c "import flet; print(f'Flet {flet.__version__} OK')"
   ```

3. **测试程序运行**：
   ```bash
   python main.py
   ```

4. **确认无误后再打包**：
   ```bash
   python build.py
   ```

### 打包后处理

如果打包后的程序提示 Flet 可执行文件缺失：

1. **在目标机器上安装 Python**
2. **手动安装 Flet**：
   ```bash
   pip install flet>=0.82.0
   ```
3. **触发运行时下载**：
   ```bash
   python -c "import flet; print('下载运行时')"
   ```
4. **重新运行程序**

## 常见问题

### Q1: 提示 "No module named 'flet'"

**解决方案**：
- Flet 库未安装，请运行：`pip install flet>=0.82.0`

### Q2: Flet 运行时下载失败

**解决方案**：
1. 检查网络连接
2. 使用国内镜像加速
3. 手动复制运行时文件
4. 在有网络环境预下载后打包

### Q3: 打包后无法下载 Flet 运行时

**解决方案**：
1. 打包前预下载运行时
2. 手动复制 `.flet/` 目录到目标机器
3. 在目标机器手动安装 Flet

### Q4: 运行时文件位置错误

**解决方案**：
1. 检查环境变量 `FLET_DESKTOP_EXECUTABLE`
2. 确保文件在正确位置：`~/.flet/bin/flet`
3. 设置正确的文件权限

## 配置文件

项目配置文件 `requirements.txt` 中包含 Flet 依赖：

```
# GUI framework
flet>=0.82.0
```

如需修改版本要求，请编辑此文件。

## 环境变量

### Flet 相关环境变量

```bash
# Flet 可执行文件路径（可选）
FLET_DESKTOP_EXECUTABLE=/path/to/flet

# Flet 缓存目录（可选）
FLET_CACHE_DIR=/path/to/cache
```

## 获取帮助

如果以上方案都无法解决问题：

1. 检查系统环境：Python 版本、pip 版本
2. 查看详细错误信息
3. 尝试在不同的网络环境下安装
4. 查看项目 GitHub Issues 寻求帮助

## 相关链接

- [Flet 官方文档](https://flet.dev/docs/)
- [Flet GitHub](https://github.com/flet-dev/flet)
- [Flet PyPI](https://pypi.org/project/flet/)
- [项目文档](../README.md)

## 快速解决方案汇总

| 问题类型 | 解决方案 |
|---------|---------|
| Flet 库缺失 | `pip install flet>=0.82.0` |
| 运行时缺失 | 程序自动下载或预下载 |
| 网络问题 | 使用镜像源或手动复制 |
| 打包版本 | 打包前预下载运行时 |
| 离线环境 | 复制 `.flet/` 目录 |

## 示例命令汇总

```bash
# 安装 Flet 库
pip install flet>=0.82.0

# 触发运行时下载
python -c "import flet; print('下载运行时')"

# 使用项目依赖
pip install -r requirements.txt

# 国内镜像安装
pip install flet -i https://pypi.tuna.tsinghua.edu.cn/simple

# 验证安装
python -c "import flet; print(f'Flet {flet.__version__} OK')"

# 测试程序
python main.py
```
