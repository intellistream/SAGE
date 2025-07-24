#pragma once

#include "data_source.h"
#include <memory>
#include <string>
#include <vector>

namespace sage_flow {

/**
 * @brief Factory function to create data sources
 * 
 * Creates appropriate data source instances based on the source type
 * specified in the configuration. Supports lazy initialization pattern
 * compatible with SAGE's distributed execution model.
 * 
 * Supported source types:
 * - "file": File-based data source for reading from local/remote files
 * - "stream": Stream-based data source for continuous data feeds  
 * - "kafka": Kafka-based data source for message queue integration
 * 
 * @param source_type Type of data source to create
 * @param config Configuration for the data source
 * @return Unique pointer to the created data source
 * @throws std::invalid_argument if source_type is not supported
 */
auto CreateDataSource(const std::string& source_type, 
                     const DataSourceConfig& config) -> std::unique_ptr<DataSource>;

/**
 * @brief Get list of supported data source types
 * @return Vector of supported source type names
 */
auto GetSupportedSourceTypes() -> std::vector<std::string>;

/**
 * @brief Check if a data source type is supported
 * @param source_type Source type to check
 * @return true if supported, false otherwise
 */
auto IsSourceTypeSupported(const std::string& source_type) -> bool;

}  // namespace sage_flow
