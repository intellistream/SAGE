#pragma once

#include <atomic>
#include <chrono>
#include <cstdint>

namespace sage_flow {

/**
 * @brief Performance metrics for stream engine monitoring
 */
struct PerformanceMetrics {
  std::atomic<uint64_t> total_processed_messages{0};
  std::atomic<uint64_t> total_failed_messages{0};
  std::atomic<double> avg_processing_time_ms{0.0};
  std::atomic<double> current_throughput{0.0};
  std::atomic<uint64_t> memory_usage_bytes{0};
  std::chrono::steady_clock::time_point start_time;

  // Default constructor
  PerformanceMetrics() = default;

  // Custom copy constructor to handle atomic members
  PerformanceMetrics(const PerformanceMetrics& other) {
    total_processed_messages = other.total_processed_messages.load();
    total_failed_messages = other.total_failed_messages.load();
    avg_processing_time_ms = other.avg_processing_time_ms.load();
    current_throughput = other.current_throughput.load();
    memory_usage_bytes = other.memory_usage_bytes.load();
    start_time = other.start_time;
  }

  // Custom assignment operator
  PerformanceMetrics& operator=(const PerformanceMetrics& other) {
    if (this != &other) {
      total_processed_messages = other.total_processed_messages.load();
      total_failed_messages = other.total_failed_messages.load();
      avg_processing_time_ms = other.avg_processing_time_ms.load();
      current_throughput = other.current_throughput.load();
      memory_usage_bytes = other.memory_usage_bytes.load();
      start_time = other.start_time;
    }
    return *this;
  }

  auto reset() -> void {
    total_processed_messages = 0;
    total_failed_messages = 0;
    avg_processing_time_ms = 0.0;
    current_throughput = 0.0;
    memory_usage_bytes = 0;
    start_time = std::chrono::steady_clock::now();
  }
};

}  // namespace sage_flow