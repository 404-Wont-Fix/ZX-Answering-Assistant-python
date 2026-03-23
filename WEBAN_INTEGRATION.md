# WeBan 模块集成说明

本项目使用 Git Submodule 集成了 [WeBan](https://github.com/hangone/WeBan) 项目，实现代码隔离、独立更新和自动打包。

## 架构说明

### 代码隔离

- **WeBan 子模块路径**: `src/modules/WeBan`
- **适配器模块**: `src/modules/weban_adapter.py`
- **GUI 视图**: `src/ui/views/weban_view.py`

WeBan 项目作为独立的 Git 子模块存在，拥有自己的版本控制和更新周期，不会影响主项目的代码结构。

### 自动更新

更新 WeBan 到最新版本：

```bash
# 方法 1: 更新到最新主分支
git submodule update --remote src/modules/WeBan

# 方法 2: 进入子模块目录手动更新
cd src/modules/WeBan
git pull origin main
cd ../..
git add src/modules/WeBan
git commit -m "chore: update WeBan submodule"
```

### 独立仓库

WeBan 是一个独立的 Git 仓库，位于：
- 远程地址: https://github.com/hangone/WeBan.git
- 本地路径: `src/modules/WeBan`

## 使用方法

### 1. 安装依赖

WeBan 模块需要额外的依赖包：

```bash
pip install -r requirements.txt
```

WeBan 相关依赖：
- `ddddocr==1.6.1` - 验证码识别
- `loguru==0.7.3` - 日志处理
- `pycryptodome==3.23.0` - 加密库

### 2. 配置账号

WeBan 模块使用独立的配置文件 `weban_config.json`，位于项目根目录。

**配置格式**：

```json
[
  {
    "tenant_name": "学校名称",
    "account": "用户名",
    "password": "密码",
    "user": {
      "userId": "用户ID",
      "token": "访问令牌"
    },
    "study": true,
    "study_time": 20,
    "restudy_time": 0,
    "exam": true,
    "exam_use_time": 250
  }
]
```

**配置说明**：
- `tenant_name`: 学校全称（必填）
- `account` + `password`: 账号密码登录（二选一）
- `user.userId` + `user.token`: Token 登录（推荐，二选一）
- `study`: 是否自动学习课程
- `study_time`: 每个任务学习时长（秒）
- `restudy_time`: 重学时长（秒）
- `exam`: 是否自动考试
- `exam_use_time`: 考试总时长（秒）

### 3. GUI 使用

启动应用后，在导航栏点击 **"安全微伴"** 即可进入 WeBan 模块界面。

**功能**：
- 添加账号配置（支持密码登录和 Token 登录）
- 验证学校名称
- 多账号管理
- 多线程并发执行
- 实时日志显示

### 4. 获取 Token

推荐使用 Token 登录，更稳定且无需密码。

1. 在浏览器中登录 [安全微伴](https://weiban.mycourse.cn/)
2. 按 F12 打开开发者工具
3. 切换到 "应用程序" 或 "存储" 标签
4. 找到 "本地存储" (Local Storage)
5. 复制 `user` 和 `token` 的值到配置文件

## 开发说明

### 适配器接口

`WeBanAdapter` 类提供了与主项目隔离的接口：

```python
from src.modules.weban_adapter import get_weban_adapter

# 创建适配器实例
adapter = get_weban_adapter(progress_callback=my_callback)

# 验证学校
result = adapter.validate_tenant("重庆大学")

# 加载配置
adapter.load_config(config_list)

# 执行任务
result = adapter.start(use_multithread=True)

# 停止执行
adapter.stop()
```

### 打包配置

WeBan 模块已集成到打包系统中：

1. **隐藏导入**: `build_config.yaml` 中的 `hidden_imports` 包含了 WeBan 的依赖
2. **数据文件**: `src/build_tools/spec_generator.py` 自动将 WeBan 模块打包到可执行文件
3. **Git 子模块**: 打包时会自动包含 WeBan 的所有文件

**注意**: 首次打包时需要确保子模块已初始化：

```bash
git submodule update --init --recursive
```

## 常见问题

### 1. 子模块为空

如果克隆项目后 WeBan 目录为空：

```bash
git submodule update --init --recursive
```

### 2. 依赖导入失败

确保已安装所有依赖：

```bash
pip install -r requirements.txt
```

### 3. 学校名称验证失败

- 确保学校名称与 WeBan 平台显示的完全一致
- 使用 GUI 中的 "验证学校" 功能检查

### 4. 验证码识别失败

WeBan 使用 `ddddocr` 进行验证码识别，但部分学校使用腾讯云验证码无法自动识别。

**解决方案**：
- 使用 Token 登录（可能跳过验证码）
- 手动完成需要验证码的课程

### 5. 打包后模块不可用

确保：
1. 子模块已初始化
2. `build_config.yaml` 包含 WeBan 的隐藏导入
3. 打包前执行了 `git submodule update --init --recursive`

## 维护指南

### 更新 WeBan 版本

```bash
# 进入子模块目录
cd src/modules/WeBan

# 查看当前版本
git log -1

# 更新到最新版本
git pull origin main

# 返回主项目
cd ../..

# 提交更新
git add src/modules/WeBan
git commit -m "chore: update WeBan to latest version"
```

### 回退 WeBan 版本

```bash
cd src/modules/WeBan
git checkout <commit-hash>
cd ../..
git add src/modules/WeBan
git commit -m "chore: revert WeBan to <commit-hash>"
```

## 许可证

WeBan 模块遵循其原始许可证：
- 项目地址: https://github.com/hangone/WeBan
- 许可证: 详见 WeBan 项目

## 参考资料

- [Git Submodule 官方文档](https://git-scm.com/book/zh/v2/Git-%E5%B7%A5%E5%85%B7-%E5%AD%90%E6%A8%A1%E5%9D%97)
- [WeBan 原项目 README](src/modules/WeBan/README.md)
