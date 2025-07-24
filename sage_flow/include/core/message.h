#pragma once

#include <string>
#include <unordered_map>
#include <memory>
#include <chrono>

namespace sage_flow {

/**
 * @brief Basic message class for data flow processing
 * 
 * Represents a single data item flowing through the stream processing pipeline.
 * Similar to SAGE's data context objects but simplified for C++ usage.
 */
class Message {
 public:
  /**
   * @brief Constructor with content
   * @param content The message content
   */
  explicit Message(std::string content) 
      : content_(std::move(content)), 
        timestamp_(std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count()) {}
  
  /**
   * @brief Constructor with content and metadata
   * @param content The message content
   * @param metadata Additional metadata
   */
  Message(std::string content, std::unordered_map<std::string, std::string> metadata)
      : content_(std::move(content)), 
        metadata_(std::move(metadata)),
        timestamp_(std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count()) {}

  /**
   * @brief Default constructor
   */
  Message() : timestamp_(std::chrono::duration_cast<std::chrono::milliseconds>(
      std::chrono::system_clock::now().time_since_epoch()).count()) {}

  /**
   * @brief Get message content
   * @return The message content
   */
  auto get_content() const -> const std::string& { return content_; }
  
  /**
   * @brief Set message content
   * @param content New content
   */
  void set_content(std::string content) { content_ = std::move(content); }
  
  /**
   * @brief Get message timestamp
   * @return Timestamp in milliseconds since epoch
   */
  auto get_timestamp() const -> int64_t { return timestamp_; }
  
  /**
   * @brief Get metadata value
   * @param key Metadata key
   * @param default_value Default value if key not found
   * @return Metadata value or default
   */
  auto get_metadata(const std::string& key, const std::string& default_value = "") const -> std::string {
    auto it = metadata_.find(key);
    return (it != metadata_.end()) ? it->second : default_value;
  }
  
  /**
   * @brief Set metadata value
   * @param key Metadata key
   * @param value Metadata value
   */
  void set_metadata(const std::string& key, const std::string& value) {
    metadata_[key] = value;
  }
  
  /**
   * @brief Get all metadata
   * @return Reference to metadata map
   */
  auto get_all_metadata() const -> const std::unordered_map<std::string, std::string>& {
    return metadata_;
  }
  
  /**
   * @brief Check if message is empty
   * @return true if content is empty
   */
  auto is_empty() const -> bool { return content_.empty(); }

 private:
  std::string content_;
  std::unordered_map<std::string, std::string> metadata_;
  int64_t timestamp_;
};

}  // namespace sage_flow
