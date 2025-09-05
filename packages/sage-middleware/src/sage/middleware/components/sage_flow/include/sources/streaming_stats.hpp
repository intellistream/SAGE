#pragma once

#include <chrono>
#include <cstddef>
#include <string>

namespace sage_flow {

/**
 * @brief Statistics for reading operations
 */
struct ReadingStats {
  size_t bytes_read_;
  size_t total_bytes_;
  double read_rate_;  // bytes per second
  std::chrono::steady_clock::time_point start_time_;
  std::chrono::steady_clock::time_point last_read_time_;
  bool is_active_;
};

/**
 * @brief Statistics for Kafka operations
 */
struct KafkaStats {
  std::string topic_;
  std::string group_id_;
  size_t partition_count_;
  size_t consumer_count_;
  size_t messages_processed_;
  size_t messages_failed_;
  double processing_rate_;  // messages per second
  std::string last_error_;
  bool is_connected_;
};

/**
 * @brief Statistics for streaming operations
 */
struct StreamingStats {
  size_t total_events_;
  size_t processed_events_;
  size_t failed_events_;
  double throughput_;  // events per second
  std::chrono::steady_clock::time_point window_start_;
  std::chrono::milliseconds window_duration_;
  bool is_streaming_;
  std::string stream_id_;
};

}  // namespace sage_flow