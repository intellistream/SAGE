"""
Enhanced bytecode compilation integration for SAGE packages.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
from .bytecode_compiler import BytecodeCompiler


class CompilationManager:
    """编译管理器，集成编译、构建和发布功能"""
    
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.config = self._load_project_config()
    
    def _load_project_config(self) -> Dict[str, Any]:
        """加载项目配置"""
        import tomli
        config_path = self.project_root / "project_config.toml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"项目配置文件不存在: {config_path}")
        
        with open(config_path, 'rb') as f:
            return tomli.load(f)
    
    def get_package_info(self, package_name: str) -> Dict[str, Any]:
        """获取包信息"""
        packages = self.config.get('packages', {})
        
        if package_name not in packages:
            raise ValueError(f"未知的包名: {package_name}")
        
        package_path = self.project_root / packages[package_name]
        
        return {
            'name': package_name,
            'path': package_path,
            'description': self.config.get('package_descriptions', {}).get(package_name, ''),
            'is_opensource': self._is_opensource_package(package_name)
        }
    
    def _is_opensource_package(self, package_name: str) -> bool:
        """判断是否为开源包"""
        # 开源包列表（可以从配置文件读取）
        opensource_packages = {
            "intellistream-sage-kernel",
            "intellistream-sage-middleware", 
            "intellistream-sage",
        }
        return package_name in opensource_packages
    
    def compile_for_distribution(
        self, 
        package_name: str,
        target_type: str = "opensource",  # "opensource" or "proprietary"
        output_dir: Optional[Path] = None,
        build_wheel: bool = True
    ) -> Dict[str, Any]:
        """
        为发布编译包
        
        Args:
            package_name: 包名
            target_type: 目标类型 ("opensource" 或 "proprietary")
            output_dir: 输出目录
            build_wheel: 是否构建 wheel
            
        Returns:
            编译结果信息
        """
        package_info = self.get_package_info(package_name)
        
        # 开源包直接构建，不需要字节码编译
        if target_type == "opensource":
            return self._build_opensource_package(package_info, output_dir, build_wheel)
        else:
            return self._build_proprietary_package(package_info, output_dir, build_wheel)
    
    def _build_opensource_package(
        self, 
        package_info: Dict[str, Any], 
        output_dir: Optional[Path] = None,
        build_wheel: bool = True
    ) -> Dict[str, Any]:
        """构建开源包（保留源码）"""
        from rich.console import Console
        console = Console()
        
        package_path = package_info['path']
        package_name = package_info['name']
        
        console.print(f"📦 构建开源包: {package_name}", style="green")
        
        if build_wheel:
            # 直接在原目录构建 wheel
            import subprocess
            import os
            
            original_cwd = os.getcwd()
            try:
                os.chdir(package_path)
                result = subprocess.run(
                    ["python", "-m", "build"], 
                    capture_output=True, 
                    text=True
                )
                
                if result.returncode != 0:
                    raise RuntimeError(f"构建失败: {result.stderr}")
                
                console.print(f"✅ {package_name}: 开源包构建完成", style="green")
                
                return {
                    'type': 'opensource',
                    'package_name': package_name,
                    'package_path': package_path,
                    'build_path': package_path / "dist",
                    'success': True
                }
                
            finally:
                os.chdir(original_cwd)
        
        return {
            'type': 'opensource',
            'package_name': package_name,
            'package_path': package_path,
            'success': True
        }
    
    def _build_proprietary_package(
        self, 
        package_info: Dict[str, Any], 
        output_dir: Optional[Path] = None,
        build_wheel: bool = True
    ) -> Dict[str, Any]:
        """构建闭源包（编译为字节码）"""
        from rich.console import Console
        console = Console()
        
        package_path = package_info['path']
        package_name = package_info['name']
        
        console.print(f"🔒 构建闭源包: {package_name}", style="yellow")
        
        # 使用字节码编译器
        compiler = BytecodeCompiler(package_path)
        compiled_path = compiler.compile_package(output_dir, use_sage_home=True)
        
        if build_wheel:
            # 在编译后的目录构建 wheel
            wheel_path = compiler.build_wheel(compiled_path)
            
            return {
                'type': 'proprietary',
                'package_name': package_name,
                'package_path': package_path,
                'compiled_path': compiled_path,
                'wheel_path': wheel_path,
                'success': True
            }
        
        return {
            'type': 'proprietary',
            'package_name': package_name,
            'package_path': package_path,
            'compiled_path': compiled_path,
            'success': True
        }
    
    def list_packages(self) -> List[Dict[str, Any]]:
        """列出所有包"""
        packages = []
        for name in self.config.get('packages', {}):
            try:
                info = self.get_package_info(name)
                packages.append(info)
            except Exception:
                continue
        return packages
    
    def get_opensource_packages(self) -> List[str]:
        """获取开源包列表"""
        return [
            name for name in self.config.get('packages', {})
            if self._is_opensource_package(name)
        ]
    
    def get_proprietary_packages(self) -> List[str]:
        """获取闭源包列表"""
        return [
            name for name in self.config.get('packages', {})
            if not self._is_opensource_package(name)
        ]
