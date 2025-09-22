#!/usr/bin/env python3
"""
SAGE高性能队列使用示例
演示在SAGE系统中如何使用mmap_queue进行高效的进程间通信
"""

import sys
import os
import time
import multiprocessing

# 添加sage.common.utils到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sage.extensions.sage_queue import SageQueue, SageQueueRef, destroy_queue


class SAGEDataProcessor:
    """SAGE数据处理组件示例"""
    
    def __init__(self, processor_id: str):
        self.processor_id = processor_id
        self.processed_count = 0
    
    def process_batch(self, input_queue_name: str, output_queue_name: str, batch_size: int):
        """处理一批数据"""
        print(f"[{self.processor_id}] 开始处理批次，大小: {batch_size}")
        
        input_queue = SageQueue(input_queue_name)
        output_queue = SageQueue(output_queue_name)
        
        try:
            for i in range(batch_size):
                # 从输入队列读取原始数据
                raw_data = input_queue.get(timeout=5.0)
                
                # 模拟SAGE数据处理
                processed_data = {
                    'processor_id': self.processor_id,
                    'original_data': raw_data,
                    'processed_timestamp': time.time(),
                    'processing_results': {
                        'feature_vector': [x * 2 for x in raw_data.get('values', [])],
                        'metadata': f"Processed by SAGE component {self.processor_id}",
                        'confidence': 0.95
                    }
                }
                
                # 写入输出队列
                output_queue.put(processed_data)
                self.processed_count += 1
                
                if (i + 1) % 100 == 0:
                    print(f"[{self.processor_id}] 已处理 {i + 1}/{batch_size}")
        
        except Exception as e:
            print(f"[{self.processor_id}] 处理错误: {e}")
        
        finally:
            input_queue.close()
            output_queue.close()
            
        print(f"[{self.processor_id}] 批处理完成，总计: {self.processed_count}")


def sage_data_generator(queue_name: str, data_count: int):
    """SAGE数据生成器进程"""
    print(f"数据生成器: 开始生成 {data_count} 条数据")
    
    queue = SageQueue(queue_name)
    
    try:
        for i in range(data_count):
            # 模拟SAGE系统的真实数据
            data_item = {
                'id': i,
                'timestamp': time.time(),
                'source': 'SAGE_sensor_array',
                'values': [i + j for j in range(10)],  # 10维特征向量
                'metadata': {
                    'sensor_type': 'lidar' if i % 2 == 0 else 'camera',
                    'quality': 'high',
                    'location': f"sensor_{i % 5}"
                }
            }
            
            queue.put(data_item)
            
            if (i + 1) % 200 == 0:
                print(f"数据生成器: 已生成 {i + 1}/{data_count}")
                
            # 模拟真实数据生成速率
            time.sleep(0.001)
    
    except Exception as e:
        print(f"数据生成器错误: {e}")
    
    finally:
        queue.close()
    
    print(f"数据生成器: 完成，总计生成 {data_count} 条数据")


def sage_result_collector(queue_name: str, expected_count: int):
    """SAGE结果收集器进程"""
    print(f"结果收集器: 开始收集，预期 {expected_count} 条结果")
    
    queue = SageQueue(queue_name)
    results = []
    
    try:
        start_time = time.time()
        
        while len(results) < expected_count:
            try:
                result = queue.get(timeout=2.0)
                results.append(result)
                
                if len(results) % 100 == 0:
                    print(f"结果收集器: 已收集 {len(results)}/{expected_count}")
                    
            except Exception as e:
                if "timed out" in str(e):
                    elapsed = time.time() - start_time
                    if elapsed > 30:  # 30秒超时
                        print(f"结果收集器: 超时，只收集到 {len(results)} 条结果")
                        break
                    continue
                else:
                    raise
        
        # 分析结果
        processor_stats = {}
        for result in results:
            pid = result.get('processor_id', 'unknown')
            processor_stats[pid] = processor_stats.get(pid, 0) + 1
        
        print(f"结果收集器: 完成，收集 {len(results)} 条结果")
        print(f"处理器统计: {processor_stats}")
        
        return results
    
    except Exception as e:
        print(f"结果收集器错误: {e}")
        return results
    
    finally:
        queue.close()


