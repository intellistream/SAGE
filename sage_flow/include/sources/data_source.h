#pragma once

#include <memory>
#include <string>
#include <unordered_map>

namespace sage_flow {

// Forward declarations
class MultiModalMessage;

/**
 * @brief Configuration for data sources
 * 
 * Provides a generic configuration interface that supports various
 * data source types through a key-value property system.
 */
struct DataSourceConfig {
  std::string source_type_;
  std::unordered_map<std::string, std::string> properties_;
  
  DataSourceConfig() = default;
  explicit DataSourceConfig(std::string source_type) 
      : source_type_(std::move(source_type)) {}
      
  /**
   * @brief Get a property value with optional default
   * @param key Property key to lookup
   * @param default_value Default value if key not found
   * @return Property value or default
   */
  auto get_property(const std::string& key, 
                   const std::string& default_value = "") const -> std::string {
    auto it = properties_.find(key);
    return (it != properties_.end()) ? it->second : default_value;
  }
  
  /**
   * @brief Set a property value
   * @param key Property key
   * @param value Property value
   */
  void set_property(const std::string& key, const std::string& value) {
    properties_[key] = value;
  }
};

/**
 * @brief Abstract base class for data sources
 * 
 * Data sources are responsible for reading data from various inputs
 * and converting them into messages that can be processed by the stream.
 * 
 * This design follows SAGE's SourceFunction pattern with C++ adaptations:
 * - Lazy initialization support for distributed environments
 * - State management for resumable reading
 * - Resource lifecycle management with proper cleanup
 * - Configuration-driven source creation
 */
class DataSource {
 public:
  DataSource() = default;
  virtual ~DataSource() = default;

  // Prevent copying
  DataSource(const DataSource&) = delete;
  auto operator=(const DataSource&) -> DataSource& = delete;

  // Allow moving
  DataSource(DataSource&&) = default;
  auto operator=(DataSource&&) -> DataSource& = default;

  /**
   * @brief Initialize the data source with configuration
   * 
   * This method implements lazy initialization pattern similar to
   * SAGE's KafkaSourceFunction._lazy_init(), allowing for proper
   * resource creation in distributed environments.
   * 
   * @param config Source configuration parameters
   * @return true if initialization successful, false otherwise
   */
  virtual auto initialize(const DataSourceConfig& config) -> bool = 0;

  /**
   * @brief Check if there are more messages to read
   * 
   * Provides backpressure control and allows consumers to check
   * data availability before attempting to read.
   * 
   * @return true if more messages available, false otherwise
   */
  virtual auto has_next() -> bool = 0;

  /**
   * @brief Read the next message from the source
   * 
   * Similar to SAGE's SourceFunction.execute(), this method produces
   * the next data item. Returns nullptr when no data is available.
   * 
   * @return Unique pointer to the next message, nullptr if no more messages
   */
  virtual auto next_message() -> std::unique_ptr<MultiModalMessage> = 0;

  /**
   * @brief Close the data source and cleanup resources
   * 
   * Ensures proper resource cleanup similar to SAGE's cleanup mechanisms.
   * Should be called to release connections, file handles, etc.
   */
  virtual void close() = 0;

  /**
   * @brief Get source configuration
   * @return Reference to the configuration
   */
  virtual auto get_config() const -> const DataSourceConfig& = 0;
  
  /**
   * @brief Check if the data source is properly initialized
   * @return true if initialized and ready to produce data
   */
  virtual auto is_initialized() const -> bool = 0;
  
  /**
   * @brief Check if the data source has been closed
   * @return true if the data source is closed
   */
  virtual auto is_closed() const -> bool = 0;
};

}  // namespace sage_flow
