#pragma once

#include <memory>
#include <string>

namespace sage_flow {

class KafkaDataSource {
public:
  explicit KafkaDataSource(const std::string& config_path);
  virtual ~KafkaDataSource() = default;
  
  virtual std::string getType() const = 0;
  virtual void init() = 0;
  virtual void close() = 0;

private:
  std::string config_path_;
};

}  // namespace sage_flow