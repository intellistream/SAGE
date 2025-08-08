"""Core module initialization."""

from .bytecode_compiler import BytecodeCompiler, compile_multiple_packages

__all__ = [
    'BytecodeCompiler',
    'compile_multiple_packages'
]
