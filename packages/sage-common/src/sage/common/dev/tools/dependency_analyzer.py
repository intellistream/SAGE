"""
Dependency Summary Tool - Integrated from scripts/dependency_summary.py

This tool analyzes and reports on project dependencies across all packages.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
import json
import subprocess
import yaml
try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for older Python versions
from collections import defaultdict
from ..core.exceptions import SAGEDevToolkitError


class DependencyAnalyzer:
    """Tool for analyzing project dependencies."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.packages_dir = self.project_root / "packages"
        
    def analyze_all_dependencies(self) -> Dict[str, Any]:
        """Analyze dependencies across all packages."""
        try:
            analysis = {
                'project_root': str(self.project_root),
                'packages': {},
                'summary': {
                    'total_packages': 0,
                    'total_dependencies': 0,
                    'unique_dependencies': set(),
                    'dependency_conflicts': [],
                    'circular_dependencies': []
                },
                'dependency_graph': {},
                'version_matrix': defaultdict(dict)
            }
            
            # Find all packages
            package_dirs = self._find_package_directories()
            
            for package_dir in package_dirs:
                package_name = package_dir.name
                package_analysis = self._analyze_package_dependencies(package_dir)
                
                analysis['packages'][package_name] = package_analysis
                analysis['summary']['total_packages'] += 1
                
                # Update global dependency tracking
                for dep_name, dep_info in package_analysis['dependencies'].items():
                    analysis['summary']['unique_dependencies'].add(dep_name)
                    analysis['summary']['total_dependencies'] += 1
                    
                    # Track version matrix
                    if 'version' in dep_info:
                        analysis['version_matrix'][dep_name][package_name] = dep_info['version']
            
            # Convert set to list for JSON serialization
            analysis['summary']['unique_dependencies'] = list(analysis['summary']['unique_dependencies'])
            analysis['summary']['total_unique_dependencies'] = len(analysis['summary']['unique_dependencies'])
            
            # Build dependency graph
            analysis['dependency_graph'] = self._build_dependency_graph(analysis['packages'])
            
            # Detect conflicts and circular dependencies
            analysis['summary']['dependency_conflicts'] = self._detect_version_conflicts(analysis['version_matrix'])
            analysis['summary']['circular_dependencies'] = self._detect_circular_dependencies(analysis['dependency_graph'])
            
            return analysis
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Dependency analysis failed: {e}")
    
    def generate_dependency_report(self, output_format: str = 'json') -> Dict[str, Any]:
        """Generate comprehensive dependency report."""
        try:
            analysis = self.analyze_all_dependencies()
            
            if output_format == 'json':
                # Convert defaultdict to regular dict for JSON
                analysis['version_matrix'] = dict(analysis['version_matrix'])
                return analysis
            
            elif output_format == 'markdown':
                return self._generate_markdown_report(analysis)
            
            elif output_format == 'summary':
                return self._generate_summary_report(analysis)
            
            else:
                raise SAGEDevToolkitError(f"Unsupported output format: {output_format}")
                
        except Exception as e:
            raise SAGEDevToolkitError(f"Report generation failed: {e}")
    
    def check_dependency_health(self) -> Dict[str, Any]:
        """Check overall dependency health."""
        try:
            analysis = self.analyze_all_dependencies()
            
            health_score = 100
            issues = []
            recommendations = []
            
            # Check for version conflicts
            conflicts = analysis['summary']['dependency_conflicts']
            if conflicts:
                health_score -= len(conflicts) * 10
                issues.append(f"Found {len(conflicts)} version conflicts")
                recommendations.append("Resolve version conflicts to ensure compatibility")
            
            # Check for circular dependencies
            circular = analysis['summary']['circular_dependencies']
            if circular:
                health_score -= len(circular) * 15
                issues.append(f"Found {len(circular)} circular dependencies")
                recommendations.append("Refactor to eliminate circular dependencies")
            
            # Check for outdated dependencies
            outdated = self._check_outdated_dependencies(analysis)
            if outdated:
                health_score -= len(outdated) * 5
                issues.append(f"Found {len(outdated)} potentially outdated dependencies")
                recommendations.append("Consider updating outdated dependencies")
            
            # Check for security vulnerabilities
            vulnerabilities = self._check_security_vulnerabilities()
            if vulnerabilities:
                health_score -= len(vulnerabilities) * 20
                issues.append(f"Found {len(vulnerabilities)} security vulnerabilities")
                recommendations.append("Address security vulnerabilities immediately")
            
            health_score = max(0, health_score)  # Don't go below 0
            
            return {
                'health_score': health_score,
                'grade': self._get_health_grade(health_score),
                'issues': issues,
                'recommendations': recommendations,
                'conflicts': conflicts,
                'circular_dependencies': circular,
                'outdated': outdated,
                'vulnerabilities': vulnerabilities,
                'total_packages': analysis['summary']['total_packages'],
                'total_dependencies': analysis['summary']['total_unique_dependencies']
            }
            
        except Exception as e:
            raise SAGEDevToolkitError(f"Dependency health check failed: {e}")
    
    def _find_package_directories(self) -> List[Path]:
        """Find all package directories."""
        package_dirs = []
        
        # Check packages/ directory
        if self.packages_dir.exists():
            for item in self.packages_dir.iterdir():
                if item.is_dir() and self._is_python_package(item):
                    package_dirs.append(item)
        
        # Check root directory for packages
        root_files = ['pyproject.toml', 'setup.py', 'requirements.txt']
        if any((self.project_root / f).exists() for f in root_files):
            package_dirs.append(self.project_root)
        
        return package_dirs
    
    def _is_python_package(self, path: Path) -> bool:
        """Check if directory is a Python package."""
        package_files = ['pyproject.toml', 'setup.py', 'requirements.txt', 'setup.cfg']
        return any((path / f).exists() for f in package_files)
    
    def _analyze_package_dependencies(self, package_dir: Path) -> Dict[str, Any]:
        """Analyze dependencies for a single package."""
        analysis = {
            'name': package_dir.name,
            'path': str(package_dir),
            'dependencies': {},
            'dev_dependencies': {},
            'optional_dependencies': {},
            'dependency_sources': []
        }
        
        # Check pyproject.toml
        pyproject_file = package_dir / 'pyproject.toml'
        if pyproject_file.exists():
            self._parse_pyproject_dependencies(pyproject_file, analysis)
        
        # Check setup.py
        setup_file = package_dir / 'setup.py'
        if setup_file.exists():
            self._parse_setup_dependencies(setup_file, analysis)
        
        # Check requirements.txt
        req_file = package_dir / 'requirements.txt'
        if req_file.exists():
            self._parse_requirements_dependencies(req_file, analysis)
        
        # Check requirements-dev.txt
        dev_req_file = package_dir / 'requirements-dev.txt'
        if dev_req_file.exists():
            self._parse_requirements_dependencies(dev_req_file, analysis, is_dev=True)
        
        return analysis
    
    def _parse_pyproject_dependencies(self, pyproject_file: Path, analysis: Dict):
        """Parse dependencies from pyproject.toml."""
        try:
            with open(pyproject_file, 'rb') as f:
                data = tomllib.load(f)
            
            analysis['dependency_sources'].append('pyproject.toml')
            
            # Main dependencies
            if 'project' in data and 'dependencies' in data['project']:
                for dep in data['project']['dependencies']:
                    dep_name, dep_info = self._parse_dependency_spec(dep)
                    analysis['dependencies'][dep_name] = dep_info
            
            # Optional dependencies
            if 'project' in data and 'optional-dependencies' in data['project']:
                for group, deps in data['project']['optional-dependencies'].items():
                    for dep in deps:
                        dep_name, dep_info = self._parse_dependency_spec(dep)
                        analysis['optional_dependencies'][dep_name] = {
                            **dep_info,
                            'group': group
                        }
            
        except Exception as e:
            print(f"Warning: Could not parse {pyproject_file}: {e}")
    
    def _parse_setup_dependencies(self, setup_file: Path, analysis: Dict):
        """Parse dependencies from setup.py (basic parsing)."""
        try:
            analysis['dependency_sources'].append('setup.py')
            
            # This is a simplified parser - in practice, you might want to use AST
            with open(setup_file, 'r') as f:
                content = f.read()
            
            # Look for install_requires
            if 'install_requires' in content:
                # Extract dependencies using regex (simplified approach)
                import re
                pattern = r'install_requires\s*=\s*\[(.*?)\]'
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    deps_str = match.group(1)
                    deps = re.findall(r'["\']([^"\']+)["\']', deps_str)
                    for dep in deps:
                        dep_name, dep_info = self._parse_dependency_spec(dep)
                        analysis['dependencies'][dep_name] = dep_info
                        
        except Exception as e:
            print(f"Warning: Could not parse {setup_file}: {e}")
    
    def _parse_requirements_dependencies(self, req_file: Path, analysis: Dict, is_dev: bool = False):
        """Parse dependencies from requirements.txt files."""
        try:
            source_name = req_file.name
            analysis['dependency_sources'].append(source_name)
            
            with open(req_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and not line.startswith('-'):
                        dep_name, dep_info = self._parse_dependency_spec(line)
                        target_dict = analysis['dev_dependencies'] if is_dev else analysis['dependencies']
                        target_dict[dep_name] = dep_info
                        
        except Exception as e:
            print(f"Warning: Could not parse {req_file}: {e}")
    
    def _parse_dependency_spec(self, dep_spec: str) -> tuple:
        """Parse a dependency specification."""
        import re
        
        # Remove extras specification
        dep_spec = re.sub(r'\[.*?\]', '', dep_spec)
        
        # Parse name and version
        match = re.match(r'([a-zA-Z0-9_-]+)\s*([><=!~].*)?', dep_spec.strip())
        if match:
            name = match.group(1)
            version_spec = match.group(2) if match.group(2) else None
            
            return name, {
                'version': version_spec,
                'spec': dep_spec.strip()
            }
        else:
            return dep_spec.strip(), {'version': None, 'spec': dep_spec.strip()}
    
    def _build_dependency_graph(self, packages: Dict) -> Dict[str, List[str]]:
        """Build dependency graph."""
        graph = {}
        
        for package_name, package_info in packages.items():
            dependencies = []
            
            # Add direct dependencies
            for dep_name in package_info['dependencies'].keys():
                # Only include SAGE internal dependencies
                if dep_name.startswith('sage-') or dep_name in packages:
                    dependencies.append(dep_name)
            
            graph[package_name] = dependencies
        
        return graph
    
    def _detect_version_conflicts(self, version_matrix: Dict) -> List[Dict]:
        """Detect version conflicts."""
        conflicts = []
        
        for dep_name, package_versions in version_matrix.items():
            versions = set(v for v in package_versions.values() if v)
            
            if len(versions) > 1:
                conflicts.append({
                    'dependency': dep_name,
                    'versions': list(versions),
                    'packages': dict(package_versions)
                })
        
        return conflicts
    
    def _detect_circular_dependencies(self, graph: Dict) -> List[List[str]]:
        """Detect circular dependencies using DFS."""
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node, path):
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                dfs(neighbor, path + [neighbor])
            
            rec_stack.remove(node)
        
        for node in graph:
            if node not in visited:
                dfs(node, [node])
        
        return cycles
    
    def _check_outdated_dependencies(self, analysis: Dict) -> List[Dict]:
        """Check for potentially outdated dependencies."""
        # This is a simplified check - in practice, you'd want to query PyPI
        outdated = []
        
        for package_name, package_info in analysis['packages'].items():
            for dep_name, dep_info in package_info['dependencies'].items():
                if dep_info.get('version') and '<' in dep_info['version']:
                    outdated.append({
                        'package': package_name,
                        'dependency': dep_name,
                        'current_spec': dep_info['version'],
                        'reason': 'Uses upper bound version constraint'
                    })
        
        return outdated
    
    def _check_security_vulnerabilities(self) -> List[Dict]:
        """Check for security vulnerabilities."""
        try:
            # Try to use safety if available
            result = subprocess.run([
                sys.executable, '-m', 'safety', 'check', '--json'
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and result.stdout:
                return json.loads(result.stdout)
            
        except:
            pass
        
        return []  # Return empty list if safety is not available
    
    def _get_health_grade(self, score: int) -> str:
        """Get health grade based on score."""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'
    
    def _generate_markdown_report(self, analysis: Dict) -> str:
        """Generate markdown report."""
        report_lines = [
            "# SAGE Dependency Analysis Report",
            "",
            f"**Project Root:** {analysis['project_root']}",
            f"**Total Packages:** {analysis['summary']['total_packages']}",
            f"**Total Dependencies:** {analysis['summary']['total_unique_dependencies']}",
            "",
            "## Package Summary",
            ""
        ]
        
        for package_name, package_info in analysis['packages'].items():
            report_lines.extend([
                f"### {package_name}",
                f"- **Path:** `{package_info['path']}`",
                f"- **Dependencies:** {len(package_info['dependencies'])}",
                f"- **Dev Dependencies:** {len(package_info['dev_dependencies'])}",
                f"- **Optional Dependencies:** {len(package_info['optional_dependencies'])}",
                ""
            ])
        
        # Add conflicts section
        if analysis['summary']['dependency_conflicts']:
            report_lines.extend([
                "## Version Conflicts",
                ""
            ])
            for conflict in analysis['summary']['dependency_conflicts']:
                report_lines.extend([
                    f"### {conflict['dependency']}",
                    f"- **Conflicting Versions:** {', '.join(conflict['versions'])}",
                    f"- **Affected Packages:** {', '.join(conflict['packages'].keys())}",
                    ""
                ])
        
        return "\n".join(report_lines)
    
    def _generate_summary_report(self, analysis: Dict) -> Dict[str, Any]:
        """Generate summary report."""
        return {
            'project_root': analysis['project_root'],
            'total_packages': analysis['summary']['total_packages'],
            'total_dependencies': analysis['summary']['total_unique_dependencies'],
            'conflicts': len(analysis['summary']['dependency_conflicts']),
            'circular_dependencies': len(analysis['summary']['circular_dependencies']),
            'top_dependencies': self._get_top_dependencies(analysis),
            'package_count': {name: len(info['dependencies']) 
                            for name, info in analysis['packages'].items()}
        }
    
    def _get_top_dependencies(self, analysis: Dict) -> List[Dict]:
        """Get most commonly used dependencies."""
        dep_count = defaultdict(int)
        
        for package_info in analysis['packages'].values():
            for dep_name in package_info['dependencies'].keys():
                dep_count[dep_name] += 1
        
        # Sort by usage count
        sorted_deps = sorted(dep_count.items(), key=lambda x: x[1], reverse=True)
        
        return [{'name': name, 'usage_count': count} for name, count in sorted_deps[:10]]
