#pragma once

#include <functional>
#include <memory>
#include <vector>
#include <optional>
#include <string>
#include <any>

#include "../engine/execution_graph.hpp"
#include "../engine/stream_engine.hpp"
#include "../message/multimodal_message.hpp"

namespace sage_flow {

template<typename T>
class Stream {
public:
  Stream(std::shared_ptr<StreamEngine> engine,
             std::shared_ptr<ExecutionGraph> graph,
             ExecutionGraph::OperatorId last_operator_id = static_cast<ExecutionGraph::OperatorId>(-1))
      : engine_(std::move(engine)), graph_(std::move(graph)), last_operator_id_(last_operator_id) {}

  static Stream from_vector(const std::vector<T>& data, std::shared_ptr<StreamEngine> engine = nullptr) {
    if (!engine) {
      engine = std::make_shared<StreamEngine>();
    }
    auto graph = std::make_shared<ExecutionGraph>();
    // TODO: Add source operator for data as T
    // Placeholder for lazy planning
    return Stream(engine, graph);
  }

  template<typename U, typename Func>
  Stream<U> map(const Func& f) {
    // TODO: Create and add MapOperator<T, U> with lambda f to graph
    // Connect to last_operator_id_
    // Placeholder implementation for compilation
    auto new_graph = graph_;
    ExecutionGraph::OperatorId new_id = (last_operator_id_ == static_cast<ExecutionGraph::OperatorId>(-1)) ? 0 : last_operator_id_ + 1;
    return Stream<U>(engine_, new_graph, new_id);
  }

  template<typename Func>
  Stream<T> filter(const Func& pred) {
    // TODO: Create and add FilterOperator<T> with predicate pred to graph
    // Placeholder
    ExecutionGraph::OperatorId new_id = (last_operator_id_ == static_cast<ExecutionGraph::OperatorId>(-1)) ? 0 : last_operator_id_ + 1;
    return Stream<T>(engine_, graph_, new_id);
  }

  template<typename Func>
  Stream<T> apply_operator(const std::string& name, const Func& f) {
    // General apply for operators, treat as map for now
    // TODO: Add specific operator based on name
    return map(f);
  }

  void execute() {
    // Lazy execution: submit and run the graph
    if (graph_ && engine_) {
      auto graph_id = engine_->submitGraph(graph_);
      engine_->executeGraph(graph_id);
    }
  }

private:
  std::shared_ptr<StreamEngine> engine_;
  std::shared_ptr<ExecutionGraph> graph_;
  ExecutionGraph::OperatorId last_operator_id_;
};

} // namespace sage_flow
