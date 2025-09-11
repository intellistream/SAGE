#pragma once

#include <functional>

#include "base_function.hpp"

namespace sage_flow {

/**
 * @brief Filter function type definition
 *
 * Based on candyFlow's filter pattern, adapted for MultiModalMessage
 */

/**
 * @brief Filter Function class
 *
 * Filters messages based on a predicate function.
 * Based on candyFlow's FilterFunction design.
 */
template <typename InType, typename OutType>
class FilterFunction final : public BaseFunction<InType, OutType> {
public:
  using FilterFunc = std::function<bool(const InType&)>;

  explicit FilterFunction(std::string name);
  FilterFunction(std::string name, FilterFunc filter_func);

  ~FilterFunction() override = default;

  // Pure function interface - no Response dependency
  std::optional<OutType> execute(const InType& input) override;
  void execute_batch(const std::vector<InType>& inputs, std::vector<OutType>& outputs) override;

  /**
   * @brief Set the filter function
   * @param filter_func Predicate function to filter messages
   */
  void setFilterFunc(FilterFunc filter_func);

private:
  FilterFunc filter_func_;
};

}  // namespace sage_flow
