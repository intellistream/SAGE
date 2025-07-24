#include "operator/operator.h"

#include "operator/source_operator.h"
#include "operator/map_operator.h"
#include "operator/filter_operator.h"
#include "operator/sink_operator.h"
#include "operator/join_operator.h"
#include "operator/aggregate_operator.h"
#include "operator/topk_operator.h"
#include "operator/window_operator.h"

namespace sage_flow {

auto CreateOperator(OperatorType type, const std::string& name) -> std::unique_ptr<Operator> {
  // Note: These are abstract base classes, so we can't create instances directly
  // This would typically require concrete implementations
  (void)type; // Suppress unused parameter warning
  (void)name; // Suppress unused parameter warning
  return nullptr;
}

auto CreateTopKOperator(const std::string& name, size_t k) -> std::unique_ptr<TopKOperator> {
  // Note: TopKOperator is abstract, would need concrete implementation
  (void)name; // Suppress unused parameter warning
  (void)k;    // Suppress unused parameter warning
  return nullptr;
}

auto CreateWindowOperator(const std::string& name, 
                         WindowOperator::WindowType window_type) -> std::unique_ptr<WindowOperator> {
  // Note: WindowOperator is abstract, would need concrete implementation
  (void)name;        // Suppress unused parameter warning
  (void)window_type; // Suppress unused parameter warning
  return nullptr;
}

}  // namespace sage_flow
