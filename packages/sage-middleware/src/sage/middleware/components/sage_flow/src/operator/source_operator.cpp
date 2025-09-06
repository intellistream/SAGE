#include "operator/source_operator.hpp"

#include <iostream>
#include <utility>

#include "message/multimodal_message.hpp"
#include "operator/response.hpp"

namespace sage_flow {

// SourceOperator implementation
SourceOperator::SourceOperator(std::string name)
    : BaseOperator(OperatorType::kSource, std::move(name)) {}

auto SourceOperator::process(const std::vector<std::shared_ptr<MultiModalMessage>>& input) -> std::optional<Response<MultiModalMessage>> {
  static_cast<void>(input);  // Source operators ignore input

  std::cout << "[SourceOperator] Processing, hasNext: " << hasNext() << std::endl;

  if (hasNext()) {
    auto message = next();
    std::cout << "[SourceOperator] Generated message: " << (message ? "yes" : "no") << std::endl;
    if (message) {
      auto output_response = Response<MultiModalMessage>(std::vector<std::shared_ptr<MultiModalMessage>>{std::move(message)});
      std::cout << "[SourceOperator] Emitting message" << std::endl;
      emit(0, output_response);
      incrementProcessedCount();
      incrementOutputCount();
      return output_response;
    }
  }
  return std::nullopt;
}

auto SourceOperator::runSource() -> void {
  while (hasNext()) {
    auto result = process(std::vector<std::shared_ptr<MultiModalMessage>>{});
    if (!result.has_value()) {
      break;
    }
  }
}

}  // namespace sage_flow
