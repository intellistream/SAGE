#!/usr/bin/env python3
"""
SAGE CLI Exceptions
===================

自定义异常类，用于处理CLI操作中的各种错误情况
"""


class CLIException(Exception):
    """CLI操作的基础异常类"""
    
    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.exit_code = exit_code


class ConfigurationError(CLIException):
    """配置相关错误"""
    
    def __init__(self, message: str):
        super().__init__(f"Configuration error: {message}", 2)


class ConnectionError(CLIException):
    """连接相关错误"""
    
    def __init__(self, message: str):
        super().__init__(f"Connection error: {message}", 3)


class ValidationError(CLIException):
    """输入验证错误"""
    
    def __init__(self, message: str):
        super().__init__(f"Validation error: {message}", 4)


class DeploymentError(CLIException):
    """部署相关错误"""
    
    def __init__(self, message: str):
        super().__init__(f"Deployment error: {message}", 5)


class ServiceError(CLIException):
    """服务相关错误"""
    
    def __init__(self, message: str):
        super().__init__(f"Service error: {message}", 6)


class JobError(CLIException):
    """作业相关错误"""
    
    def __init__(self, message: str):
        super().__init__(f"Job error: {message}", 7)


class ExtensionError(CLIException):
    """扩展相关错误"""
    
    def __init__(self, message: str):
        super().__init__(f"Extension error: {message}", 8)
