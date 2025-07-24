#include "sources/data_source_factory.h"
#include "sources/file_data_source.h"
#include "sources/stream_data_source.h"
#include "sources/kafka_data_source.h"
#include <stdexcept>
#include <algorithm>

namespace sage_flow {

auto CreateDataSource(const std::string& source_type, 
                     const DataSourceConfig& config) -> std::unique_ptr<DataSource> {
  if (source_type == "file") {
    return std::make_unique<FileDataSource>();
  }
  
  if (source_type == "stream") {
    return std::make_unique<StreamDataSource>();
  }
  
  if (source_type == "kafka") {
    return std::make_unique<KafkaDataSource>();
  }
  
  throw std::invalid_argument("Unsupported data source type: " + source_type);
}

auto GetSupportedSourceTypes() -> std::vector<std::string> {
  return {"file", "stream", "kafka"};
}

auto IsSourceTypeSupported(const std::string& source_type) -> bool {
  const auto supported_types = GetSupportedSourceTypes();
  return std::find(supported_types.begin(), supported_types.end(), source_type) 
         != supported_types.end();
}

}  // namespace sage_flow
