#!/usr/bin/env python3
"""
Test Summary Generator for SAGE Core API Tests

This script analyzes the test suite and generates comprehensive reports
about test coverage, organization, and compliance with testing standards.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict


class TestAnalyzer:
    """Analyzes test files and generates reports"""
    
    def __init__(self, test_dir: Path):
        self.test_dir = test_dir
        self.test_files = list(test_dir.glob("test_*.py"))
        
    def analyze_test_file(self, file_path: Path) -> Dict:
        """Analyze a single test file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            return {"error": f"Syntax error: {e}"}
        
        analysis = {
            "file": file_path.name,
            "classes": [],
            "functions": [],
            "markers": set(),
            "imports": [],
            "total_lines": len(content.splitlines()),
            "docstring": ast.get_docstring(tree) or ""
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = {
                    "name": node.name,
                    "methods": [],
                    "docstring": ast.get_docstring(node) or ""
                }
                
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_info = {
                            "name": item.name,
                            "decorators": [self._get_decorator_name(d) for d in item.decorator_list],
                            "docstring": ast.get_docstring(item) or ""
                        }
                        class_info["methods"].append(method_info)
                        
                        # Extract pytest markers
                        for decorator in item.decorator_list:
                            if isinstance(decorator, ast.Attribute):
                                if (isinstance(decorator.value, ast.Attribute) and
                                    isinstance(decorator.value.value, ast.Name) and
                                    decorator.value.value.id == "pytest" and
                                    decorator.value.attr == "mark"):
                                    analysis["markers"].add(decorator.attr)
                
                analysis["classes"].append(class_info)
            
            elif isinstance(node, ast.FunctionDef) and not any(isinstance(parent, ast.ClassDef) 
                                                             for parent in ast.walk(tree) 
                                                             if any(child == node for child in ast.walk(parent))):
                func_info = {
                    "name": node.name,
                    "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
                    "docstring": ast.get_docstring(node) or ""
                }
                analysis["functions"].append(func_info)
            
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    analysis["imports"].append(alias.name)
            
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    analysis["imports"].append(f"{module}.{alias.name}")
        
        return analysis
    
    def _get_decorator_name(self, decorator) -> str:
        """Extract decorator name from AST node"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Attribute):
            if isinstance(decorator.value, ast.Name):
                return f"{decorator.value.id}.{decorator.attr}"
            elif isinstance(decorator.value, ast.Attribute):
                return f"{self._get_decorator_name(decorator.value)}.{decorator.attr}"
        return str(decorator)
    
    def generate_coverage_report(self) -> str:
        """Generate test coverage report"""
        report = []
        report.append("# SAGE Core API Test Coverage Report")
        report.append("=" * 50)
        report.append("")
        
        total_test_methods = 0
        total_test_classes = 0
        files_analysis = []
        
        for test_file in self.test_files:
            analysis = self.analyze_test_file(test_file)
            if "error" in analysis:
                continue
                
            files_analysis.append(analysis)
            file_test_methods = sum(len([m for m in cls["methods"] if m["name"].startswith("test_")]) 
                                  for cls in analysis["classes"])
            file_test_classes = len([cls for cls in analysis["classes"] 
                                   if cls["name"].startswith("Test")])
            
            total_test_methods += file_test_methods
            total_test_classes += file_test_classes
            
            report.append(f"## {analysis['file']}")
            report.append(f"- **Test Classes**: {file_test_classes}")
            report.append(f"- **Test Methods**: {file_test_methods}")
            report.append(f"- **Markers Used**: {', '.join(sorted(analysis['markers']))}")
            report.append(f"- **Lines of Code**: {analysis['total_lines']}")
            
            if analysis['docstring']:
                report.append(f"- **Description**: {analysis['docstring'].split('.')[0]}")
            
            report.append("")
            
            # Detail test classes
            for cls in analysis["classes"]:
                if cls["name"].startswith("Test"):
                    test_methods = [m for m in cls["methods"] if m["name"].startswith("test_")]
                    report.append(f"  ### {cls['name']} ({len(test_methods)} tests)")
                    
                    for method in test_methods[:5]:  # Show first 5 methods
                        markers = [d for d in method["decorators"] if "pytest.mark" in d]
                        marker_str = f" [{', '.join(markers)}]" if markers else ""
                        report.append(f"  - `{method['name']}`{marker_str}")
                    
                    if len(test_methods) > 5:
                        report.append(f"  - ... and {len(test_methods) - 5} more tests")
                    
                    report.append("")
        
        # Summary
        report.insert(3, f"**Total Test Files**: {len(files_analysis)}")
        report.insert(4, f"**Total Test Classes**: {total_test_classes}")
        report.insert(5, f"**Total Test Methods**: {total_test_methods}")
        report.insert(6, "")
        
        return "\n".join(report)
    
    def generate_compliance_report(self) -> str:
        """Generate compliance report against testing standards"""
        report = []
        report.append("# SAGE Core API Test Compliance Report")
        report.append("=" * 50)
        report.append("")
        
        compliance_issues = []
        
        for test_file in self.test_files:
            analysis = self.analyze_test_file(test_file)
            if "error" in analysis:
                compliance_issues.append(f"❌ {analysis['file']}: {analysis['error']}")
                continue
            
            file_issues = []
            
            # Check file naming
            if not analysis["file"].startswith("test_"):
                file_issues.append("File doesn't follow test_*.py naming convention")
            
            # Check docstring presence
            if not analysis["docstring"]:
                file_issues.append("Missing module docstring")
            
            # Check test classes
            for cls in analysis["classes"]:
                if cls["name"].startswith("Test"):
                    if not cls["docstring"]:
                        file_issues.append(f"Class {cls['name']} missing docstring")
                    
                    # Check test methods
                    test_methods = [m for m in cls["methods"] if m["name"].startswith("test_")]
                    for method in test_methods:
                        if not method["docstring"]:
                            file_issues.append(f"Method {cls['name']}.{method['name']} missing docstring")
                        
                        # Check pytest markers
                        has_unit_or_integration = any("pytest.mark.unit" in d or "pytest.mark.integration" in d 
                                                    for d in method["decorators"])
                        if not has_unit_or_integration:
                            file_issues.append(f"Method {cls['name']}.{method['name']} missing @pytest.mark.unit or @pytest.mark.integration")
            
            if file_issues:
                compliance_issues.extend([f"⚠️  {analysis['file']}: {issue}" for issue in file_issues])
            else:
                compliance_issues.append(f"✅ {analysis['file']}: All compliance checks passed")
        
        if compliance_issues:
            report.append("## Compliance Issues")
            report.extend(compliance_issues)
        else:
            report.append("✅ All files pass compliance checks!")
        
        return "\n".join(report)
    
    def generate_organization_report(self) -> str:
        """Generate report on test organization"""
        report = []
        report.append("# SAGE Core API Test Organization Report")
        report.append("=" * 50)
        report.append("")
        
        # Map test files to source files
        source_to_test_mapping = {
            "base_environment.py": "test_base_environment.py",
            "local_environment.py": "test_local_environment.py", 
            "remote_environment.py": "test_remote_environment.py",
            "datastream.py": "test_datastream.py",
            "connected_streams.py": "test_connected_streams.py"
        }
        
        report.append("## Source-to-Test File Mapping")
        for source, test in source_to_test_mapping.items():
            test_path = self.test_dir / test
            status = "✅" if test_path.exists() else "❌"
            report.append(f"{status} `src/sage/core/api/{source}` → `tests/core/api/{test}`")
        
        report.append("")
        report.append("## Test File Structure")
        
        for test_file in sorted(self.test_files):
            if test_file.name.startswith("test_"):
                analysis = self.analyze_test_file(test_file)
                if "error" not in analysis:
                    report.append(f"### {analysis['file']}")
                    report.append(f"```")
                    for cls in analysis["classes"]:
                        if cls["name"].startswith("Test"):
                            report.append(f"class {cls['name']}:")
                            test_methods = [m for m in cls["methods"] if m["name"].startswith("test_")]
                            for method in test_methods:
                                report.append(f"    def {method['name']}()")
                    report.append(f"```")
                    report.append("")
        
        return "\n".join(report)


def main():
    """Generate all reports"""
    test_dir = Path(__file__).parent
    analyzer = TestAnalyzer(test_dir)
    
    # Generate reports
    print("Generating test reports...")
    
    # Coverage report
    coverage_report = analyzer.generate_coverage_report()
    with open(test_dir / "TEST_COVERAGE_REPORT.md", "w") as f:
        f.write(coverage_report)
    print("✅ Coverage report generated: TEST_COVERAGE_REPORT.md")
    
    # Compliance report
    compliance_report = analyzer.generate_compliance_report()
    with open(test_dir / "TEST_COMPLIANCE_REPORT.md", "w") as f:
        f.write(compliance_report)
    print("✅ Compliance report generated: TEST_COMPLIANCE_REPORT.md")
    
    # Organization report
    organization_report = analyzer.generate_organization_report()
    with open(test_dir / "TEST_ORGANIZATION_REPORT.md", "w") as f:
        f.write(organization_report)
    print("✅ Organization report generated: TEST_ORGANIZATION_REPORT.md")
    
    print("\n📊 All reports generated successfully!")
    print(f"📁 Reports location: {test_dir}")


if __name__ == "__main__":
    main()
