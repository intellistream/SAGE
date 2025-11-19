#!/usr/bin/env python3
"""验证关键依赖的版本兼容性

这个脚本检查 SAGE 项目中关键依赖包的版本兼容性，特别是：
- torch 和 vllm 的版本兼容性
- Python 版本要求
- CUDA 版本（如果需要）

用法:
    python tools/install/verify_dependencies.py
    python tools/install/verify_dependencies.py --verbose
"""

import sys
import warnings
from typing import Optional

try:
    from packaging import version
except ImportError:
    print("⚠️  packaging 模块未安装，正在尝试安装...")
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "packaging"])
    from packaging import version


def get_version_safe(module_name: str) -> Optional[str]:
    """安全地获取模块版本，如果模块不存在返回 None"""
    try:
        module = __import__(module_name)
        return getattr(module, "__version__", None)
    except ImportError:
        return None
    except Exception as e:
        warnings.warn(f"获取 {module_name} 版本时出错: {e}", stacklevel=2)
        return None


def verify_torch_vllm_compatibility() -> tuple[bool, str]:
    """验证 torch 和 vllm 的版本兼容性

    Returns:
        (is_compatible, message): 兼容性状态和说明信息
    """
    torch_ver_str = get_version_safe("torch")
    vllm_ver_str = get_version_safe("vllm")

    # 如果 vllm 未安装，这是可选依赖，不报错
    if vllm_ver_str is None:
        return True, "⚠️  vLLM 未安装（可选依赖）"

    # 如果 torch 未安装但 vllm 已安装，这是一个问题
    if torch_ver_str is None:
        return False, "❌ vLLM 已安装但 torch 未安装"

    # 解析版本（移除 +cpu, +cu118 等后缀）
    torch_ver = version.parse(torch_ver_str.split("+")[0])
    vllm_ver = version.parse(vllm_ver_str.split("+")[0])

    # 定义版本兼容性规则
    compatibility_rules = [
        {
            "vllm_min": version.parse("0.11.0"),
            "vllm_max": version.parse("0.12.0"),
            "torch_min": version.parse("2.5.0"),
            "description": "vLLM 0.11.x 需要 torch >= 2.5.0",
        },
        {
            "vllm_min": version.parse("0.10.0"),
            "vllm_max": version.parse("0.11.0"),
            "torch_min": version.parse("2.4.0"),
            "description": "vLLM 0.10.x 需要 torch >= 2.4.0 (需要 torch._inductor.config)",
        },
        {
            "vllm_min": version.parse("0.9.0"),
            "vllm_max": version.parse("0.10.0"),
            "torch_min": version.parse("2.3.0"),
            "description": "vLLM 0.9.x 需要 torch >= 2.3.0",
        },
        {
            "vllm_min": version.parse("0.4.0"),
            "vllm_max": version.parse("0.9.0"),
            "torch_min": version.parse("2.2.0"),
            "description": "vLLM 0.4.x-0.8.x 需要 torch >= 2.2.0",
        },
    ]

    # 检查兼容性
    for rule in compatibility_rules:
        if rule["vllm_min"] <= vllm_ver < rule["vllm_max"]:
            if torch_ver < rule["torch_min"]:
                msg = (
                    f"❌ 版本不兼容:\n"
                    f"   vLLM: {vllm_ver_str}\n"
                    f"   Torch: {torch_ver_str}\n"
                    f"   要求: {rule['description']}\n"
                    f"\n修复方法:\n"
                    f"   pip uninstall -y torch torchaudio torchvision vllm\n"
                    f"   pip install vllm=={vllm_ver_str.split('+')[0]}"
                )
                return False, msg
            else:
                msg = (
                    f"✅ 版本兼容:\n"
                    f"   vLLM: {vllm_ver_str}\n"
                    f"   Torch: {torch_ver_str}\n"
                    f"   满足: {rule['description']}"
                )
                return True, msg

    # 如果没有匹配的规则，给出警告
    msg = (
        f"⚠️  未知的 vLLM 版本:\n"
        f"   vLLM: {vllm_ver_str}\n"
        f"   Torch: {torch_ver_str}\n"
        f"   请验证兼容性: https://docs.vllm.ai/"
    )
    return True, msg


def verify_torch_inductor() -> tuple[bool, str]:
    """验证 torch._inductor.config 是否可用（vLLM 0.10+ 需要）

    Returns:
        (is_available, message): 可用性状态和说明信息
    """
    vllm_ver_str = get_version_safe("vllm")

    # 如果 vllm 未安装或版本 < 0.10，不需要检查
    if vllm_ver_str is None:
        return True, "vLLM 未安装，跳过检查"

    vllm_ver = version.parse(vllm_ver_str.split("+")[0])
    if vllm_ver < version.parse("0.10.0"):
        return True, f"vLLM {vllm_ver_str} < 0.10.0，不需要 torch._inductor.config"

    # 检查 torch._inductor.config 是否存在
    try:
        import torch._inductor.config  # noqa: F401

        msg = f"✅ torch._inductor.config 可用（vLLM {vllm_ver_str} 需要）"
        return True, msg
    except (ImportError, AttributeError) as e:
        msg = (
            f"❌ torch._inductor.config 不可用:\n"
            f"   vLLM {vllm_ver_str} 需要 torch >= 2.4.0\n"
            f"   错误: {e}\n"
            f"\n修复方法:\n"
            f"   pip uninstall -y torch torchaudio torchvision\n"
            f"   pip install torch>=2.4.0"
        )
        return False, msg


def verify_python_version() -> tuple[bool, str]:
    """验证 Python 版本是否满足要求

    Returns:
        (is_compatible, message): 兼容性状态和说明信息
    """
    current_version = version.parse(
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )
    min_version = version.parse("3.9.0")

    if current_version < min_version:
        msg = (
            f"❌ Python 版本过低:\n"
            f"   当前版本: {sys.version}\n"
            f"   最低要求: Python {min_version}\n"
            f"\n请升级 Python 版本"
        )
        return False, msg

    msg = f"✅ Python 版本满足要求: {sys.version.split()[0]}"
    return True, msg


def main(verbose: bool = False):
    """主函数：运行所有验证检查"""
    print("🔍 SAGE 依赖版本兼容性检查")
    print("=" * 60)

    checks = [
        ("Python 版本", verify_python_version),
        ("Torch & vLLM 兼容性", verify_torch_vllm_compatibility),
        ("torch._inductor.config", verify_torch_inductor),
    ]

    all_passed = True
    results = []

    for check_name, check_func in checks:
        print(f"\n检查: {check_name}")
        print("-" * 60)
        try:
            passed, message = check_func()
            results.append((check_name, passed, message))
            print(message)
            if not passed:
                all_passed = False
        except Exception as e:
            results.append((check_name, False, f"检查失败: {e}"))
            print(f"❌ 检查失败: {e}")
            all_passed = False
            if verbose:
                import traceback

                traceback.print_exc()

    # 打印总结
    print("\n" + "=" * 60)
    print("📊 检查总结")
    print("=" * 60)

    for check_name, passed, _ in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {check_name}")

    print("=" * 60)

    if all_passed:
        print("✅ 所有检查通过！")
        return 0
    else:
        print("❌ 存在依赖版本问题，请查看上面的错误信息并修复")
        print("\n💡 提示: 运行以下命令获取详细帮助:")
        print("   cat docs/dev-notes/l0-infra/vllm-torch-version-conflict.md")
        return 1


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    sys.exit(main(verbose=verbose))
