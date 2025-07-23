#include "operator/filter_operator.h"

#include "operator/response.h"
#include <utility>

namespace sage_flow {

FilterOperator::FilterOperator(std::string name)
    : Operator(OperatorType::kFilter, std::move(name)) {}

auto FilterOperator::process(Response& input_record, int slot) -> bool {
  (void)slot; // Suppress unused parameter warning
  
  if (!input_record.hasMessage()) {
    return false;
  }
  
  auto input_message = input_record.getMessage();
  if (!input_message) {
    return false;
  }
  
  incrementProcessedCount();
  
  if (filter(*input_message)) {
    Response output_record(std::move(input_message));
    emit(0, output_record);
    incrementOutputCount();
    return true;
  }
  
  // Message was filtered out
  return false;
}

}  // namespace sage_flow
