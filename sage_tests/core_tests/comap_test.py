import pytest
import time
import threading
from typing import List, Dict, Any
from sage_core.environment.base_environment import LocalEnvironment
from sage_core.function.source_function import SourceFunction
from sage_core.function.comap_function import BaseCoMapFunction
from sage_core.function.sink_function import SinkFunction
import json
import tempfile
from pathlib import Path

class OrderDataSource(SourceFunction):
    """生成订单数据"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.orders = [
            {"id": "order1", "user_id": "user1", "product": "laptop", "amount": 999.0, "type": "order"},
            {"id": "order2", "user_id": "user2", "product": "mouse", "amount": 29.9, "type": "order"},
            {"id": "order3", "user_id": "user1", "product": "keyboard", "amount": 79.0, "type": "order"},
            {"id": "order4", "user_id": "user3", "product": "monitor", "amount": 299.0, "type": "order"},
        ]
    
    def execute(self):
        if self.counter >= len(self.orders):
            return None
        
        data = self.orders[self.counter]
        self.counter += 1
        self.logger.info(f"OrderSource generated: {data}")
        return data


class PaymentDataSource(SourceFunction):
    """生成支付数据"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.payments = [
            {"id": "pay1", "order_id": "order1", "method": "credit_card", "status": "success", "type": "payment"},
            {"id": "pay2", "order_id": "order2", "method": "paypal", "status": "success", "type": "payment"},
            {"id": "pay3", "order_id": "order3", "method": "debit_card", "status": "failed", "type": "payment"},
            {"id": "pay4", "order_id": "order4", "method": "credit_card", "status": "pending", "type": "payment"},
        ]
    
    def execute(self):
        if self.counter >= len(self.payments):
            return None
        
        data = self.payments[self.counter]
        self.counter += 1
        self.logger.info(f"PaymentSource generated: {data}")
        return data


class InventoryDataSource(SourceFunction):
    """生成库存数据"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counter = 0
        self.inventory = [
            {"product": "laptop", "stock": 50, "warehouse": "WH1", "type": "inventory"},
            {"product": "mouse", "stock": 200, "warehouse": "WH1", "type": "inventory"},
            {"product": "keyboard", "stock": 0, "warehouse": "WH2", "type": "inventory"},
            {"product": "monitor", "stock": 30, "warehouse": "WH2", "type": "inventory"},
        ]
    
    def execute(self):
        if self.counter >= len(self.inventory):
            return None
        
        data = self.inventory[self.counter]
        self.counter += 1
        self.logger.info(f"InventorySource generated: {data}")
        return data


class CoMapDebugSink(SinkFunction):
    """调试用的Sink，通过文件系统记录CoMap处理结果"""
    
    def __init__(self, output_file=None, **kwargs):
        super().__init__(**kwargs)
        
        self.parallel_index = None
        self.received_count = 0
        # 如果没有指定输出文件，使用临时文件
        if output_file is None:
            self.output_file = Path(tempfile.gettempdir()) / "comap_test_results.json"
        else:
            self.output_file = Path(output_file)
        self.logger.info(f"CoMapDebugSink initialized, output file: {self.output_file}")
    def execute(self, data: Any):
        if self.runtime_context:
            self.parallel_index = self.runtime_context.parallel_index
        self.logger.info("!!!!!!")
        self.received_count += 1
        
        result_type = data.get('type', 'unknown')
        source_stream = data.get('source_stream', -1)
        
        # 准备要写入文件的记录
        record = {
            'timestamp': time.time(),
            'parallel_index': self.parallel_index,
            'received_count': self.received_count,
            'data': data
        }
        
        # 原子性地追加到文件
        self._append_record(record)
        
        self.logger.info(
            f"[Instance {self.parallel_index}] "
            f"Received {result_type} from stream {source_stream}: {data}"
        )
        
        # 打印调试信息
        print(f"🔍 [Instance {self.parallel_index}] Type: {result_type}, "
              f"Stream: {source_stream}, Data: {data}")
        
        return data
    
    def _append_record(self, record):
        """原子性地追加记录到文件"""
        import fcntl  # Unix文件锁
        
        try:
            # 以追加模式打开文件
            with open(self.output_file, 'a') as f:
                # 获取文件锁
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                # 写入一行JSON
                f.write(json.dumps(record) + '\n')
                f.flush()
                # 锁会在with块结束时自动释放
        except Exception as e:
            self.logger.error(f"Failed to write record: {e}")
    
    @staticmethod
    def read_results(output_file=None):
        """读取测试结果"""
        if output_file is None:
            output_file = Path(tempfile.gettempdir()) / "comap_test_results.json"
        else:
            output_file = Path(output_file)
        
        if not output_file.exists():
            return {}
        
        results = {}
        try:
            with open(output_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        record = json.loads(line)
                        parallel_index = record.get('parallel_index', 0)
                        if parallel_index not in results:
                            results[parallel_index] = []
                        results[parallel_index].append(record['data'])
        except Exception as e:
            print(f"Error reading results: {e}")
        print(f"📂 Read {len(results)} parallel instances from results file: {output_file}")
        return results
    
    @staticmethod
    def clear_results(output_file=None):
        """清理结果文件"""
        if output_file is None:
            output_file = Path(tempfile.gettempdir()) / "comap_test_results.json"
        else:
            output_file = Path(output_file)
        
        if output_file.exists():
            output_file.unlink()


class OrderPaymentCoMapFunction(BaseCoMapFunction):
    """CoMap函数：处理订单和支付数据"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.processed_orders = 0
        self.processed_payments = 0
    
    def map0(self, order_data):
        """处理订单数据流 (stream 0)"""
        self.processed_orders += 1
        
        result = {
            "type": "processed_order",
            "order_id": order_data["id"],
            "user_id": order_data["user_id"],
            "product": order_data["product"],
            "amount": order_data["amount"],
            "processing_sequence": self.processed_orders,
            "source_stream": 0,
            "processor": "OrderProcessor"
        }
        
        self.logger.info(f"CoMap map0: processed order {order_data['id']} (#{self.processed_orders})")
        return result
    
    def map1(self, payment_data):
        """处理支付数据流 (stream 1)"""
        self.processed_payments += 1
        
        result = {
            "type": "processed_payment",
            "payment_id": payment_data["id"],
            "order_id": payment_data["order_id"],
            "method": payment_data["method"],
            "status": payment_data["status"],
            "processing_sequence": self.processed_payments,
            "source_stream": 1,
            "processor": "PaymentProcessor"
        }
        
        self.logger.info(f"CoMap map1: processed payment {payment_data['id']} (#{self.processed_payments})")
        return result


