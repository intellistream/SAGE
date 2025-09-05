#pragma once

#include <memory>
#include <string>

#include "base_operator.hpp"
#include "../function/filter_function.hpp"

namespace sage_flow {

class MultiModalMessage;
class Response;

/**
 * @brief Filter operator for selective data processing
 *
 * Evaluates a predicate function on each input message and only passes
 * messages that satisfy the condition. Uses composition pattern with
 * FilterFunction.
 */
class FilterOperator final : public BaseOperator {
public:
  explicit FilterOperator(std::string name);

  /**
   * @brief Constructor with FilterFunction
   * @param name Operator name
   * @param filter_function FilterFunction instance to handle processing logic
   */
  FilterOperator(std::string name,
                 std::unique_ptr<FilterFunction> filter_function);

  // Prevent copying
  FilterOperator(const FilterOperator&) = delete;
  auto operator=(const FilterOperator&) -> FilterOperator& = delete;

  // Allow moving
  FilterOperator(FilterOperator&&) = default;
  auto operator=(FilterOperator&&) -> FilterOperator& = default;

  auto process(Response& input_record, int slot) -> bool override;

  /**
   * @brief Set the filter function
   * @param filter_function FilterFunction instance to handle processing logic
   */
  void setFilterFunction(std::unique_ptr<FilterFunction> filter_function);

  /**
   * @brief Get the filter function
   * @return Reference to the contained FilterFunction
   */
  auto getFilterFunction() -> FilterFunction&;

private:
  std::unique_ptr<FilterFunction> filter_function_;
};

}  // namespace sage_flow
