# WeBan 子模块配置指南

本指南说明如何将 WeBan 项目作为 Git Submodule 添加到插件中。

## 为什么使用 Git Submodule？

使用 Git Submodule 管理 WeBan 的优势：

✅ **独立版本管理** - WeBan 有自己的版本历史
✅ **轻松更新** - 可以单独更新 WeBan 到新版本
✅ **避免重复** - 不需要将 WeBan 代码复制到主项目
✅ **协作友好** - 其他开发者可以轻松获取 WeBan 代码

## 添加 WeBan 子模块

### 方法 1: 使用现有的 WeBan 仓库

```bash
# 1. 进入插件目录
cd plugins/weban_plugin

# 2. 创建 modules 目录（如果不存在）
mkdir -p modules
cd modules

# 3. 添加 WeBan 作为子模块
git submodule add https://github.com/TianJiaJi/WeBan.git WeBan

# 4. 返回项目根目录
cd ../../..

# 5. 提交更改
git add plugins/weban_plugin/modules
git commit -m "feat(weban): 添加 WeBan Git Submodule"
```

### 方法 2: 使用本地 WeBan 目录

如果 WeBan 已经在项目根目录：

```bash
# 1. 删除或移动根目录的 WeBan（可选）
# mv WeBan WeBan.backup

# 2. 添加子模块
cd plugins/weban_plugin
mkdir -p modules
cd modules
git submodule add ../../WeBan WeBan

# 3. 返回项目根目录
cd ../../..

# 4. 提交更改
git add plugins/weban_plugin/modules
git commit -m "feat(weban): 添加 WeBan Git Submodule"
```

## 克隆包含子模块的项目

当其他开发者克隆项目时：

```bash
# 方法 1: 克隆时自动初始化子模块
git clone --recursive <主项目仓库URL>

# 方法 2: 克隆后初始化子模块
git clone <主项目仓库URL>
cd <项目目录>
git submodule init
git submodule update
```

## 更新 WeBan 子模块

### 更新到最新版本

```bash
cd plugins/weban_plugin/modules/WeBan
git pull origin main
cd ../../..
git add plugins/weban_plugin/modules/WeBan
git commit -m "chore(weban): 更新 WeBan 子模块到最新版本"
```

### 切换到特定版本

```bash
cd plugins/weban_plugin/modules/WeBan
git checkout v1.0.0  # 或其他 tag/branch
cd ../../..
git add plugins/weban_plugin/modules/WeBan
git commit -m "chore(weban): 切换 WeBan 到 v1.0.0"
```

## 查看子模块状态

```bash
# 查看所有子模块
git submodule status

# 查看子模块详细信息
git submodule--helper status
```

## 删除子模块

如果需要删除 WeBan 子模块：

```bash
# 1. 删除子模块
git submodule deinit -f plugins/weban_plugin/modules/WeBan

# 2. 删除 .gitmodules 中的配置
git config -f .gitmodules --remove-section submodule.plugins/weban_plugin/modules/WeBan

# 3. 删除文件
git rm -f plugins/weban_plugin/modules/WeBan

# 4. 清理 .git/modules
rm -rf .git/modules/plugins/weban_plugin/modules/WeBan

# 5. 提交更改
git commit -m "chore(weban): 删除 WeBan 子模块"
```

## 自动配置（备选方案）

如果您不想使用 Git Submodule，插件支持自动配置：

1. 将 WeBan 项目放在项目根目录的 `WeBan/` 文件夹
2. 插件会在首次加载时自动创建符号链接或复制文件
3. 无需手动配置

**注意**：自动配置需要 WeBan 在版本控制中，或者每个开发者都需要单独设置。

## 常见问题

### Q: 子模块显示 "modified" 但没有改动？

A: 这可能是由于子模块中的未提交更改。检查：

```bash
cd plugins/weban_plugin/modules/WeBan
git status
```

如果有未提交的更改，可以：
- 提交更改：`git commit -am "xxx"`
- 或丢弃更改：`git reset --hard HEAD`

### Q: 克隆后子模块目录为空？

A: 初始化并更新子模块：

```bash
git submodule update --init --recursive
```

### Q: 如何禁用自动配置，强制使用子模块？

A: 删除项目根目录的 `WeBan/` 文件夹，只保留 `plugins/weban_plugin/modules/WeBan/` 子模块。

## 总结

推荐配置：
- ✅ **使用 Git Submodule**（推荐）
- ✅ 子模块路径：`plugins/weban_plugin/modules/WeBan/`
- ✅ 插件自动检测并使用子模块
- ✅ 版本控制和更新更方便
