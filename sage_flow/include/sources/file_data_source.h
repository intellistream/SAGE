#pragma once

#include "data_source.h"
#include <fstream>
#include <vector>
#include <string>

namespace sage_flow {

/**
 * @brief File-based data source implementation
 * 
 * Supports reading from various file formats including:
 * - Plain text files (.txt)
 * - CSV files (.csv) 
 * - JSON files (.json)
 * - And other structured formats
 * 
 * This implementation follows SAGE's FileSource pattern with features:
 * - Position tracking for resumable reading (similar to file_pos in Python)
 * - Support for multiple file processing with directory scanning
 * - Lazy initialization for distributed environments
 * - Proper resource management and cleanup
 */
class FileDataSource : public DataSource {
 public:
  FileDataSource() = default;
  ~FileDataSource() override;

  // DataSource interface implementation
  auto initialize(const DataSourceConfig& config) -> bool override;
  auto has_next() -> bool override;
  auto next_message() -> std::unique_ptr<MultiModalMessage> override;
  void close() override;
  auto get_config() const -> const DataSourceConfig& override;
  auto is_initialized() const -> bool override;
  auto is_closed() const -> bool override;

  /**
   * @brief Reset reading position to beginning
   * Similar to ContextFileSource.reset() in SAGE Python implementation
   */
  void reset();
  
  /**
   * @brief Skip to specific file index (for multi-file processing)
   * @param index File index to skip to
   */
  void skip_to_index(size_t index);
  
  /**
   * @brief Get current reading statistics
   * @return Statistics about reading progress
   */
  struct ReadingStats {
    size_t total_files_;
    size_t current_file_index_;
    size_t current_position_;
    size_t total_lines_read_;
  };
  auto get_reading_stats() const -> ReadingStats;

 private:
  DataSourceConfig config_;
  std::string file_path_;
  std::string format_;
  bool recursive_ = false;
  bool initialized_ = false;
  bool closed_ = false;
  
  // File reading state (similar to SAGE's FileSource implementation)
  std::ifstream current_file_;
  size_t current_position_ = 0;
  std::vector<std::string> file_list_;
  size_t current_file_index_ = 0;
  size_t total_lines_read_ = 0;
  
  // Private helper methods
  auto scan_files(const std::string& path, bool recursive) -> std::vector<std::string>;
  auto open_next_file() -> bool;
  auto read_line_from_current_file() -> std::string;
  auto is_supported_format(const std::string& file_path) const -> bool;
  void cleanup_current_file();
};

}  // namespace sage_flow
