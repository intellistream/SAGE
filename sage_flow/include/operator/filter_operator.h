#pragma once

#include <string>
#include "base_operator.h"

namespace sage_flow {

class MultiModalMessage;
class Response;

/**
 * @brief Filter operator for selective data processing
 * 
 * Evaluates a predicate function on each input message and only passes
 * messages that satisfy the condition.
 */
class FilterOperator : public Operator {
 public:
  explicit FilterOperator(std::string name);

  // Prevent copying
  FilterOperator(const FilterOperator&) = delete;
  auto operator=(const FilterOperator&) -> FilterOperator& = delete;

  // Allow moving
  FilterOperator(FilterOperator&&) = default;
  auto operator=(FilterOperator&&) -> FilterOperator& = default;
  
  auto process(Response& input_record, int slot) -> bool override;
  
  // Filter-specific interface
  virtual auto filter(const MultiModalMessage& input) -> bool = 0;
};

}  // namespace sage_flow
