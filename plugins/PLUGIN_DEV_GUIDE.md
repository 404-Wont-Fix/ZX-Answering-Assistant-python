# 插件开发指南

## 插件依赖自动安装功能

从当前版本开始，插件系统支持**自动依赖安装**功能。开发者无需再手动安装插件依赖。

### 如何使用

1. **在插件目录中创建 `requirements.txt` 文件**

```
plugins/
├── your_plugin/
│   ├── manifest.json
│   ├── requirements.txt    # 新增：依赖配置文件
│   ├── core.py
│   └── ui.py
```

2. **在 `requirements.txt` 中填写依赖**

```txt
# 支持标准 pip requirements 格式
requests>=2.31.0
beautifulsoup4>=4.12.0
pandas>=2.0.0
```

3. **程序运行时自动安装**

   - 启动应用时，扫描插件目录
   - 检查每个插件的 `requirements.txt`
   - 自动安装未安装的依赖
   - 已安装的依赖会自动跳过

### 支持的版本格式

```txt
# 精确版本
package==1.0.0

# 最低版本
package>=1.0.0

# 兼容版本
package~=1.0.0

# 无版本要求（不推荐）
package
```

### 示例

#### 示例 1: 简单依赖
```txt
# 插件只需要 requests 库
requests>=2.31.0
```

#### 示例 2: 多个依赖
```txt
# 网络请求
requests>=2.31.0

# HTML 解析
beautifulsoup4>=4.12.0
lxml>=4.9.0

# 数据处理
pandas>=2.0.0
numpy>=1.24.0
```

#### 示例 3: 无需依赖
```txt
# 如果插件不需要额外依赖，此文件可以为空
# 或删除此文件
```

### 工作流程

1. **插件扫描时**
   ```
   扫描插件 → 发现 requirements.txt → 检查依赖 → 自动安装 → 加载插件
   ```

2. **插件启用时**
   ```
   用户启用插件 → 检查依赖 → 安装缺失依赖 → 启用成功
   ```

3. **依赖检查逻辑**
   ```
   对于每个依赖包：
   - 检查是否已安装
   - 如果已安装 → 跳过
   - 如果未安装 → 自动安装
   ```

### 注意事项

1. **版本兼容性**
   - 建议指定最低版本要求（如 `>=1.0.0`）
   - 避免使用过新的版本，可能导致兼容性问题
   - 测试插件时确保依赖版本正确

2. **性能考虑**
   - 依赖安装只在插件首次加载或启用时执行
   - 已安装的依赖会自动跳过，不影响启动速度
   - 安装超时时间为 5 分钟

3. **错误处理**
   - 依赖安装失败不会阻止插件加载
   - 控制台会显示警告信息
   - 用户可以手动安装依赖来解决问题

4. **最佳实践**
   - 保持最小化依赖，只添加必需的包
   - 在文档中说明插件依赖
   - 测试插件在不同环境下的兼容性

### 调试

查看依赖安装日志：

```
[PluginManager] Installing 2 package(s) for plugin: your_plugin
  - requests>=2.31.0
  - beautifulsoup4>=4.12.0
[PluginManager] Successfully installed dependencies for plugin: your_plugin
```

### 手动安装依赖

如果自动安装失败，可以手动安装：

```bash
# 进入插件目录
cd plugins/your_plugin

# 手动安装依赖
pip install -r requirements.txt
```

### 常见问题

**Q: 依赖安装失败怎么办？**
A: 检查网络连接，或手动运行 `pip install -r requirements.txt`

**Q: 如何测试依赖是否正确安装？**
A: 运行应用时查看控制台日志，或手动导入依赖测试

**Q: 依赖会影响应用启动速度吗？**
A: 不会，依赖安装只在首次加载时执行，已安装的依赖会自动跳过

**Q: 不同插件的依赖冲突怎么办？**
A: pip 会自动处理依赖冲突，建议使用版本约束来避免问题
