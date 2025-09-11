#pragma once

#include <memory>
#include <string>
#include <vector>
#include <map>

namespace sage_flow {

class MultiModalMessage {
public:
  MultiModalMessage() = default;
  virtual ~MultiModalMessage() = default;
  
  virtual std::unique_ptr<MultiModalMessage> clone() const = 0;
  virtual std::string getContent() const = 0;
  virtual void setContent(const std::string& content) = 0;
  virtual std::string getType() const = 0;
  virtual void setType(const std::string& type) = 0;
  
  // Template instantiation reference
  static std::unique_ptr<MultiModalMessage> create();
};

}  // namespace sage_flow
