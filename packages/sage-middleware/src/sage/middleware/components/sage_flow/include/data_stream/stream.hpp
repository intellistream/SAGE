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
#include "../operator/map_operator.hpp"
#include "../operator/filter_operator.hpp"
#include "../operator/source_operator.hpp"
#include "../operator/sink_operator.hpp"

#include "../function/sink_function.hpp"

namespace sage_flow {

class Stream {
public:
  using T = MultiModalMessage;
  Stream(std::shared_ptr<StreamEngine> engine,
         std::shared_ptr<ExecutionGraph> graph,
         ExecutionGraph::OperatorId last_operator_id = static_cast<ExecutionGraph::OperatorId>(-1))
      : engine_(std::move(engine)), graph_(std::move(graph)), last_operator_id_(last_operator_id) {}

  class VectorSourceOperator : public SourceOperator {
  public:
    explicit VectorSourceOperator(const std::vector<T>& data)
        : SourceOperator("vector_source"), data_(data), index_(0) {}

    auto hasNext() -> bool override { return index_ < data_.size(); }

    auto next() -> std::unique_ptr<MultiModalMessage> override {
      if (hasNext()) {
        return data_[index_++].clone();
      }
      return nullptr;
    }

    auto reset() -> void override { index_ = 0; }

  private:
    const std::vector<T>& data_;
    size_t index_ = 0;
  };

  static Stream from_vector(const std::vector<T>& data, std::shared_ptr<StreamEngine> engine = nullptr) {
    if (!engine) {
      engine = std::make_shared<StreamEngine>();
    }
    auto graph = std::make_shared<ExecutionGraph>();
    auto source_op = std::make_shared<VectorSourceOperator>(data);
    graph->addOperator(source_op);
    return Stream(engine, graph);
  }

  Stream map(const std::function<std::shared_ptr<T>(const std::shared_ptr<T>&)>& f) {
    auto new_graph = std::make_shared<ExecutionGraph>();
    // Copy previous graph if needed, but for simplicity, assume new chain
    auto map_op = std::make_shared<MapOperator>("map", f);
    auto new_id = new_graph->addOperator(map_op);
    if (last_operator_id_ != static_cast<ExecutionGraph::OperatorId>(-1)) {
      new_graph->connectOperators(last_operator_id_, new_id);
    }
    return Stream(engine_, new_graph, new_id);
  }

  Stream filter(const std::function<bool(const std::shared_ptr<T>&)>& pred) {
    auto new_graph = std::make_shared<ExecutionGraph>();
    auto filter_op = std::make_shared<FilterOperator>("filter", pred);
    auto new_id = new_graph->addOperator(filter_op);
    if (last_operator_id_ != static_cast<ExecutionGraph::OperatorId>(-1)) {
      new_graph->connectOperators(last_operator_id_, new_id);
    }
    return Stream(engine_, new_graph, new_id);
  }

  Stream source() {
    auto new_graph = std::make_shared<ExecutionGraph>();
    auto source_op = std::make_shared<VectorSourceOperator>(std::vector<T>{});
    auto new_id = new_graph->addOperator(source_op);
    return Stream(engine_, new_graph, new_id);
  }

  class LambdaSinkFunction : public SinkFunction {
  public:
    using SinkFunc = std::function<void(const MultiModalMessage&)>;
    explicit LambdaSinkFunction(SinkFunc snk) : SinkFunction("lambda_sink"), snk_(std::move(snk)) {}

    void init() override { /* no-op */ }

    void close() override { /* no-op */ }

    void setSinkFunc(SinkFunc snk) { snk_ = std::move(snk); }

  private:
    SinkFunc snk_;
  };

  void sink(const std::function<void(const T&)>& snk) {
    auto new_graph = std::make_shared<ExecutionGraph>();
    auto sink_func = std::make_unique<LambdaSinkFunction>(snk);
    auto sink_op = std::make_shared<SinkOperator>("sink", std::move(sink_func));
    auto new_id = new_graph->addOperator(sink_op);
    if (last_operator_id_ != static_cast<ExecutionGraph::OperatorId>(-1)) {
      new_graph->connectOperators(last_operator_id_, new_id);
    }
  }

  void execute() {
    if (graph_) {
      graph_->run();
    }
  }

private:
  std::shared_ptr<StreamEngine> engine_;
  std::shared_ptr<ExecutionGraph> graph_;
  ExecutionGraph::OperatorId last_operator_id_;
};

} // namespace sage_flow
