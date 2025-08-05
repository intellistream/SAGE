"""
SAGE Development Toolkit exceptions.

This module defines the exception hierarchy for the SAGE Development Toolkit.
All toolkit-specific exceptions inherit from SAGEDevToolkitError.
"""

from typing import Optional, Any


class SAGEDevToolkitError(Exception):
    """Base exception for all SAGE Development Toolkit errors."""
    
    def __init__(
        self, 
        message: str, 
        details: Optional[dict] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause
    
    def __str__(self) -> str:
        parts = [self.message]
        if self.details:
            parts.append(f"Details: {self.details}")
        if self.cause:
            parts.append(f"Caused by: {self.cause}")
        return " | ".join(parts)


class ConfigError(SAGEDevToolkitError):
    """Raised when there are configuration-related errors."""
    
    def __init__(self, message: str, config_path: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.config_path = config_path


class ToolError(SAGEDevToolkitError): 
    """Raised when there are tool execution errors."""
    
    def __init__(
        self, 
        message: str, 
        tool_name: Optional[str] = None,
        exit_code: Optional[int] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.tool_name = tool_name
        self.exit_code = exit_code


class AnalysisError(SAGEDevToolkitError):
    """Raised when there are analysis-related errors."""
    
    def __init__(
        self,
        message: str,
        analysis_type: Optional[str] = None,
        failed_files: Optional[list] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.analysis_type = analysis_type
        self.failed_files = failed_files or []


class TestExecutionError(ToolError):
    """Raised when test execution fails."""
    
    def __init__(
        self,
        message: str,
        failed_tests: Optional[list] = None,
        **kwargs
    ):
        super().__init__(message, tool_name="test_runner", **kwargs)
        self.failed_tests = failed_tests or []


class PackageManagementError(ToolError):
    """Raised when package management operations fail."""
    
    def __init__(
        self,
        message: str,
        package_name: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, tool_name="package_manager", **kwargs)
        self.package_name = package_name
        self.operation = operation


class DependencyAnalysisError(AnalysisError):
    """Raised when dependency analysis fails."""
    
    def __init__(
        self,
        message: str,
        circular_deps: Optional[list] = None,
        **kwargs
    ):
        super().__init__(message, analysis_type="dependency", **kwargs)
        self.circular_deps = circular_deps or []


class ReportGenerationError(SAGEDevToolkitError):
    """Raised when report generation fails."""
    
    def __init__(
        self,
        message: str,
        report_type: Optional[str] = None,
        template_path: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.report_type = report_type
        self.template_path = template_path
