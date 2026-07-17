"""
Playwright 工作线程引擎

管理专用工作线程、任务队列、线程自愈（reset_worker）。
所有 Playwright 操作通过 submit_task 序列化到单个工作线程执行。
"""

from typing import Callable, Any
import threading
import concurrent.futures
import logging
import queue
import os

logger = logging.getLogger(__name__)


def force_kill_process_tree(timeout: float = 2.0) -> None:
    """强制终止当前 Python 进程派生的所有子进程（递归整棵树）。

    Playwright 的 Node driver 是当前进程的子进程，而浏览器（Chrome/Edge）由 Node driver
    派生，属于孙进程——只杀 node.exe 会让浏览器成为孤儿继续驻留。这里用 psutil 递归杀掉
    全部后代，作为退出流程的兜底，确保不残留孤儿浏览器进程。

    Args:
        timeout: terminate 后等待进程退出的超时时间，超时则升级为 kill。
    """
    try:
        import psutil
    except ImportError:
        logger.debug("psutil 未安装，跳过子进程树强制终止")
        return

    try:
        parent = psutil.Process(os.getpid())
        children = parent.children(recursive=True)
        if not children:
            return

        logger.info(f"强制终止 {len(children)} 个子进程（Playwright/浏览器进程树）")
        for proc in children:
            try:
                proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        gone, alive = psutil.wait_procs(children, timeout=timeout)
        for proc in alive:
            try:
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        logger.debug(f"获取子进程列表失败: {e}")
    except Exception as e:
        logger.debug(f"强制终止子进程树失败: {e}")


