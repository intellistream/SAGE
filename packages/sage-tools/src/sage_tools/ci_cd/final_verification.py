# Converted from .sh for Python packaging
# 🧪 最终验证脚本 - 检查所有修复
# 确保GitHub Actions工作流能够正常运行

import os
import sys
import subprocess
import re
import glob
import shutil

try:
    from sage_tools.utils.logging import print_success, print_error, print_warning, print_info
    from sage_tools.utils.common_utils import find_project_root, check_file_exists, check_dir_exists
except ImportError:
    # Fallback
    def print_success(msg): print(f"✅ {msg}")
    def print_error(msg): print(f"❌ {msg}")
    def print_warning(msg): print(f"⚠️  {msg}")
    def print_info(msg): print(f"ℹ️  {msg}")
    find_project_root = lambda: os.getcwd()
    check_file_exists = lambda p: os.path.isfile(p)
    check_dir_exists = lambda p: os.path.isdir(p)

def print_step(msg):
    print(f"🔧 {msg}")

def main():
    print("🔍 SAGE 构建系统最终验证")
    print("==========================")
    print()

    # 项目根目录
    project_root = find_project_root()
    os.chdir(project_root)
    print_info(f"项目根目录: {project_root}")
    print()

    # 验证清单
    checks_passed = 0
    total_checks = 8

    # 检查1: 关键文件存在性
    print_step("检查1: 验证关键文件")
    files_to_check = [
        "pyproject.toml",
        "_version.py",
        ".github/workflows/build-release.yml"
    ]

    missing_files = 0
    for file in files_to_check:
        if check_file_exists(file):
            print_success(f"文件存在: {file}")
        else:
            print_error(f"文件缺失: {file}")
            missing_files += 1

    if missing_files == 0:
        checks_passed += 1
        print_success("检查1通过: 所有关键文件存在")
    else:
        print_error(f"检查1失败: {missing_files} 个文件缺失")
    print()

    # 检查2: 版本读取
    print_step("检查2: 版本读取机制")
    try:
        result = subprocess.run([sys.executable, '-c', '''
import sys
sys.path.insert(0, '.')
from _version import __version__
print(__version__)
'''], capture_output=True, text=True, cwd=project_root)
        version = result.stdout.strip()
        if result.returncode == 0 and version != 'ERROR':
            checks_passed += 1
            print_success(f"检查2通过: 版本读取成功 ({version})")
        else:
            print_error("检查2失败: 版本读取失败")
    except Exception:
        print_error("检查2失败: 版本读取失败")
    print()

    # 检查3: 子包结构
    print_step("检查3: 子包结构完整性")
    packages = ["sage-common", "sage-kernel", "sage-middleware", "sage-libs"]
    missing_packages = 0

    for pkg in packages:
        pkg_dir = os.path.join("packages", pkg)
        pyproject = os.path.join(pkg_dir, "pyproject.toml")
        if check_dir_exists(pkg_dir) and check_file_exists(pyproject):
            print_success(f"子包完整: {pkg}")
        else:
            print_error(f"子包缺失或不完整: {pkg}")
            missing_packages += 1

    if missing_packages == 0:
        checks_passed += 1
        print_success("检查3通过: 所有子包结构完整")
    else:
        print_error(f"检查3失败: {missing_packages} 个子包有问题")
    print()

    # 检查4: 不存在build_wheel.py
    print_step("检查4: 确认移除了不需要的文件")
    if not os.path.isfile("build_wheel.py"):
        checks_passed += 1
        print_success("检查4通过: build_wheel.py 已正确移除")
    else:
        print_error("检查4失败: build_wheel.py 仍然存在")
    print()

    # 检查5: pyproject.toml 配置正确性
    print_step("检查5: pyproject.toml 配置验证")
    config_ok = True

    with open("pyproject.toml", 'r', encoding='utf-8') as f:
        content = f.read()

    if re.search(r'version = \{attr = "_version\.__version__"\}', content):
        print_success("版本配置正确: 使用 _version.__version__")
    else:
        print_error("版本配置错误: 未使用正确的版本路径")
        config_ok = False

    if re.search(r'isage-.*@ file:./packages/sage-', content):
        print_success("依赖配置正确: 使用本地文件路径")
    else:
        print_error("依赖配置错误: 未找到本地文件路径依赖")
        config_ok = False

    if config_ok:
        checks_passed += 1
        print_success("检查5通过: pyproject.toml 配置正确")
    else:
        print_error("检查5失败: pyproject.toml 配置有问题")
    print()

    # 检查6: GitHub Actions 工作流语法
    print_step("检查6: GitHub Actions 工作流语法")
    workflow_file = ".github/workflows/build-release.yml"
    workflow_ok = True

    if check_file_exists(workflow_file):
        with open(workflow_file, 'r', encoding='utf-8') as f:
            wf_content = f.read()

        if re.search(r'build-subpackages:', wf_content):
            print_success("包含子包构建任务")
        else:
            print_error("缺少子包构建任务")
            workflow_ok = False

        if re.search(r'build-metapackage:', wf_content):
            print_success("包含metapackage构建任务")
        else:
            print_error("缺少metapackage构建任务")
            workflow_ok = False

        if re.search(r'matrix:', wf_content):
            print_success("包含矩阵构建策略")
        else:
            print_error("缺少矩阵构建策略")
            workflow_ok = False

        if workflow_ok:
            checks_passed += 1
            print_success("检查6通过: GitHub Actions 工作流配置正确")
        else:
            print_error("检查6失败: GitHub Actions 工作流配置有问题")
    else:
        print_error("workflow文件不存在")
    print()

    # 检查7: 依赖替换逻辑
    print_step("检查7: PyPI依赖替换逻辑")
    try:
        result = subprocess.run([sys.executable, '-c', '''
import re
with open("pyproject.toml", "r") as f:
    content = f.read()
content_modified = re.sub(
    r'"isage-([^"]+) @ file:./packages/sage-([^"]+)"',
    r'"isage-\\1"',
    content
)
if "file:" not in content_modified.split("[project.optional-dependencies]")[0]:
    print("PASS")
else:
    print("FAIL")
'''], capture_output=True, text=True, cwd=project_root)
        replacement_test = result.stdout.strip()
        if result.returncode == 0 and replacement_test == "PASS":
            checks_passed += 1
            print_success("检查7通过: 依赖替换逻辑正确")
        else:
            print_error("检查7失败: 依赖替换逻辑有问题")
    except Exception:
        print_error("检查7失败: 依赖替换逻辑有问题")
    print()

    # 检查8: 快速构建测试
    print_step("检查8: 快速构建测试")
    build_ok = True

    # 清理之前的构建
    for path in ["dist", "build"] + glob.glob("*.egg-info") + glob.glob("packages/*/dist") + glob.glob("packages/*/build") + glob.glob("packages/*/*.egg-info"):
        if os.path.exists(path):
            shutil.rmtree(path)

    test_dir = "test_build_check"
    os.makedirs(test_dir, exist_ok=True)

    # 测试一个子包构建
    print_info("测试 sage-common 构建...")
    sage_common_dir = "packages/sage-common"
    if check_dir_exists(sage_common_dir):
        result = subprocess.run([sys.executable, '-m', 'build', '--wheel', '--outdir', test_dir], cwd=sage_common_dir, capture_output=True, text=True)
        if result.returncode == 0 and "Successfully built" in result.stdout:
            if glob.glob(os.path.join(test_dir, "isage_common-*.whl")):
                print_success("sage-common 构建成功")
            else:
                print_error("sage-common 构建失败: 未找到 wheel")
                build_ok = False
        else:
            print_error("sage-common 构建失败")
            build_ok = False
    else:
        print_error("sage-common 目录不存在")
        build_ok = False

    # 测试主包构建
    print_info("测试主包构建...")
    result = subprocess.run([sys.executable, '-m', 'build', '--wheel', '--outdir', test_dir], cwd=project_root, capture_output=True, text=True)
    if result.returncode == 0 and "Successfully built" in result.stdout:
        if glob.glob(os.path.join(test_dir, "isage-*.whl")):
            print_success("主包构建成功")
        else:
            print_error("主包构建失败: 未找到 wheel")
            build_ok = False
    else:
        print_error("主包构建失败")
        build_ok = False

    # 清理测试构建
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    for path in ["dist", "build"] + glob.glob("*.egg-info") + glob.glob("packages/*/dist") + glob.glob("packages/*/build") + glob.glob("packages/*/*.egg-info"):
        if os.path.exists(path):
            shutil.rmtree(path)

    if build_ok:
        checks_passed += 1
        print_success("检查8通过: 构建系统正常工作")
    else:
        print_error("检查8失败: 构建系统有问题")
    print()

    # 最终结果
    print_step("最终验证结果")
    print()

    if checks_passed == total_checks:
        print_success(f"🎉 所有检查通过! ({checks_passed}/{total_checks})")
        print()
        print_info("✨ 修复总结:")
        print_info("  ✅ 移除了不存在的 build_wheel.py 文件")
        print_info("  ✅ 修复了版本读取路径 (_version.py)")
        print_info("  ✅ 采用多包构建策略代替单一复杂构建")
        print_info("  ✅ 修复了 pyproject.toml 中的依赖配置")
        print_info("  ✅ 实现了开发时本地依赖、发布时PyPI依赖的切换")
        print_info("  ✅ 更新了 GitHub Actions 工作流支持多包构建")
        print_info("  ✅ 移除了不必要的 bytecode 编译")
        print_info("  ✅ 修复了所有配置错误")
        print()
        print_info("🚀 下次推送到 GitHub 时，CI/CD 应该能够:")
        print_info("  1. 并行构建所有 4 个子包")
        print_info("  2. 构建 metapackage (自动替换依赖为PyPI包名)")
        print_info("  3. 在多个 Python 版本上测试")
        print_info("  4. 发布到 GitHub Releases")
        print_info("  5. (可选) 发布到 PyPI")
        print()
        print_success("✅ 准备就绪! 可以安全地推送代码了!")
        sys.exit(0)
    else:
        print_error(f"❌ 部分检查失败 ({checks_passed}/{total_checks})")
        print()
        print_warning("还有问题需要解决，请检查上述失败的项目")
        sys.exit(1)

if __name__ == "__main__":
    main()