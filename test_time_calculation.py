#!/usr/bin/env python3
"""
验证监控系统时间计算逻辑的测试脚本
"""
from sage.kernel.runtime.monitoring.metrics_collector import MetricsCollector
from sage.kernel.runtime.monitoring.metrics import PacketMetrics
import time

print("="*70)
print("验证监控系统时间计算逻辑")
print("="*70)

collector = MetricsCollector(name="time_test")

# 测试1: 基本时间计算
print("\n[测试1] 基本时间计算逻辑")
print("-"*70)
packet_id = "test_001"
start = time.time()
collector.record_packet_start(packet_id)
time.sleep(0.1)  # 模拟100ms处理时间
collector.record_packet_end(packet_id, success=True)
end = time.time()

# 获取指标
metrics = collector.get_real_time_metrics()
actual_duration = (end - start) * 1000  # 转换为毫秒

print(f"实际耗时: {actual_duration:.2f} ms")
print(f"记录的执行时间: {metrics.avg_latency:.2f} ms")
print(f"差异: {abs(actual_duration - metrics.avg_latency):.2f} ms")
diff_percent = abs(actual_duration - metrics.avg_latency) / actual_duration * 100
print(f"差异百分比: {diff_percent:.2f}%")

if abs(actual_duration - metrics.avg_latency) < 10:  # 允许10ms误差
    print("✓ 时间计算准确")
else:
    print("✗ 时间计算存在较大误差")

# 测试2: 队列等待时间
print("\n[测试2] 队列等待时间计算")
print("-"*70)
collector.reset_metrics()
packet_id2 = "test_002"

# 手动设置arrival_time和processing_start_time
arrival = time.time()
wait_delay = 0.05  # 50ms等待
time.sleep(wait_delay)
processing_start = time.time()

# 模拟包的生命周期
packet = PacketMetrics(packet_id=packet_id2)
packet.arrival_time = arrival
packet.processing_start_time = processing_start
packet.processing_end_time = processing_start + 0.03  # 30ms处理
packet.calculate_times()

print(f"到达时间: {arrival:.6f}")
print(f"开始处理时间: {processing_start:.6f}")
print(f"结束时间: {packet.processing_end_time:.6f}")
wait_ms = packet.queue_wait_time * 1000
expected_wait_ms = wait_delay * 1000
print(f"队列等待时间: {wait_ms:.2f} ms (预期: ~{expected_wait_ms:.2f} ms)")
exec_ms = packet.execution_time * 1000
print(f"执行时间: {exec_ms:.2f} ms (预期: ~30 ms)")

wait_time_error = abs(packet.queue_wait_time - wait_delay) * 1000
exec_time_error = abs(packet.execution_time - 0.03) * 1000

if wait_time_error < 5:
    print("✓ 队列等待时间计算准确")
else:
    print(f"✗ 队列等待时间误差: {wait_time_error:.2f} ms")

if exec_time_error < 5:
    print("✓ 执行时间计算准确")
else:
    print(f"✗ 执行时间误差: {exec_time_error:.2f} ms")

# 测试3: TPS计算
print("\n[测试3] TPS (每秒吞吐量) 计算")
print("-"*70)
collector.reset_metrics()

start_time = time.time()
num_packets = 10
for i in range(num_packets):
    pid = f"tps_test_{i}"
    collector.record_packet_start(pid)
    time.sleep(0.01)  # 10ms间隔
    collector.record_packet_end(pid, success=True)

elapsed = time.time() - start_time
metrics = collector.get_real_time_metrics()

expected_tps = num_packets / elapsed
actual_tps = metrics.packets_per_second

print(f"处理包数: {num_packets}")
print(f"总耗时: {elapsed:.3f} 秒")
print(f"预期 TPS: {expected_tps:.2f}")
print(f"实际 TPS: {actual_tps:.2f}")
print(f"差异: {abs(expected_tps - actual_tps):.2f}")
tps_diff_percent = abs(expected_tps - actual_tps) / expected_tps * 100
print(f"差异百分比: {tps_diff_percent:.2f}%")

if abs(expected_tps - actual_tps) / expected_tps < 0.05:  # 允许5%误差
    print("✓ TPS计算准确")
else:
    print("✗ TPS计算存在误差")

# 测试4: 时间窗口TPS
print("\n[测试4] 时间窗口TPS计算")
print("-"*70)
collector.reset_metrics()

# 在1分钟内发送一些包
for i in range(5):
    pid = f"window_test_{i}"
    collector.record_packet_start(pid)
    collector.record_packet_end(pid, success=True)
    time.sleep(0.01)

metrics = collector.get_real_time_metrics()
print(f"最近1分钟TPS: {metrics.last_minute_tps:.4f}")
print(f"最近5分钟TPS: {metrics.last_5min_tps:.4f}")
print(f"最近1小时TPS: {metrics.last_hour_tps:.4f}")

# 验证时间窗口逻辑
if metrics.last_minute_tps >= metrics.last_5min_tps >= metrics.last_hour_tps:
    print("✓ 时间窗口TPS递减关系正确")
else:
    print("⚠ 时间窗口TPS关系异常（可能因为时间太短）")

# 测试5: 百分位数计算
print("\n[测试5] 延迟百分位数计算")
print("-"*70)
collector.reset_metrics()

# 创建已知分布的延迟
latencies_ms = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # 1-10ms
for lat in latencies_ms:
    pid = f"perc_test_{lat}"
    collector.record_packet_start(pid)
    time.sleep(lat / 1000.0)
    collector.record_packet_end(pid, success=True)

metrics = collector.get_real_time_metrics()
print(f"P50 (中位数): {metrics.p50_latency:.2f} ms (预期: ~5.5 ms)")
print(f"P95: {metrics.p95_latency:.2f} ms (预期: ~9.5 ms)")
print(f"P99: {metrics.p99_latency:.2f} ms (预期: ~9.9 ms)")
print(f"最小延迟: {metrics.min_latency:.2f} ms (预期: ~1 ms)")
print(f"最大延迟: {metrics.max_latency:.2f} ms (预期: ~10 ms)")
print(f"平均延迟: {metrics.avg_latency:.2f} ms (预期: ~5.5 ms)")

# 验证P50应该接近中位数
if 4 <= metrics.p50_latency <= 7:
    print("✓ P50计算合理")
else:
    print(f"⚠ P50值 {metrics.p50_latency:.2f} 超出预期范围")

# 验证P95应该接近高值
if 8 <= metrics.p95_latency <= 11:
    print("✓ P95计算合理")
else:
    print(f"⚠ P95值 {metrics.p95_latency:.2f} 超出预期范围")

print("\n" + "="*70)
print("时间计算逻辑验证完成")
print("="*70)
