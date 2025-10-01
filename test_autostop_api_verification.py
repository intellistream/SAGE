"""
简单验证 RemoteEnvironment autostop 参数支持
不实际运行，只验证 API 是否正确
"""
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

from sage.core.api.remote_environment import RemoteEnvironment
from sage.core.api.function.batch_function import BatchFunction
from sage.core.api.function.sink_function import SinkFunction
from sage.core.api.service.base_service import BaseService
import inspect


def test_remote_environment_autostop_signature():
    """验证 RemoteEnvironment.submit() 是否支持 autostop 参数"""
    print("=" * 80)
    print("Test 1: RemoteEnvironment.submit() 方法签名验证")
    print("=" * 80)
    
    # 获取 submit 方法的签名
    sig = inspect.signature(RemoteEnvironment.submit)
    params = list(sig.parameters.keys())
    
    print(f"submit() 参数列表: {params}")
    
    if 'autostop' in params:
        print("✅ RemoteEnvironment.submit() 支持 autostop 参数")
        
        # 获取默认值
        autostop_param = sig.parameters['autostop']
        print(f"   - 参数类型: {autostop_param.annotation if autostop_param.annotation != inspect.Parameter.empty else 'any'}")
        print(f"   - 默认值: {autostop_param.default}")
        return True
    else:
        print("❌ RemoteEnvironment.submit() 不支持 autostop 参数")
        return False


def test_jobmanager_client_signature():
    """验证 JobManagerClient.submit_job() 是否支持 autostop 参数"""
    print("\n" + "=" * 80)
    print("Test 2: JobManagerClient.submit_job() 方法签名验证")
    print("=" * 80)
    
    from sage.kernel.jobmanager.jobmanager_client import JobManagerClient
    
    sig = inspect.signature(JobManagerClient.submit_job)
    params = list(sig.parameters.keys())
    
    print(f"submit_job() 参数列表: {params}")
    
    if 'autostop' in params:
        print("✅ JobManagerClient.submit_job() 支持 autostop 参数")
        
        autostop_param = sig.parameters['autostop']
        print(f"   - 参数类型: {autostop_param.annotation if autostop_param.annotation != inspect.Parameter.empty else 'any'}")
        print(f"   - 默认值: {autostop_param.default}")
        return True
    else:
        print("❌ JobManagerClient.submit_job() 不支持 autostop 参数")
        return False


def test_jobmanager_signature():
    """验证 JobManager.submit_job() 是否支持 autostop 参数"""
    print("\n" + "=" * 80)
    print("Test 3: JobManager.submit_job() 方法签名验证")
    print("=" * 80)
    
    from sage.kernel.jobmanager.job_manager import JobManager
    
    sig = inspect.signature(JobManager.submit_job)
    params = list(sig.parameters.keys())
    
    print(f"submit_job() 参数列表: {params}")
    
    if 'autostop' in params:
        print("✅ JobManager.submit_job() 支持 autostop 参数")
        
        autostop_param = sig.parameters['autostop']
        print(f"   - 参数类型: {autostop_param.annotation if autostop_param.annotation != inspect.Parameter.empty else 'any'}")
        print(f"   - 默认值: {autostop_param.default}")
        return True
    else:
        print("❌ JobManager.submit_job() 不支持 autostop 参数")
        return False


def test_jobinfo_signature():
    """验证 JobInfo 是否支持 autostop 参数"""
    print("\n" + "=" * 80)
    print("Test 4: JobInfo.__init__() 方法签名验证")
    print("=" * 80)
    
    from sage.kernel.jobmanager.job_info import JobInfo
    
    sig = inspect.signature(JobInfo.__init__)
    params = list(sig.parameters.keys())
    
    print(f"__init__() 参数列表: {params}")
    
    if 'autostop' in params:
        print("✅ JobInfo.__init__() 支持 autostop 参数")
        
        autostop_param = sig.parameters['autostop']
        print(f"   - 参数类型: {autostop_param.annotation if autostop_param.annotation != inspect.Parameter.empty else 'any'}")
        print(f"   - 默认值: {autostop_param.default}")
        return True
    else:
        print("❌ JobInfo.__init__() 不支持 autostop 参数")
        return False


def test_wait_for_completion_exists():
    """验证 RemoteEnvironment 是否有 _wait_for_completion 方法"""
    print("\n" + "=" * 80)
    print("Test 5: RemoteEnvironment._wait_for_completion() 方法存在性验证")
    print("=" * 80)
    
    if hasattr(RemoteEnvironment, '_wait_for_completion'):
        print("✅ RemoteEnvironment 有 _wait_for_completion() 方法")
        return True
    else:
        print("❌ RemoteEnvironment 没有 _wait_for_completion() 方法")
        return False


def main():
    print("\n" + "🔍" * 40)
    print("RemoteEnvironment autostop 功能 API 验证")
    print("🔍" * 40 + "\n")
    
    results = []
    
    # 运行所有测试
    results.append(("RemoteEnvironment.submit()", test_remote_environment_autostop_signature()))
    results.append(("JobManagerClient.submit_job()", test_jobmanager_client_signature()))
    results.append(("JobManager.submit_job()", test_jobmanager_signature()))
    results.append(("JobInfo.__init__()", test_jobinfo_signature()))
    results.append(("RemoteEnvironment._wait_for_completion()", test_wait_for_completion_exists()))
    
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
    print(f"通过率: {passed}/{total} ({passed*100//total}%)")
    print("-" * 80)
    
    if passed == total:
        print("\n🎉 所有测试通过！autostop 功能已成功添加到 RemoteEnvironment")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，需要检查代码")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
