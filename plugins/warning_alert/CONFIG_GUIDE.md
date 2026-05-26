# 警告提示器插件 - 配置文件说明

## 📁 配置存储

警告提示器设置通过应用的统一设置管理器保存，不在插件源码目录中写入运行配置。`warning_config.example.json` 仅作为可导入的安全示例。

## 🔧 配置项说明

### 基本设置
| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `title` | string | "⚠️ 重要警告" | 警告窗口标题 |
| `content` | string | "这是一条重要的警告信息..." | 警告内容文本（支持`\n`换行） |
| `warning_level` | string | "warning" | 警告级别：info/warning/error/success/critical |
| `button_text` | string | "✓ 我知道了" | 关闭按钮文本 |

### 窗口设置
| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `window_size` | string | "large" | 窗口大小预设：small/medium/large/xlarge |
| `window_width` | int | 700 | 窗口宽度（像素） |
| `window_height` | int | 450 | 窗口高度（像素） |
| `window_opacity` | float | 1.0 | 窗口透明度（0.3-1.0） |
| `always_on_top` | boolean | true | 是否总是置顶 |

### 外观样式
| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `bgcolor` | string | "red" | 背景颜色：red/orange/yellow/blue/green/purple/grey |
| `title_color` | string | "red_800" | 标题颜色：red_800/orange_800/blue_800等 |
| `show_icon` | boolean | true | 是否显示图标 |
| `icon_size` | int | 48 | 图标大小（32-64） |
| `enable_animation` | boolean | true | 是否启用淡入动画 |

### 字体设置
| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `font_family` | string | "Microsoft YaHei" | 字体名称 |
| `title_size` | int | 32 | 标题字体大小（20-48） |
| `content_size` | int | 16 | 内容字体大小（12-24） |

### 高级功能
| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `auto_close` | boolean | false | 是否自动关闭 |
| `auto_close_seconds` | int | 10 | 自动关闭时间（秒） |
| `enable_escape` | boolean | true | 是否支持ESC键关闭 |

## 📝 配置示例

### 示例1：信息提示窗口
```json
{
  "title": "ℹ️ 系统提示",
  "content": "您的操作已成功完成！",
  "warning_level": "info",
  "bgcolor": "blue",
  "title_color": "blue_800",
  "window_size": "medium",
  "auto_close": true,
  "auto_close_seconds": 5
}
```

### 示例2：错误警告窗口
```json
{
  "title": "❌ 操作失败",
  "content": "发生严重错误，请联系管理员！\n\n错误代码：ERR-500",
  "warning_level": "error",
  "bgcolor": "red",
  "title_color": "red_800",
  "window_size": "large",
  "always_on_top": true,
  "enable_animation": true
}
```

### 示例3：成功提示窗口
```json
{
  "title": "✅ 完成成功",
  "content": "所有任务已完成！",
  "warning_level": "success",
  "bgcolor": "green",
  "title_color": "green_800",
  "window_size": "small",
  "auto_close": true,
  "auto_close_seconds": 3
}
```

## 🔄 配置管理

### 自动保存
- 在插件设置界面修改配置后，点击"保存设置"按钮
- 配置会自动保存到应用的用户配置目录
- 下次打开插件时自动加载

### 导入导出
使用插件界面中的导入/导出功能处理 JSON 配置；可从 `warning_config.example.json` 开始修改。

### 重置配置
点击插件设置中的重置操作，插件会恢复默认配置。

## 🎨 颜色方案

### 背景颜色
- `red` - 红色 (#FFEBEE)
- `orange` - 橙色 (#FFF3E0)
- `yellow` - 黄色 (#FFFDE7)
- `blue` - 蓝色 (#E3F2FD)
- `green` - 绿色 (#E8F5E9)
- `purple` - 紫色 (#F3E5F5)
- `grey` - 灰色 (#F5F5F5)

### 标题颜色
- `red_800` - 深红 (#C62828)
- `orange_800` - 深橙 (#E65100)
- `blue_800` - 深蓝 (#1565C0)
- `green_800` - 深绿 (#2E7D32)
- `purple_800` - 深紫 (#6A1B9A)
- `grey_800` - 深灰 (#424242)

## 🚨 警告级别图标

- `info` - ℹ️ 信息
- `warning` - ⚠️ 警告
- `error` - ❌ 错误
- `success` - ✅ 成功
- `critical` - 🚨 严重

## 💡 使用技巧

1. **快速通知**：使用 `small` 窗口大小 + `auto_close` 自动关闭
2. **重要警告**：使用 `large` 窗口大小 + `always_on_top` 置顶
3. **不遮挡提示**：设置 `window_opacity` 为 0.7-0.9
4. **醒目提示**：使用红色/橙色主题 + 大图标
