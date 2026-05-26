# 插件目录

本目录包含所有已安装的插件。

## 内置插件

| 插件 | 说明 |
|------|------|
| `cloud_exam` | 云考试助手 - 云考试答题、题库匹配 |
| `course_certification` | 课程认证助手 - 教师课程认证答题 |
| `evaluation` | 评估出题助手 - 评估出题功能 |
| `warning_alert` | 警告提示器 - 自定义提醒窗口 |
| `weban_plugin` | 安全微伴 - 微伴相关功能 |

## 安装新插件

1. 将插件文件夹复制到此目录
2. 如果插件包含 `requirements.txt`，在当前虚拟环境中执行 `python -m pip install -r plugins/<插件目录>/requirements.txt`
3. 重启应用，新插件将自动被发现

## 插件依赖管理

### 显式依赖安装

插件通过 `requirements.txt` 声明额外依赖：

1. 在插件目录中创建 `requirements.txt` 文件
2. 填写插件依赖（标准 pip 格式）
3. 安装或更新插件时由用户/安装脚本显式安装依赖

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
- 安装插件 → 安装其 `requirements.txt` → 启动应用 → 扫描并加载插件
- 扫描插件时会提示未安装的依赖，但不会联网或修改当前 Python 环境

**详细指南**: 请参阅 [PLUGIN_DEV_GUIDE.md](PLUGIN_DEV_GUIDE.md) 了解更多关于插件依赖管理的信息。

## 插件开发

详细的插件开发指南请参阅 [PLUGIN_DEVELOPMENT.md](../PLUGIN_DEVELOPMENT.md)。

## 目录结构

```
plugins/
└── my_plugin/
    ├── manifest.json     # 插件元数据（必需）
    ├── requirements.txt  # Python 依赖声明（可选）
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
