#pragma once

#include <memory>
#include <vector>

#include "../message/multimodal_message.hpp"

namespace sage_flow {
/**
 * @brief Response container for function execution results
 *
 * Simplified version of candyFlow's Response, adapted for MultiModalMessage
 */
class FunctionResponse {
public:
  FunctionResponse() = default;
  ~FunctionResponse() = default;

  // Disable copy constructor and assignment (can't copy unique_ptr)
  FunctionResponse(const FunctionResponse&) = delete;
  auto operator=(const FunctionResponse&) -> FunctionResponse& = delete;

  // Enable move constructor and assignment
  FunctionResponse(FunctionResponse&&) = default;
  auto operator=(FunctionResponse&&) -> FunctionResponse& = default;

  // Add a message to the response
  void addMessage(std::unique_ptr<MultiModalMessage> message) {
    messages_.push_back(std::move(message));
  }

  // Get all messages
  auto getMessages() -> std::vector<std::unique_ptr<MultiModalMessage>>& {
    return messages_;
  }

  // Get messages (const)
  auto getMessages() const
      -> const std::vector<std::unique_ptr<MultiModalMessage>>& {
    return messages_;
  }

  // Check if response is empty
  auto isEmpty() const -> bool { return messages_.empty(); }

  // Clear all messages
  void clear() { messages_.clear(); }

  // Get message count
  auto size() const -> size_t { return messages_.size(); }

private:
  std::vector<std::unique_ptr<MultiModalMessage>> messages_;
};

}  // namespace sage_flow
