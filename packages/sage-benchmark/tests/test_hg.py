"""
测试 Hugging Face 官方和镜像站点的连通性
Test connectivity to Hugging Face official site and mirror sites
"""

import pytest
import requests


class TestHuggingFaceConnectivity:
    """测试 Hugging Face 连通性"""

    @pytest.mark.parametrize(
        "site_name,base_url",
        [
            ("HuggingFace Official", "https://huggingface.co"),
            ("HF Mirror (hf-mirror.com)", "https://hf-mirror.com"),
        ],
    )
    def test_site_connectivity(self, site_name, base_url):
        """
        测试站点是否可访问（始终通过，只记录结果）
        Test if the site is accessible (always pass, just record results)
        """
        print(f"\n正在测试 {site_name}: {base_url}")

        try:
            response = requests.get(base_url, timeout=10)
            print(f"  状态码: {response.status_code}")
            print(f"  响应时间: {response.elapsed.total_seconds():.2f}秒")

            if response.status_code == 200:
                print(f"  ✓ {site_name} 连接成功")
                return True
            else:
                print(f"  ⚠ {site_name} 返回状态码 {response.status_code}")
                return False

        except requests.exceptions.Timeout:
            print(f"  ⚠ {site_name} 连接超时 (>10秒)")
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"  ⚠ {site_name} 连接失败: 网络不可达")
            return False
        except Exception as e:
            print(f"  ⚠ {site_name} 发生错误: {type(e).__name__}")
            return False

    @pytest.mark.parametrize(
        "site_name,base_url,repo_id,filename",
        [
            (
                "HuggingFace Official",
                "https://huggingface.co",
                "bert-base-uncased",
                "config.json",
            ),
            (
                "HF Mirror",
                "https://hf-mirror.com",
                "bert-base-uncased",
                "config.json",
            ),
        ],
    )
    def test_model_file_accessibility(self, site_name, base_url, repo_id, filename):
        """
        测试热门模型文件是否可访问（始终通过，只记录结果）
        使用 bert-base-uncased 作为测试（下载量最高的模型之一）
        Test if popular model files are accessible (always pass, just record results)
        Using bert-base-uncased as test (one of the most downloaded models)
        """
        # 构建模型文件的 URL
        file_url = f"{base_url}/{repo_id}/resolve/main/{filename}"
        print(f"\n正在测试 {site_name} 模型文件访问")
        print(f"  模型: {repo_id}")
        print(f"  URL: {file_url}")

        try:
            # 使用 HEAD 请求只获取头信息，不下载整个文件
            response = requests.head(file_url, timeout=10, allow_redirects=True)
            print(f"  状态码: {response.status_code}")
            print(f"  响应时间: {response.elapsed.total_seconds():.2f}秒")

            if "content-length" in response.headers:
                size_kb = int(response.headers["content-length"]) / 1024
                print(f"  文件大小: {size_kb:.2f} KB")

            if response.status_code == 200:
                print(f"  ✓ {site_name} 模型文件可访问")
                return True
            else:
                print(f"  ⚠ {site_name} 模型文件返回状态码 {response.status_code}")
                return False

        except requests.exceptions.Timeout:
            print(f"  ⚠ {site_name} 模型文件访问超时 (>10秒)")
            return False
        except requests.exceptions.ConnectionError as e:
            print(f"  ⚠ {site_name} 模型文件访问失败: 网络不可达")
            return False
        except Exception as e:
            print(f"  ⚠ {site_name} 模型文件访问错误: {type(e).__name__}")
            return False

    def test_connectivity_summary(self):
        """
        综合连通性测试并给出结论（始终通过）
        Comprehensive connectivity test with conclusions (always pass)
        """
        print("\n" + "=" * 60)
        print("Hugging Face 连通性综合测试")
        print("=" * 60)

        sites = [
            ("HuggingFace Official", "https://huggingface.co"),
            ("HF Mirror", "https://hf-mirror.com"),
        ]

        results = {}

        # 测试基本连通性
        print("\n[1] 基本站点连通性测试")
        print("-" * 60)
        for site_name, base_url in sites:
            print(f"\n测试 {site_name}...")
            try:
                response = requests.get(base_url, timeout=10)
                accessible = response.status_code == 200
                response_time = response.elapsed.total_seconds()

                results[site_name] = {
                    "site_accessible": accessible,
                    "site_response_time": response_time,
                }

                if accessible:
                    print(f"  ✓ 可访问 (响应时间: {response_time:.2f}秒)")
                else:
                    print(f"  ⚠ 不可访问 (状态码: {response.status_code})")

            except Exception as e:
                results[site_name] = {
                    "site_accessible": False,
                    "site_error": type(e).__name__,
                }
                print(f"  ⚠ 连接失败: {type(e).__name__}")

        # 测试模型文件访问
        print("\n[2] 模型文件访问测试 (bert-base-uncased)")
        print("-" * 60)
        for site_name, base_url in sites:
            print(f"\n测试 {site_name}...")
            file_url = f"{base_url}/bert-base-uncased/resolve/main/config.json"

            try:
                response = requests.head(file_url, timeout=10, allow_redirects=True)
                accessible = response.status_code == 200
                response_time = response.elapsed.total_seconds()

                results[site_name]["file_accessible"] = accessible
                results[site_name]["file_response_time"] = response_time

                if accessible:
                    print(f"  ✓ 可访问 (响应时间: {response_time:.2f}秒)")
                else:
                    print(f"  ⚠ 不可访问 (状态码: {response.status_code})")

            except Exception as e:
                results[site_name]["file_accessible"] = False
                results[site_name]["file_error"] = type(e).__name__
                print(f"  ⚠ 访问失败: {type(e).__name__}")

        # 输出结论
        print("\n" + "=" * 60)
        print("测试结论")
        print("=" * 60)

        for site_name, result in results.items():
            print(f"\n{site_name}:")
            print(
                f"  站点连通性: {'✓ 可用' if result.get('site_accessible') else '✗ 不可用'}"
            )
            print(
                f"  文件访问性: {'✓ 可用' if result.get('file_accessible') else '✗ 不可用'}"
            )

            if result.get("site_accessible") and result.get("file_accessible"):
                print(f"  综合评价: ✓ 完全可用")
            elif result.get("site_accessible") or result.get("file_accessible"):
                print(f"  综合评价: ⚠ 部分可用")
            else:
                print(f"  综合评价: ✗ 不可用")

        # 给出推荐结论
        print("\n" + "=" * 60)
        print("推荐结论")
        print("=" * 60)

        official_ok = results.get("HuggingFace Official", {}).get(
            "site_accessible", False
        ) and results.get("HuggingFace Official", {}).get("file_accessible", False)
        mirror_ok = results.get("HF Mirror", {}).get(
            "site_accessible", False
        ) and results.get("HF Mirror", {}).get("file_accessible", False)

        if official_ok and mirror_ok:
            print("✓ 官方站点和镜像站点均可用")
            print("  推荐: 可以使用任一站点，建议优先使用镜像站点以获得更好的速度")
        elif mirror_ok:
            print("✓ 镜像站点可用，官方站点不可用")
            print("  推荐: 使用镜像站点 (https://hf-mirror.com)")
            print("  原因: 可能由于网络限制无法访问官方站点")
        elif official_ok:
            print("✓ 官方站点可用，镜像站点不可用")
            print("  推荐: 使用官方站点 (https://huggingface.co)")
        else:
            print("⚠ 所有站点均不可用")
            print("  建议: 检查网络连接或尝试其他镜像站点")

        print("=" * 60)

        # 测试始终通过
        assert True, "连通性测试完成"


if __name__ == "__main__":
    # 直接运行测试
    import sys

    print("开始测试 Hugging Face 连通性...")
    print("=" * 60)

    test = TestHuggingFaceConnectivity()

    # 运行综合测试
    try:
        test.test_connectivity_summary()
        print("\n✓ 测试完成")
    except Exception as e:
        print(f"\n⚠ 测试过程出现异常: {e}")
        print("✓ 测试完成（含警告）")
