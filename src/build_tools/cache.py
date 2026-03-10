"""
依赖缓存模块
缓存 Playwright 浏览器和 Flet 等大型依赖
"""

import hashlib
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


class DependencyCache:
    """依赖缓存管理器"""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / ".zx_build_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_index = self.cache_dir / "cache_index.json"
        self._load_index()

    def _load_index(self):
        """加载缓存索引"""
        if self.cache_index.exists():
            with open(self.cache_index, 'r') as f:
                self.index = json.load(f)
        else:
            self.index = {}

    def _save_index(self):
        """保存缓存索引"""
        with open(self.cache_index, 'w') as f:
            json.dump(self.index, f, indent=2)

    def get_cache_key(self, url: str, version: str) -> str:
        """生成缓存键"""
        key_data = f"{version}_{hashlib.md5(url.encode()).hexdigest()}"
        return key_data

    def is_cached(self, cache_key: str) -> bool:
        """检查是否已缓存"""
        cache_path = self.cache_dir / cache_key
        return cache_path.exists() and cache_key in self.index

    def get_cache(self, cache_key: str) -> Optional[Path]:
        """获取缓存路径"""
        if self.is_cached(cache_key):
            return self.cache_dir / cache_key
        return None

    def set_cache(self, cache_key: str, source_path: Path, metadata: dict = None):
        """设置缓存"""
        cache_path = self.cache_dir / cache_key
        cache_path.mkdir(parents=True, exist_ok=True)

        # 复制文件/目录到缓存
        if source_path.is_file():
            shutil.copy2(source_path, cache_path / source_path.name)
        elif source_path.is_dir():
            shutil.copytree(source_path, cache_path / source_path.name, dirs_exist_ok=True)

        # 更新索引
        self.index[cache_key] = {
            'timestamp': datetime.now().isoformat(),
            'type': 'file' if source_path.is_file() else 'directory',
            'source': str(source_path),
            **(metadata or {})
        }
        self._save_index()

        print(f"[OK] 已缓存: {cache_key}")

    def clear_cache(self, older_than_days: int = 30):
        """清理旧缓存"""
        cutoff = datetime.now() - timedelta(days=older_than_days)
        to_remove = []

        for key, info in self.index.items():
            cache_time = datetime.fromisoformat(info['timestamp'])
            if cache_time < cutoff:
                to_remove.append(key)

        for key in to_remove:
            cache_path = self.cache_dir / key
            if cache_path.exists():
                shutil.rmtree(cache_path)
            del self.index[key]

        self._save_index()
        print(f"[INFO] 清理了 {len(to_remove)} 个过期缓存")

    def get_cache_size(self) -> int:
        """获取缓存总大小（字节）"""
        total_size = 0
        for cache_path in self.cache_dir.iterdir():
            if cache_path.is_dir() and cache_path != self.cache_index.parent:
                total_size += sum(f.stat().st_size for f in cache_path.rglob('*') if f.is_file())
        return total_size


# 全局缓存实例
_global_cache: Optional[DependencyCache] = None


def get_dependency_cache() -> DependencyCache:
    """获取全局缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = DependencyCache()
    return _global_cache
