#include "operator/filter_operator.hpp"

#include <iostream>
#include "data_stream/response.hpp"

namespace sage_flow {

template <typename InputType>
FilterOperator<InputType>::FilterOperator(std::string name, PredicateFunc pred)
    : BaseOperator<InputType, InputType>(OperatorType::kFilter, std::move(name)), predicate_func_(std::move(pred)) {}

template <typename InputType>
FilterOperator<InputType>::FilterOperator(std::string name, PredicateFunc pred, std::string description)
    : BaseOperator<InputType, InputType>(OperatorType::kFilter, std::move(name), std::move(description)), predicate_func_(std::move(pred)) {}

template <typename InputType>
void FilterOperator<InputType>::setPredicate(PredicateFunc pred) {
  predicate_func_ = std::move(pred);
}

template <typename InputType>
auto FilterOperator<InputType>::getPredicate() const -> const PredicateFunc& {
  return predicate_func_;
}

template <typename InputType>
auto FilterOperator<InputType>::process(const std::vector<std::unique_ptr<InputType>>& input) -> std::optional<Response<InputType>> {
  if (input.empty()) {
    return this->createEmptyResponse();
  }

  std::vector<std::unique_ptr<InputType>> results;
  results.reserve(input.size());

  try {
    for (const auto& msg : input) {
      this->incrementProcessedCount();
      if (!msg) continue;

      if (predicate_func_(*msg)) {
        results.push_back(msg->clone());  // Assuming InputType has clone method or use move if appropriate
      }
    }

    if (results.empty()) {
      return this->createEmptyResponse();
    }

    auto output = Response<InputType>(std::move(results));
    this->emit(0, output);
    this->incrementOutputCount();

    return std::make_optional(std::move(output));
  } catch (const std::exception& e) {
    std::cerr << "[FilterOperator] Error processing batch: " << e.what() << std::endl;
    return this->createEmptyResponse();
  }
}

// Explicit template instantiation for MultiModalMessage
template class FilterOperator<sage_flow::MultiModalMessage>;

}  // namespace sage_flow
