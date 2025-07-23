#include "operator/sink_operator.h"

#include "operator/response.h"
#include <utility>

namespace sage_flow {

SinkOperator::SinkOperator(std::string name)
    : Operator(OperatorType::kSink, std::move(name)) {}

auto SinkOperator::process(Response& input_record, int slot) -> bool {
  (void)slot; // Suppress unused parameter warning
  
  if (!input_record.hasMessage()) {
    return false;
  }
  
  auto input_message = input_record.getMessage();
  if (!input_message) {
    return false;
  }
  
  sink(std::move(input_message));
  incrementProcessedCount();
  // Sink operators don't produce output, so no need to increment output count
  
  return true;
}

}  // namespace sage_flow
