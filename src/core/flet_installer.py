"""
Flet 库安装管理模块
Flet Library Installation Manager

负责 Flet 库的检测、安装和版本管理

注意：Flet 会在首次使用时自动下载桌面运行时文件，无需手动处理。
如果遇到运行时下载问题，请查看：FLET_MANUAL_DOWNLOAD.md
"""

import subprocess
import sys
import importlib.metadata as importlib_metadata
from pathlib import Path
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class FletInstaller:
    """Flet 库安装管理器"""

    # 最低支持的 Flet 版本
    MIN_FLET_VERSION = "0.80.0"
    RECOMMENDED_FLET_VERSION = "0.82.0"

    def __init__(self):
        """初始化 Flet 安装管理器"""
        self._flet_checked = False

    def check_flet_installed(self) -> Tuple[bool, str, Optional[str]]:
        """
        检查 Flet 是否已安装并获取版本信息

        Returns:
            Tuple[bool, str, Optional[str]]: (是否已安装, 状态消息, 版本号)
        """
        try:
            # 检查 Flet 是否已安装
            import flet
            version = importlib_metadata.version("flet")

            # 检查版本是否满足最低要求
            if self._version_comparable(version) >= self._version_comparable(self.MIN_FLET_VERSION):
                return True, f"Flet 已安装 (v{version})", version
            else:
                return False, f"Flet 版本过低 (v{version}，需要 v{self.MIN_FLET_VERSION}+)", version

        except ImportError:
            return False, "Flet 未安装", None
        except Exception as e:
            return False, f"检查 Flet 时出错: {str(e)}", None

    def install_flet(self, show_progress: bool = True) -> Tuple[bool, str]:
        """
        安装 Flet 库

        Args:
            show_progress: 是否显示安装进度

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息)
        """
        if show_progress:
            logger.info("开始安装 Flet 库...")

        try:
            # 尝试安装推荐版本
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", f"flet>={self.RECOMMENDED_FLET_VERSION}"],
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode == 0:
                if show_progress:
                    logger.info("✓ Flet 安装成功！")

                # 验证安装
                is_installed, msg, version = self.check_flet_installed()
                if is_installed:
                    return True, f"Flet v{version} 安装成功"
                else:
                    return False, f"安装完成但验证失败: {msg}"
            else:
                error_msg = result.stderr or result.stdout or "未知错误"
                if show_progress:
                    logger.error(f"✗ Flet 安装失败: {error_msg}")
                return False, error_msg

        except subprocess.TimeoutExpired:
            error_msg = "Flet 安装超时（5分钟）"
            if show_progress:
                logger.error(f"✗ {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"安装过程出错: {str(e)}"
            if show_progress:
                logger.error(f"✗ {error_msg}")
            return False, error_msg

    def install_from_local_wheel(self, wheel_path: str) -> Tuple[bool, str]:
        """
        从本地 wheel 文件安装 Flet

        Args:
            wheel_path: 本地 wheel 文件路径

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息)
        """
        logger.info(f"尝试从本地 wheel 文件安装 Flet: {wheel_path}")

        try:
            wheel_file = Path(wheel_path)

            # 检查文件是否存在
            if not wheel_file.exists():
                return False, f"指定的 wheel 文件不存在: {wheel_path}"

            # 检查文件扩展名
            if not wheel_file.suffix == ".whl":
                return False, f"指定的文件不是 wheel 文件: {wheel_path}"

            # 使用 pip 安装本地 wheel 文件
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", str(wheel_file)],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                logger.info("✓ Flet 从本地 wheel 文件安装成功")

                # 验证安装
                is_installed, msg, version = self.check_flet_installed()
                if is_installed:
                    return True, f"Flet v{version} 安装成功"
                else:
                    return False, f"安装完成但验证失败: {msg}"
            else:
                error_msg = result.stderr or result.stdout or "未知错误"
                return False, error_msg

        except Exception as e:
            return False, f"从本地 wheel 文件安装失败: {str(e)}"

    def install_from_requirements(self, requirements_dir: str) -> Tuple[bool, str]:
        """
        从包含 requirements.txt 的目录安装 Flet

        Args:
            requirements_dir: 包含 requirements.txt 的目录路径

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息)
        """
        logger.info(f"尝试从目录安装 Flet: {requirements_dir}")

        try:
            req_dir = Path(requirements_dir)

            # 检查目录是否存在
            if not req_dir.exists():
                return False, f"指定的目录不存在: {requirements_dir}"

            # 检查是否有 requirements.txt
            req_file = req_dir / "requirements.txt"
            if not req_file.exists():
                return False, f"目录中未找到 requirements.txt: {requirements_dir}"

            # 使用 pip 安装
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )

            if result.returncode == 0:
                logger.info("✓ Flet 从 requirements.txt 安装成功")

                # 验证安装
                is_installed, msg, version = self.check_flet_installed()
                if is_installed:
                    return True, f"Flet v{version} 安装成功"
                else:
                    return False, f"安装完成但验证失败: {msg}"
            else:
                error_msg = result.stderr or result.stdout or "未知错误"
                return False, error_msg

        except Exception as e:
            return False, f"从 requirements.txt 安装失败: {str(e)}"

    def ensure_flet_installed(self, auto_install: bool = True) -> Tuple[bool, str]:
        """
        确保 Flet 已安装，提供多种备选方案

        注意：Flet 会在首次使用时自动下载桌面运行时文件

        Args:
            auto_install: 是否自动安装（默认True）

        Returns:
            Tuple[bool, str]: (是否成功, 错误信息)
        """
        # 如果已经检查过，直接返回
        if self._flet_checked:
            return True, ""

        logger.info("检查 Flet 库安装状态...")

        # 方案1: 检查 Flet 是否已安装
        is_installed, msg, version = self.check_flet_installed()
        if is_installed:
            logger.info(f"✓ {msg}")
            self._flet_checked = True
            return True, ""

        logger.warning(f"✗ {msg}")

        if not auto_install:
            error_msg = f"""
            ================================================
            Flet 库未安装！
            ================================================

            当前状态: {msg}

            请尝试以下备选方案:

            方案1: 使用 pip 自动安装
            ------------------------
            打开命令行，执行以下命令:
                pip install flet>={self.RECOMMENDED_FLET_VERSION}

            方案2: 使用项目 requirements.txt
            ------------------------
            在项目根目录执行:
                pip install -r requirements.txt

            方案3: 手动下载 wheel 文件
            ------------------------
            1. 访问: https://pypi.org/project/flet/#files
            2. 下载对应版本的 .whl 文件
            3. 使用: pip install flet-x.x.x-py3-none-any.whl

            方案4: 离线安装
            ------------------------
            1. 在有网络的机器上下载 wheel 文件
            2. 复制到目标机器
            3. 使用方案3中的命令安装

            ⚠️ 重要提示: Flet 首次使用时会自动下载桌面运行时文件
            如果运行时下载失败，请查看: FLET_MANUAL_DOWNLOAD.md

            详细文档: docs/FLET_SETUP.md
            ================================================
            """
            return False, error_msg.strip()

        # 方案2: 自动安装 Flet
        logger.info("尝试自动安装 Flet...")
        success, error = self.install_flet(show_progress=True)
        if success:
            self._flet_checked = True
            return True, ""

        # 自动安装失败
        error_msg = f"""
        ================================================
        Flet 库安装失败！
        ================================================

        自动安装失败原因: {error}

        请尝试手动安装:

        方法1: pip 安装
        ------------------------
        pip install flet>={self.RECOMMENDED_FLET_VERSION}

        方法2: 使用项目 requirements
        ------------------------
        pip install -r requirements.txt

        方法3: 国内镜像加速
        ------------------------
        pip install flet -i https://pypi.tuna.tsinghua.edu.cn/simple

        ⚠️ 重要提示: Flet 首次使用时会自动下载桌面运行时文件
        如果运行时下载失败，请查看: FLET_MANUAL_DOWNLOAD.md

        详细文档: docs/FLET_SETUP.md
        ================================================
        """
        return False, error_msg.strip()

    def _version_comparable(self, version_string: str) -> tuple:
        """
        将版本字符串转换为可比较的元组

        Args:
            version_string: 版本字符串 (如 "0.82.0")

        Returns:
            tuple: 版本元组 (如 (0, 82, 0))
        """
        try:
            # 移除可能的 'v' 前缀
            version_string = version_string.lstrip('v')
            # 分割版本号并转换为整数
            return tuple(map(int, version_string.split('.')))
        except Exception:
            # 如果解析失败，返回 (0, 0, 0)
            return (0, 0, 0)


# 全局 Flet 安装管理器实例
_flet_installer: Optional[FletInstaller] = None


def get_flet_installer() -> FletInstaller:
    """
    获取全局 Flet 安装管理器实例

    Returns:
        FletInstaller: 管理器实例
    """
    global _flet_installer
    if _flet_installer is None:
        _flet_installer = FletInstaller()
    return _flet_installer


def ensure_flet_installed(auto_install: bool = True) -> Tuple[bool, str]:
    """
    确保 Flet 已安装的快捷函数

    Args:
        auto_install: 是否自动安装（默认True）

    Returns:
        Tuple[bool, str]: (是否成功, 错误信息)
    """
    return get_flet_installer().ensure_flet_installed(auto_install)
