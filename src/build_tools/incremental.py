"""
增量构建模块
实现智能增量构建，只重新构建修改过的文件
"""

import hashlib
import json
from pathlib import Path
from datetime import datetime


def get_file_hash(file_path: Path) -> str:
    """计算文件的 MD5 哈希值"""
    if not file_path.exists():
        return None
    return hashlib.md5(file_path.read_bytes()).hexdigest()


def get_source_state(source_dir: Path) -> dict:
    """获取源代码状态（所有文件的哈希）"""
    state = {}
    for py_file in source_dir.rglob('*.py'):
        rel_path = str(py_file.relative_to(source_dir))
        state[rel_path] = get_file_hash(py_file)
    return state


def save_build_state(build_dir: Path, state: dict):
    """保存构建状态"""
    build_dir.mkdir(parents=True, exist_ok=True)
    state_file = build_dir / '.build_state.json'
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'state': state
        }, f, indent=2)


def load_build_state(build_dir: Path) -> dict:
    """加载构建状态"""
    state_file = build_dir / '.build_state.json'
    if not state_file.exists():
        return {}
    with open(state_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('state', {})


def should_rebuild(source_dir: Path, build_dir: Path) -> bool:
    """检查是否需要重新构建"""
    if not build_dir.exists():
        return True

    current_state = get_source_state(source_dir)
    last_state = load_build_state(build_dir)

    if not last_state:
        return True

    # 检查文件修改
    for file_path, file_hash in current_state.items():
        if last_state.get(file_path) != file_hash:
            print(f"[INFO] 文件已修改: {file_path}")
            return True

    # 检查文件删除
    for file_path in last_state:
        if file_path not in current_state:
            print(f"[INFO] 文件已删除: {file_path}")
            return True

    return False


def incremental_build_check(source_dir: str = "src", build_dir: str = "build") -> bool:
    """增量构建检查"""
    source_path = Path(source_dir)
    build_path = Path(build_dir)

    if should_rebuild(source_path, build_path):
        print("[INFO] 检测到源代码变更，需要重新构建")
        return True
    else:
        print("[INFO] 无需重新构建（使用缓存）")
        return False


def clean_build_state(build_dir: Path):
    """清理构建状态"""
    state_file = build_dir / '.build_state.json'
    if state_file.exists():
        state_file.unlink()
        print(f"[INFO] 已清理构建状态: {state_file}")
