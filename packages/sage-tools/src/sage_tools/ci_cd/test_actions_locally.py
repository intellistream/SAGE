# Converted from .sh for Python packaging
# 🧪 本地测试GitHub Actions工作流
# 这个脚本模拟GitHub Actions环境，测试我们的CI/CD配置

import os
import sys
import subprocess
import tomllib
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
    print("🚀 SAGE GitHub Actions 本地测试")
    print("==================================")
    print()

    # 项目根目录
    project_root = find_project_root()
    os.chdir(project_root)
    print(f"📁 项目根目录: {project_root}")
    print()

    # 测试1: 基础依赖安装
    print_step("测试1: 基础依赖安装")
    print_info("模拟: Install build dependencies")

    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'build', 'setuptools', 'wheel', 'tomli'], 
                       check=True, capture_output=True)
        print_success("基础依赖安装成功")
    except subprocess.CalledProcessError:
        print_error("基础依赖安装失败")
        sys.exit(1)
    print()

    # 测试2: 版本提取
    print_step("测试2: 版本提取测试")
    print_info("模拟: Get version step")

    try:
        with open('pyproject.toml', 'rb') as f:
            data = tomllib.load(f)
        version = data.get('project', {}).get('version', '0.1.0')
        if version != '0.1.0':
            print_success(f"版本提取成功: {version}")
        else:
            print_warning(f"使用默认版本: {version}")
    except Exception as e:
        print_error(f"版本提取失败: {e}")
        sys.exit(1)
    print()

    # 测试3: 依赖解析
    print_step("测试3: 依赖解析测试")
    print_info("检查 file: 路径依赖是否会在CI中造成问题")

    try:
        with open('pyproject.toml', 'rb') as f:
            data = tomllib.load(f)
        deps = data.get('project', {}).get('dependencies', [])
        file_deps = [dep for dep in deps if 'file:' in dep]
        if file_deps:
            print("⚠️  发现 file: 路径依赖（在GitHub Actions中可能有问题）:")
            for dep in file_deps:
                print(f'   - {dep}')
            print()
            print('💡 建议解决方案：')
            print('   1. 在CI中使用 pip install -e packages/package-name')
            print('   2. 或者修改CI脚本直接安装子包')
        else:
            print('✅ 没有发现 file: 路径依赖')
        print_warning("依赖分析完成（存在潜在CI问题）")
    except Exception as e:
        print_error(f"依赖分析失败: {e}")
    print()

    # 测试4: 模拟quickstart.sh安装（快速模式）
    print_step("测试4: 模拟快速安装流程")
    print_info("模拟: ./quickstart.sh --quick")

    quickstart_path = './quickstart.sh'
    if check_file_exists(quickstart_path) and os.access(quickstart_path, os.X_OK):
        print_info("检测到quickstart.sh，测试快速安装逻辑...")
        print("   → 检查Python环境")
        try:
            result = subprocess.run([sys.executable, '--version'], capture_output=True, text=True)
            python_version = result.stdout.strip().split() [1]
            print_success(f"Python检查: {python_version}")
        except:
            print_error("Python3未找到")
            sys.exit(1)
        
        print("   → 检查pip")
        try:
            subprocess.run([sys.executable, '-m', 'pip', '--version'], check=True, capture_output=True)
            print_success("pip检查通过")
        except:
            print_error("pip未找到")
            sys.exit(1)
        
        print("   → 检查pyproject.toml")
        if check_file_exists("pyproject.toml"):
            print_success("pyproject.toml存在")
        else:
            print_error("pyproject.toml不存在")
            sys.exit(1)
        
        print_success("快速安装模拟成功")
    else:
        print_warning("quickstart.sh不存在或不可执行")
    print()

    # 测试5: CI环境变量模拟
    print_step("测试5: CI环境变量模拟")
    print_info("模拟GitHub Actions环境变量")

    os.environ['CI'] = 'true'
    os.environ['GITHUB_ACTIONS'] = 'true'
    os.environ['GITHUB_WORKSPACE'] = project_root

    print("   设置环境变量:")
    print("   - CI=true")
    print("   - GITHUB_ACTIONS=true")  
    print(f"   - GITHUB_WORKSPACE={project_root}")

    if os.environ.get('CI') == 'true' and os.environ.get('GITHUB_ACTIONS') == 'true':
        print_success("CI环境变量设置成功")
    else:
        print_error("CI环境变量设置失败")
    print()

    # 测试6: 子包结构检查
    print_step("测试6: 子包结构检查")
    print_info("检查SAGE子包结构")

    packages_dir = "packages"
    if check_dir_exists(packages_dir):
        print("   发现的子包:")
        for pkg_dir in glob.glob(os.path.join(packages_dir, '*')):
            if os.path.isdir(pkg_dir):
                pkg_name = os.path.basename(pkg_dir)
                pyproject = os.path.join(pkg_dir, 'pyproject.toml')
                if check_file_exists(pyproject):
                    print_success(f"   - {pkg_name} (有pyproject.toml)")
                else:
                    print_warning(f"   - {pkg_name} (缺少pyproject.toml)")
        print_success("子包结构检查完成")
    else:
        print_error("packages目录不存在")
        sys.exit(1)
    print()

    # 测试7: GitHub Actions workflow语法检查
    print_step("测试7: GitHub Actions workflow语法检查")
    print_info("检查workflow文件语法")

    workflows_dir = ".github/workflows"
    if check_dir_exists(workflows_dir):
        yaml_files = glob.glob(os.path.join(workflows_dir, '*.yml')) + glob.glob(os.path.join(workflows_dir, '*.yaml'))
        if yaml_files:
            print("   发现的workflow文件:")
            for file in yaml_files:
                print(f"   - {os.path.basename(file)}")
            
            try:
                import yaml
                print_info("使用Python yaml模块验证语法...")
                for file in yaml_files:
                    with open(file, 'r') as f:
                        try:
                            yaml.safe_load(f)
                            print_success(f"   {os.path.basename(file)} 语法正确")
                        except yaml.YAMLError:
                            print_error(f"   {os.path.basename(file)} 语法错误")
            except ImportError:
                print_warning("yaml模块未安装，跳过语法检查")
        else:
            print_warning("未找到workflow文件")
    else:
        print_warning(".github/workflows目录不存在")
    print()

    # 测试8: 提供CI修复建议
    print_step("测试8: CI修复建议")
    print_info("分析并提供CI改进建议")

    print()
    print("📋 GitHub Actions 改进建议:")
    print("==========================")
    print()

    print("1. 📦 依赖安装策略:")
    print("   当前问题: pyproject.toml使用file:路径，在CI中不可用")
    print("   建议修复: 在CI中使用以下安装顺序:")
    print("     pip install -e packages/sage-common")
    print("     pip install -e packages/sage-kernel") 
    print("     pip install -e packages/sage-middleware")
    print("     pip install -e packages/sage-libs")
    print("     pip install -e .")
    print()

    print("2. 🧪 测试策略:")
    print("   建议: 使用quickstart.sh --minimal进行CI测试")
    print("   原因: 减少依赖，提高CI速度和稳定性")
    print()

    print("3. 🔧 构建策略:")
    print("   当前: 可能存在C扩展构建问题")
    print("   建议: 确保所有C扩展都有proper build.sh或Makefile")
    print()

    print("4. 📈 性能优化:")
    print("   建议: 使用缓存加速CI")
    print("   - pip cache")
    print("   - conda cache (如果使用)")
    print("   - 编译后的C扩展cache")
    print()

    print_success("本地CI测试完成！")
    print()
    print("🎯 下一步行动:")
    print("1. 根据上述建议修改CI配置")
    print("2. 提交更改并观察GitHub Actions运行结果")
    print("3. 如有问题，查看GitHub Actions日志进行调试")
    print()

    # 清理环境变量
    for var in ['CI', 'GITHUB_ACTIONS', 'GITHUB_WORKSPACE']:
        if var in os.environ:
            del os.environ[var]

if __name__ == "__main__":
    main()