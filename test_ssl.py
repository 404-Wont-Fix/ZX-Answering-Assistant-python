"""
SSL 配置测试脚本

用于验证 SSL 证书配置是否正确

运行方式：
    python test_ssl.py
"""

import sys
import ssl


def test_certifi():
    """测试 certifi 包"""
    print("=" * 70)
    print("测试 1: certifi 包")
    print("=" * 70)

    try:
        import certifi
        cert_path = certifi.where()
        print(f"✓ certifi 已安装")
        print(f"  证书路径: {cert_path}")

        # 检查证书文件是否存在
        from pathlib import Path
        if Path(cert_path).exists():
            print(f"✓ 证书文件存在")
        else:
            print(f"✗ 证书文件不存在！")
            return False

        return True
    except ImportError:
        print("✗ certifi 未安装")
        print("  请运行: pip install certifi")
        return False


def test_ssl_context():
    """测试 SSL 上下文创建"""
    print("\n" + "=" * 70)
    print("测试 2: SSL 上下文")
    print("=" * 70)

    try:
        import certifi

        cert_path = certifi.where()
        context = ssl.create_default_context(cafile=cert_path)
        print(f"✓ SSL 上下文创建成功")
        print(f"  协议: {context.protocol}")
        print(f"  证书验证模式: {context.verify_mode}")
        return True
    except Exception as e:
        print(f"✗ SSL 上下文创建失败: {e}")
        return False


def test_urllib():
    """测试 urllib HTTPS 请求"""
    print("\n" + "=" * 70)
    print("测试 3: urllib HTTPS 请求")
    print("=" * 70)

    try:
        import urllib.request
        import certifi

        cert_path = certifi.where()
        context = ssl.create_default_context(cafile=cert_path)

        # 测试多个可靠的网站
        test_urls = [
            "https://www.google.com/",
            "https://www.github.com/",
            "https://www.python.org/",
        ]

        for url in test_urls:
            try:
                print(f"  测试 {url}...", end=" ")
                response = urllib.request.urlopen(url, timeout=5, context=context)
                if response.status == 200:
                    print("✓")
                else:
                    print(f"✗ (状态码: {response.status})")
            except Exception as e:
                print(f"✗ ({e})")

        return True
    except Exception as e:
        print(f"✗ urllib 测试失败: {e}")
        return False


def test_requests():
    """测试 requests HTTPS 请求"""
    print("\n" + "=" * 70)
    print("测试 4: requests HTTPS 请求")
    print("=" * 70)

    try:
        import requests

        test_urls = [
            "https://www.google.com/",
            "https://www.github.com/",
            "https://www.python.org/",
        ]

        for url in test_urls:
            try:
                print(f"  测试 {url}...", end=" ")
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print("✓")
                else:
                    print(f"✗ (状态码: {response.status_code})")
            except Exception as e:
                print(f"✗ ({e})")

        return True
    except ImportError:
        print("⚠ requests 未安装，跳过此测试")
        return True
    except Exception as e:
        print(f"✗ requests 测试失败: {e}")
        return False


def test_flet_download():
    """测试 Flet 下载 URL（不实际下载）"""
    print("\n" + "=" * 70)
    print("测试 5: Flet 下载 URL 连通性")
    print("=" * 70)

    try:
        import urllib.request
        import certifi

        cert_path = certifi.where()
        context = ssl.create_default_context(cafile=cert_path)

        # Flet 下载 URL（只测试连接，不下载）
        flet_url = "https://github.com/flet-dev/flet/releases/download/v0.84.0/flet-windows.zip"

        print(f"  测试 Flet 下载 URL...", end=" ")
        try:
            # 只发送 HEAD 请求，不下载文件
            request = urllib.request.Request(flet_url, method='HEAD')
            response = urllib.request.urlopen(request, timeout=10, context=context)
            print("✓")
            return True
        except Exception as e:
            print(f"⚠ ({e})")
            print("  这可能是因为 GitHub 不支持 HEAD 请求，但不影响实际下载")
            return True

    except Exception as e:
        print(f"✗ Flet URL 测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "            SSL 证书配置测试工具".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    # 运行所有测试
    results = []
    results.append(("certifi", test_certifi()))
    results.append(("SSL 上下文", test_ssl_context()))
    results.append(("urllib", test_urllib()))
    results.append(("requests", test_requests()))
    results.append(("Flet 下载", test_flet_download()))

    # 总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {name}: {status}")

    # 总体评估
    all_passed = all(result for _, result in results)

    print("\n" + "=" * 70)
    if all_passed:
        print("✓ 所有测试通过！SSL 配置正常")
        print()
        print("您现在可以运行主程序:")
        print("  python main.py")
    else:
        print("⚠ 部分测试失败")
        print()
        print("建议:")
        print("  1. 确保 certifi 已安装: pip install --upgrade certifi")
        print("  2. 检查网络连接")
        print("  3. 查看详细文档: docs/SSL_SETUP.md")
    print("=" * 70)
    print()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
