# 插件开发指南

本文档详细说明如何为 ZX Answering Assistant 开发自定义插件。

---

## 目录

- [插件系统概述](#插件系统概述)
- [快速开始](#快速开始)
- [插件目录结构](#插件目录结构)
- [manifest.json 规范](#manifestjson-规范)
- [插件生命周期](#插件生命周期)
- [依赖注入](#依赖注入)
- [UI 开发指南](#ui-开发指南)
- [核心业务开发](#核心业务开发)
- [最佳实践](#最佳实践)
- [调试技巧](#调试技巧)
- [示例插件](#示例插件)

---

## 插件系统概述

### 架构设计

插件系统采用**依赖注入**模式，核心服务通过 `PluginContext` 注入到插件中：

```
┌─────────────────────────────────────────────────────────────┐
│                      PluginManager                           │
│  • 扫描 plugins/ 目录                                        │
│  • 加载 manifest.json                                        │
│  • 创建 PluginContext                                        │
│  • 调用插件入口点                                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      PluginContext                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ api_client  │ │browser_mgr  │ │settings_mgr │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│  ┌─────────────┐ ┌─────────────┐                            │
│  │ plugin_id   │ │ run_task()  │                            │
│  └─────────────┘ └─────────────┘                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      插件实例                                │
│  ui.py: create_view(page, context)                          │
│  core.py: Workflow(context)                                 │
└─────────────────────────────────────────────────────────────┘
```

### 核心概念

| 概念 | 说明 |
|------|------|
| **PluginManager** | 插件管理器，负责扫描、加载、管理插件生命周期 |
| **PluginContext** | 插件上下文，提供依赖注入和服务访问 |
| **manifest.json** | 插件元数据文件，定义插件的基本信息 |
| **entry_ui** | UI 入口点，创建插件的用户界面 |
| **entry_core** | 核心功能入口点，实现插件的业务逻辑 |

---

## 快速开始

### 1. 创建插件目录

在 `plugins/` 目录下创建新的插件文件夹：

```bash
plugins/
└── my_plugin/
    ├── manifest.json     # 必需：插件元数据
    ├── __init__.py       # 必需：Python 包标识
    ├── ui.py             # 必需：UI 入口
    └── core.py           # 可选：业务逻辑
```

### 2. 编写 manifest.json

```json
{
  "id": "my_plugin",
  "name": "我的插件",
  "version": "1.0.0",
  "description": "这是一个示例插件",
  "icon": "extension",
  "author": "开发者",
  "entry_ui": "ui.create_view",
  "entry_core": "core.Workflow",
  "min_app_version": "3.0.0",
  "dependencies": [],
  "enabled": true
}
```

### 3. 实现 UI 入口

```python
# plugins/my_plugin/ui.py

import flet as ft
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def create_view(page: ft.Page, context):
    """
    创建插件 UI 视图

    Args:
        page: Flet 页面对象
        context: PluginContext 实例

    Returns:
        ft.Control: 插件的根控件
    """
    return ft.Column([
        ft.Text("我的插件", size=24, weight=ft.FontWeight.BOLD),
        ft.Text("欢迎使用我的插件！"),
        ft.ElevatedButton(
            "点击我",
            on_click=lambda e: print("按钮被点击了！")
        ),
    ])
```

### 4. 实现业务逻辑（可选）

```python
# plugins/my_plugin/core.py

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class Workflow:
    """插件工作流"""

    def __init__(self, context):
        """
        初始化工作流

        Args:
            context: PluginContext 实例
        """
        self.context = context
        self.api_client = context.api_client
        self.browser_manager = context.browser_manager

    def execute(self):
        """执行工作流"""
        print("[MyPlugin] 执行工作流...")
        return {"success": True, "message": "执行完成"}
```

### 5. 重启应用

重启应用后，新插件将自动被发现并显示在插件中心。

---

## 插件目录结构

### 标准结构

```
plugins/
└── my_plugin/                 # 插件目录（使用插件 ID 命名）
    ├── manifest.json          # 必需：插件元数据
    ├── __init__.py            # 必需：Python 包标识（可以为空）
    ├── ui.py                  # 必需：UI 入口
    ├── core.py                # 可选：业务逻辑
    ├── utils.py               # 可选：工具函数
    ├── models.py              # 可选：数据模型
    └── assets/                # 可选：资源文件
        ├── icons/
        └── data/
```

### 文件说明

| 文件 | 必需 | 说明 |
|------|------|------|
| `manifest.json` | ✅ | 插件元数据，定义插件的基本信息 |
| `__init__.py` | ✅ | Python 包标识，可以为空文件 |
| `ui.py` | ✅ | UI 入口，必须实现 `create_view(page, context)` 函数 |
| `core.py` | ❌ | 业务逻辑，实现 `Workflow` 类 |
| `utils.py` | ❌ | 工具函数和辅助方法 |
| `models.py` | ❌ | 数据模型和类型定义 |
| `assets/` | ❌ | 资源文件（图标、数据等） |

---

## manifest.json 规范

### 完整示例

```json
{
  "id": "course_certification",
  "name": "课程认证助手",
  "version": "1.0.0",
  "description": "自动化处理教师课程认证答题任务",
  "icon": "school",
  "author": "TianJiaJi",
  "entry_ui": "ui.create_view",
  "entry_core": "core.Workflow",
  "min_app_version": "3.0.0",
  "dependencies": [],
  "enabled": true
}
```

### 字段说明

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | 插件唯一标识符，只能包含小写字母、数字和下划线 |
| `name` | string | ✅ | 插件显示名称，显示在 UI 中 |
| `version` | string | ✅ | 语义化版本号，如 "1.0.0" |
| `description` | string | ❌ | 插件功能描述 |
| `icon` | string | ❌ | Material Design 图标名称，默认 "extension" |
| `author` | string | ❌ | 插件作者 |
| `entry_ui` | string | ✅ | UI 入口点，格式：`模块名.函数名` |
| `entry_core` | string | ❌ | 核心功能入口点，格式：`模块名.类名` |
| `min_app_version` | string | ❌ | 最低兼容的应用版本 |
| `dependencies` | array | ❌ | 依赖的其他插件 ID 列表 |
| `enabled` | boolean | ❌ | 默认是否启用，默认 true |

### 图标名称

使用 Material Design 图标名称，常用图标：

| 图标名称 | 用途 |
|----------|------|
| `extension` | 通用插件（默认） |
| `school` | 教育相关 |
| `quiz` | 考试相关 |
| `assignment` | 作业相关 |
| `settings` | 设置相关 |
| `analytics` | 分析相关 |
| `cloud` | 云服务相关 |
| `security` | 安全相关 |

完整图标列表：[Material Design Icons](https://fonts.google.com/icons)

---

## 插件生命周期

### 状态流转

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Discovered │────▶│   Loaded    │────▶│ Initialized │
│  (已发现)   │     │  (已加载)   │     │  (已初始化) │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Unloaded   │◀────│  Disabled   │◀────│   Enabled   │
│  (已卸载)   │     │  (已禁用)   │     │  (已启用)   │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 生命周期说明

| 状态 | 说明 | 触发时机 |
|------|------|----------|
| **Discovered** | 插件被扫描发现 | 应用启动时扫描 `plugins/` 目录 |
| **Loaded** | 插件模块已导入 | 读取 `manifest.json` 并导入模块 |
| **Initialized** | 插件已初始化 | 创建 `PluginContext` 并注入依赖 |
| **Enabled** | 插件已启用 | 用户启用插件或默认启用 |
| **Disabled** | 插件已禁用 | 用户禁用插件 |
| **Unloaded** | 插件已卸载 | 应用关闭或插件被移除 |

---

## 依赖注入

### PluginContext 接口

```python
class PluginContext:
    """插件上下文"""

    @property
    def api_client(self) -> APIClient:
        """API 客户端实例（单例）"""
        pass

    @property
    def browser_manager(self) -> BrowserManager:
        """浏览器管理器实例（单例）"""
        pass

    @property
    def settings_manager(self) -> SettingsManager:
        """设置管理器实例"""
        pass

    @property
    def plugin_id(self) -> str:
        """当前插件 ID"""
        pass

    def run_task(self, func: Callable, callback: Callable = None):
        """在后台线程安全地执行耗时操作"""
        pass

    def get_plugin_config(self, key: str) -> Any:
        """获取插件特定配置"""
        pass

    def set_plugin_config(self, key: str, value: Any):
        """设置插件特定配置"""
        pass
```

### 正确使用依赖注入

```python
class Workflow:
    def __init__(self, context):
        self.context = context

        self.api_client = context.api_client
        self.browser_manager = context.browser_manager
        self.settings_manager = context.settings_manager

    def do_something(self):
        result = self.api_client.get("/api/endpoint")
        return result
```

### 错误示例

```python
class Workflow:
    def __init__(self, context):
        pass

    def do_something(self):
        from src.core.api_client import get_api_client
        api_client = get_api_client()
        return api_client.get("/api/endpoint")
```

---

## UI 开发指南

### UI 入口函数规范

```python
def create_view(page: ft.Page, context) -> ft.Control:
    """
    创建插件 UI 视图

    Args:
        page: Flet 页面对象
        context: PluginContext 实例

    Returns:
        ft.Control: 插件的根控件（通常是 ft.Column 或 ft.Container）
    """
    pass
```

### 使用现有视图

如果插件复用现有的视图组件：

```python
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.ui.views.my_view import MyView


def create_view(page, context):
    view = MyView(page, main_app=None)
    return view.get_content()
```

### 完整 UI 示例

```python
import flet as ft
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def create_view(page: ft.Page, context):
    def on_click(e):
        result_text.value = "按钮被点击了！"
        page.update()

    result_text = ft.Text("等待操作...")

    return ft.Column([
        ft.Text("我的插件", size=24, weight=ft.FontWeight.BOLD),
        ft.Divider(),
        ft.Text("这是一个示例插件，演示基本的 UI 结构。"),
        ft.ElevatedButton("点击我", on_click=on_click),
        ft.Divider(),
        ft.Text("结果："),
        result_text,
    ], scroll=ft.ScrollMode.AUTO)
```

---

## 核心业务开发

### Workflow 类规范

```python
class Workflow:
    """插件工作流"""

    def __init__(self, context):
        """
        初始化工作流

        Args:
            context: PluginContext 实例
        """
        self.context = context
        self.api_client = context.api_client
        self.browser_manager = context.browser_manager

    def execute(self, **kwargs):
        """
        执行工作流

        Args:
            **kwargs: 工作流参数

        Returns:
            dict: 执行结果
        """
        result = {
            'success': False,
            'message': '',
            'data': None
        }

        try:
            pass

            result['success'] = True
            result['message'] = '执行成功'

        except Exception as e:
            result['message'] = f'执行失败: {str(e)}'

        return result
```

### 异步任务处理

```python
def create_view(page: ft.Page, context):
    def on_task_complete(result):
        status_text.value = f"任务完成: {result}"
        page.update()

    def start_task(e):
        status_text.value = "任务执行中..."
        page.update()

        def long_running_task():
            import time
            time.sleep(3)
            return "成功"

        context.run_task(long_running_task, on_task_complete)

    status_text = ft.Text("就绪")

    return ft.Column([
        ft.ElevatedButton("开始任务", on_click=start_task),
        status_text,
    ])
```

---

## 最佳实践

### 1. 模块化设计

将功能拆分为独立模块：

```
plugins/
└── my_plugin/
    ├── ui.py           # UI 层
    ├── core.py         # 业务逻辑层
    ├── utils.py        # 工具函数
    └── models.py       # 数据模型
```

### 2. 错误处理

始终进行错误处理：

```python
def execute(self):
    result = {'success': False, 'message': ''}

    try:
        pass
        result['success'] = True
    except Exception as e:
        result['message'] = f'执行失败: {str(e)}'
        import traceback
        traceback.print_exc()

    return result
```

### 3. 日志输出

使用统一的日志格式：

```python
print(f"[MyPlugin] 开始执行任务...")
print(f"[MyPlugin] 任务执行成功")
print(f"[MyPlugin] 错误: {str(e)}")
```

### 4. 配置管理

使用 PluginContext 管理配置：

```python
config = context.get_plugin_config('my_setting')
context.set_plugin_config('my_setting', 'new_value')
```

### 5. 资源清理

在插件禁用或卸载时清理资源：

```python
class Workflow:
    def __init__(self, context):
        self._resources = []

    def cleanup(self):
        for resource in self._resources:
            resource.close()
        self._resources.clear()
```

---

## 调试技巧

### 1. 查看插件加载日志

启动应用时查看控制台输出：

```
[PluginManager] Found plugin: 云考试助手 v1.0.0
[PluginManager] Found plugin: 课程认证助手 v1.0.0
[PluginManager] Total plugins found: 2
```

### 2. 检查 manifest.json

使用 JSON 验证工具检查 `manifest.json` 格式是否正确。

### 3. 独立测试

创建独立的测试脚本测试插件功能：

```python
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.plugin_context import PluginContext

class MockContext:
    @property
    def api_client(self):
        return None

    @property
    def browser_manager(self):
        return None

context = MockContext()

from plugins.my_plugin.ui import create_view
from plugins.my_plugin.core import Workflow

workflow = Workflow(context)
result = workflow.execute()
print(result)
```

---

## 示例插件

### 完整示例：课程认证插件

**manifest.json**
```json
{
  "id": "course_certification",
  "name": "课程认证助手",
  "version": "1.0.0",
  "description": "自动化处理教师课程认证答题任务",
  "icon": "school",
  "author": "TianJiaJi",
  "entry_ui": "ui.create_view",
  "entry_core": "core.Workflow",
  "enabled": true
}
```

**ui.py**
```python
import flet as ft
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.ui.views.course_certification_view import CourseCertificationView


def create_view(page, context):
    view = CourseCertificationView(page, main_app=None)
    return view.get_content()
```

**core.py**
```python
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.certification.workflow import get_access_token, start_answering


class Workflow:
    def __init__(self, context):
        self.context = context
        self.api_client = context.api_client
        self.browser_manager = context.browser_manager

    def execute(self, question_bank_path=None):
        result = {'success': False, 'message': ''}

        try:
            token = get_access_token()
            if token:
                result['success'] = True
                result['message'] = '成功获取访问令牌'
            else:
                result['message'] = '获取访问令牌失败'

        except Exception as e:
            result['message'] = f'执行失败: {str(e)}'

        return result
```

---

## 常见问题

### 1. 插件无法被发现

**原因**: `manifest.json` 格式错误或缺少必要字段

**解决方案**: 检查 `manifest.json` 格式，确保包含 `id`、`name`、`version`、`entry_ui` 字段。

### 2. 插件加载失败

**原因**: 模块导入路径错误

**解决方案**: 确保 `ui.py` 和 `core.py` 中正确设置了项目根目录路径：

```python
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
```

### 3. 依赖注入失败

**原因**: 直接实例化全局单例而不是使用 PluginContext

**解决方案**: 始终通过 `context` 获取服务实例：

```python
self.api_client = context.api_client
```

### 4. UI 不显示

**原因**: `create_view` 函数返回了错误的类型

**解决方案**: 确保 `create_view` 返回 `ft.Control` 类型（通常是 `ft.Column` 或 `ft.Container`）。

---

## 更多资源

- [README.md](README.md) - 项目概述
- [CLAUDE.md](CLAUDE.md) - Claude Code 指导文档
- [Flet 文档](https://flet.dev/docs/) - Flet UI 框架文档
- [Material Design Icons](https://fonts.google.com/icons) - 图标参考
