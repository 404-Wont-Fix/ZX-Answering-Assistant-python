# Git 子模块设置说明

## 当前状态

项目中的 WeBan 目录**不是**真正的 Git 子模块，而是一个普通的目录克隆。

## 转换为真正的 Git 子模块（可选）

如果您想要使用 Git 子模块的标准功能（如 `git submodule update`），可以执行以下步骤：

### 步骤 1：删除现有的 WeBan 目录

```bash
# 从 Git 中移除（但保留文件）
git rm --cached plugins/weban_plugin/modules/WeBan

# 删除目录
rm -rf plugins/weban_plugin/modules/WeBan
```

### 步骤 2：添加为子模块

```bash
# 添加子模块
git submodule add https://github.com/hangone/WeBan.git plugins/weban_plugin/modules/WeBan

# 提交
git commit -m "feat(weban): 添加 WeBan 作为 Git 子模块"
```

### 步骤 3：更新子模块

```bash
# 更新到最新版本
cd plugins/weban_plugin/modules/WeBan
git pull origin main
cd ../../..
git add plugins/weban_plugin/modules/WeBan
git commit -m "chore(weban): 更新 WeBan 子模块"
```

## 克隆包含子模块的项目

其他开发者克隆项目时：

```bash
# 方法 1：克隆时自动初始化子模块
git clone --recursive <repository-url>

# 方法 2：克隆后手动初始化
git clone <repository-url>
cd <project-directory>
git submodule init
git submodule update
```

## 不使用子模块（当前方案）

如果您选择不使用 Git 子模块，插件已经支持自动检测：

### 插件会自动查找 WeBan 的位置：

1. `plugins/weban_plugin/modules/WeBan/` （推荐）
2. `plugins/weban_plugin/WeBan/`
3. `WeBan/` （项目根目录）
4. `submodules/WeBan/`

### 更新 WeBan：

```bash
# 手动更新
cd plugins/weban_plugin/modules/WeBan
git pull origin main
```

## 建议

- **个人开发/小团队**：不使用子模块，插件自动检测足够
- **大团队/正式项目**：使用 Git 子模块，更规范

## 故障排除

### 子模块显示 "modified"

```bash
cd plugins/weban_plugin/modules/WeBan
git status
# 如果有未提交的更改，提交或丢弃
```

### 子模块为空

```bash
git submodule update --init --recursive
```
