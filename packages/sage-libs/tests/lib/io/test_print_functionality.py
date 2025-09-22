"""
import logging
测试 datastream.logging.info() 方法和 PrintSink 功能
"""

import os
import sys
import unittest
from io import StringIO
from unittest.mock import patch

from sage.libs.io_utils.sink import PrintSink

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPrintSink(unittest.TestCase):
    """测试 PrintSink 类的功能"""

    def setUp(self):
        """测试前准备"""
        self.print_sink = PrintSink(quiet=True)
        self.print_sink_with_prefix = PrintSink(
            prefix="TEST", separator=" -> ", quiet=True
        )

    def test_simple_string(self):
        """测试简单字符串输出"""
        with patch("sys.stdout", new=StringIO()) as fake_out:
            self.print_sink.execute("Hello World")
            output = fake_out.getvalue().strip()
            self.assertEqual(output, "Hello World")

    def test_qa_tuple_colored(self):
        """测试问答对元组输出（彩色）"""
        qa_data = ("什么是Python?", "Python是一种编程语言")

        with patch("sys.stdout", new=StringIO()) as fake_out:
            self.print_sink.execute(qa_data)
            output = fake_out.getvalue().strip()
            # 检查是否包含问题和答案
            self.assertIn("什么是Python?", output)
            self.assertIn("Python是一种编程语言", output)
            self.assertIn("[Q]", output)
            self.assertIn("[A]", output)

    def test_qa_tuple_no_color(self):
        """测试问答对元组输出（无彩色）"""
        print_sink_no_color = PrintSink(colored=False, quiet=True)
        qa_data = ("什么是AI?", "AI是人工智能")

        with patch("sys.stdout", new=StringIO()) as fake_out:
            print_sink_no_color.execute(qa_data)
            output = fake_out.getvalue().strip()
            # 检查是否包含问题和答案，但不包含ANSI颜色代码
            self.assertIn("什么是AI?", output)
            self.assertIn("AI是人工智能", output)
            self.assertIn("[Q]", output)
            self.assertIn("[A]", output)
            self.assertNotIn("\033[", output)  # 不应包含ANSI颜色代码

    def test_retrieval_tuple(self):
        """测试检索结果元组输出"""
        retrieval_data = ("查询内容", ["结果1", "结果2", "结果3"])

        with patch("sys.stdout", new=StringIO()) as fake_out:
            self.print_sink.execute(retrieval_data)
            output = fake_out.getvalue().strip()
            self.assertIn("查询内容", output)
            self.assertIn("结果1", output)
            self.assertIn("结果2", output)
            self.assertIn("结果3", output)
            self.assertIn("[Q]", output)
            self.assertIn("[Chunks]", output)

    def test_string_list(self):
        """测试字符串列表输出"""
        list_data = ["项目1", "项目2", "项目3"]

        with patch("sys.stdout", new=StringIO()) as fake_out:
            self.print_sink.execute(list_data)
            output = fake_out.getvalue().strip()
            self.assertIn("- 项目1", output)
            self.assertIn("- 项目2", output)
            self.assertIn("- 项目3", output)

    def test_dictionary(self):
        """测试字典输出"""
        dict_data = {"name": "张三", "age": 25, "city": "北京"}

        with patch("sys.stdout", new=StringIO()) as fake_out:
            self.print_sink.execute(dict_data)
            output = fake_out.getvalue().strip()
            self.assertIn("name", output)
            self.assertIn("张三", output)
            self.assertIn("age", output)
            self.assertIn("25", output)

    def test_prefix_and_separator(self):
        """测试前缀和分隔符"""
        with patch("sys.stdout", new=StringIO()) as fake_out:
            self.print_sink_with_prefix.execute("测试数据")
            output = fake_out.getvalue().strip()
            self.assertIn("TEST -> 测试数据", output)

    def test_other_types(self):
        """测试其他数据类型"""
        with patch("sys.stdout", new=StringIO()) as fake_out:
            self.print_sink.execute(12345)
            output = fake_out.getvalue().strip()
            self.assertEqual(output, "12345")


if __name__ == "__main__":
    unittest.main()
