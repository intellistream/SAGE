#include "operator/response.h"

#include "message/multimodal_message.h"
#include <utility>

namespace sage_flow {

Response::Response(std::unique_ptr<MultiModalMessage> message) {
  if (message) {
    messages_.push_back(std::move(message));
  }
}

Response::Response(std::vector<std::unique_ptr<MultiModalMessage>> messages)
    : messages_(std::move(messages)) {}

Response::Response(Response&& other) noexcept
    : messages_(std::move(other.messages_)) {}

auto Response::operator=(Response&& other) noexcept -> Response& {
  if (this != &other) {
    messages_ = std::move(other.messages_);
  }
  return *this;
}

auto Response::hasMessage() const -> bool {
  return !messages_.empty();
}

auto Response::hasMessages() const -> bool {
  return messages_.size() > 1;
}

auto Response::getMessage() -> std::unique_ptr<MultiModalMessage> {
  if (messages_.empty()) {
    return nullptr;
  }
  auto message = std::move(messages_.front());
  messages_.erase(messages_.begin());
  return message;
}

auto Response::getMessages() -> std::vector<std::unique_ptr<MultiModalMessage>> {
  return std::move(messages_);
}

auto Response::size() const -> size_t {
  return messages_.size();
}

}  // namespace sage_flow
