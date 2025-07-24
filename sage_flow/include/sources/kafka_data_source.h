#pragma once

#include "data_source.h"
#include <thread>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <chrono>

namespace sage_flow {

/**
 * @brief Kafka-based data source implementation
 * 
 * Supports reading from Apache Kafka topics with:
 * - Configurable consumer groups
 * - Automatic offset management  
 * - Batch processing support
 * - Backpressure handling with local buffering
 * 
 * This implementation closely follows SAGE's KafkaSourceFunction pattern:
 * - Lazy initialization for distributed serialization support
 * - Background consumer thread with local buffering
 * - Proper resource cleanup and connection management
 * - Configuration-driven setup with Kafka-specific parameters
 */
class KafkaDataSource : public DataSource {
 public:
  KafkaDataSource() = default;
  ~KafkaDataSource() override;

  // DataSource interface implementation
  auto initialize(const DataSourceConfig& config) -> bool override;
  auto has_next() -> bool override;
  auto next_message() -> std::unique_ptr<MultiModalMessage> override;
  void close() override;
  auto get_config() const -> const DataSourceConfig& override;
  auto is_initialized() const -> bool override;
  auto is_closed() const -> bool override;

  /**
   * @brief Get Kafka consumer statistics
   * @return Statistics about Kafka consumption
   */
  struct KafkaStats {
    std::string topic_;
    std::string group_id_;
    bool consumer_active_;
    size_t buffer_size_;
    size_t max_buffer_size_;
    size_t messages_consumed_;
    std::string last_error_;
  };
  auto get_kafka_stats() const -> KafkaStats;

 private:
  DataSourceConfig config_;
  
  // Kafka configuration (serializable, similar to SAGE's approach)
  std::string broker_list_;
  std::string topic_;
  std::string consumer_group_;
  std::string auto_offset_reset_ = "latest";
  std::string value_deserializer_ = "string";
  size_t buffer_size_ = 10000;
  size_t max_poll_records_ = 500;
  std::chrono::milliseconds consumer_timeout_{1000};
  
  // State management
  bool initialized_ = false;
  bool closed_ = false;
  
  // Runtime objects (non-serializable, created during lazy_init)
  std::atomic<bool> consumer_active_{false};
  std::atomic<bool> running_{false};
  std::unique_ptr<std::thread> consumer_thread_;
  
  // Message buffering system (similar to SAGE's _local_buffer)
  std::queue<std::string> message_buffer_;
  mutable std::mutex buffer_mutex_;
  std::condition_variable buffer_condition_;
  
  // Statistics and monitoring
  mutable std::atomic<size_t> messages_consumed_{0};
  mutable std::string last_error_;
  mutable std::mutex error_mutex_;
  
  // Private methods implementing SAGE's pattern
  void lazy_init();  // Similar to SAGE's _lazy_init()
  void consume_loop();  // Background thread main loop (like SAGE's _consume_loop)
  void cleanup_resources();  // Resource cleanup
  
  // Kafka-specific helpers
  auto parse_kafka_config() -> bool;
  auto create_kafka_consumer() -> bool;  // Platform-specific Kafka consumer creation  
  void handle_consumer_error(const std::string& error);
  auto deserialize_message(const std::string& raw_message) -> std::string;
};

}  // namespace sage_flow
