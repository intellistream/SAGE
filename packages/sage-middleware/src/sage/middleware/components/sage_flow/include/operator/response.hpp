#pragma once

#include <memory>
#include <vector>
#include "../message/multimodal_message.hpp"

namespace sage_flow {

template <typename T>
class Response {
public:
  Response() = default;
  
  explicit Response(std::vector<std::shared_ptr<T>> messages) : messages_(std::move(messages)) {}
  
  bool hasMessages() const { return !messages_.empty(); }
  
  std::shared_ptr<T> getMessage() const {
    if (!messages_.empty()) {
      return messages_[0];
    }
    return nullptr;
  }
  
  const std::vector<std::shared_ptr<T>>& getMessages() const {
    return messages_;
  }
  
  std::vector<std::shared_ptr<T>>& getMessages() {
    return messages_;
  }
  
  size_t size() const { return messages_.size(); }
  
private:
  std::vector<std::shared_ptr<T>> messages_;
};

// No extern template - instantiate in cpp

}  // namespace sage_flow