class TripleStreamCoMapFunction(BaseCoMapFunction):
    """三路CoMap函数：处理订单、支付和库存数据"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stream_counters = [0, 0, 0]  # 每个流的处理计数
    
    def map0(self, order_data):
        """处理订单数据流 (stream 0)"""
        self.stream_counters[0] += 1
        
        result = {
            "type": "enriched_order",
            "order_id": order_data["id"],
            "user_id": order_data["user_id"],
            "product": order_data["product"],
            "amount": order_data["amount"],
            "stream_sequence": self.stream_counters[0],
            "source_stream": 0,
            "enrichment": "order_enriched"
        }
        
        self.logger.info(f"TripleCoMap map0: enriched order {order_data['id']}")
        return result
    
    def map1(self, payment_data):
        """处理支付数据流 (stream 1)"""
        self.stream_counters[1] += 1
        
        result = {
            "type": "enriched_payment",
            "payment_id": payment_data["id"],
            "order_id": payment_data["order_id"],
            "method": payment_data["method"],
            "status": payment_data["status"],
            "stream_sequence": self.stream_counters[1],
            "source_stream": 1,
            "enrichment": "payment_enriched"
        }
        
        self.logger.info(f"TripleCoMap map1: enriched payment {payment_data['id']}")
        return result
    
    def map2(self, inventory_data):
        """处理库存数据流 (stream 2)"""
        self.stream_counters[2] += 1
        
        result = {
            "type": "enriched_inventory",
            "product": inventory_data["product"],
            "stock": inventory_data["stock"],
            "warehouse": inventory_data["warehouse"],
            "stream_sequence": self.stream_counters[2],
            "source_stream": 2,
            "enrichment": "inventory_enriched"
        }
        
        self.logger.info(f"TripleCoMap map2: enriched inventory {inventory_data['product']}")
        return result


class StatefulCoMapFunction(BaseCoMapFunction):
    """有状态的CoMap函数，演示状态维护"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.order_cache = {}      # 订单缓存
        self.payment_stats = {     # 支付统计
            "total_amount": 0.0,
            "success_count": 0,
            "failed_count": 0
        }
    
    def map0(self, order_data):
        """处理订单数据，缓存订单信息"""
        order_id = order_data["id"]
        self.order_cache[order_id] = order_data
        
        result = {
            "type": "cached_order",
            "order_id": order_id,
            "user_id": order_data["user_id"],
            "amount": order_data["amount"],
            "cache_size": len(self.order_cache),
            "source_stream": 0
        }
        
        self.logger.info(f"StatefulCoMap map0: cached order {order_id}, cache size: {len(self.order_cache)}")
        return result
    
    def map1(self, payment_data):
        """处理支付数据，更新统计并关联订单"""
        order_id = payment_data["order_id"]
        payment_status = payment_data["status"]
        
        # 更新支付统计
        if payment_status == "success":
            self.payment_stats["success_count"] += 1
            # 查找对应订单金额
            order_info = self.order_cache.get(order_id, {})
            if "amount" in order_info:
                self.payment_stats["total_amount"] += order_info["amount"]
        elif payment_status == "failed":
            self.payment_stats["failed_count"] += 1
        
        result = {
            "type": "enriched_payment_with_stats",
            "payment_id": payment_data["id"],
            "order_id": order_id,
            "status": payment_status,
            "method": payment_data["method"],
            "order_info": self.order_cache.get(order_id, {"error": "order_not_found"}),
            "payment_stats": dict(self.payment_stats),  # 复制当前统计
            "source_stream": 1
        }
        
        self.logger.info(f"StatefulCoMap map1: processed payment {payment_data['id']}, stats: {self.payment_stats}")
        return result