def demonstration_simple_pipeline():
    """演示简单的SAGE数据处理流水线"""
    print("\n" + "="*50)
    print("SAGE简单流水线演示")
    print("="*50)
    
    # 队列名称
    input_queue_name = "sage_input"
    output_queue_name = "sage_output"
    
    # 清理旧队列
    destroy_queue(input_queue_name)
    destroy_queue(output_queue_name)
    
    # 创建队列
    input_queue = SageQueue(input_queue_name, maxsize=128*1024)
    output_queue = SageQueue(output_queue_name, maxsize=128*1024)
    
    # 配置参数
    data_count = 500
    processor_count = 2
    
    print(f"配置: {data_count} 条数据, {processor_count} 个处理器")
    
    try:
        # 启动数据生成器
        generator_process = multiprocessing.Process(
            target=sage_data_generator,
            args=(input_queue_name, data_count)
        )
        generator_process.start()
        
        # 启动处理器
        processors = []
        for i in range(processor_count):
            processor = SAGEDataProcessor(f"SAGE_Processor_{i}")
            process = multiprocessing.Process(
                target=processor.process_batch,
                args=(input_queue_name, output_queue_name, data_count // processor_count)
            )
            process.start()
            processors.append(process)
        
        # 启动结果收集器
        collector_process = multiprocessing.Process(
            target=sage_result_collector,
            args=(output_queue_name, data_count)
        )
        collector_process.start()
        
        # 等待所有进程完成
        print("等待数据生成器完成...")
        generator_process.join(timeout=30)
        
        print("等待处理器完成...")
        for proc in processors:
            proc.join(timeout=30)
        
        print("等待结果收集器完成...")
        collector_process.join(timeout=30)
        
        # 显示最终统计
        input_stats = input_queue.get_stats()
        output_stats = output_queue.get_stats()
        
        print(f"\n✓ 流水线演示完成:")
        print(f"  输入队列: 写入 {input_stats['total_bytes_written']} 字节")
        print(f"  输出队列: 读取 {output_stats['total_bytes_read']} 字节") 
        print(f"  处理效率: {output_stats['utilization']:.2%}")
        
    except Exception as e:
        print(f"✗ 流水线演示失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        input_queue.close()
        output_queue.close()
        
        # 清理进程
        for proc in [generator_process] + processors + [collector_process]:
            if proc.is_alive():
                proc.terminate()


def demonstration_queue_reference():
    """演示队列引用在分布式系统中的使用"""
    print("\n" + "="*50)
    print("SAGE队列引用演示")
    print("="*50)
    
    queue_name = "sage_reference_demo"
    destroy_queue(queue_name)
    
    # 主进程创建队列
    main_queue = SageQueue(queue_name, maxsize=32*1024)
    print("✓ 主进程创建队列")
    
    # 添加一些测试数据
    for i in range(10):
        data = {
            'message_id': i,
            'content': f"SAGE Message {i}",
            'sensor_data': list(range(i*10, (i+1)*10)),
            'timestamp': time.time()
        }
        main_queue.put(data)
    
    print("✓ 添加测试数据")
    
    # 获取队列引用
    queue_ref = main_queue.get_reference()
    print(f"✓ 获取队列引用: {queue_ref}")
    
    # 子进程使用引用访问队列
    def worker_process(queue_ref_state, worker_id):
        # 反序列化引用
        import pickle
        ref = pickle.loads(queue_ref_state)
        
        # 从引用获取队列实例
        worker_queue = ref.get_queue()
        print(f"工作进程{worker_id}: 从引用获取队列实例")
        
        # 处理数据
        processed = 0
        try:
            while processed < 5:  # 每个工作进程处理5条数据
                data = worker_queue.get(timeout=2.0)
                print(f"工作进程{worker_id}: 处理消息 {data['message_id']}")
                processed += 1
        except:
            pass
        
        worker_queue.close()
        print(f"工作进程{worker_id}: 处理完成 {processed} 条数据")
    
    # 序列化引用用于跨进程传递
    import pickle
    queue_ref_state = pickle.dumps(queue_ref)
    
    # 启动工作进程
    workers = []
    for i in range(2):
        process = multiprocessing.Process(
            target=worker_process,
            args=(queue_ref_state, i)
        )
        process.start()
        workers.append(process)
    
    # 等待工作进程完成
    for process in workers:
        process.join(timeout=10)
    
    # 检查剩余数据
    remaining = 0
    while not main_queue.empty():
        try:
            main_queue.get_nowait()
            remaining += 1
        except:
            break
    
    print(f"✓ 队列引用演示完成，剩余数据: {remaining}")
    main_queue.close()


def main():
    """主演示函数"""
    print("SAGE高性能内存映射队列使用演示")
    print("基于mmap的零拷贝进程间通信解决方案")
    
    try:
        # 演示1: 简单流水线
        demonstration_simple_pipeline()
        
        # 演示2: 队列引用
        demonstration_queue_reference()
        
        print("\n" + "="*50)
        print("🎉 所有演示完成!")
        print("SAGE高性能队列可以显著提升分布式系统的通信效率")
        print("="*50)
        
    except Exception as e:
        print(f"✗ 演示过程出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 设置多进程启动方法
    if hasattr(multiprocessing, 'set_start_method'):
        try:
            multiprocessing.set_start_method('spawn')
        except RuntimeError:
            pass
    
    main()
