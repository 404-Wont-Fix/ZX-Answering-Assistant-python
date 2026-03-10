"""
构建验证模块
在构建完成后验证产物，包括体积检查、校验和生成等
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .common import calculate_directory_size, format_size


def generate_sha256(file_path: Path) -> str:
    """
    计算文件的 SHA256 校验和

    Args:
        file_path: 文件路径

    Returns:
        str: 十六进制格式的 SHA256 校验和
    """
    sha256_hash = hashlib.sha256()

    try:
        with open(file_path, "rb") as f:
            # 分块读取文件，避免内存问题
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()

    except Exception as e:
        return f"ERROR: {e}"


def validate_build_artifact(artifact_path: Path) -> Dict:
    """
    验证单个构建产物

    Args:
        artifact_path: 构建产物路径（文件或目录）

    Returns:
        dict: 验证结果字典
            - path: 产物路径
            - type: "file" 或 "directory"
            - exists: 是否存在
            - size_bytes: 大小（字节）
            - size_human: 人类可读的大小
            - sha256: SHA256 校验和（仅文件）
            - error: 错误信息（如果有）
    """
    result = {
        "path": str(artifact_path),
        "type": "file" if artifact_path.is_file() else "directory",
        "exists": artifact_path.exists(),
        "size_bytes": 0,
        "size_human": "0 B",
        "sha256": None,
        "error": None
    }

    if not result["exists"]:
        result["error"] = "Path does not exist"
        return result

    try:
        if artifact_path.is_file():
            # 文件
            size = artifact_path.stat().st_size
            result["size_bytes"] = size
            result["size_human"] = format_size(size)
            result["sha256"] = generate_sha256(artifact_path)

        elif artifact_path.is_dir():
            # 目录
            size = calculate_directory_size(artifact_path)
            result["size_bytes"] = size
            result["size_human"] = format_size(size)
            result["sha256"] = None  # 目录不生成 SHA256

    except Exception as e:
        result["error"] = str(e)

    return result


def validate_build(dist_dir: Path, artifacts: List[str]) -> Dict:
    """
    验证构建产物

    Args:
        dist_dir: 分发目录路径
        artifacts: 要验证的产物名称列表

    Returns:
        dict: 验证报告
            - timestamp: 验证时间
            - dist_dir: 分发目录路径
            - artifacts: 各产物的验证结果列表
            - total_size: 总大小（字节）
            - total_size_human: 人类可读的总大小
            - summary: 摘要信息
    """
    report = {
        "timestamp": datetime.now().isoformat(),
        "dist_dir": str(dist_dir),
        "artifacts": [],
        "total_size": 0,
        "total_size_human": "0 B",
        "summary": {
            "total": len(artifacts),
            "valid": 0,
            "invalid": 0,
            "missing": 0
        }
    }

    for artifact_name in artifacts:
        artifact_path = dist_dir / artifact_name

        # 如果是目录模式，检查目录内的可执行文件
        if artifact_path.is_dir():
            # 查找 .exe 文件
            exe_files = list(artifact_path.glob("*.exe"))
            if exe_files:
                artifact_path = exe_files[0]  # 使用第一个找到的 .exe

        result = validate_build_artifact(artifact_path)
        result["artifact_name"] = artifact_name
        report["artifacts"].append(result)

        # 统计
        report["total_size"] += result["size_bytes"]

        if result["error"]:
            if "does not exist" in result["error"]:
                report["summary"]["missing"] += 1
            else:
                report["summary"]["invalid"] += 1
        else:
            report["summary"]["valid"] += 1

    report["total_size_human"] = format_size(report["total_size"])

    return report


def print_validation_report(report: Dict):
    """
    打印验证报告

    Args:
        report: 验证报告字典
    """
    print("\n" + "=" * 70)
    print("📊 构建验证报告")
    print("=" * 70)
    print(f"⏰ 验证时间: {report['timestamp']}")
    print(f"📁 分发目录: {report['dist_dir']}")
    print(f"\n📦 总计: {report['summary']['total']} 个产物")
    print(f"✅ 有效: {report['summary']['valid']} 个")
    print(f"❌ 无效: {report['summary']['invalid']} 个")
    print(f"⚠️  缺失: {report['summary']['missing']} 个")
    print(f"💾 总大小: {report['total_size_human']}")

    print("\n" + "-" * 70)
    print("📋 产物详情:")
    print("-" * 70)

    for artifact in report["artifacts"]:
        print(f"\n🔹 {artifact['artifact_name']}")
        print(f"   路径: {artifact['path']}")
        print(f"   类型: {artifact['type']}")

        if artifact["error"]:
            print(f"   状态: ❌ {artifact['error']}")
        else:
            print(f"   状态: ✅ 有效")
            print(f"   大小: {artifact['size_human']}")
            if artifact["sha256"]:
                print(f"   SHA256: {artifact['sha256']}")

    print("\n" + "=" * 70)


def save_validation_report(report: Dict, output_path: Path):
    """
    保存验证报告到 JSON 文件

    Args:
        report: 验证报告字典
        output_path: 输出文件路径
    """
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"✅ 验证报告已保存: {output_path}")

    except Exception as e:
        print(f"❌ 保存验证报告失败: {e}")


def generate_checksums_file(dist_dir: Path, output_filename: str = "checksums.txt") -> Path:
    """
    为分发目录中的所有文件生成校验和文件

    Args:
        dist_dir: 分发目录路径
        output_filename: 输出文件名

    Returns:
        Path: 校验和文件路径
    """
    checksums_path = dist_dir / output_filename

    try:
        with open(checksums_path, 'w', encoding='utf-8') as f:
            # 递归处理所有文件
            for file_path in sorted(dist_dir.rglob('*')):
                if file_path.is_file() and file_path != checksums_path:
                    # 计算相对路径
                    rel_path = file_path.relative_to(dist_dir)
                    sha256 = generate_sha256(file_path)

                    # 写入校验和（格式：SHA256 文件名）
                    f.write(f"{sha256}  {rel_path}\n")

        print(f"✅ 校验和文件已生成: {checksums_path}")
        return checksums_path

    except Exception as e:
        print(f"❌ 生成校验和文件失败: {e}")
        return checksums_path


def check_disk_space(required_bytes: int, path: Path = None) -> Dict:
    """
    检查磁盘剩余空间是否足够

    Args:
        required_bytes: 需要的字节数
        path: 要检查的路径，默认为当前目录

    Returns:
        dict: 磁盘空间信息
            - path: 检查的路径
            - required_bytes: 需要的字节数
            - required_human: 人类可读的需要大小
            - free_bytes: 剩余字节数
            - free_human: 人类可读的剩余大小
            - sufficient: 是否足够
    """
    import shutil

    if path is None:
        path = Path.cwd()

    try:
        stat = shutil.disk_usage(path)

        return {
            "path": str(path),
            "required_bytes": required_bytes,
            "required_human": format_size(required_bytes),
            "free_bytes": stat.free,
            "free_human": format_size(stat.free),
            "sufficient": stat.free >= required_bytes
        }

    except Exception as e:
        return {
            "path": str(path),
            "error": str(e),
            "sufficient": False
        }


def verify_build_dependencies() -> Dict:
    """
    验证构建依赖是否完整

    Returns:
        dict: 依赖检查结果
            - all_available: 是否所有依赖都可用
            - dependencies: 各依赖的可用性
    """
    result = {
        "all_available": True,
        "dependencies": {}
    }

    dependencies = {
        "PyInstaller": "PyInstaller",
        "playwright": "playwright",
        "playwright.sync_api": "playwright.sync_api",
        "requests": "requests",
        "flet": "flet",
        "keyboard": "keyboard"
    }

    for module_name, display_name in dependencies.items():
        try:
            __import__(module_name)
            result["dependencies"][display_name] = {
                "available": True,
                "error": None
            }
        except ImportError as e:
            result["dependencies"][display_name] = {
                "available": False,
                "error": str(e)
            }
            result["all_available"] = False

    return result
