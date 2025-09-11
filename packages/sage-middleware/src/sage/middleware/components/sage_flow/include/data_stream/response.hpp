#pragma once

#include <memory>
#include <string>
#include <vector>

namespace sage_flow {

template <typename T>
class Response {
public:
  Response() = default;
  
  explicit Response(std::vector<std::unique_ptr<T>> messages);
  Response(std::vector<std::unique_ptr<T>> messages, std::string metadata);
  
  void addMessage(std::unique_ptr<T> message);
  const std::vector<std::unique_ptr<T>>& getMessages() const;
  std::vector<std::unique_ptr<T>>& getMessages();
  std::string getMetadata() const;
  void setMetadata(std::string metadata);
  void clear();
  size_t size() const;
  bool empty() const;

private:
  std::vector<std::unique_ptr<T>> messages_;
  std::string metadata_;
};

}  // namespace sage_flow
