"""
SSL证书配置模块
SSL Certificate Configuration Helper

自动配置SSL证书，解决Windows环境下的SSL验证失败问题

主要功能：
1. 自动使用 certifi 提供的根证书
2. 配置 Python SSL 全局默认设置
3. 配置 urllib 和 requests 的 SSL 上下文
4. 确保 Flet 和 Playwright 的网络请求不会因 SSL 问题失败
"""

import os
import sys
import ssl
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def configure_ssl_certificate():
    """
    配置SSL证书，解决SSL验证失败问题

    此函数应该在程序启动时尽早调用，在任何网络操作之前
    特别是在导入 Flet 或 Playwright 之前调用
    """
    try:
        # 1. 尝试导入 certifi
        import certifi

        # 2. 获取证书文件路径
        cert_path = certifi.where()
        logger.info(f"使用 certifi 证书: {cert_path}")

        # 3. 设置环境变量（影响大多数使用 SSL 的库）
        os.environ['SSL_CERT_FILE'] = cert_path
        os.environ['REQUESTS_CA_BUNDLE'] = cert_path
        os.environ['CURL_CA_BUNDLE'] = cert_path

        # 4. 配置 Python 全局 SSL 默认设置
        # 这会影响所有创建的 SSL 上下文，除非明确指定其他设置
        ssl._create_default_https_context = ssl.create_default_context
        ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=cert_path)

        logger.info("✓ SSL证书配置完成")

        return True, cert_path

    except ImportError:
        logger.warning("⚠ certifi 未安装，尝试使用系统证书")
        # certifi 未安装，尝试使用系统证书
        try:
            # 创建默认 SSL 上下文（使用系统证书）
            ssl._create_default_https_context = ssl.create_default_context
            logger.info("✓ 使用系统默认证书")
            return True, None
        except Exception as e:
            logger.error(f"✗ 配置系统证书失败: {e}")
            return False, str(e)

    except Exception as e:
        logger.error(f"✗ 配置SSL证书失败: {e}")
        return False, str(e)


def configure_urllib_ssl():
    """
    专门配置 urllib 的 SSL 设置

    这对 Flet 下载可执行文件特别重要
    """
    try:
        import ssl
        import certifi

        cert_path = certifi.where()

        # 创建 SSL 上下文
        ssl_context = ssl.create_default_context(cafile=cert_path)

        # 配置 urllib 使用此 SSL 上下文
        import urllib.request
        urllib.request.ssl_context = ssl_context

        logger.info("✓ urllib SSL 配置完成")
        return True

    except ImportError:
        logger.warning("⚠ certifi 未安装，urllib 使用系统证书")
        return False
    except Exception as e:
        logger.error(f"✗ 配置 urllib SSL 失败: {e}")
        return False


def configure_requests_ssl():
    """
    配置 requests 库的 SSL 设置

    这会影响所有使用 requests 的 HTTP 请求
    """
    try:
        import certifi

        cert_path = certifi.where()

        # requests 会自动读取 REQUESTS_CA_BUNDLE 环境变量
        # 已经在 configure_ssl_certificate() 中设置
        # 这里只是确认一下

        logger.info("✓ requests SSL 配置完成")
        return True

    except ImportError:
        logger.warning("⚠ certifi 未安装，requests 使用系统证书")
        return False
    except Exception as e:
        logger.error(f"✗ 配置 requests SSL 失败: {e}")
        return False


def install_certifi_if_missing() -> bool:
    """
    如果 certifi 未安装，尝试安装它

    Returns:
        bool: 是否成功安装或已存在
    """
    try:
        import certifi
        logger.info("✓ certifi 已安装")
        return True
    except ImportError:
        logger.info("certifi 未安装，尝试安装...")
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "certifi"],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                logger.info("✓ certifi 安装成功")
                return True
            else:
                logger.error(f"✗ certifi 安装失败: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"✗ 安装 certifi 时出错: {e}")
            return False


def verify_ssl_configuration() -> bool:
    """
    验证 SSL 配置是否正确

    尝试发起一个简单的 HTTPS 请求来验证

    Returns:
        bool: SSL 配置是否正确
    """
    try:
        import urllib.request
        import certifi

        cert_path = certifi.where()

        # 尝试访问一个简单的 HTTPS 网站
        # 使用较短的 timeout
        response = urllib.request.urlopen(
            "https://www.google.com/",
            timeout=5,
            context=ssl.create_default_context(cafile=cert_path)
        )

        if response.status == 200:
            logger.info("✓ SSL 验证测试成功")
            return True
        else:
            logger.warning(f"⚠ SSL 验证测试返回状态: {response.status}")
            return False

    except Exception as e:
        logger.warning(f"⚠ SSL 验证测试失败: {e}")
        # 这不一定意味着配置失败，可能是网络问题
        return False


def setup_ssl_auto_config(silent: bool = False) -> bool:
    """
    自动配置 SSL 证书（一步式函数）

    这是最简单的使用方式，在程序启动时调用一次即可

    Args:
        silent: 是否静默模式（不打印日志）

    Returns:
        bool: 是否配置成功
    """
    def log(msg):
        if not silent:
            print(f"[SSL] {msg}")

    try:
        log("正在配置 SSL 证书...")

        # 1. 确保 certifi 已安装
        if not install_certifi_if_missing():
            log("⚠ certifi 安装失败，将使用系统证书")

        # 2. 配置全局 SSL 证书
        success, cert_path = configure_ssl_certificate()
        if success:
            if cert_path:
                log(f"✓ SSL 证书配置完成: {cert_path}")
            else:
                log("✓ SSL 证书配置完成（使用系统证书）")
        else:
            log("⚠ SSL 证书配置失败，但程序可能仍能运行")

        # 3. 配置特定库的 SSL 设置
        configure_urllib_ssl()
        configure_requests_ssl()

        # 4. 可选：验证配置（在网络环境允许的情况下）
        # verify_ssl_configuration()

        return True

    except Exception as e:
        log(f"✗ SSL 自动配置失败: {e}")
        return False


# 预配置模块：在导入时自动配置
# 这样可以确保在任何网络操作之前 SSL 都已配置好
_auto_configured = False


def ensure_ssl_configured():
    """
    确保 SSL 已配置（幂等操作）

    可以安全地多次调用，只会配置一次
    """
    global _auto_configured
    if not _auto_configured:
        setup_ssl_auto_config(silent=True)
        _auto_configured = True
