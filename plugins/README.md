# 插件系统说明文档

## 插件目录结构规范

所有插件必须放置在 `plugins/` 目录下，每个插件一个子目录：

```
plugins/
└── course_certification/
    ├── manifest.json     # 插件元数据（必须）
    ├── __init__.py       # Python 包标识
    ├── ui.py             # 插件 UI 视图代码
    └── core.py           # 插件业务逻辑代码
```

## manifest.json 格式标准

每个插件必须包含 `manifest.json` 文件，格式如下：

```json
{
  "id": "course_certification",           // 插件唯一标识符（必须）
  "name": "课程认证助手",                   // 插件显示名称（必须）
  "version": "1.0.0",                     // 插件版本号（必须）
  "description": "自动化处理教师课程认证答题任务", // 插件描述（可选）
  "icon": "school",                       // 插件图标名称（可选）
  "author": "TianJiaJi",                  // 插件作者（可选）
  "entry_ui": "ui.create_view",           // UI 入口点（必须）
  "entry_core": "core.Workflow",          // 核心功能入口点（可选）
  "min_app_version": "2.9.0",             // 最低应用版本（可选）
  "dependencies": [],                     // 依赖的其他插件（可选）
  "enabled": true                         // 默认启用状态（可选）
}
```

## 字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | 插件唯一标识符，只能包含小写字母、数字和下划线 |
| `name` | string | ✅ | 插件显示名称 |
| `version` | string | ✅ | 语义化版本号，如 "1.0.0" |
| `description` | string | ❌ | 插件功能描述 |
| `icon` | string | ❌ | Material Design 图标名称 |
| `author` | string | ❌ | 插件作者 |
| `entry_ui` | string | ✅ | UI 入口点，格式：`模块名.函数名` |
| `entry_core` | string | ❌ | 核心功能入口点，格式：`模块名.类名` |
| `min_app_version` | string | ❌ | 最低兼容的应用版本 |
| `dependencies` | array | ❌ | 依赖的其他插件 ID 列表 |
| `enabled` | boolean | ❌ | 默认是否启用，默认 true |

## 依赖注入规范

### ✅ 正确做法

插件必须通过构造函数接收 `PluginContext`，从中获取所需的资源：

```python
class Workflow:
    def __init__(self, context):
        # ✅ 正确：使用注入的实例
        self.api_client = context.api_client
        self.browser_manager = context.browser_manager
```

### ❌ 错误做法

严禁在插件内部直接实例化全局单例：

```python
# ❌ 错误：严禁这样做！
from src.core.api_client import get_api_client
self.api_client = get_api_client()

# ❌ 错误：严禁这样做！
from src.core.browser import get_browser_manager
self.browser_manager = get_browser_manager()
```

## PluginContext 接口

`PluginContext` 提供以下属性和方法：

### 属性
- `api_client`: APIClient 实例（单例）
- `browser_manager`: BrowserManager 实例（单例）
- `settings_manager`: SettingsManager 实例（单）
- `plugin_id`: 当前插件 ID

### 方法
- `run_task(func, callback)`: 在后台线程安全地执行耗时操作
- `get_plugin_config(key)`: 获取插件特定配置
- `set_plugin_config(key, value)`: 设置插件特定配置

## UI 入口点规范

UI 入口函数必须接收以下参数：

```python
def create_view(page: ft.Page, context: PluginContext) -> ft.Control:
    """
    创建插件 UI

    Args:
        page: Flet 页面对象
        context: PluginContext 实例

    Returns:
        ft.Control: 插件的根控件
    """
    pass
```

## 核心功能入口点规范

核心功能类必须实现以下构造函数：

```python
class Workflow:
    def __init__(self, context: PluginContext):
        """
        初始化工作流

        Args:
            context: PluginContext 实例
        """
        pass
```

## 插件状态持久化

插件的配置和状态应该存储在 `cli_config.json` 中：

```json
{
  "plugins": {
    "disabled_plugins": ["plugin_id"],
    "plugin_specific_configs": {
      "course_certification": {
        "custom_setting": true
      }
    }
  }
}
```

## 插件开发示例

参考 `plugins/course_certification/` 目录下的示例插件了解完整的插件结构。
