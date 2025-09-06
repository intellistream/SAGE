#include "operator/map_operator.hpp"

#include <iostream>
#include "message/multimodal_message.hpp"
#include "operator/response.hpp"

namespace sage_flow {

MapOperator::MapOperator(std::string name, MapFunc f)
    : BaseOperator<MultiModalMessage, MultiModalMessage>(OperatorType::kMap, std::move(name)), map_func_(std::move(f)) {}

auto MapOperator::process(const std::vector<std::shared_ptr<MultiModalMessage>>& input) -> std::optional<Response<MultiModalMessage>> {
  if (input.empty()) {
    return BaseOperator<MultiModalMessage, MultiModalMessage>::createEmptyResponse();
  }

  std::vector<std::shared_ptr<MultiModalMessage>> results;
  results.reserve(input.size());

  try {
    for (const auto& msg : input) {
      incrementProcessedCount();
      if (!msg) continue;

      auto result_msg = map_func_(msg);
      if (result_msg) {
        results.push_back(std::move(result_msg));
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
    std::cerr << "[MapOperator] Error processing batch: " << e.what() << std::endl;
    return BaseOperator<MultiModalMessage, MultiModalMessage>::createEmptyResponse();
  }
}

}  // namespace sage_flow
