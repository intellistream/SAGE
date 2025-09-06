#pragma once

#include <functional>
#include <memory>
#include <string>
#include <vector>
#include <optional>

#include "base_operator.hpp"
#include "operator/response.hpp"
#include "message/multimodal_message.hpp"

namespace sage_flow {

class FilterOperator : public BaseOperator<MultiModalMessage, MultiModalMessage> {
public:
  using PredicateFunc = std::function<bool(const std::shared_ptr<MultiModalMessage>&)>;

  explicit FilterOperator(std::string name, PredicateFunc pred);
  FilterOperator(std::string name, PredicateFunc pred, std::string description);

  // Prevent copying
  FilterOperator(const FilterOperator&) = delete;
  auto operator=(const FilterOperator&) -> FilterOperator& = delete;

  // Allow moving
  FilterOperator(FilterOperator&&) = default;
  auto operator=(FilterOperator&&) -> FilterOperator& = default;

  auto process(const std::vector<std::shared_ptr<MultiModalMessage>>& input) -> std::optional<Response<MultiModalMessage>> override;

private:
  PredicateFunc predicate_func_;
};

}  // namespace sage_flow
