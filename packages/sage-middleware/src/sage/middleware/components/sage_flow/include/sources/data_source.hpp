#pragma once

#include <memory>
#include <string>

namespace sage_flow {

class DataSource {
public:
  DataSource() = default;
  virtual ~DataSource() = default;
  
  virtual std::string getType() const = 0;
  virtual void setConfig(const std::string& config) = 0;
  virtual void init() = 0;
  virtual void close() = 0;
};

}  // namespace sage_flow