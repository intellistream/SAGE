#pragma once

#include <memory>
#include <string>
#include <unordered_map>

namespace sage_flow {

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
  auto get_property(const std::string& key, const std::string& default_value =
                                                "") const -> std::string {
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

}  // namespace sage_flow