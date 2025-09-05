#pragma once

#include <cstddef>
#include <string>

namespace sage_flow {

/**
 * @brief Statistics for Kafka data source consumption
 */
struct KafkaDataSourceStats {
  std::string topic_;
  std::string group_id_;
  bool consumer_active_;
  size_t buffer_size_;
  size_t max_buffer_size_;
  size_t messages_consumed_;
  std::string last_error_;
};

}  // namespace sage_flow