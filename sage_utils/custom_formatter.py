import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Union, Optional
import threading
import inspect



class CustomFormatter(logging.Formatter):
    """
    自定义格式化器，合并IDE格式和两行格式：
    第一行：时间 | 级别 | 对象名 | 文件路径:行号
    第二行：	→ 日志消息
    第三行： 留空
    """
    COLOR_RESET = "\033[0m"
    COLOR_DEBUG = "\033[36m"  # 青色
    COLOR_INFO = "\033[32m"   # 绿色
    COLOR_WARNING = "\033[33m" # 黄色
    COLOR_ERROR = "\033[31m"  # 红色
    COLOR_CRITICAL = "\033[35m" # 紫色


    def format(self, record):

        if record.levelno == logging.DEBUG:
            color = self.COLOR_DEBUG
        elif record.levelno == logging.INFO:
            color = self.COLOR_INFO
        elif record.levelno == logging.WARNING:
            color = self.COLOR_WARNING
        elif record.levelno == logging.ERROR:
            color = self.COLOR_ERROR
        elif record.levelno == logging.CRITICAL:
            color = self.COLOR_CRITICAL
        else:
            color = self.COLOR_RESET

        # 第一行：时间 | 级别 | 对象名 | 文件路径:行号
        timestamp = self.formatTime(record, '%Y-%m-%d %H:%M:%S')
        level = record.levelname
        name = record.name
        pathname = record.pathname
        lineno = record.lineno

        # 第二行：→ 消息内容
        message = record.getMessage()

        # 如果有异常信息，添加到消息后面
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            message = message + '\n' + record.exc_text
        if record.stack_info:
            message = message + '\n' + self.formatStack(record.stack_info)

        # 组合格式：既美观又支持IDE点击
        formatted_message = f"{timestamp} | {level:<5} | {name} | {pathname}:{lineno} →\n\t {color}{message}{self.COLOR_RESET}\n"

        return formatted_message