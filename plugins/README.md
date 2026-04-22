# 插件目录

本目录包含所有已安装的插件。

## 内置插件

| 插件 | 说明 |
|------|------|
| `cloud_exam` | 云考试助手 - 云考试答题、题库匹配 |
| `course_certification` | 课程认证助手 - 教师课程认证答题 |
| `evaluation` | 评估出题助手 - 评估出题功能 |
| `weban_plugin` | 安全微伴 - 微伴相关功能 |

## 安装新插件

1. 将插件文件夹复制到此目录
2. 重启应用，新插件将自动被发现
3. **依赖自动安装**: 如果插件包含 `requirements.txt`，程序会自动安装依赖

## 插件依赖管理

### 自动依赖安装 (推荐)

从当前版本开始，插件支持**自动依赖安装**功能：

1. 在插件目录中创建 `requirements.txt` 文件
2. 填写插件依赖（标准 pip 格式）
3. 程序启动时会自动检查并安装依赖

**示例 `requirements.txt`:**
```txt
# 网络请求
requests>=2.31.0

# HTML 解析
beautifulsoup4>=4.12.0

# 数据处理
pandas>=2.0.0
```

**工作流程:**
- 启动应用 → 扫描插件 → 检查 `requirements.txt` → 自动安装缺失依赖 → 加载插件
- 已安装的依赖会自动跳过，不影响启动速度
- 支持启用插件时自动安装依赖

**详细指南**: 请参阅 [PLUGIN_DEV_GUIDE.md](PLUGIN_DEV_GUIDE.md) 了解更多关于插件依赖管理的信息。

## 插件开发

详细的插件开发指南请参阅 [PLUGIN_DEVELOPMENT.md](../PLUGIN_DEVELOPMENT.md)。

## 目录结构

```
plugins/
└── my_plugin/
    ├── manifest.json     # 插件元数据（必需）
    ├── requirements.txt  # 依赖配置（可选，支持自动安装）
    ├── __init__.py       # Python 包标识（必需）
    ├── ui.py             # UI 入口（必需）
    └── core.py           # 业务逻辑（可选）
```

## manifest.json 示例

```json
{
  "id": "my_plugin",
  "name": "我的插件",
  "version": "1.0.0",
  "description": "插件描述",
  "icon": "extension",
  "author": "作者",
  "entry_ui": "ui.create_view",
  "entry_core": "core.Workflow",
  "enabled": true
}
```
