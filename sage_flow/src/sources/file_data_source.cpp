#include "sources/file_data_source.h"
#include "message/multimodal_message.h"
#include <filesystem>
#include <algorithm>

namespace sage_flow {

FileDataSource::~FileDataSource() {
  // Don't call virtual method in destructor
  if (!closed_) {
    cleanup_current_file();
    closed_ = true;
  }
}

auto FileDataSource::initialize(const DataSourceConfig& config) -> bool {
  if (initialized_) {
    return true;
  }
  
  config_ = config;
  
  // Extract configuration parameters
  file_path_ = config_.get_property("file_path", "");
  if (file_path_.empty()) {
    return false;
  }
  
  format_ = config_.get_property("format", "txt");
  recursive_ = (config_.get_property("recursive", "false") == "true");
  
  // Scan for files to process
  file_list_ = scan_files(file_path_, recursive_);
  if (file_list_.empty()) {
    return false;
  }
  
  // Reset state
  current_file_index_ = 0;
  current_position_ = 0;
  total_lines_read_ = 0;
  
  initialized_ = true;
  return true;
}

auto FileDataSource::has_next() -> bool {
  if (!initialized_ || closed_) {
    return false;
  }
  
  // Check if current file has more data
  if (current_file_.is_open() && !current_file_.eof()) {
    return true;
  }
  
  // Check if there are more files to process
  return current_file_index_ < file_list_.size();
}

auto FileDataSource::next_message() -> std::unique_ptr<MultiModalMessage> {
  if (!has_next()) {
    return nullptr;
  }
  
  std::string line = read_line_from_current_file();
  if (line.empty() && !open_next_file()) {
    return nullptr;
  }
  
  if (line.empty()) {
    line = read_line_from_current_file();
  }
  
  if (!line.empty()) {
    ++total_lines_read_;
    // Create a text-based multimodal message
    static uint64_t uid_counter = 0;
    return CreateTextMessage(++uid_counter, std::move(line));
  }
  
  return nullptr;
}

void FileDataSource::close() {
  if (closed_) {
    return;
  }
  
  cleanup_current_file();
  closed_ = true;
}

auto FileDataSource::get_config() const -> const DataSourceConfig& {
  return config_;
}

auto FileDataSource::is_initialized() const -> bool {
  return initialized_;
}

auto FileDataSource::is_closed() const -> bool {
  return closed_;
}

void FileDataSource::reset() {
  if (!initialized_) {
    return;
  }
  
  cleanup_current_file();
  current_file_index_ = 0;
  current_position_ = 0;
  total_lines_read_ = 0;
}

void FileDataSource::skip_to_index(size_t index) {
  if (!initialized_ || index >= file_list_.size()) {
    return;
  }
  
  cleanup_current_file();
  current_file_index_ = index;
  current_position_ = 0;
}

auto FileDataSource::get_reading_stats() const -> ReadingStats {
  return ReadingStats{
    .total_files_ = file_list_.size(),
    .current_file_index_ = current_file_index_,
    .current_position_ = current_position_,
    .total_lines_read_ = total_lines_read_
  };
}

// Private helper methods

auto FileDataSource::scan_files(const std::string& path, bool recursive) -> std::vector<std::string> {
  std::vector<std::string> files;
  
  try {
    std::filesystem::path fs_path(path);
    
    if (std::filesystem::is_regular_file(fs_path)) {
      if (is_supported_format(path)) {
        files.push_back(path);
      }
    } else if (std::filesystem::is_directory(fs_path)) {
      if (recursive) {
        for (const auto& entry : std::filesystem::recursive_directory_iterator(fs_path)) {
          if (entry.is_regular_file() && is_supported_format(entry.path().string())) {
            files.push_back(entry.path().string());
          }
        }
      } else {
        for (const auto& entry : std::filesystem::directory_iterator(fs_path)) {
          if (entry.is_regular_file() && is_supported_format(entry.path().string())) {
            files.push_back(entry.path().string());
          }
        }
      }
    }
  } catch (const std::filesystem::filesystem_error& e) {
    // Return empty vector on filesystem error
    (void)e;  // Suppress unused variable warning
  }
  
  // Sort files for consistent processing order
  std::sort(files.begin(), files.end());
  return files;
}

auto FileDataSource::open_next_file() -> bool {
  cleanup_current_file();
  
  if (current_file_index_ >= file_list_.size()) {
    return false;
  }
  
  const std::string& file_path = file_list_[current_file_index_];
  current_file_.open(file_path, std::ios::in);
  
  if (!current_file_.is_open()) {
    ++current_file_index_;
    return open_next_file();  // Try next file
  }
  
  current_position_ = 0;
  ++current_file_index_;
  return true;
}

auto FileDataSource::read_line_from_current_file() -> std::string {
  if (!current_file_.is_open()) {
    if (!open_next_file()) {
      return "";
    }
  }
  
  std::string line;
  if (std::getline(current_file_, line)) {
    ++current_position_;
    return line;
  }
  
  return "";
}

auto FileDataSource::is_supported_format(const std::string& file_path) const -> bool {
  std::filesystem::path path(file_path);
  std::string extension = path.extension().string();
  
  // Convert to lowercase for comparison
  std::transform(extension.begin(), extension.end(), extension.begin(), ::tolower);
  
  return extension == ".txt" || 
         extension == ".csv" || 
         extension == ".json" || 
         extension == ".log";
}

void FileDataSource::cleanup_current_file() {
  if (current_file_.is_open()) {
    current_file_.close();
  }
}

}  // namespace sage_flow
