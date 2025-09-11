#pragma once

#include <functional>
#include <memory>
#include <string>
#include <vector>
#include <optional>

#include "base_operator.hpp"
#include "data_stream/response.hpp"
#include "message/multimodal_message.hpp"

namespace sage_flow {

template <typename InputType>
class FilterOperator : public BaseOperator<InputType, InputType> {
public:
  using PredicateFunc = std::function<bool(const InputType&)>;

  explicit FilterOperator(std::string name, PredicateFunc pred);
  FilterOperator(std::string name, PredicateFunc pred, std::string description);

  // Prevent copying
  FilterOperator(const FilterOperator&) = delete;
  auto operator=(const FilterOperator&) -> FilterOperator& = delete;

  // Allow moving
  FilterOperator(FilterOperator&&) = default;
  auto operator=(FilterOperator&&) -> FilterOperator& = default;

  auto process(const std::vector<std::unique_ptr<InputType>>& input) -> std::optional<Response<InputType>> override;

  /**
   * @brief Set the filter predicate function
   */
  void setPredicate(PredicateFunc pred);

  /**
   * @brief Get the current predicate function
   */
  auto getPredicate() const -> const PredicateFunc&;

private:
  PredicateFunc predicate_func_;
};

}  // namespace sage_flow
