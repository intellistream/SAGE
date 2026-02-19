"""
验证 FlownetEnvironment autostop 参数支持
不实际运行，只验证 API 是否正确

Migrated from RemoteEnvironment → FlownetEnvironment (intellistream/SAGE#1443)
"""

import inspect
import sys
from pathlib import Path

# 添加 SAGE 包路径
repo_root = Path(__file__).parent
src_paths = [
    repo_root / "packages" / "sage" / "src",
    repo_root / "packages" / "sage-common" / "src",
    repo_root / "packages" / "sage-kernel" / "src",
    repo_root / "packages" / "sage-middleware" / "src",
    repo_root / "packages" / "sage-libs" / "src",
    repo_root / "packages" / "sage-tools" / "src",
]
for p in src_paths:
    sys.path.insert(0, str(p))

from sage.kernel.api.flownet_environment import FlownetEnvironment  # noqa: E402


def test_flownet_environment_autostop_signature():
    """验证 FlownetEnvironment.submit() 是否支持 autostop 参数"""
    print("=" * 80)
    print("Test 1: FlownetEnvironment.submit() 方法签名验证")
    print("=" * 80)

    # 获取 submit 方法的签名
    sig = inspect.signature(FlownetEnvironment.submit)
    params = list(sig.parameters.keys())

    print(f"submit() 参数列表: {params}")

    assert "autostop" in params, "FlownetEnvironment.submit() 不支持 autostop 参数"
    print("✅ FlownetEnvironment.submit() 支持 autostop 参数")

    # 获取默认值
    autostop_param = sig.parameters["autostop"]
    print(
        f"   - 参数类型: {autostop_param.annotation if autostop_param.annotation != inspect.Parameter.empty else 'any'}"
    )
    print(f"   - 默认值: {autostop_param.default}")


def test_jobmanager_client_signature():
    """验证 JobManagerClient.submit_job() 是否支持 autostop 参数"""
    print("\n" + "=" * 80)
    print("Test 2: JobManagerClient.submit_job() 方法签名验证")
    print("=" * 80)

    from sage.kernel.runtime.jobmanager_client import JobManagerClient

    sig = inspect.signature(JobManagerClient.submit_job)
    params = list(sig.parameters.keys())

    print(f"submit_job() 参数列表: {params}")

    assert "autostop" in params, "对应的方法不支持 autostop 参数"
    print("✅ JobManagerClient.submit_job() 支持 autostop 参数")

    autostop_param = sig.parameters["autostop"]
    print(
        f"   - 参数类型: {autostop_param.annotation if autostop_param.annotation != inspect.Parameter.empty else 'any'}"
    )
    print(f"   - 默认值: {autostop_param.default}")


def test_jobmanager_signature():
    """验证 JobManager.submit_job() 是否支持 autostop 参数"""
    print("\n" + "=" * 80)
    print("Test 3: JobManager.submit_job() 方法签名验证")
    print("=" * 80)

    from sage.kernel.runtime.job_manager import JobManager

    sig = inspect.signature(JobManager.submit_job)
    params = list(sig.parameters.keys())

    print(f"submit_job() 参数列表: {params}")

    assert "autostop" in params, "对应的方法不支持 autostop 参数"
    print("✅ JobManager.submit_job() 支持 autostop 参数")

    autostop_param = sig.parameters["autostop"]
    print(
        f"   - 参数类型: {autostop_param.annotation if autostop_param.annotation != inspect.Parameter.empty else 'any'}"
    )
    print(f"   - 默认值: {autostop_param.default}")


def test_jobinfo_signature():
    """验证 JobInfo 是否支持 autostop 参数"""
    print("\n" + "=" * 80)
    print("Test 4: JobInfo.__init__() 方法签名验证")
    print("=" * 80)

    from sage.kernel.runtime.job_info import JobInfo

    sig = inspect.signature(JobInfo.__init__)
    params = list(sig.parameters.keys())

    print(f"__init__() 参数列表: {params}")

    assert "autostop" in params, "对应的方法不支持 autostop 参数"
    print("✅ JobInfo.__init__() 支持 autostop 参数")

    autostop_param = sig.parameters["autostop"]
    print(
        f"   - 参数类型: {autostop_param.annotation if autostop_param.annotation != inspect.Parameter.empty else 'any'}"
    )
    print(f"   - 默认值: {autostop_param.default}")


def test_flownet_environment_stop_method_exists():
    """验证 FlownetEnvironment 是否有 stop 和 close 方法（取代旧的 _wait_for_completion）"""
    print("\n" + "=" * 80)
    print("Test 5: FlownetEnvironment.stop() / close() 方法存在性验证")
    print("=" * 80)

    assert hasattr(FlownetEnvironment, "stop"), "FlownetEnvironment 没有 stop() 方法"
    assert hasattr(FlownetEnvironment, "close"), "FlownetEnvironment 没有 close() 方法"
    print("✅ FlownetEnvironment 有 stop() 和 close() 方法")


def main():
    print("\n" + "🔍" * 40)
    print("FlownetEnvironment autostop 功能 API 验证")
    print("🔍" * 40 + "\n")

    results = []

    # 运行所有测试
    results.append(("FlownetEnvironment.submit()", test_flownet_environment_autostop_signature()))
    results.append(("JobManagerClient.submit_job()", test_jobmanager_client_signature()))
    results.append(("JobManager.submit_job()", test_jobmanager_signature()))
    results.append(("JobInfo.__init__()", test_jobinfo_signature()))
    results.append(("FlownetEnvironment.stop()", test_flownet_environment_stop_method_exists()))

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")

    print("\n" + "-" * 80)
    print(f"通过率: {passed}/{total} ({passed * 100 // total}%)")
    print("-" * 80)

    if passed == total:
        print("\n🎉 所有测试通过！autostop 功能已成功添加到 FlownetEnvironment")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，需要检查代码")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
