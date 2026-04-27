# v3.5.0 发布说明

## 📋 更新日期
2026-04-27

## 🎯 本次更新

### 优化项目结构
- ✅ 删除 `cache_template.py` 和 `cache_template.bat`
  - Flet 会自动处理模板缓存，无需手动下载
  - 简化项目结构

- ✅ 删除多余文档
  - `BUILD_CACHE_GUIDE.md`
  - `BUILD_FIXES.md`
  - `STARTUP_ANIMATION_GUIDE.md`
  - `BUILD_QUICK_START.md`
  - `UPDATE_SUMMARY.md`

### 优化依赖管理
- ✅ 移除构建时依赖
  - `pyyaml` - Flet 打包时自动安装
  - `py7zr` - Flet 打包时自动安装

- ✅ 移除未使用的依赖
  - `keyboard` - 代码中未使用，所有 `keyboard` 引用都是 Python 内置的 `KeyboardInterrupt` 异常

- ✅ 保留运行时依赖
  - 所有应用运行所需的依赖保持不变

## 📝 说明

### Flet 模板缓存机制

Flet 构建系统会自动处理模板缓存：

1. **首次编译**: 自动从 GitHub 下载模板到 `build/flutter`
2. **后续编译**: 自动使用本地缓存，无需重复下载
3. **清理缓存**: 运行 `build.bat` 或手动删除 `build/flutter`

### 一键编译

使用提供的构建脚本：

```bash
build.bat
```

功能：
- 自动清理旧的构建文件
- 删除损坏的模板缓存
- 重新编译应用

## ✅ 保留功能

所有 v3.4.1 的功能保持不变：

- ✅ 启动动画系统
- ✅ 一键构建脚本
- ✅ `__builtins__` 兼容性修复
- ✅ Flet API 兼容性修复
- ✅ 软件标题乱码修复
- ✅ 启动屏幕中文显示
- ✅ ImportError 修复

## 🚀 升级指南

### 从 v3.4.1 升级

无需特殊操作，直接更新代码即可：

```bash
git pull
```

### 编译应用

```bash
# 激活虚拟环境
.venv\Scripts\activate

# 编译
build.bat
```

## 📊 版本对比

| 项目 | v3.4.1 | v3.5.0 |
|------|--------|--------|
| Python 文件 | 7 个 | 5 个 |
| 文档文件 | 10 个 | 5 个 |
| 运行时依赖 | 11 个 | 8 个 |
| 功能 | 完整 | 完整 |

## 🎯 下一步

- [ ] 添加应用图标
- [ ] 配置应用元数据
- [ ] 优化打包体积
- [ ] 添加自动更新功能

---

**版本**: v3.5.0
**发布日期**: 2026-04-27
**Git 提交**: (待更新)
