#pragma once

#include <functional>
#include <memory>
#include <string>
#include <unordered_map>
#include <variant>
#include <vector>
#include <optional>

#include "base_operator.hpp"
#include "operator/response.hpp"
#include "message/multimodal_message.hpp"

namespace sage_flow {

class JoinOperator : public BaseOperator<MultiModalMessage, MultiModalMessage> {
public:
  using KeyType = std::string;
  using JoinFunc = std::function<std::shared_ptr<MultiModalMessage>(const std::shared_ptr<MultiModalMessage>&, const std::shared_ptr<MultiModalMessage>&)>;
  using KeyExtractorLeft = std::function<KeyType(const std::shared_ptr<MultiModalMessage>&)>;
  using KeyExtractorRight = std::function<KeyType(const std::shared_ptr<MultiModalMessage>&)>;
   
  JoinOperator(std::string name, KeyExtractorLeft key_left, KeyExtractorRight key_right, JoinFunc join_func);
  JoinOperator(std::string name, KeyExtractorLeft key_left, KeyExtractorRight key_right, JoinFunc join_func, std::string description);
  
  // Prevent copying
  JoinOperator(const JoinOperator&) = delete;
  auto operator=(const JoinOperator&) -> JoinOperator& = delete;
  
  // Allow moving
  JoinOperator(JoinOperator&&) = default;
  auto operator=(JoinOperator&&) -> JoinOperator& = default;

  auto process(const std::vector<std::shared_ptr<MultiModalMessage>>& input) -> std::optional<Response<MultiModalMessage>> override;

private:
  KeyExtractorLeft key_left_;
  KeyExtractorRight key_right_;
  JoinFunc join_func_;
  std::string description_;
  std::unordered_map<KeyType, std::vector<std::shared_ptr<MultiModalMessage>>> left_buffer_;
  std::unordered_map<KeyType, std::vector<std::shared_ptr<MultiModalMessage>>> right_buffer_;

  auto processLeftInput(const std::shared_ptr<MultiModalMessage>& message) -> void;
  auto processRightInput(const std::shared_ptr<MultiModalMessage>& message) -> void;
  auto tryJoin(const KeyType& key) -> void;
};

}  // namespace sage_flow
