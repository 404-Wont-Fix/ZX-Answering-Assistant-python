"""
版本信息模块测试
测试 version.py 中的功能（使用子进程避免 stdout/stderr 冲突）
"""

import pytest
import subprocess
import sys
from pathlib import Path


class TestVersionInfo:
    """测试版本信息"""

    def test_version_constants(self):
        """测试版本常量"""
        code = "import version; assert version.VERSION == '2.7.2'"
        result = subprocess.run([sys.executable, "-c", code], capture_output=True)
        assert result.returncode == 0, f"stderr: {result.stderr.decode()}"

    def test_version_name(self):
        """测试版本名称"""
        code = "import version; assert version.VERSION_NAME == 'ZX Answering Assistant'"
        result = subprocess.run([sys.executable, "-c", code], capture_output=True)
        assert result.returncode == 0

    def test_get_version_string(self):
        """测试获取版本字符串"""
        code = "import version; s = version.get_version_string(); assert 'ZX Answering Assistant' in s and '2.7.2' in s"
        result = subprocess.run([sys.executable, "-c", code], capture_output=True)
        assert result.returncode == 0

    def test_get_full_version_string(self):
        """测试获取完整版本字符串"""
        code = "import version; s = version.get_full_version_string(); assert 'v2.7.2' in s"
        result = subprocess.run([sys.executable, "-c", code], capture_output=True)
        assert result.returncode == 0

    def test_get_build_info(self):
        """测试获取构建信息"""
        code = """
import version
info = version.get_build_info()
assert isinstance(info, dict)
assert 'version' in info
assert 'name' in info
assert 'build_date' in info
assert 'build_time' in info
"""
        result = subprocess.run([sys.executable, "-c", code], capture_output=True)
        assert result.returncode == 0


class TestVersionFile:
    """测试版本文件生成"""

    def test_create_version_file(self, tmp_path):
        """测试创建版本文件"""
        code = f"""
import version
version_file = version.create_version_file(r'{tmp_path}\\test_version.txt')
assert version_file.exists()
"""
        result = subprocess.run([sys.executable, "-c", code], capture_output=True)
        assert result.returncode == 0
        assert (tmp_path / "test_version.txt").exists()

    def test_version_file_content(self, tmp_path):
        """测试版本文件内容"""
        code = f"""
import version
version_file = version.create_version_file(r'{tmp_path}\\test_version2.txt')
with open(version_file, 'r', encoding='utf-8') as f:
    content = f.read()
    assert 'ZX Answering Assistant' in content
    assert '2.7.2' in content
"""
        result = subprocess.run([sys.executable, "-c", code], capture_output=True)
        assert result.returncode == 0


@pytest.mark.unit
class TestVersionInfoValues:
    """测试版本信息值"""

    def test_version_format(self):
        """测试版本号格式"""
        code = """
import version
import re
pattern = r'^\\d+\\.\\d+\\.\\d+$'
assert re.match(pattern, version.VERSION)
"""
        result = subprocess.run([sys.executable, "-c", code], capture_output=True)
        assert result.returncode == 0

    def test_build_date_format(self):
        """测试构建日期格式"""
        code = """
import version
import re
pattern = r'^\\d{4}-\\d{2}-\\d{2}$'
assert re.match(pattern, version.BUILD_DATE)
"""
        result = subprocess.run([sys.executable, "-c", code], capture_output=True)
        assert result.returncode == 0

    def test_build_time_format(self):
        """测试构建时间格式"""
        code = """
import version
import re
pattern = r'^\\d{2}:\\d{2}:\\d{2}$'
assert re.match(pattern, version.BUILD_TIME)
"""
        result = subprocess.run([sys.executable, "-c", code], capture_output=True)
        assert result.returncode == 0