class WorkerEngine:
    """Playwright 工作线程引擎，管理任务队列和线程生命周期。

    负责：
    - 维护单个专用工作线程执行所有 Playwright 操作
    - 任务队列 + Future 结果回传
    - 线程自愈：reset_worker 强杀浏览器进程 + 重建 worker

    Args:
        state_lock: 由 BrowserManager 传入的 RLock，用于 reset_worker 中
                    跨线程清理浏览器状态时保证线程安全。
        cleanup_callback: reset_worker 时调用的无参回调，
                          负责清 _browser/_playwright/_contexts/_pages。
    """

    def __init__(
        self,
        state_lock: threading.RLock,
        cleanup_callback: Callable[[], None],
    ):
        self._state_lock = state_lock
        self._cleanup_callback = cleanup_callback

        # 线程生命周期
        self._worker_thread = None
        self._worker_lock = threading.Lock()
        self._worker_ready_event = threading.Event()
        self._worker_generation = 0

        # 任务队列
        self._task_queue = queue.Queue()
        self._result_futures = {}
        self._cancelled_task_ids = set()
        self._task_id = 0
        self._task_id_lock = threading.Lock()
        self._result_futures_lock = threading.Lock()

        # 线程本地存储（标记当前是否在 worker 线程）
        self._thread_local = threading.local()

    def is_worker_thread(self) -> bool:
        """判断当前代码是否运行在 Playwright 专用工作线程。"""
        return getattr(self._thread_local, 'is_worker', False)

    def is_alive(self) -> bool:
        """检查 worker 线程是否存活。"""
        with self._worker_lock:
            return self._worker_thread is not None and self._worker_thread.is_alive()

    def submit_task(self, func: Callable, *args, **kwargs) -> Any:
        """提交任务到工作线程执行。

        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数的返回值
        """
        self._ensure_worker_thread()

        is_worker = getattr(self._thread_local, 'is_worker', False)
        logger.debug(f"submit_task: 是否在工作线程中? {is_worker}, 当前线程ID: {threading.get_ident()}")

        if is_worker:
            logger.debug("已在工作线程中，直接执行任务")
            return func(*args, **kwargs)

        # 生成任务ID
        with self._task_id_lock:
            task_id = self._task_id
            self._task_id += 1

        logger.debug(f"提交任务 {task_id} 到工作线程队列，函数: {func.__name__}")

        # 创建 Future 用于获取结果
        future = concurrent.futures.Future()
        with self._result_futures_lock:
            self._result_futures[task_id] = future

        # 提交任务到队列
        self._task_queue.put((task_id, func, args, kwargs))

        # 等待结果
        try:
            result = future.result(timeout=300)  # 最多等待5分钟
            logger.debug(f"任务 {task_id} 完成")
            return result
        except concurrent.futures.TimeoutError:
            logger.error(f"任务 {task_id} 超时，触发 worker 重置以自愈")
            with self._result_futures_lock:
                timed_out_future = self._result_futures.pop(task_id, None)
                self._cancelled_task_ids.add(task_id)
            if timed_out_future and not timed_out_future.done():
                timed_out_future.cancel()
            # 300s 超时几乎必然是 worker 卡死，触发 reset 重建 worker + 浏览器
            self.reset_worker(reason="任务超时（300s）")
            raise TimeoutError(f"任务执行超时: {func.__name__}")

    def reset_worker(self, reason: str = "manual"):
        """重置 worker 线程：强杀浏览器进程逼卡死的 func 抛异常退出，清理状态。

        用于 worker 卡死（page.goto 永久阻塞）时的运行时自愈。
        下次 submit_task → _ensure_worker_thread 会自动起新 generation 的 worker。
        """
        with self._worker_lock:
            logger.warning(f"🔄 重置 worker 线程: {reason}")
            old_thread = self._worker_thread
            # 1. 升代际 → 旧 worker 从 func 异常恢复后读到不匹配会退出
            self._worker_generation += 1
            # 2. 强杀浏览器进程树，逼旧 worker 的 Playwright 调用抛 TargetClosedError
            try:
                force_kill_process_tree(timeout=2.0)
            except Exception as e:
                logger.error(f"reset force_kill 失败: {e}")
            # 3. 等旧 worker 退出（卡死则超时；旧线程作为 daemon 泄漏，进程退出时回收）
            if old_thread is not None and old_thread.is_alive():
                old_thread.join(timeout=5)
            # 4. 清理 Playwright 状态（加锁）
            with self._state_lock:
                self._cleanup_callback()
            # 5. 排空待处理任务队列（全部失败）
            self._drain_pending_tasks()
            # 6. worker_thread 置 None，下次 _ensure_worker_thread 起新 generation 的 worker
            self._worker_thread = None
            logger.info("✅ worker 线程已重置，下次操作将自动重建")

    def _ensure_worker_thread(self):
        """确保工作线程已启动"""
        with self._worker_lock:
            if self._worker_thread is None or not self._worker_thread.is_alive():
                logger.info("启动 Playwright 工作线程")
                self._worker_ready_event.clear()
                self._worker_thread = threading.Thread(
                    target=self._worker_loop,
                    args=(self._worker_generation,),
                    daemon=True,
                )
                self._worker_thread.start()
                logger.info("Playwright 工作线程已创建，等待就绪信号")

        if not self._worker_ready_event.wait(timeout=5):
            raise RuntimeError("Playwright 工作线程启动超时")

    def _worker_loop(self, my_generation: int):
        """工作线程的主循环，处理任务队列。

        my_generation: 该 worker 的代际编号；reset_worker 会升代际，
        旧 worker 从 func 异常恢复后读到不匹配则退出（while 条件）。
        """
        worker_thread_id = threading.get_ident()
        logger.info(f"Playwright 工作线程开始运行，线程ID: {worker_thread_id}, 代际: {my_generation}")
        self._thread_local.is_worker = True
        self._worker_ready_event.set()

        while self._worker_generation == my_generation:
            try:
                try:
                    task_id, func, args, kwargs = self._task_queue.get(timeout=1.0)
                    logger.info(f"[工作线程 {worker_thread_id}] 收到任务 {task_id}: {func.__name__}")
                except queue.Empty:
                    continue

                with self._result_futures_lock:
                    is_cancelled = task_id in self._cancelled_task_ids
                    if is_cancelled:
                        self._cancelled_task_ids.discard(task_id)
                        self._result_futures.pop(task_id, None)

                if is_cancelled:
                    logger.warning(f"[工作线程] 跳过已超时取消的任务 {task_id}: {func.__name__}")
                    self._task_queue.task_done()
                    continue

                # 执行任务
                try:
                    logger.debug(f"[工作线程] 开始执行任务 {task_id}")
                    result = func(*args, **kwargs)
                    logger.debug(f"[工作线程] 任务 {task_id} 执行成功")
                    with self._result_futures_lock:
                        self._cancelled_task_ids.discard(task_id)
                        future = self._result_futures.pop(task_id, None)
                    if future and not future.done():
                        future.set_result(result)
                except Exception as e:
                    logger.error(f"任务 {task_id} 执行失败: {e}", exc_info=True)
                    with self._result_futures_lock:
                        self._cancelled_task_ids.discard(task_id)
                        future = self._result_futures.pop(task_id, None)
                    if future and not future.done():
                        future.set_exception(e)

                self._task_queue.task_done()

            except Exception as e:
                logger.error(f"工作线程主循环异常: {e}", exc_info=True)

    def _drain_pending_tasks(self):
        """排空待处理任务队列（reset_worker 时调用，全部标记失败）。"""
        with self._result_futures_lock:
            while not self._task_queue.empty():
                try:
                    task_id, func, args, kwargs = self._task_queue.get_nowait()
                    future = self._result_futures.pop(task_id, None)
                    if future is not None and not future.done():
                        future.set_exception(RuntimeError("worker 已重置，任务被丢弃"))
                except queue.Empty:
                    break
            self._cancelled_task_ids.clear()
