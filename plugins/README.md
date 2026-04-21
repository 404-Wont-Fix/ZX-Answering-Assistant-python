# 插件目录

本目录包含所有已安装的插件。

## 内置插件

| 插件 | 说明 |
|------|------|
| `cloud_exam` | 云考试助手 - 云考试答题、题库匹配 |
| `course_certification` | 课程认证助手 - 教师课程认证答题 |
| `evaluation` | 评估出题助手 - 评估出题功能 |

## 安装新插件

1. 将插件文件夹复制到此目录
2. 重启应用，新插件将自动被发现

## 插件开发

详细的插件开发指南请参阅 [PLUGIN_DEVELOPMENT.md](../PLUGIN_DEVELOPMENT.md)。

## 目录结构

```
plugins/
└── my_plugin/
    ├── manifest.json     # 插件元数据（必需）
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
