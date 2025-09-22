#!/usr/bin/env python3
"""
SAGE Kernel Package Setup with C Extensions
自动编译C++扩展的安装脚本
"""

import os
import subprocess
import sys
from pathlib import Path

from setuptools import find_packages, setup
from setuptools.command.build_ext import build_ext
from setuptools.command.develop import develop
from setuptools.command.install import install


class BuildCExtensions(build_ext):
    """自定义C扩展编译命令"""

    def run(self):
        """编译C扩展"""
        # sage_queue has been removed
        super().run()


class CustomInstall(install):
    """自定义安装命令"""

    def run(self):
        # 先编译C扩展
        self.run_command("build_ext")
        # 然后安装
        super().run()


class CustomDevelop(develop):
    """自定义开发安装命令"""

    def run(self):
        # 先编译C扩展
        self.run_command("build_ext")
        # 然后开发安装
        super().run()


if __name__ == "__main__":
    setup(
        cmdclass={
            "build_ext": BuildCExtensions,
            "install": CustomInstall,
            "develop": CustomDevelop,
        }
    )
