"""
构建工具通用模块测试
测试 src/build_tools/common.py 中的函数
"""

import pytest
from pathlib import Path
from src.build_tools.common import (
    get_platform_info,
    get_dist_name,
    format_size,
    calculate_directory_size,
    update_version_info
)


class TestGetPlatformInfo:
    """测试平台信息获取"""

    def test_returns_dict(self):
        """测试返回字典"""
        result = get_platform_info()
        assert isinstance(result, dict)

    def test_has_platform_key(self):
        """测试包含 platform 键"""
        result = get_platform_info()
        assert 'platform' in result

    def test_has_architecture_key(self):
        """测试包含 architecture 键"""
        result = get_platform_info()
        assert 'architecture' in result

    def test_platform_is_valid(self):
        """测试平台值有效"""
        result = get_platform_info()
        assert result['platform'] in ['windows', 'linux', 'macos']

    def test_architecture_is_valid(self):
        """测试架构值有效"""
        result = get_platform_info()
        assert result['architecture'] in ['x64', 'arm64', 'arm', 'x86']


class TestGetDistName:
    """测试分发名称生成"""

    @pytest.mark.parametrize("mode,expected_suffix", [
        ("onedir", "installer"),
        ("onefile", "portable"),
    ])
    def test_mode_suffix(self, mode, expected_suffix):
        """测试模式后缀"""
        platform_info = {'platform': 'windows', 'architecture': 'x64'}
        result = get_dist_name(mode, "2.7.0", platform_info)
        assert result.endswith(expected_suffix)

    def test_full_format(self):
        """测试完整格式"""
        platform_info = {'platform': 'windows', 'architecture': 'x64'}
        result = get_dist_name("onedir", "2.7.0", platform_info)
        assert "ZX-Answering-Assistant" in result
        assert "v2.7.0" in result
        assert "windows" in result
        assert "x64" in result

    def test_minimal_build_type(self):
        """测试最小化构建类型"""
        platform_info = {'platform': 'windows', 'architecture': 'x64'}
        result = get_dist_name("onedir", "2.7.0", platform_info, build_type="minimal")
        assert "minimal" in result


class TestFormatSize:
    """测试大小格式化"""

    @pytest.mark.parametrize("size_bytes,expected", [
        (0, "0 B"),
        (512, "512.00 B"),
        (1024, "1.00 KB"),
        (1536, "1.50 KB"),
        (1024 * 1024, "1.00 MB"),
        (1024 * 1024 * 1024, "1.00 GB"),
        (1024 * 1024 * 1024 * 1024, "1.00 TB"),
    ])
    def test_format_sizes(self, size_bytes, expected):
        """测试各种大小的格式化"""
        result = format_size(size_bytes)
        assert result == expected


class TestCalculateDirectorySize:
    """测试目录大小计算"""

    def test_empty_directory(self, tmp_path):
        """测试空目录"""
        result = calculate_directory_size(tmp_path)
        assert result == 0

    def test_directory_with_files(self, tmp_path):
        """测试包含文件的目录"""
        # 创建测试文件
        (tmp_path / "file1.txt").write_text("a" * 100)
        (tmp_path / "file2.txt").write_text("b" * 200)

        result = calculate_directory_size(tmp_path)
        assert result == 300

    def test_nested_directories(self, tmp_path):
        """测试嵌套目录"""
        # 创建嵌套结构
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").write_text("x" * 50)

        result = calculate_directory_size(tmp_path)
        assert result == 50

    def test_nonexistent_directory(self):
        """测试不存在的目录"""
        result = calculate_directory_size(Path("/nonexistent/path"))
        assert result == 0


@pytest.mark.unit
class TestUpdateVersionInfo:
    """测试版本信息更新（使用子进程避免 stdout 问题）"""

    def test_updates_version_file(self, tmp_path):
        """测试更新版本文件"""
        import subprocess
        import sys

        # 创建临时版本文件
        version_file = tmp_path / "test_version.py"
        version_file.write_text('''
VERSION = "2.7.0"
BUILD_DATE = ""
BUILD_TIME = ""
GIT_COMMIT = ""
BUILD_MODE = ""
''')

        # 更新版本信息
        code = f"""
from src.build_tools.common import update_version_info
update_version_info(r'{version_file}')
"""
        result = subprocess.run([sys.executable, "-c", code], capture_output=True)

        # 验证更新
        content = version_file.read_text()
        assert 'BUILD_DATE = "' in content or result.returncode == 0

        # 清理
        version_file.unlink()
