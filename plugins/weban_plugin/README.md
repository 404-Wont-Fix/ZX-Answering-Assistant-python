# 安全微伴插件 (WeBan Plugin)

## 📦 插件简介

安全微伴插件是一个完全独立的插件，集成了WeBan（安全微伴）的全部功能。插件内部包含了完整的WeBan代码库，无需外部依赖。

## 🏗️ 插件结构

```
plugins/weban_plugin/
├── __init__.py              # 插件包初始化和自动设置逻辑
├── manifest.json            # 插件元数据
├── README.md                # 本文件
├── ui.py                    # UI入口模块
├── core.py                  # 核心功能模块
├── weban_adapter.py         # WeBan适配器（自动查找和导入）
├── weban_view.py            # WeBan视图组件
└── modules/                 # 插件模块目录
    └── WeBan/               # WeBan代码库（自动创建）
        ├── __init__.py      # WeBan包初始化
        ├── api.py           # WeBan API客户端
        ├── client.py        # WeBan客户端实现
        ├── main.py          # WeBan主程序
        ├── answer/          # 题库目录
        │   └── answer.json  # 题库数据
        ├── images/          # 图片资源
        ├── config.example.json  # 配置示例
        ├── requirements.txt # 依赖列表
        └── README.md        # WeBan原始文档
```

**重要说明**：
- `weban_adapter.py`、`weban_view.py` 等核心文件在插件根目录（会被 Git 跟踪）
- `modules/WeBan/` 目录在插件导入时自动创建（从项目根目录复制或链接）
- 推荐将 WeBan 项目作为 Git Submodule 添加到 `modules/WeBan/`
- 即使从云端拉取没有 `modules/WeBan/` 目录，插件也会自动处理

## ✨ 特性

### 自动依赖管理
- ✅ **自动检测和配置 WeBan 模块**
- ✅ 支持多个 WeBan 位置（插件目录、项目根目录、submodules）
- ✅ 首次加载时自动创建符号链接或复制文件
- ✅ 即使 WeBan 不在插件目录也能正常工作
- ✅ 无需手动配置 Git 子模块或运行初始化脚本

### 完全独立
- ✅ 插件内部包含完整的WeBan代码库（自动从项目根目录获取）
- ✅ 不依赖外部Git子模块手动操作
- ✅ 所有代码自动配置到`lib/WeBan/`目录中

### 功能完整
- ✅ 自动学习课程
- ✅ 智能答题（基于题库）
- ✅ 验证码识别（部分学校）
- ✅ 多账号支持
- ✅ 题库同步
- ✅ 进度追踪

### 用户友好
- ✅ 集成到插件中心
- ✅ GUI界面操作
- ✅ 实时日志显示
- ✅ 错误处理和重试

## 📋 依赖项

插件需要以下Python包：

```
ddddocr==1.6.1      # 验证码识别
loguru==0.7.3       # 日志处理
pycryptodome==3.23.0  # 加密解密
Pillow>=10.0.0      # 图像处理（验证码）
requests>=2.32.5    # HTTP请求
```

**自动安装**：

主程序会在加载插件时自动检查并安装这些依赖，无需手动操作。

**手动安装（可选）**：

如果自动安装失败，可以手动安装：

```bash
pip install ddddocr==1.6.1 loguru==0.7.3 pycryptodome==3.23.0 Pillow>=10.0.0 requests>=2.32.5
```

或使用插件的 requirements.txt：

```bash
pip install -r plugins/weban_plugin/requirements.txt
```

## 🚀 使用方法

### GUI模式（推荐）

1. 启动应用程序：
   ```bash
   python main.py --mode gui
   ```

2. 在左侧导航栏中点击 **"插件中心"**

3. 在 **"我的插件"** 标签页中找到 **"安全微伴"** 插件

4. 点击插件图标进入功能界面

5. 按照界面提示：
   - 输入学校名称（可先验证）
   - 输入账号和密码
   - 勾选"记住我"可保存凭据
   - 点击"开始执行"即可

## ⚠️ 注意事项

### 验证码识别
- 部分学校使用腾讯云验证码，无法自动识别
- 遇到验证码时会弹出窗口要求手动输入
- 系统会自动打开验证码图片供查看

### 题库匹配
- 如果题库中没有答案，会弹出窗口让您手动作答
- 题库位于 `lib/WeBan/answer/answer.json`
- 可以根据需要更新题库文件

### 学校验证
- ✅ **改进的验证体验** (v1.3.0)
  - 点击"验证学校"后显示加载进度条
  - 验证完成后显示明确的结果对话框
  - 成功：绿色对勾图标 + 成功消息
  - 失败：红色错误图标 + 错误详情
- 建议先点击"验证学校"确认学校名称正确
- 学校名称需要完整输入（如：重庆大学）
- 验证过程在后台执行，不阻塞UI界面

### 网络要求
- 需要稳定的网络连接
- 部分功能需要访问教育平台API
- 建议在网络良好的环境下使用

## 🔧 配置说明

### 题库文件
题库文件位于 `lib/WeBan/answer/answer.json`，格式如下：

```json
{
  "题目文本": {
    "optionList": [
      {
        "content": "选项内容",
        "isCorrect": 1  // 1=正确答案，0=错误选项
      }
    ]
  }
}
```

