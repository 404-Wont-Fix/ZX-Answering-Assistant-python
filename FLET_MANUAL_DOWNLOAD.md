# Flet 可执行文件手动下载和安装指南

## 🚨 问题说明

如果程序启动时提示 Flet 可执行文件缺失，或者自动下载失败，请按照以下步骤手动下载和安装。

## 📥 第一步：下载 Flet 可执行文件

### 方法1：从官方网站下载

访问 Flet GitHub 发布页面：
```
https://github.com/flet-dev/flet/releases
```

下载对应您操作系统的最新版本。

### 方法2：直接下载链接

**Windows 用户**：
```
https://github.com/flet-dev/flet/releases/latest/download/flet-latest-windows-x64.zip
```

**Linux 用户**：
```
https://github.com/flet-dev/flet/releases/latest/download/flet-latest-linux-x64.tar.gz
```

**macOS 用户**：
```
https://github.com/flet-dev/flet/releases/latest/download/flet-latest-macos-x64.tar.gz
```

## 📁 第二步：解压文件

### Windows 用户
1. 找到下载的 `.zip` 文件
2. 右键点击 → "解压全部" 或使用 WinRAR/7-Zip
3. 解压后会得到 `flet.exe` 文件

### Linux/Mac 用户
1. 打开终端
2. 进入下载目录：
   ```bash
   cd ~/Downloads
   ```
3. 解压文件：
   ```bash
   tar -xzf flet-latest-linux-x64.tar.gz  # Linux
   tar -xzf flet-latest-macos-x64.tar.gz  # macOS
   ```

## 📂 第三步：放置到正确位置

### Windows 用户

1. **创建目标目录**（如果不存在）：
   ```
   创建文件夹: C:\Users\YourName\.flet\bin\
   ```

   **方法**：
   - 打开文件资源管理器
   - 在地址栏输入：`%USERPROFILE%\.flet\bin`
   - 如果提示不存在，点击"新建文件夹"

2. **复制文件**：
   - 将解压后的 `flet.exe` 复制到 `C:\Users\YourName\.flet\bin\` 目录

3. **验证安装**：
   - 按 `Win + R`，输入：`cmd`
   - 运行命令：
     ```cmd
     dir C:\Users\YourName\.flet\bin\flet.exe
     ```
   - 应该显示文件信息

### Linux 用户

1. **创建目标目录**：
   ```bash
   mkdir -p ~/.flet/bin
   ```

2. **复制文件并设置权限**：
   ```bash
   cp ~/Downloads/flet ~/.flet/bin/
   chmod +x ~/.flet/bin/flet
   ```

3. **验证安装**：
   ```bash
   ls -lh ~/.flet/bin/flet
   ```
   应该显示文件信息（约 50-100 MB）

### macOS 用户

1. **创建目标目录**：
   ```bash
   mkdir -p ~/.flet/bin
   ```

2. **复制文件并设置权限**：
   ```bash
   cp ~/Downloads/flet ~/.flet/bin/
   chmod +x ~/.flet/bin/flet
   ```

3. **验证安装**：
   ```bash
   ls -lh ~/.flet/bin/flet
   ```

## ✅ 第四步：验证和运行

1. **验证文件存在**：
   - **Windows**: 打开文件资源管理器，检查 `C:\Users\YourName\.flet\bin\flet.exe` 是否存在
   - **Linux/Mac**: 运行 `ls ~/.flet/bin/flet`

2. **重启程序**：
   ```bash
   python main.py
   ```

3. **程序应该正常启动**，不再提示 Flet 可执行文件缺失。

## 🔧 常见问题

### Q1: 不知道用户名是什么？

**Windows 用户**：
- 按 `Win + R`，输入 `%USERPROFILE%`，回车
- 这会打开您的用户目录，记住路径中的用户名

**Linux/Mac 用户**：
- 运行 `whoami` 命令查看用户名
- 或者直接使用 `~/.flet/bin/` 路径（`~` 代表当前用户目录）

### Q2: 目录创建失败

**Windows**：
- 确保您有创建文件夹的权限
- 如果不行，尝试以管理员身份运行文件资源管理器

**Linux/Mac**：
- 确保 `~/.flet/` 目录可写
- 检查权限：`ls -la ~/ | grep .flet`

### Q3: 下载速度慢或无法下载

**解决方案**：
1. 使用网络加速器或代理
2. 尝试在不同的网络环境下下载
3. 从其他机器下载后通过 U 盘复制

### Q4: 文件损坏或无法运行

**解决方案**：
1. 重新下载文件
2. 验证文件大小（应该是 50-100 MB）
3. 确保下载完全完成

## 📞 仍然无法解决？

如果按照以上步骤仍然无法解决问题：

1. **检查下载的文件完整性**：
   - Windows: 右键点击文件 → 属性，查看文件大小
   - 应该是 50-100 MB 左右

2. **尝试其他下载源**：
   - Flet 官网：https://flet.dev/
   - PyPI 页面：https://pypi.org/project/flet/

3. **查看详细日志**：
   - 运行程序时查看完整的错误信息
   - 截图保存错误提示

4. **获取帮助**：
   - 查看 `docs/FLET_SETUP.md` 获取更多技术细节
   - 在项目 GitHub 提交 Issue

## 🎯 快速检查清单

完成安装后，请确认：

- [ ] 已下载对应平台的 Flet 可执行文件
- [ ] 文件大小正常（50-100 MB）
- [ ] 已放置在正确位置：
  - Windows: `C:\Users\YourName\.flet\bin\flet.exe`
  - Linux/Mac: `~/.flet/bin/flet`
- [ ] 文件权限正确（Linux/Mac 可执行）
- [ ] 重新运行程序，不再出现错误提示

## 📝 文件位置总结

| 平台 | 可执行文件名 | 目标位置 |
|------|-------------|----------|
| Windows | flet.exe | `C:\Users\YourName\.flet\bin\flet.exe` |
| Linux | flet | `~/.flet/bin/flet` |
| macOS | flet | `~/.flet/bin/flet` |

**注意**: `YourName` 需要替换为您的实际用户名。

## 💡 小提示

- **首次安装建议**：在首次运行程序前，建议先手动下载 Flet 可执行文件，避免首次启动时等待下载。
- **定期更新**：Flet 会不定期更新，建议定期检查并更新到最新版本。
- **保留原文件**：下载的压缩包可以保留，以便将来需要时重新安装。
