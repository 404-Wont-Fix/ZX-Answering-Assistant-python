"""
SSL证书配置模块 - 无 certifi 依赖版本
SSL Certificate Configuration Helper - No certifi dependency

此版本不依赖 certifi 包，用于打包时 certifi 缺失的情况

主要功能：
1. 优先使用 certifi（如果可用）
2. 回退到内联证书或系统证书
3. 确保在打包环境下仍能正常工作
"""

import os
import sys
import ssl
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# Mozilla 根证书（简化版本，包含常用 CA）
# 这个证书可以从 https://curl.se/docs/caextract.html 获取完整版
MOZILLA_ROOT_CERTS = """
# This is a simplified version of Mozilla root certificates
# For production use, please use certifi or download the full bundle from:
# https://curl.se/docs/caextract.html

-----BEGIN CERTIFICATE-----
MIIDxTCCAq2gAwIBAgIQAqxcJmoLQJuPC3nyrkYldzANBgkqhkiG9w0BAQUFADBs
MQswCQYDVQQGEwJVUzEVMBMGA1UEChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3
d3cuZGlnaWNlcnQuY29tMSswKQYDVQQDEyJEaWdpQ2VydCBIaWdoIEFzc3VyYW5j
ZSBFViBSb290IENBMB4XDTA2MTExMDAwMDAwMFoXDTMxMTExMDAwMDAwMFowbDEL
MAkGA1UEBhMCVVMxFTATBgNVBAoTDERpZ2lDZXJ0IEluYzEZMBcGA1UECxMQd3d3
LmRpZ2ljZXJ0LmNvbTErMCkGA1UEAxMiRGlnaUNlcnQgSGlnaCBBc3N1cmFuY2Ug
RVYgUm9vdCBDQTCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAMbM5XPm
+9S75S0t9qQq6f2ArHvGnbfy9QJx3N5jJ8pI0VPkHqSgBZFLcwfDOJb7i4rfKJL1
tK/zG+NBq0jKb6VK+iDeTrnHKUt8VP+yN+xLZk7fGiPdPFq5RnvLg9dQX5dNFzvy
...
[省略证书内容，实际使用时应该包含完整证书]
-----END CERTIFICATE-----
"""


def configure_ssl_certificate():
    """
    配置SSL证书，解决SSL验证失败问题

    尝试顺序：
    1. certifi（如果已安装）
    2. 内联证书
    3. 系统证书
    """
    # 1. 尝试使用 certifi
    try:
        import certifi
        cert_path = certifi.where()

        if os.path.exists(cert_path):
            logger.info(f"✓ 使用 certifi 证书: {cert_path}")
            os.environ['SSL_CERT_FILE'] = cert_path
            os.environ['REQUESTS_CA_BUNDLE'] = cert_path
            os.environ['CURL_CA_BUNDLE'] = cert_path
            ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=cert_path)
            return True, cert_path
        else:
            logger.warning(f"⚠ certifi 证书文件不存在: {cert_path}")
    except ImportError:
        logger.info("ℹ certifi 未安装，尝试备用方案")
    except Exception as e:
        logger.warning(f"⚠ certifi 配置失败: {e}")

    # 2. 尝试使用内联证书
    try:
        cert_path = Path(__file__).parent / "mozilla_root_certs.pem"
        if cert_path.exists():
            logger.info(f"✓ 使用内联证书: {cert_path}")
            os.environ['SSL_CERT_FILE'] = str(cert_path)
            os.environ['REQUESTS_CA_BUNDLE'] = str(cert_path)
            os.environ['CURL_CA_BUNDLE'] = str(cert_path)
            ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=str(cert_path))
            return True, str(cert_path)
        else:
            logger.info("ℹ 内联证书文件不存在")
    except Exception as e:
        logger.warning(f"⚠ 内联证书配置失败: {e}")

    # 3. 使用系统默认证书（最不推荐，但总比没有好）
    try:
        logger.info("ℹ 使用系统默认证书")
        ssl._create_default_https_context = ssl.create_default_context

        # 清除之前设置的环境变量
        for key in ['SSL_CERT_FILE', 'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE']:
            if key in os.environ:
                del os.environ[key]

        return True, None
    except Exception as e:
        logger.error(f"✗ 系统证书配置失败: {e}")
        return False, str(e)


def configure_urllib_ssl():
    """配置 urllib 的 SSL 设置"""
    try:
        import ssl
        import urllib.request

        # 尝试使用环境变量中的证书
        if 'SSL_CERT_FILE' in os.environ:
            cert_path = os.environ['SSL_CERT_FILE']
            ssl_context = ssl.create_default_context(cafile=cert_path)
            urllib.request.ssl_context = ssl_context
            logger.info("✓ urllib SSL 配置完成（使用环境变量证书）")
        else:
            # 使用系统默认
            urllib.request.ssl_context = ssl.create_default_context()
            logger.info("✓ urllib SSL 配置完成（使用系统证书）")

        return True
    except Exception as e:
        logger.warning(f"⚠ 配置 urllib SSL 失败: {e}")
        return False


def configure_requests_ssl():
    """配置 requests 库的 SSL 设置"""
    try:
        # requests 会自动读取环境变量
        # 已经在 configure_ssl_certificate() 中设置
        logger.info("✓ requests SSL 配置完成")
        return True
    except Exception as e:
        logger.warning(f"⚠ 配置 requests SSL 失败: {e}")
        return False


def setup_ssl_auto_config(silent: bool = False) -> bool:
    """
    自动配置 SSL 证书（一步式函数）

    Args:
        silent: 是否静默模式

    Returns:
        bool: 是否配置成功
    """
    def log(msg):
        if not silent:
            print(f"[SSL] {msg}")

    try:
        log("正在配置 SSL 证书...")

        # 1. 配置全局 SSL 证书
        success, cert_path = configure_ssl_certificate()
        if success:
            if cert_path:
                log(f"✓ SSL 证书配置完成: {cert_path}")
            else:
                log("✓ SSL 证书配置完成（使用系统证书）")
        else:
            log("⚠ SSL 证书配置失败，但程序可能仍能运行")

        # 2. 配置特定库的 SSL 设置
        configure_urllib_ssl()
        configure_requests_ssl()

        return True

    except Exception as e:
        log(f"✗ SSL 自动配置失败: {e}")
        return False


# 预配置模块
_auto_configured = False


def ensure_ssl_configured():
    """确保 SSL 已配置（幂等操作）"""
    global _auto_configured
    if not _auto_configured:
        setup_ssl_auto_config(silent=True)
        _auto_configured = True
