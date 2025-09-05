#pragma once

#include <cstddef>
#include <string>

namespace sage_flow {

/**
 * @brief Statistics for stream data source performance
 */
struct StreamDataSourceStats {
  size_t messages_received_;
  size_t buffer_size_;
  size_t max_buffer_size_;
  bool is_streaming_;
  std::string stream_status_;
};

}  // namespace sage_flow