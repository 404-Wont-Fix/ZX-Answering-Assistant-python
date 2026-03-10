"""
并行构建模块
同时构建 onedir 和 onefile 版本
"""

import concurrent.futures
from typing import Dict, Callable, Any


def build_parallel(
    build_func: Callable,
    modes: list = None,
    max_workers: int = 2,
    **kwargs
) -> Dict[str, Any]:
    """
    并行构建多个版本

    Args:
        build_func: 构建函数
        modes: 要构建的模式列表（如 ['onedir', 'onefile']）
        max_workers: 最大并发数
        **kwargs: 传递给构建函数的参数

    Returns:
        dict: 各模式的构建结果
    """
    if modes is None:
        modes = ['onedir', 'onefile']

    results = {}

    print(f"[INFO] 开始并行构建: {', '.join(modes)}")
    print(f"[INFO] 并发数: {max_workers}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有构建任务
        future_to_mode = {}
        for mode in modes:
            future = executor.submit(build_func, mode=mode, **kwargs)
            future_to_mode[future] = mode

        # 等待完成并收集结果
        for future in concurrent.futures.as_completed(future_to_mode):
            mode = future_to_mode[future]
            try:
                result = future.result()
                results[mode] = {'status': 'success', 'result': result}
                print(f"[OK] {mode} 构建完成")
            except Exception as e:
                results[mode] = {'status': 'failed', 'error': str(e)}
                print(f"[ERROR] {mode} 构建失败: {e}")

    # 总结
    success_count = sum(1 for r in results.values() if r['status'] == 'success')
    print(f"\n[INFO] 并行构建完成: {success_count}/{len(modes)} 成功")

    return results


def build_sequential(
    build_func: Callable,
    modes: list = None,
    **kwargs
) -> Dict[str, Any]:
    """
    串行构建多个版本（备用方案）

    Args:
        build_func: 构建函数
        modes: 要构建的模式列表
        **kwargs: 传递给构建函数的参数

    Returns:
        dict: 各模式的构建结果
    """
    if modes is None:
        modes = ['onedir', 'onefile']

    results = {}

    print(f"[INFO] 开始串行构建: {', '.join(modes)}")

    for mode in modes:
        print(f"\n[INFO] 正在构建: {mode}")
        try:
            result = build_func(mode=mode, **kwargs)
            results[mode] = {'status': 'success', 'result': result}
            print(f"[OK] {mode} 构建完成")
        except Exception as e:
            results[mode] = {'status': 'failed', 'error': str(e)}
            print(f"[ERROR] {mode} 构建失败: {e}")

    return results
