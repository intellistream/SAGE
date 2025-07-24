#pragma once

#include <memory>
#include <string>
#include "base_operator.h"

namespace sage_flow {

class MultiModalMessage;
class Response;

/**
 * @brief Source operator for data ingestion
 * 
 * Generates data from various sources (files, streams, etc.) and emits
 * MultiModalMessage objects into the processing pipeline.
 */
class SourceOperator : public Operator {
 public:
  explicit SourceOperator(std::string name);

  // Prevent copying
  SourceOperator(const SourceOperator&) = delete;
  auto operator=(const SourceOperator&) -> SourceOperator& = delete;

  // Allow moving
  SourceOperator(SourceOperator&&) = default;
  auto operator=(SourceOperator&&) -> SourceOperator& = default;
  
  auto process(Response& input_record, int slot) -> bool override;
  
  // Source-specific interface
  virtual auto hasNext() -> bool = 0;
  virtual auto next() -> std::unique_ptr<MultiModalMessage> = 0;
  virtual auto reset() -> void = 0;
  
 protected:
  auto runSource() -> void;
};

}  // namespace sage_flow
