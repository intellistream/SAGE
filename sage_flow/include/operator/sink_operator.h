#pragma once

#include <memory>
#include <string>
#include "base_operator.h"

namespace sage_flow {

class MultiModalMessage;
class Response;

/**
 * @brief Sink operator for data output
 * 
 * Consumes processed messages and performs final operations such as
 * writing to files, databases, or external systems.
 */
class SinkOperator : public Operator {
 public:
  explicit SinkOperator(std::string name);

  // Prevent copying
  SinkOperator(const SinkOperator&) = delete;
  auto operator=(const SinkOperator&) -> SinkOperator& = delete;

  // Allow moving
  SinkOperator(SinkOperator&&) = default;
  auto operator=(SinkOperator&&) -> SinkOperator& = default;
  
  auto process(Response& input_record, int slot) -> bool override;
  
  // Sink-specific interface
  virtual auto sink(std::unique_ptr<MultiModalMessage> input) -> void = 0;
  virtual auto flush() -> void = 0;
};

}  // namespace sage_flow
