#!/usr/bin/env python3
"""
简化批处理系统基础演示

展示新设计的核心特性：
1. 批处理算子自己进行迭代
2. 当迭代返回空时自动发送停止信号
3. 支持基本的数据流处理
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sage_core.api.local_environment import LocalEnvironment


def demo_basic_batch():
    """基础批处理演示"""
    print("🚀 简化批处理系统基础演示")
    print("=" * 50)
    
    # 创建本地环境
    env = LocalEnvironment("batch_demo")
    
    # 创建一些测试数据
    test_data = ["数据1", "数据2", "数据3", "数据4", "数据5"]
    print(f"测试数据: {test_data}")
    print()
    
    # 使用批处理接口创建数据流
    print("创建批处理数据流...")
    data_stream = env.from_batch_collection(test_data)
    
    # 添加打印输出
    data_stream.print("批处理输出: ")
    
    print("提交并执行批处理任务...")
    
    # 提交环境以执行
    env.submit()
    
    print("\n✅ 批处理演示完成!")
    print("=" * 50)


def demo_file_batch():
    """文件批处理演示"""
    import tempfile
    
    print("📁 文件批处理演示")
    print("=" * 50)
    
    # 创建临时测试文件
    test_content = ["第一行", "第二行", "第三行", "第四行"]
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        for line in test_content:
            f.write(line + '\n')
        temp_file = f.name
    
    try:
        print(f"临时文件: {temp_file}")
        print(f"文件内容: {test_content}")
        print()
        
        # 创建环境并处理文件
        env = LocalEnvironment("file_batch_demo")
        
        print("创建文件批处理数据流...")
        file_stream = env.from_batch_file(temp_file)
        
        # 添加处理和输出
        file_stream.print("文件行: ")
        
        print("执行文件批处理...")
        env.submit()
        
    finally:
        # 清理临时文件
        os.unlink(temp_file)
    
    print("\n✅ 文件批处理演示完成!")
    print("=" * 50)


def demo_range_batch():
    """范围批处理演示"""
    print("🔢 范围批处理演示")
    print("=" * 50)
    
    env = LocalEnvironment("range_batch_demo")
    
    # 生成1到10的数字
    print("生成范围: 1 到 10")
    range_stream = env.from_batch_range(1, 11)
    
    # 添加处理
    range_stream.map(lambda x: x * x).print("平方数: ")
    
    print("执行范围批处理...")
    env.submit()
    
    print("\n✅ 范围批处理演示完成!")
    print("=" * 50)


if __name__ == "__main__":
    print("🌟 SAGE 简化批处理系统演示")
    print("本演示展示了新的简化批处理设计")
    print()
    
    # 运行基础演示
    demo_basic_batch()
    print()
    
    # 运行文件演示
    demo_file_batch()
    print()
    
    # 运行范围演示
    demo_range_batch()
    
    print("\n" + "=" * 60)
    print("🎉 所有演示完成!")
    print("关键特性:")
    print("✅ 批处理算子自动迭代")
    print("✅ 自动发送停止信号")
    print("✅ 支持多种数据源")
    print("✅ 简化的用户接口")
    print("=" * 60)
