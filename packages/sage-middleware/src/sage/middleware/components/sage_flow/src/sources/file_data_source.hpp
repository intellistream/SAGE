#pragma once

#include <memory>
#include <string>

namespace sage_flow {

class FileDataSource {
public:
  explicit FileDataSource(const std::string& file_path);
  virtual ~FileDataSource() = default;
  
  virtual std::string getType() const = 0;
  virtual void init() = 0;
  virtual void close() = 0;

private:
  std::string file_path_;
};

}  // namespace sage_flow