#include "engine/stream_engine.hpp"

#include <algorithm>
#include <memory>
#include <vector>

namespace sage_flow {

StreamEngine::StreamEngine() : engine_running_(false) {}

void StreamEngine::start() {
  engine_running_ = true;
  // Start the execution engine
}

void StreamEngine::stop() {
  engine_running_ = false;
  // Stop the execution engine
}

void StreamEngine::run() {
  if (!engine_running_) {
    start();
  }
  
  // Execute the graph
  if (graph_) {
    graph_->run();
  }
}

void StreamEngine::processGraph(ExecutionGraph& graph) {
  // Get all operators from the graph
  const auto& operators = graph.getOperators();
  
  // Initialize intermediate results storage
  intermediate_results_.clear();
  for (const auto& op_pair : operators) {
    intermediate_results_[op_pair.first] = std::vector<std::shared_ptr<MultiModalMessage>>();
  }
  
  // First pass: run source operators
  for (const auto& op_pair : operators) {
    const auto& op = op_pair.second;
    if (op->getType() == OperatorType::kSource) {
      auto source_op = std::dynamic_pointer_cast<SourceOperator<MultiModalMessage>>(op);
      if (source_op) {
        auto input = source_op->next();
        if (input) {
          intermediate_results_[op_pair.first].push_back(input);
        }
      }
    }
  }
  
  // Second pass: run transformation operators
  for (const auto& op_pair : operators) {
    const auto& op = op_pair.second;
    if (op->getType() == OperatorType::kSource) continue;
    
    auto input = getInputForOperator(op_pair.first);
    if (input) {
      op->process(input);
    }
  }
  
  // Third pass: run sink operators
  for (const auto& op_pair : operators) {
    const auto& op = op_pair.second;
    if (op->getType() == OperatorType::kSink) {
      auto input = getInputForOperator(op_pair.first);
      if (input) {
        op->process(input);
      }
    }
  }
}

std::shared_ptr<MultiModalMessage> StreamEngine::getInputForOperator(ExecutionGraph::OperatorId op_id) {
  // Implementation to get input for a specific operator
  // This would typically involve looking up the previous operator in the graph
  // and retrieving its output
  return nullptr;
}

}  // namespace sage_flow