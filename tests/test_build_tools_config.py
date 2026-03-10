"""
构建配置管理测试
测试 src/build_tools/config.py 中的配置管理功能
"""

import pytest
import yaml
from pathlib import Path
from src.build_tools.config import BuildConfig, get_build_config, reload_config


class TestBuildConfig:
    """测试构建配置类"""

    def test_load_default_config_when_no_file(self, tmp_path):
        """测试配置文件不存在时使用默认配置"""
        config_file = tmp_path / "nonexistent.yaml"
        config = BuildConfig(str(config_file))

        assert config.config is not None
        assert isinstance(config.config, dict)
        assert 'build' in config.config

    def test_load_config_from_file(self, tmp_path):
        """测试从文件加载配置"""
        # 创建配置文件
        config_file = tmp_path / "test_config.yaml"
        test_config = {
            'build': {
                'mode': 'onedir',
                'upx': True
            }
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(test_config, f)

        # 加载配置
        config = BuildConfig(str(config_file))

        assert config.get('build.mode') == 'onedir'
        assert config.get('build.upx') is True

    def test_get_nested_value(self):
        """测试获取嵌套配置值"""
        config = BuildConfig()  # 使用默认配置

        # 获取嵌套值
        mode = config.get('build.mode')
        assert mode in ['onedir', 'onefile', 'both']

        auto_detect = config.get('playwright.auto_detect_version')
        assert isinstance(auto_detect, bool)

    def test_get_with_default(self):
        """测试使用默认值获取不存在的键"""
        config = BuildConfig()

        # 获取不存在的键
        result = config.get('nonexistent.key', 'default_value')
        assert result == 'default_value'

    def test_set_nested_value(self):
        """测试设置嵌套配置值"""
        config = BuildConfig()

        # 设置值
        config.set('build.mode', 'onefile')
        assert config.get('build.mode') == 'onefile'

        # 设置深层嵌套值
        config.set('new.nested.key', 'value')
        assert config.get('new.nested.key') == 'value'

    def test_validate_valid_config(self):
        """测试验证有效配置"""
        config = BuildConfig()
        assert config.validate() is True

    def test_validate_invalid_mode(self):
        """测试验证无效的构建模式"""
        config = BuildConfig()
        config.set('build.mode', 'invalid_mode')

        assert config.validate() is False

    def test_validate_invalid_download_source(self):
        """测试验证无效的下载源"""
        config = BuildConfig()
        config.set('flet.download_source', 'invalid_source')

        assert config.validate() is False

    def test_save_config(self, tmp_path):
        """测试保存配置到文件"""
        config_file = tmp_path / "test_save.yaml"
        config = BuildConfig(str(config_file))

        # 修改配置
        config.set('build.mode', 'onefile')

        # 保存
        config.save()

        # 验证保存
        assert config_file.exists()

        # 重新加载并验证
        new_config = BuildConfig(str(config_file))
        assert new_config.get('build.mode') == 'onefile'


class TestGlobalConfigInstance:
    """测试全局配置实例"""

    def test_get_build_config_returns_singleton(self):
        """测试获取全局配置返回单例"""
        config1 = get_build_config()
        config2 = get_build_config()

        # 应该是同一个实例
        assert config1 is config2

    def test_reload_config_creates_new_instance(self):
        """测试重新加载配置创建新实例"""
        config1 = get_build_config()
        config2 = reload_config()

        # 应该是不同的实例
        assert config1 is not config2


@pytest.mark.unit
class TestConfigIntegration:
    """配置集成测试"""

    def test_config_matches_default_structure(self):
        """测试配置结构符合预期"""
        config = get_build_config()

        # 检查顶级键
        expected_keys = [
            'build',
            'playwright',
            'flet',
            'artifacts',
            'logging',
            'validation',
            'signing',
            'performance',
            'development'
        ]

        for key in expected_keys:
            assert key in config.config, f"缺少配置键: {key}"

    def test_build_config_has_required_fields(self):
        """测试构建配置包含必需字段"""
        config = get_build_config()

        # 检查必需的构建字段
        assert 'mode' in config.config['build']
        assert 'upx' in config.config['build']
        assert 'compile_src' in config.config['build']

    def test_playwright_config_has_required_fields(self):
        """测试 Playwright 配置包含必需字段"""
        config = get_build_config()

        # 检查必需的 Playwright 字段
        assert 'auto_detect_version' in config.config['playwright']
        assert 'browsers_path' in config.config['playwright']

    def test_flet_config_has_required_fields(self):
        """测试 Flet 配置包含必需字段"""
        config = get_build_config()

        # 检查必需的 Flet 字段
        assert 'download_source' in config.config['flet']
        assert 'version' in config.config['flet']
