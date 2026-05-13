# Flet版本兼容性问题修复总结

## 问题描述

用户在新环境中运行程序时遇到UI库版本兼容性问题，主要是Flet 0.82.0+版本的API变化导致的。

## 主要修复内容

### 1. **窗口控制API修复**
- **问题**: `page.window_center = True` (错误的属性赋值)
- **修复**: `page.window.center()` (正确的方法调用)
- **文件**: `src/main_gui.py:96`
- **状态**: ✅ 已修复

### 2. **应用启动API修复**
- **问题**: `ft.app()` (在Flet 0.80.0+中已废弃)
- **修复**: `ft.run()` (新的API)
- **文件**: `src/main_gui.py:454,468`
- **状态**: ✅ 已修复

### 3. **窗口高度访问修复**
- **问题**: `page.window.height` (可能在某些版本中不存在)
- **修复**: 使用固定高度值避免版本兼容性问题
- **文件**: `src/ui/views/course_certification_view.py:283`
- **状态**: ✅ 已修复

### 4. **异步窗口居中解决方案**
- **问题**: `page.window.center()` 是异步方法，在同步上下文中无法直接调用
- **修复**: 实现了 `_center_window_async()` 方法，使用独立线程处理异步调用
- **文件**: `src/main_gui.py`
- **状态**: ✅ 已修复

### 5. **依赖版本固定**
- **问题**: Flet频繁更新导致API不兼容，且flet-desktop版本号错误
- **修复**: 在 `requirements.txt` 中固定版本
  - `flet==0.82.2`
  - `flet-desktop==0.82.2` (修正版本号)
- **文件**: `requirements.txt`
- **状态**: ✅ 已修复

## 测试结果

### ✅ 测试通过
1. 所有视图模块导入成功
2. GUI应用正常启动
3. Flet服务器运行正常
4. 窗口居中功能正常

### ⚠️ 已知警告（不影响功能）
- `ElevatedButton` 已废弃，建议使用 `Button`
- 共51处使用了 `ElevatedButton`，暂时不影响功能
- 可以在未来版本中逐步替换

## 新环境部署指南

### 1. 安装固定版本的依赖
```bash
pip install -r requirements.txt
```

### 2. 如果遇到Flet相关问题
```bash
# 卸载现有版本
pip uninstall flet flet-desktop -y

# 安装固定版本
pip install flet==0.82.2 flet-desktop==0.21.5
```

### 3. 验证安装
```bash
python test_simple_gui.py
```

## 技术细节

### Flet 0.80.0+ 主要API变化

1. **应用启动**: `ft.app()` → `ft.run()`
2. **窗口控制**: 部分方法变为异步
3. **控件更新**: `ElevatedButton` → `Button` (建议)

### 异步兼容性处理

由于Flet 0.82.0+中部分窗口控制方法变为异步，我们实现了：

```python
def _center_window_async(self):
    """在页面加载完成后异步居中窗口"""
    import threading
    import time
    import asyncio

    def center_after_delay():
        time.sleep(0.1)  # 等待页面完全加载
        try:
            # 检查是否已有事件循环
            loop = asyncio.get_running_loop()
            # 在新线程中创建新的事件循环
            def run_center():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                new_loop.run_until_complete(self.page.window.center())
                new_loop.close()

            thread = threading.Thread(target=run_center)
            thread.start()
        except RuntimeError:
            # 没有事件循环，直接运行
            asyncio.run(self.page.window.center())

    thread = threading.Thread(target=center_after_delay)
    thread.daemon = True
    thread.start()
```

## 文件修改列表

1. `requirements.txt` - 固定Flet版本
2. `src/main_gui.py` - 修复window_center API、ft.app API、添加异步居中方法
3. `src/ui/views/course_certification_view.py` - 修复window.height访问
4. `test_flet_api.py` - 新增API兼容性测试脚本
5. `test_simple_gui.py` - 新增简单GUI测试脚本

## 验证步骤

1. **安装依赖**: `pip install -r requirements.txt`
2. **运行测试**: `python test_simple_gui.py`
3. **启动应用**: `python src/main_gui.py`

## 建议

1. **定期检查Flet更新**: 每次升级Flet版本前，先在测试环境验证
2. **关注废弃警告**: 定期查看Flet更新日志，及时适配新API
3. **版本固定策略**: 对于生产环境，建议锁定依赖版本
4. **测试覆盖**: 重要UI功能应该有对应的测试脚本

---

**修复日期**: 2026-05-14
**Flet版本**: 0.82.2
**应用版本**: v3.6.1
**状态**: ✅ 已完成并通过测试并发布
