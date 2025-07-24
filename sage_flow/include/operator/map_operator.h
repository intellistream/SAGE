#pragma once

#include <memory>
#include <string>
#include "base_operator.h"

namespace sage_flow {

class MultiModalMessage;
class Response;

/**
 * @brief Map operator for one-to-one transformations
 * 
 * Applies a transformation function to each input message and produces
 * exactly one output message.
 */
class MapOperator : public Operator {
 public:
  explicit MapOperator(std::string name);

  // Prevent copying
  MapOperator(const MapOperator&) = delete;
  auto operator=(const MapOperator&) -> MapOperator& = delete;

  // Allow moving
  MapOperator(MapOperator&&) = default;
  auto operator=(MapOperator&&) -> MapOperator& = default;
  
  auto process(Response& input_record, int slot) -> bool override;
  
  // Map-specific interface
  virtual auto map(std::unique_ptr<MultiModalMessage> input) 
      -> std::unique_ptr<MultiModalMessage> = 0;
};

}  // namespace sage_flow
