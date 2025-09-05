#include "operator/source_operator.hpp"

#include <iostream>
#include <utility>

#include "message/multimodal_message.hpp"
#include "operator/response.hpp"

namespace sage_flow {

// SourceOperator implementation
SourceOperator::SourceOperator(std::string name)
    : BaseOperator(OperatorType::kSource, std::move(name)) {}

auto SourceOperator::process(Response& input_record, int slot) -> bool {
  static_cast<void>(input_record);  // Suppress unused parameter warning
  static_cast<void>(slot);          // Suppress unused parameter warning

  std::cout << "[SourceOperator] Processing, hasNext: " << hasNext() << std::endl;

  if (hasNext()) {
    auto message = next();
    std::cout << "[SourceOperator] Generated message: " << (message ? "yes" : "no") << std::endl;
    if (message) {
      Response output_response(std::move(message));
      std::cout << "[SourceOperator] Emitting message" << std::endl;
      emit(0, output_response);
      incrementProcessedCount();
      incrementOutputCount();
      return true;
    }
  }
  return false;
}

auto SourceOperator::runSource() -> void {
  while (hasNext()) {
    Response dummy_input(std::vector<std::unique_ptr<MultiModalMessage>>{});
    if (!process(dummy_input, 0)) {
      break;
    }
  }
}

}  // namespace sage_flow
