"""
Windows 代码签名模块
为可执行文件添加数字签名
"""

import subprocess
from pathlib import Path
from typing import Optional


def find_signtool() -> Optional[Path]:
    """查找 signtool.exe"""
    # 常见安装路径
    possible_paths = [
        Path("C:/Program Files (x86)/Windows Kits/10/bin/10.0.22000.0/x64/signtool.exe"),
        Path("C:/Program Files (x86)/Windows Kits/10/bin/x64/signtool.exe"),
        Path("C:/Program Files/Windows Kits/10/bin/x64/signtool.exe"),
    ]

    # 检查 PATH
    try:
        result = subprocess.run(["where", "signtool"], capture_output=True, text=True)
        if result.returncode == 0:
            return Path(result.stdout.strip().split('\n')[0])
    except:
        pass

    # 检查常见路径
    for path in possible_paths:
        if path.exists():
            return path

    return None


def sign_executable(
    exe_path: Path,
    cert_path: Path,
    cert_password: str,
    timestamp_url: str = "http://timestamp.digicert.com",
    algorithm: str = "sha256"
) -> bool:
    """
    对可执行文件进行代码签名

    Args:
        exe_path: 可执行文件路径
        cert_path: 证书文件路径（.pfx 文件）
        cert_password: 证书密码
        timestamp_url: 时间戳服务器 URL
        algorithm: 签名算法（sha1, sha256, sha384, sha512）

    Returns:
        bool: 是否签名成功
    """
    if not exe_path.exists():
        print(f"[ERROR] 文件不存在: {exe_path}")
        return False

    if not cert_path.exists():
        print(f"[ERROR] 证书文件不存在: {cert_path}")
        return False

    # 查找 signtool
    signtool = find_signtool()
    if not signtool:
        print("[ERROR] 未找到 signtool.exe")
        print("[INFO] 请安装 Windows SDK")
        return False

    print(f"[INFO] 使用 signtool: {signtool}")

    # 构建命令
    cmd = [
        str(signtool),
        "sign",
        "/f", str(cert_path),
        "/p", cert_password,
        "/tr", timestamp_url,
        "/td", algorithm,
        "/fd", algorithm,
        str(exe_path)
    ]

    print(f"[INFO] 正在签名: {exe_path.name}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"[OK] 签名成功: {exe_path.name}")
        if result.stdout:
            print(f"[INFO] {result.stdout}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] 签名失败: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False


def verify_signature(exe_path: Path) -> bool:
    """
    验证可执行文件的签名

    Args:
        exe_path: 可执行文件路径

    Returns:
        bool: 签名是否有效
    """
    signtool = find_signtool()
    if not signtool:
        return False

    cmd = [str(signtool), "verify", "/pa", str(exe_path)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False


def sign_with_config(exe_path: Path, config: dict) -> bool:
    """
    使用配置进行签名

    Args:
        exe_path: 可执行文件路径
        config: 签名配置（从 build_config.yaml 读取）

    Returns:
        bool: 是否签名成功
    """
    if not config.get('enabled', False):
        print("[INFO] 代码签名未启用")
        return False

    cert_path = config.get('cert_path')
    if not cert_path:
        print("[ERROR] 未配置证书路径")
        return False

    # 证书密码可以从环境变量读取
    import os
    cert_password = os.getenv('CERT_PASSWORD', '')
    if not cert_password:
        print("[ERROR] 未设置证书密码（CERT_PASSWORD 环境变量）")
        return False

    timestamp_url = config.get('timestamp_url', 'http://timestamp.digicert.com')
    algorithm = config.get('algorithm', 'sha256')

    return sign_executable(
        exe_path=exe_path,
        cert_path=Path(cert_path),
        cert_password=cert_password,
        timestamp_url=timestamp_url,
        algorithm=algorithm
    )
