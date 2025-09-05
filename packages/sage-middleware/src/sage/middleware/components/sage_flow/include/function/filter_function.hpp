#pragma once

#include <functional>

#include "base_function.hpp"

namespace sage_flow {

/**
 * @brief Filter function type definition
 *
 * Based on candyFlow's filter pattern, adapted for MultiModalMessage
 */
using FilterFunc = std::function<bool(const MultiModalMessage&)>;

/**
 * @brief Filter Function class
 *
 * Filters messages based on a predicate function.
 * Based on candyFlow's FilterFunction design.
 */
class FilterFunction final : public BaseFunction {
public:
  explicit FilterFunction(std::string name);
  FilterFunction(std::string name, FilterFunc filter_func);

  ~FilterFunction() override = default;

  /**
   * @brief Execute the filter function on input messages
   * @param response Input response containing messages to filter
   * @return Response with filtered messages
   */
  using BaseFunction::execute;  // Bring base class overloads into scope
  auto execute(FunctionResponse& response) -> FunctionResponse override;

  /**
   * @brief Set the filter function
   * @param filter_func Predicate function to filter messages
   */
  void setFilterFunc(FilterFunc filter_func);

private:
  FilterFunc filter_func_;
};

}  // namespace sage_flow
