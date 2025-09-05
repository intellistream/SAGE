#pragma once

#include <cstddef>

namespace sage_flow {

/**
 * @brief Statistics for file data source reading progress
 */
struct FileDataSourceStats {
  size_t total_files_;
  size_t current_file_index_;
  size_t current_position_;
  size_t total_lines_read_;
};

}  // namespace sage_flow