#pragma once

#include <memory>
#include <vector>

#include "message/multimodal_message_core.h"

namespace sage_flow {

/**
 * @brief Response container for operator processing results
 */
class Response final {
 public:
  explicit Response(std::unique_ptr<MultiModalMessage> message);
  explicit Response(std::vector<std::unique_ptr<MultiModalMessage>> messages);
  
  // Move semantics
  Response(Response&& other) noexcept;
  auto operator=(Response&& other) noexcept -> Response&;
  
  // Disable copy operations for performance
  Response(const Response&) = delete;
  auto operator=(const Response&) -> Response& = delete;
  
  // Accessors
  auto hasMessage() const -> bool;
  auto hasMessages() const -> bool;
  auto getMessage() -> std::unique_ptr<MultiModalMessage>;
  auto getMessages() -> std::vector<std::unique_ptr<MultiModalMessage>>;
  auto size() const -> size_t;
  
 private:
  std::vector<std::unique_ptr<MultiModalMessage>> messages_;
};

}  // namespace sage_flow