### 学习参数
可调整的参数：
- `study_time`: 每门课程学习时长（秒）
- `restudy_time`: 重新学习时长（0=不重新学习）
- `exam_use_time`: 考试总时长（秒）

## 🐛 故障排除

### 问题：插件显示"未找到 WeBan 模块"

**原因**：WeBan 代码不在项目的任何位置

**自动处理机制**：
插件会在首次加载时自动查找 WeBan 并设置。支持以下位置：
1. 项目根目录：`WeBan/`
2. 插件 modules 目录（推荐）：`plugins/weban_plugin/modules/WeBan/`
3. 插件目录（兼容）：`plugins/weban_plugin/WeBan/`
4. Submodules：`submodules/WeBan/`

插件会自动：
- 创建符号链接到 `plugins/weban_plugin/modules/WeBan/`（最快）
- 如果符号链接失败，复制文件（备用）

**推荐做法（Git Submodule）**：

如果要将 WeBan 作为 Git 子模块管理：

```bash
# 在插件目录添加子模块
cd plugins/weban_plugin
mkdir -p modules
cd modules
git submodule add <WeBan仓库URL> WeBan

# 提交更改
cd ../../..
git add plugins/weban_module/modules
git commit -m "feat: 添加 WeBan 子模块"
```

**如果仍然显示未找到**：
1. 确保项目根目录有 `WeBan/` 文件夹
2. 或者将 WeBan 作为 Git 子模块添加到 `modules/WeBan/`
3. 重启应用程序让插件重新尝试自动配置

### 问题：插件无法加载
**解决方案**：
1. 检查依赖包是否已安装：`pip install -r plugins/weban_plugin/requirements.txt`
2. 确认插件目录结构完整（至少包含 __init__.py, core.py, ui.py, weban_adapter.py）
3. 查看控制台错误信息
4. 确保项目根目录有 WeBan 项目

### 问题：验证码识别失败
**解决方案**：
1. 手动输入验证码
2. 检查ddddocr是否正确安装
3. 更新ddddocr到最新版本

### 问题：题库匹配失败
**解决方案**：
1. 更新题库文件
2. 检查题目文本格式
3. 手动作答更新题库

## 📝 更新日志

### v1.3.0 (2026-04-30)
- ✨ **学校验证体验改进**
  - 添加加载进度对话框，提供实时反馈
  - 添加明确的结果提示对话框（成功/失败）
  - 使用AlertDialog替代SnackBar，更可靠的UI反馈
  - 视觉优化：成功(绿色✓)、失败(红色✗)、加载(蓝色🔄)
- 🐛 **修复** 图标引用错误
  - 修复 `ft.Icons.LOADING` 不存在的问题
  - 使用 `ft.Icons.REFRESH` 替代
- 🔧 **技术改进**
  - 重写 `_on_validate_school()` 方法
  - 新增 `_show_validation_dialog()` 方法
  - 后台线程处理验证，主线程更新UI
  - 确保Flet框架兼容性

### v1.2.1 (2026-04-23)
- 🔧 **依赖管理优化**
  - 从主项目 requirements.txt 移除 WeBan 特有依赖
  - 依赖完全由插件自行管理（requirements.txt + manifest.json）
  - 主程序自动安装插件依赖
  - 添加 Pillow>=10.0.0 到依赖列表
- 🐛 **修复** Flet API 兼容性问题
  - 修复 ft.Color 类型提示错误
  - 修复 log_text 未初始化时的崩溃
  - 修复 show_snack_bar API 变更
- 🎨 **UI 改进**
  - WeBan 缺失时显示友好提示
  - 提供详细的解决方案说明

### v1.2.0 (2026-04-23)
- ✨ **新增 Git Submodule 支持**
  - 推荐将 WeBan 添加为 Git Submodule 到 `modules/WeBan/`
  - 插件自动检测并使用子模块
  - 新增 `WEBAN_SUBMODULE_GUIDE.md` 详细说明
- 🐛 **修复** WeBanClient 为 None 时的 AttributeError
  - 添加 WeBan 可用性检查
  - 优雅降级，不因 WeBan 缺失而崩溃
- 🗂️ **目录结构优化**
  - 推荐使用 `plugins/weban_plugin/modules/WeBan/` 路径
  - 兼容 `plugins/weban_plugin/WeBan/` 路径
  - 更新 `.gitignore` 规则
- 📝 **文档更新** 说明 Git Submodule 配置方法

### v1.1.0 (2026-04-23)
- ✨ **新增自动依赖检测和配置功能**
  - 自动查找多个位置的 WeBan 模块
  - 首次加载时自动创建符号链接或复制文件
  - 无需手动配置 Git 子模块或运行脚本
- 🐛 **修复** WeBan 模块路径查找逻辑
- 📝 **更新文档** 说明自动处理机制

### v1.0.0 (2026-04-21)
- ✅ 首次发布
- ✅ 集成完整WeBan代码库
- ✅ 实现插件化架构
- ✅ 支持GUI界面操作
- ✅ 实现自动学习和答题功能

## 📄 许可证

本插件遵循原WeBan项目的许可证。详见 `lib/WeBan/LICENSE` 文件。

## 🙏 致谢

感谢原WeBan项目的作者和贡献者。

## 📧 反馈与支持

如有问题或建议，请在项目仓库提交Issue。
