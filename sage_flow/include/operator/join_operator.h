#pragma once

#include <memory>
#include <string>
#include <unordered_map>
#include "base_operator.h"

namespace sage_flow {

class MultiModalMessage;
class Response;

/**
 * @brief Join operator for combining data streams
 * 
 * Combines messages from two input streams based on a join condition.
 * Supports time-based windowing for stream joins.
 */
class JoinOperator : public Operator {
 public:
  explicit JoinOperator(std::string name);

  // Prevent copying
  JoinOperator(const JoinOperator&) = delete;
  auto operator=(const JoinOperator&) -> JoinOperator& = delete;

  // Allow moving
  JoinOperator(JoinOperator&&) = default;
  auto operator=(JoinOperator&&) -> JoinOperator& = default;
  
  auto process(Response& input_record, int slot) -> bool override;
  
  // Join-specific interface
  virtual auto join(std::unique_ptr<MultiModalMessage> left,
                   std::unique_ptr<MultiModalMessage> right)
      -> std::unique_ptr<MultiModalMessage> = 0;
  virtual auto getJoinKey(const MultiModalMessage& message) -> std::string = 0;
  
 private:
  // Internal state for join processing
  std::unordered_map<std::string, std::unique_ptr<MultiModalMessage>> left_buffer_;
  std::unordered_map<std::string, std::unique_ptr<MultiModalMessage>> right_buffer_;
  
  auto processLeftInput(std::unique_ptr<MultiModalMessage> message) -> void;
  auto processRightInput(std::unique_ptr<MultiModalMessage> message) -> void;
  auto tryJoin(const std::string& key) -> void;
};

}  // namespace sage_flow
