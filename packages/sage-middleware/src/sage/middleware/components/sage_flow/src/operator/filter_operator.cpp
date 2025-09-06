#include "operator/filter_operator.hpp"

#include <iostream>
#include "message/multimodal_message.hpp"
#include "operator/response.hpp"

namespace sage_flow {

FilterOperator::FilterOperator(std::string name, PredicateFunc pred)
    : BaseOperator<MultiModalMessage, MultiModalMessage>(OperatorType::kFilter, std::move(name)), predicate_func_(std::move(pred)) {}

auto FilterOperator::process(const std::vector<std::shared_ptr<MultiModalMessage>>& input) -> std::optional<Response<MultiModalMessage>> {
  if (input.empty()) {
    return BaseOperator<MultiModalMessage, MultiModalMessage>::createEmptyResponse();
  }

  std::vector<std::shared_ptr<MultiModalMessage>> results;
  results.reserve(input.size());

  try {
    for (const auto& msg : input) {
      incrementProcessedCount();
      if (!msg) continue;

      if (predicate_func_(msg)) {
        results.push_back(msg);
      }
    }

    if (results.empty()) {
      return BaseOperator<MultiModalMessage, MultiModalMessage>::createEmptyResponse();
    }

    auto output = Response<MultiModalMessage>(std::move(results));
    emit(0, output);
    incrementOutputCount();

    return std::make_optional(std::move(output));
  } catch (const std::exception& e) {
    std::cerr << "[FilterOperator] Error processing batch: " << e.what() << std::endl;
    return BaseOperator<MultiModalMessage, MultiModalMessage>::createEmptyResponse();
  }
}

}  // namespace sage_flow
