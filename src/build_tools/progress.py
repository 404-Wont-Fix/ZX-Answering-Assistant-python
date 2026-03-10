"""
构建进度可视化模块
使用 rich 库提供美观的进度条和状态显示
"""

from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn
)
from rich.console import Console as RichConsole
from typing import Optional, List


class BuildProgress:
    """构建进度管理器"""

    def __init__(self, console: Optional[RichConsole] = None):
        self.console = console or RichConsole()
        self.progress = None
        self.tasks = {}

    def start(self, total_steps: int, description: str = "构建项目"):
        """启动进度显示"""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
            expand=True,
        )

        self.progress.start()
        main_task = self.progress.add_task(
            f"[cyan]{description}",
            total=total_steps
        )
        self.tasks['main'] = main_task

    def update(self, advance: int = 1, description: str = None):
        """更新进度"""
        if 'main' in self.tasks:
            self.progress.update(
                self.tasks['main'],
                advance=advance,
                description=description
            )

    def add_subtask(self, description: str, total: int = 100) -> int:
        """添加子任务"""
        task_id = self.progress.add_task(f"[yellow]{description}", total=total)
        return task_id

    def update_subtask(self, task_id: int, advance: int = 1, description: str = None):
        """更新子任务"""
        self.progress.update(task_id, advance=advance, description=description)

    def stop(self):
        """停止进度显示"""
        if self.progress:
            self.progress.stop()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


# 全局进度实例
_global_progress: Optional[BuildProgress] = None


def get_build_progress() -> BuildProgress:
    """获取全局进度实例"""
    global _global_progress
    if _global_progress is None:
        _global_progress = BuildProgress()
    return _global_progress


def print_step(step_num: int, total: int, description: str):
    """打印构建步骤（简单模式）"""
    print(f"[{step_num}/{total}] {description}")


def print_success(message: str):
    """打印成功消息"""
    from rich.console import Console
    console = Console()
    console.print(f"[✓] [green]{message}[/green]")


def print_error(message: str):
    """打印错误消息"""
    from rich.console import Console
    console = Console()
    console.print(f"[✗] [red]{message}[/red]")


def print_warning(message: str):
    """打印警告消息"""
    from rich.console import Console
    console = Console()
    console.print(f"[!] [yellow]{message}[/yellow]")


def print_info(message: str):
    """打印信息消息"""
    from rich.console import Console
    console = Console()
    console.print(f"[i] [cyan]{message}[/cyan]")
