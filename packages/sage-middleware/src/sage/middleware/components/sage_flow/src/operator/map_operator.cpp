#include "operator/map_operator.hpp"

#include <iostream>
#include "data_stream/response.hpp"

namespace sage_flow {

template <typename InputType, typename OutputType>
MapOperator<InputType, OutputType>::MapOperator(std::string name, typename MapOperator<InputType, OutputType>::MapFunc f)
    : BaseOperator<InputType, OutputType>(OperatorType::kMap, std::move(name)), map_func_(std::move(f)) {}

template <typename InputType, typename OutputType>
auto MapOperator<InputType, OutputType>::process(const std::vector<std::unique_ptr<InputType>>& input) -> std::optional<Response<OutputType>> {
  if (input.empty()) {
    return BaseOperator<InputType, OutputType>::createEmptyResponse();
  }

  std::vector<std::unique_ptr<OutputType>> results;
  results.reserve(input.size());

  try {
    for (auto& msg : input) {
      this->incrementProcessedCount();
      if (!msg) continue;

      auto result_msg = map_func_(*std::move(msg));
      if (result_msg) {
        results.push_back(std::move(result_msg));
      }
    }

    if (results.empty()) {
      return BaseOperator<InputType, OutputType>::createEmptyResponse();
    }

    auto output = Response<OutputType>(std::move(results));
    emit(0, output);
    this->incrementOutputCount();

    return std::make_optional(std::move(output));
  } catch (const std::exception& e) {
    std::cerr << "[MapOperator] Error processing batch: " << e.what() << std::endl;
    return BaseOperator<InputType, OutputType>::createEmptyResponse();
  }
}

}  // namespace sage_flow
