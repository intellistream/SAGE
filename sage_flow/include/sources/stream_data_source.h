#pragma once

#include "data_source.h"
#include <thread>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <atomic>

namespace sage_flow {

/**
 * @brief Stream-based data source implementation
 * 
 * Supports reading from continuous data streams such as:
 * - Network streams
 * - Pipes  
 * - Real-time data feeds
 * - WebSocket connections
 * 
 * This implementation follows SAGE's streaming pattern with features:
 * - Background thread for continuous data consumption
 * - Local buffer with backpressure handling (similar to Kafka implementation) 
 * - Lazy initialization for distributed environments
 * - Proper thread synchronization and resource cleanup
 */
class StreamDataSource : public DataSource {
 public:
  StreamDataSource() = default;
  ~StreamDataSource() override;

  // DataSource interface implementation
  auto initialize(const DataSourceConfig& config) -> bool override;
  auto has_next() -> bool override;
  auto next_message() -> std::unique_ptr<MultiModalMessage> override;
  void close() override;
  auto get_config() const -> const DataSourceConfig& override;
  auto is_initialized() const -> bool override;
  auto is_closed() const -> bool override;

  /**
   * @brief Get streaming statistics
   * @return Statistics about streaming performance
   */
  struct StreamingStats {
    size_t messages_received_;
    size_t buffer_size_;
    size_t max_buffer_size_;
    bool is_streaming_;
    std::string stream_status_;
  };
  auto get_streaming_stats() const -> StreamingStats;

 private:
  DataSourceConfig config_;
  std::string stream_url_;
  size_t buffer_size_ = 10000;  // Default buffer size
  bool initialized_ = false;
  bool closed_ = false;
  
  // Streaming state (similar to SAGE's KafkaSourceFunction background processing)
  std::atomic<bool> stream_active_{false};
  std::atomic<bool> running_{false};
  std::unique_ptr<std::thread> consumer_thread_;
  
  // Thread-safe buffer for incoming messages
  std::queue<std::string> message_buffer_;
  mutable std::mutex buffer_mutex_;
  std::condition_variable buffer_condition_;
  
  // Statistics
  mutable std::atomic<size_t> messages_received_{0};
  
  // Private methods
  void start_streaming();
  void stop_streaming(); 
  void consume_loop();  // Background thread main loop
  auto read_from_stream() -> std::string;  // Platform-specific implementation
  void cleanup_resources();
};

}  // namespace sage_flow
