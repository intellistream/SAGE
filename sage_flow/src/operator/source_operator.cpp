#include "operator/source_operator.h"

#include "operator/response.h"
#include "message/multimodal_message.h"
#include <utility>

namespace sage_flow {

SourceOperator::SourceOperator(std::string name)
    : Operator(OperatorType::kSource, std::move(name)) {}

auto SourceOperator::process(Response& input_record, int slot) -> bool {
  (void)input_record; // Source operators don't use input records
  (void)slot;         // Suppress unused parameter warning
  
  if (hasNext()) {
    auto message = next();
    if (message) {
      Response output_record(std::move(message));
      emit(0, output_record);
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
    process(dummy_input, 0);
  }
}

}  // namespace sage_flow
