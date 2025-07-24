#include "operator/map_operator.h"

#include "operator/response.h"
#include <utility>

namespace sage_flow {

MapOperator::MapOperator(std::string name)
    : Operator(OperatorType::kMap, std::move(name)) {}

auto MapOperator::process(Response& input_record, int slot) -> bool {
  (void)slot; // Suppress unused parameter warning
  
  if (!input_record.hasMessage()) {
    return false;
  }
  
  auto input_message = input_record.getMessage();
  if (!input_message) {
    return false;
  }
  
  auto output_message = map(std::move(input_message));
  if (output_message) {
    Response output_record(std::move(output_message));
    emit(0, output_record);
    incrementProcessedCount();
    incrementOutputCount();
    return true;
  }
  
  incrementProcessedCount();
  return false;
}

}  // namespace sage_flow
