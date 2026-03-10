"""
构建配置管理模块
负责加载和管理构建配置
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class BuildConfig:
    """构建配置管理类"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化构建配置

        Args:
            config_path: 配置文件路径，默认为项目根目录下的 build_config.yaml
        """
        if config_path is None:
            # 默认配置文件路径（项目根目录）
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "build_config.yaml"

        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件

        Returns:
            dict: 配置字典
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                print(f"[OK] 已加载配置文件: {self.config_path}")
                return config
            except Exception as e:
                print(f"[WARN] 配置文件加载失败: {e}")
                print(f"[INFO] 使用默认配置")
                return self._get_default_config()
        else:
            print(f"[INFO] 配置文件不存在: {self.config_path}")
            print(f"[INFO] 使用默认配置")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """
        获取默认配置

        Returns:
            dict: 默认配置字典
        """
        return {
            'build': {
                'mode': 'both',
                'upx': False,
                'compile_src': False,
                'remove_source_after_compile': True,
                'incremental': False,
                'clean_before_build': False,
                'output_dir': 'dist',
                'work_dir': 'build'
            },
            'playwright': {
                'auto_detect_version': True,
                'fallback_version': 'chromium-1200',
                'copy_browser': True,
                'browsers_path': 'playwright_browsers'
            },
            'flet': {
                'download_source': 'official',
                'version': '0.80.2',
                'verify_size': True,
                'min_size': 50,
                'max_size': 300
            },
            'artifacts': {
                'generate_checksums': True,
                'checksum_algorithm': 'SHA256',
                'generate_report': True,
                'report_format': 'json'
            },
            'logging': {
                'level': 'INFO',
                'log_dir': 'logs',
                'console_output': True,
                'verbose': False,
                'retention_days': 30
            },
            'validation': {
                'validate_after_build': True,
                'min_disk_space': 2,
                'verify_dependencies': True
            },
            'signing': {
                'enabled': False,
                'cert_path': None,
                'timestamp_url': 'http://timestamp.digicert.com',
                'algorithm': 'sha256'
            },
            'performance': {
                'parallel_build': True,
                'enable_cache': True,
                'cache_dir': '.build_cache',
                'cache_ttl': 30
            },
            'development': {
                'fast_mode': False,
                'skip_browser_copy': False,
                'skip_flet_download': False,
                'less_optimization': False
            }
        }

    def get(self, key_path: str, default=None) -> Any:
        """
        获取配置值

        Args:
            key_path: 配置键路径，使用点分隔（如 "build.mode"）
            default: 默认值

        Returns:
            配置值

        Examples:
            >>> config = BuildConfig()
            >>> config.get("build.mode")
            'both'
            >>> config.get("playwright.auto_detect_version")
            True
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any) -> None:
        """
        设置配置值

        Args:
            key_path: 配置键路径，使用点分隔
            value: 配置值
        """
        keys = key_path.split('.')
        config = self.config

        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]

        config[keys[-1]] = value

    def save(self) -> None:
        """保存配置到文件"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, allow_unicode=True, default_flow_style=False)
            print(f"[OK] 配置已保存: {self.config_path}")
        except Exception as e:
            print(f"[ERROR] 保存配置失败: {e}")

    def validate(self) -> bool:
        """
        验证配置是否有效

        Returns:
            bool: 配置是否有效
        """
        # 验证构建模式
        mode = self.get("build.mode")
        if mode not in ['onedir', 'onefile', 'both']:
            print(f"[ERROR] 无效的构建模式: {mode}")
            return False

        # 验证 Flet 下载源
        source = self.get("flet.download_source")
        if source not in ['official', 'mirror']:
            print(f"[ERROR] 无效的下载源: {source}")
            return False

        # 验证日志级别
        level = self.get("logging.level")
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if level not in valid_levels:
            print(f"[ERROR] 无效的日志级别: {level}")
            return False

        return True

    def print_config(self) -> None:
        """打印当前配置"""
        import json
        print("\n" + "=" * 60)
        print("📋 当前构建配置")
        print("=" * 60)
        print(json.dumps(self.config, indent=2, ensure_ascii=False))
        print("=" * 60 + "\n")


# 全局配置实例（延迟加载）
_global_config: Optional[BuildConfig] = None


def get_build_config(config_path: Optional[str] = None) -> BuildConfig:
    """
    获取全局构建配置实例

    Args:
        config_path: 配置文件路径

    Returns:
        BuildConfig: 配置实例
    """
    global _global_config

    if _global_config is None:
        _global_config = BuildConfig(config_path)

    return _global_config


def reload_config(config_path: Optional[str] = None) -> BuildConfig:
    """
    重新加载配置

    Args:
        config_path: 配置文件路径

    Returns:
        BuildConfig: 新的配置实例
    """
    global _global_config
    _global_config = BuildConfig(config_path)
    return _global_config
