"""
Main sage-development Toolkit class.

This module contains the core SAGEDevToolkit class that orchestrates
all development tools and provides a unified interface.
"""

import importlib.util
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import ToolkitConfig
from .exceptions import (
    AnalysisError,
    DependencyAnalysisError,
    PackageManagementError,
    ReportGenerationError,
    SAGEDevToolkitError,
    TestExecutionError,
    ToolError,
)


class SAGEDevToolkit:
    """
    Main sage-development Toolkit class.

    This class provides a unified interface to all development tools
    including testing, dependency analysis, package management, and reporting.
    """

    def __init__(
        self,
        project_root: str | None = None,
        config_file: str | None = None,
        environment: str | None = None,
    ):
        """
        Initialize the sage-development Toolkit.

        Args:
            project_root: Project root directory path
            config_file: Configuration file path
            environment: Environment name (development, production, ci)
        """
        # Load configuration
        self.config = ToolkitConfig.from_config_file(
            config_path=Path(config_file) if config_file else None,
            project_root=Path(project_root) if project_root else None,
            environment=environment,
        )

        # Ensure directories exist
        self.config.ensure_directories()

        # Setup logging
        self._setup_logging()

        # Load tools
        self.tools = {}
        self._load_tools()

        self.logger.info(
            f"sage-development Toolkit initialized for environment '{self.config.environment}'"
        )
        self.logger.info(f"Project root: {self.config.project_root}")
        self.logger.info(f"Available tools: {list(self.tools.keys())}")

    def _setup_logging(self) -> None:
        """Setup logging system based on configuration."""
        log_config = self.config.get_logging_config()

        # Create logger
        self.logger = logging.getLogger("SAGEDevToolkit")
        self.logger.setLevel(getattr(logging, log_config.get("level", "INFO")))

        # Clear existing handlers
        self.logger.handlers.clear()

        # Console handler
        if log_config.get("console_logging", {}).get("enabled", True):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.logger.level)
            formatter = logging.Formatter(
                log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

        # File handler
        if log_config.get("file_logging", {}).get("enabled", True):
            log_file = self.config.logs_dir / "sage_common.log"
            try:
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(self.logger.level)
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                self.logger.warning(f"Could not setup file logging: {e}")

    def _load_tools(self) -> None:
        """Load integrated tools and dynamically load additional tools from scripts directory."""
        # Load integrated tools first
        from ..tools import (
            EnhancedPackageManager,
            EnhancedTestRunner,
            VSCodePathManager,
        )

        # Map integrated tools
        integrated_tools = {
            "test_runner": EnhancedTestRunner,
            "package_manager": EnhancedPackageManager,
            "dependency_analyzer": EnhancedTestRunner,  # Can also analyze dependencies
            "vscode_manager": VSCodePathManager,
        }

        # Load integrated tools based on configuration
        tools_config = self.config.get_tools_config()

        for tool_name, tool_class in integrated_tools.items():
            if self.config.is_tool_enabled(tool_name):
                self.tools[tool_name] = tool_class
                self.logger.info(f"Successfully loaded tool: {tool_name}")
            else:
                self.logger.info(f"Skipping disabled tool: {tool_name}")

        # Load additional tools from scripts directory (for backwards compatibility)
        for tool_name, tool_config in tools_config.items():
            if tool_name in integrated_tools:
                continue  # Already loaded as integrated tool

            if not self.config.is_tool_enabled(tool_name):
                self.logger.info(f"Skipping disabled tool: {tool_name}")
                continue

            module_name = tool_config.get("module")
            class_name = tool_config.get("class")

            if not module_name or not class_name:
                self.logger.warning(f"Incomplete tool configuration: {tool_name}")
                continue

            # Try to load module
            module_path = self.config.scripts_dir / f"{module_name}.py"
            if not module_path.exists():
                self.logger.warning(f"Tool module not found: {module_path}")
                continue

            try:
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                if spec is None or spec.loader is None:
                    self.logger.warning(f"Failed to create spec for {module_name}")
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                # Get tool class
                if hasattr(module, class_name):
                    self.tools[tool_name] = getattr(module, class_name)
                    self.logger.info(f"Successfully loaded tool: {tool_name}")
                else:
                    self.logger.warning(f"Tool class not found: {class_name} in {module_name}")

            except Exception as e:
                self.logger.error(f"Failed to load tool {tool_name}: {e}")

        if not self.tools:
            self.logger.warning("No tools were loaded successfully")

    def run_tests(self, mode: str = "diff", **kwargs) -> dict[str, Any]:
        """
        Run tests using the enhanced test runner.

        Args:
            mode: Test mode ("all", "diff", "package")
            **kwargs: Additional arguments for test runner

        Returns:
            Test results dictionary

        Raises:
            TestExecutionError: If test execution fails
        """
        self.logger.info(f"🧪 Starting SAGE tests in '{mode}' mode")
        start_time = time.time()

        if "test_runner" not in self.tools:
            raise ToolError("Test runner not available")

        try:
            # Get test configuration
            test_config = self.config.get_testing_config()

            # Merge configuration with arguments
            test_kwargs = {
                "workers": kwargs.get("workers", test_config.get("max_workers", 4)),
                "timeout": kwargs.get("timeout", test_config.get("timeout", 300)),
                **kwargs,
            }

            # Create test runner instance
            enable_coverage = kwargs.get("enable_coverage", False)
            runner = self.tools["test_runner"](
                str(self.config.project_root), enable_coverage=enable_coverage
            )

            # Execute tests using the enhanced runner
            results = runner.run_tests(mode, **test_kwargs)

            # Add metadata
            execution_time = time.time() - start_time
            results["execution_time"] = execution_time
            results["timestamp"] = datetime.now().isoformat()
            results["mode"] = mode

            # Save results
            output_file = self._save_results("test_execution", results)

            self.logger.info(f"📄 Test results saved to: {output_file}")
            self.logger.info(f"⏱️  Test execution time: {execution_time:.2f}s")

            return results

        except Exception as e:
            raise TestExecutionError(f"Test execution failed: {e}") from e

    def analyze_dependencies(self, analysis_type: str = "full") -> dict[str, Any]:
        """
        Analyze project dependencies.

        Args:
            analysis_type: Type of analysis ("full", "summary", "circular")

        Returns:
            Analysis results dictionary

        Raises:
            DependencyAnalysisError: If analysis fails
        """
        self.logger.info(f"🔍 Starting dependency analysis: {analysis_type}")
        start_time = time.time()

        if "dependency_analyzer" not in self.tools:
            raise ToolError("Dependency analyzer not available")

        try:
            # Create analyzer instance
            analyzer = self.tools["dependency_analyzer"](str(self.config.packages_dir))

            # Execute analysis based on type
            if analysis_type == "full":
                results = analyzer.analyze_all_packages()
            elif analysis_type == "summary":
                results = analyzer.generate_summary()
            elif analysis_type == "circular":
                results = analyzer.find_circular_dependencies()
            else:
                raise DependencyAnalysisError(f"Unknown analysis type: {analysis_type}")

            # Add metadata
            execution_time = time.time() - start_time
            results["execution_time"] = execution_time
            results["timestamp"] = datetime.now().isoformat()
            results["analysis_type"] = analysis_type

            # Save results
            output_file = self._save_results("dependency_analysis", results)

            self.logger.info(f"📄 Analysis results saved to: {output_file}")
            self.logger.info(f"⏱️  Analysis time: {execution_time:.2f}s")

            return results

        except Exception as e:
            raise DependencyAnalysisError(f"Dependency analysis failed: {e}") from e

    def manage_packages(
        self, action: str, package_name: str | None = None, **kwargs
    ) -> dict[str, Any]:
        """
        Manage SAGE packages using the enhanced package manager.

        Args:
            action: Package action ("list", "install", "uninstall", "status", "build")
            package_name: Name of package to operate on
            **kwargs: Additional arguments

        Returns:
            Operation results dictionary

        Raises:
            PackageManagementError: If package operation fails
        """
        self.logger.info(f"📦 Package management: {action}")

        if "package_manager" not in self.tools:
            raise ToolError("Package manager not available")

        try:
            # Create package manager instance
            manager = self.tools["package_manager"](str(self.config.project_root))

            # Execute action using the enhanced manager
            if action == "list":
                return manager.list_packages()
            elif action == "install":
                if not package_name:
                    return manager.install_all_packages(**kwargs)
                else:
                    return manager.install_package(package_name, **kwargs)
            elif action == "uninstall":
                if not package_name:
                    raise PackageManagementError("Package name required for uninstall")
                return manager.uninstall_package(package_name)
            elif action == "status":
                return manager.check_dependencies()
            elif action == "build":
                if not package_name:
                    raise PackageManagementError("Package name required for build")
                return manager.build_package(package_name)
            else:
                raise PackageManagementError(f"Unknown package action: {action}")

        except Exception as e:
            raise PackageManagementError(
                f"Package management failed: {e}",
                package_name=package_name,
                operation=action,
            ) from e

    def generate_comprehensive_report(self) -> dict[str, Any]:
        """
        Generate a comprehensive development report.

        Returns:
            Complete report dictionary

        Raises:
            ReportGenerationError: If report generation fails
        """
        self.logger.info("📊 Generating comprehensive development report")
        start_time = time.time()

        report = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "project_root": str(self.config.project_root),
                "environment": self.config.environment,
                "toolkit_version": "1.0.0",
            },
            "sections": {},
        }

        # Package status section
        try:
            self.logger.info("Gathering package status...")
            pkg_status = self.manage_packages("status")
            report["sections"]["package_status"] = {
                "status": "success",
                "data": pkg_status,
            }
        except Exception as e:
            self.logger.warning(f"Package status collection failed: {e}")
            report["sections"]["package_status"] = {"status": "error", "error": str(e)}

        # Dependency analysis section
        try:
            self.logger.info("Performing dependency analysis...")
            dep_analysis = self.analyze_dependencies("summary")
            report["sections"]["dependency_analysis"] = {
                "status": "success",
                "data": dep_analysis,
            }
        except Exception as e:
            self.logger.warning(f"Dependency analysis failed: {e}")
            report["sections"]["dependency_analysis"] = {
                "status": "error",
                "error": str(e),
            }

        # Quick test status
        try:
            self.logger.info("Running quick tests...")
            test_results = self.run_tests("diff", quick=True, timeout=60)
            report["sections"]["test_status"] = {
                "status": "success",
                "data": test_results,
            }
        except Exception as e:
            self.logger.warning(f"Test execution failed: {e}")
            report["sections"]["test_status"] = {"status": "error", "error": str(e)}

        # Add execution metadata
        execution_time = time.time() - start_time
        report["metadata"]["execution_time"] = execution_time

        # Save comprehensive report
        try:
            output_file = self._save_results("comprehensive_report", report)

            # Generate markdown version
            markdown_file = output_file.with_suffix(".md")
            self._generate_markdown_report(report, markdown_file)

            self.logger.info(f"📄 Comprehensive report saved to: {output_file}")
            self.logger.info(f"📄 Markdown report saved to: {markdown_file}")
            self.logger.info(f"⏱️  Report generation time: {execution_time:.2f}s")

            return report

        except Exception as e:
            raise ReportGenerationError(f"Failed to save report: {e}") from e

    def _save_results(self, result_type: str, data: dict[str, Any]) -> Path:
        """Save results to output directory with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.config.output_dir / f"{result_type}_{timestamp}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return output_file

    def _generate_markdown_report(self, report: dict[str, Any], output_file: Path) -> None:
        """Generate markdown version of comprehensive report."""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# sage-development Report\n\n")

            # Metadata section
            metadata = report.get("metadata", {})
            f.write("## Report Metadata\n\n")
            f.write(f"- **Generated**: {metadata.get('timestamp', 'Unknown')}\n")
            f.write(f"- **Environment**: {metadata.get('environment', 'Unknown')}\n")
            f.write(f"- **Project Root**: {metadata.get('project_root', 'Unknown')}\n")
            f.write(f"- **Execution Time**: {metadata.get('execution_time', 0):.2f}s\n\n")

            # Sections
            sections = report.get("sections", {})
            for section_name, section_data in sections.items():
                section_title = section_name.replace("_", " ").title()
                f.write(f"## {section_title}\n\n")

                status = section_data.get("status", "unknown")
                if status == "error":
                    f.write(f"❌ **Error**: {section_data.get('error', 'Unknown error')}\n\n")
                elif status == "success":
                    f.write("✅ **Status**: Success\n\n")
                    # Add summary data if available
                    data = section_data.get("data", {})
                    if isinstance(data, dict):
                        f.write("### Summary\n\n")
                        for key, value in data.items():
                            if isinstance(value, (str, int, float, bool)):
                                f.write(f"- **{key}**: {value}\n")
                        f.write("\n")
                else:
                    f.write(f"⚠️ **Status**: {status}\n\n")

    def get_tool_status(self) -> dict[str, Any]:
        """Get status of all loaded tools."""
        return {
            "loaded_tools": list(self.tools.keys()),
            "available_tools": list(self.config.get_tools_config().keys()),
            "tools_config": self.config.get_tools_config(),
        }

    def validate_configuration(self) -> list[str]:
        """Validate toolkit configuration and return any errors."""
        return self.config.validate()

    def fix_import_paths(self, dry_run: bool = False) -> dict[str, Any]:
        """Fix import paths in SAGE packages."""
        if "import_fixer" not in self.tools:
            raise ToolError("Import path fixer not available")

        try:
            fixer = self.tools["import_fixer"](str(self.config.packages_dir))
            return fixer.fix_imports(dry_run=dry_run)
        except Exception as e:
            raise SAGEDevToolkitError(f"Import path fixing failed: {e}") from e

    def update_vscode_paths(self, mode: str = "enhanced") -> dict[str, Any]:
        """Update VS Code Python path configurations."""
        if "vscode_manager" not in self.tools:
            raise ToolError("VS Code path manager not available")

        try:
            manager = self.tools["vscode_manager"](str(self.config.project_root))
            return manager.update_python_paths(mode=mode)
        except Exception as e:
            raise SAGEDevToolkitError(f"VS Code path update failed: {e}") from e

    def list_available_tests(self) -> dict[str, Any]:
        """List all available tests in the project."""
        if "test_runner" not in self.tools:
            raise ToolError("Test runner not available")

        try:
            runner = self.tools["test_runner"](str(self.config.project_root))
            return runner.list_tests()
        except Exception as e:
            raise SAGEDevToolkitError(f"Test listing failed: {e}") from e

    @staticmethod
    def get_version_info() -> dict[str, Any]:
        """Get SAGE version information from _version.py file."""
        try:
            from sage.common.config import find_sage_project_root

            # Find the _version.py file in the project root
            project_root = find_sage_project_root()
            version_file = project_root / "_version.py"

            if not version_file.exists():
                raise FileNotFoundError(f"Could not find _version.py file in {project_root}")

            # Execute _version.py to get all variables
            version_globals = {}
            with open(version_file, encoding="utf-8") as f:
                exec(f.read(), version_globals)

            # Import sys to get Python version
            import sys

            return {
                "version": version_globals.get("__version__", "unknown"),
                "project_name": version_globals.get("__project_name__", "SAGE"),
                "project_full_name": version_globals.get(
                    "__project_full_name__", "Streaming-Augmented Generative Execution"
                ),
                "author": version_globals.get("__author__", "IntelliStream Team"),
                "email": version_globals.get("__email__", "unknown"),
                "release_date": version_globals.get("__release_date__", "unknown"),
                "release_status": version_globals.get("__release_status__", "development"),
                "build": f"{version_globals.get('__version__', 'unknown')}-{version_globals.get('__release_status__', 'dev')}",
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "python_requires": version_globals.get("__python_requires__", ">=3.10"),
            }

        except Exception:
            # Return default values if something goes wrong
            import sys

            return {
                "version": "unknown",
                "project_name": "SAGE",
                "project_full_name": "Streaming-Augmented Generative Execution",
                "author": "IntelliStream Team",
                "email": "unknown",
                "release_date": "unknown",
                "release_status": "development",
                "build": "unknown-dev",
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "python_requires": ">=3.10",
            }

    def analyze_project(self) -> dict[str, Any]:
        """
        Analyze the current project structure and dependencies.

        Returns:
            Project analysis results dictionary
        """
        self.logger.info("🔍 Analyzing project structure and dependencies")
        start_time = time.time()

        analysis = {
            "project_info": {},
            "structure": {},
            "dependencies": {},
            "tools": {},
        }

        try:
            # Project info
            version_info = self.get_version_info()
            analysis["project_info"] = {
                "name": version_info.get("project_name", "SAGE"),
                "version": version_info.get("version", "unknown"),
                "root": str(self.config.project_root),
                "environment": self.config.environment,
            }

            # Project structure
            analysis["structure"] = {
                "packages_dir": str(self.config.packages_dir),
                "scripts_dir": str(self.config.scripts_dir),
                "output_dir": str(self.config.output_dir),
                "logs_dir": str(self.config.logs_dir),
            }

            # Dependencies
            try:
                dep_analysis = self.analyze_dependencies("summary")
                analysis["dependencies"] = dep_analysis
            except Exception as e:
                self.logger.warning(f"Dependency analysis failed: {e}")
                analysis["dependencies"] = {"error": str(e)}

            # Tools status
            analysis["tools"] = self.get_tool_status()

            # Add metadata
            execution_time = time.time() - start_time
            analysis["execution_time"] = execution_time  # type: ignore[assignment]
            analysis["timestamp"] = datetime.now().isoformat()  # type: ignore[assignment]

            self.logger.info(f"📄 Project analysis completed in {execution_time:.2f}s")
            return analysis

        except Exception as e:
            self.logger.error(f"Project analysis failed: {e}")
            raise AnalysisError(f"Project analysis failed: {e}") from e
