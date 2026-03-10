"""
测试配置和 fixtures
"""
import sys
from pathlib import Path
import pytest

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def project_root_dir():
    """项目根目录"""
    return project_root


@pytest.fixture(scope="session")
def src_dir(project_root_dir):
    """源代码目录"""
    return project_root_dir / "src"


@pytest.fixture(scope="session")
def tests_dir(project_root_dir):
    """测试目录"""
    return project_root_dir / "tests"


@pytest.fixture(scope="session")
def build_dir(project_root_dir):
    """构建输出目录"""
    return project_root_dir / "dist"


@pytest.fixture(scope="session")
def config_dir(project_root_dir):
    """配置目录"""
    return project_root_dir / "config"


@pytest.fixture
def temp_dir(tmp_path):
    """临时目录 fixture（每个测试独立）"""
    return tmp_path


@pytest.fixture
def temp_file(tmp_path):
    """临时文件 fixture（每个测试独立）"""
    def _create_temp_file(content="", suffix=".txt"):
        import tempfile
        fd, path = tempfile.mkstemp(suffix=suffix, dir=tmp_path, text=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return Path(path)

    return _create_temp_file


@pytest.fixture(scope="session")
def mock_settings():
    """模拟设置管理器"""
    from src.core.config import SettingsManager
    import tempfile

    # 创建临时配置文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config_file = f.name
        f.write('{"student_credentials": {"username": "test", "password": "test123"}, "teacher_credentials": {"username": "test", "password": "test123"}}')

    # 创建设置管理器
    settings = SettingsManager(config_file=config_file)

    yield settings

    # 清理
    import os
    os.unlink(config_file)


@pytest.fixture(scope="function")
def reset_settings():
    """重置设置管理器（每个测试后）"""
    from src.core.config import get_settings_manager

    # 保存原始配置
    settings = get_settings_manager()
    original_student = settings.get_student_credentials()
    original_teacher = settings.get_teacher_credentials()

    yield

    # 恢复原始配置
    settings.set_student_credentials(*original_student)
    settings.set_teacher_credentials(*original_teacher)


@pytest.fixture(scope="function", autouse=True)
def clean_logs():
    """每个测试前清理日志（自动应用）"""
    import tempfile

    # 创建临时日志目录
    log_dir = tempfile.mkdtemp(prefix="test_logs_")

    yield log_dir

    # 清理
    import shutil
    try:
        shutil.rmtree(log_dir)
    except:
        pass
