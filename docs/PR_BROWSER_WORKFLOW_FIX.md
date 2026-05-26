# PR: 浏览器工作流隔离与启动兼容修复

## 背景

本次修改修复多个功能同时调用 Playwright 时出现的浏览器上下文冲突、线程冲突，以及缺失可选 WeBan 子模块导致主程序启动失败的问题。

## 主要改动

- 将 `src` 与 `src.core` 的兼容导出改为懒加载，避免包初始化阶段提前导入 Playwright。
- 将 WeBan 版本读取改为可选探测，子模块缺失时主程序仍可启动。
- 为云考试新增独立的 `BrowserType.CLOUD_EXAM`，避免复用学生端评估答题页面。
- 将 Playwright 生命周期操作统一调度到浏览器工作线程，减少 Flet 后台线程与 sync Playwright 的 greenlet 冲突。
- 为浏览器工作线程增加 ready event，确保工作线程完成初始化后才接收任务。
- 为超时任务增加取消标记，工作线程会跳过尚未执行且已经超时的任务，并清理对应 future。
- 将答案提取、课程认证等入口的浏览器操作收回同一浏览器工作线程执行。

## 验证

已执行：

```bash
python3 -m compileall -q src plugins main.py version.py
git diff --check
```

当前环境未安装 Playwright，因此未执行真实浏览器端到端启动验证。

## 风险与回滚

- 浏览器工作流统一串行化后，同一时间只能有一个 Playwright 任务在工作线程内执行。这样牺牲少量并发，换取稳定的线程边界。
- 如果后续需要更细粒度并发，应改用 Playwright async API 或为每类工作流建立独立的专用线程与实例。