class InvalidCoMapFunction(BaseCoMapFunction):
    """无效的CoMap函数，缺少必需的map1方法（测试用）"""
    
    def map0(self, data):
        return {"processed": data, "source_stream": 0}
    
    # 故意不实现map1方法


class TestCoMapFunctionality:
    """测试CoMap功能"""
    
    def setup_method(self):
        # 清理结果文件
        CoMapDebugSink.clear_results()
    
    def test_basic_two_stream_comap(self):
        """测试基本的两路CoMap处理"""
        print("\n🚀 Testing Basic Two-Stream CoMap")
        
        env = LocalEnvironment("basic_comap_test")
        
        order_stream = env.from_source(OrderDataSource, delay=0.3)
        payment_stream = env.from_source(PaymentDataSource, delay=0.4)
        
        result_stream = (
            order_stream
            .connect(payment_stream)
            .comap(OrderPaymentCoMapFunction)
            .sink(CoMapDebugSink, parallelism=2)
            .print()
        )
        
        print("📊 Pipeline: OrderStream + PaymentStream -> comap(OrderPaymentCoMapFunction) -> Sink(parallelism=2)")
        print("🎯 Expected: Orders processed by map0, Payments processed by map1\n")
        
        try:
            env.submit()
            env.run_streaming()
            time.sleep(10)
        finally:
            env.close()
        
        # 等待一下确保文件写入完成
        time.sleep(1)
        self._verify_two_stream_comap_results()
    
    def _verify_two_stream_comap_results(self):
        """验证两路CoMap的结果"""
        received_data = CoMapDebugSink.read_results()
        
        print("\n📋 Two-Stream CoMap Results:")
        print("=" * 50)
        
        processed_orders = []
        processed_payments = []
        
        for instance_id, data_list in received_data.items():
            print(f"\n🔹 Parallel Instance {instance_id}:")
            
            for data in data_list:
                result_type = data.get("type", "unknown")
                source_stream = data.get("source_stream", -1)
                processor = data.get("processor", "unknown")
                
                if result_type == "processed_order":
                    processed_orders.append(data)
                    order_id = data.get("order_id", "unknown")
                    sequence = data.get("processing_sequence", 0)
                    print(f"   - {processor}: Order {order_id} (seq #{sequence}) from stream {source_stream}")
                    
                elif result_type == "processed_payment":
                    processed_payments.append(data)
                    payment_id = data.get("payment_id", "unknown")
                    sequence = data.get("processing_sequence", 0)
                    status = data.get("status", "unknown")
                    print(f"   - {processor}: Payment {payment_id} ({status}, seq #{sequence}) from stream {source_stream}")
        
        print(f"\n🎯 CoMap Processing Summary:")
        print(f"   - Processed orders: {len(processed_orders)}")
        print(f"   - Processed payments: {len(processed_payments)}")
        
        # 验证：应该有订单和支付处理结果
        assert len(processed_orders) > 0, "❌ No processed orders received"
        assert len(processed_payments) > 0, "❌ No processed payments received"
        
        # 验证：所有订单都来自stream 0
        for order in processed_orders:
            assert order.get("source_stream") == 0, f"❌ Order from wrong stream: {order.get('source_stream')}"
        
        # 验证：所有支付都来自stream 1  
        for payment in processed_payments:
            assert payment.get("source_stream") == 1, f"❌ Payment from wrong stream: {payment.get('source_stream')}"
        
        print("✅ Two-stream CoMap test passed: Correct stream routing and processing")


if __name__ == "__main__":
    # 可以直接运行单个测试
    test = TestCoMapFunctionality()
    test.setup_method()
    test.test_basic_two_stream_comap()

'''
# 运行所有CoMap测试
pytest sage_tests/core_tests/comap_test.py -v -s

# 运行特定测试
pytest sage_tests/core_tests/comap_test.py::TestCoMapFunctionality::test_basic_two_stream_comap -v -s
pytest sage_tests/core_tests/comap_test.py::TestCoMapFunctionality::test_three_stream_comap -v -s
pytest sage_tests/core_tests/comap_test.py::TestCoMapFunctionality::test_stateful_comap -v -s
'''