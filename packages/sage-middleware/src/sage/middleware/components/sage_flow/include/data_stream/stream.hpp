#pragma once

#include <functional>
#include <memory>
#include <vector>
#include <string>

#include "engine/execution_graph.hpp"
#include "engine/stream_engine.hpp"
#include "operator/source_operator.hpp"
#include "operator/map_operator.hpp"
#include "operator/filter_operator.hpp"
#include "function/sink_function.hpp"
#include "operator/sink_operator.hpp"
#include "function/dummy_input.hpp"

namespace sage_flow {

template <typename T>
class Stream {
public:
  Stream(std::shared_ptr<StreamEngine> engine,
         std::shared_ptr<ExecutionGraph> graph,
         ExecutionGraph::OperatorId last_operator_id = static_cast<ExecutionGraph::OperatorId>(-1))
      : engine_(std::move(engine)), graph_(std::move(graph)), last_operator_id_(last_operator_id) {}

  // Source operators
  static auto from_vector(const std::vector<T>& data, std::shared_ptr<StreamEngine> engine = nullptr) -> Stream<T>;

  // Transformation operators
  auto map(std::function<T(const T&)> transform) -> Stream<T>;
  auto filter(std::function<bool(const T&)> predicate) -> Stream<T>;

  // Sink operators
  auto sink(std::function<void(const T&)> sink_func) -> Stream<T>;

  // Execution
  auto execute() -> void;

private:
  std::shared_ptr<StreamEngine> engine_;
  std::shared_ptr<ExecutionGraph> graph_;
  ExecutionGraph::OperatorId last_operator_id_;

  class VectorSourceOperator : public SourceOperator<T> {
  public:
    explicit VectorSourceOperator(const std::vector<T>& data)
        : SourceOperator<T>("vector_source"), data_(data), index_(0) {}
    
    VectorSourceOperator(const VectorSourceOperator&) = delete;
    auto operator=(const VectorSourceOperator&) -> VectorSourceOperator& = delete;
    virtual ~VectorSourceOperator() = default;

    auto hasNext() -> bool override { return index_ < data_.size(); }
    auto next() -> std::unique_ptr<T> override {
      if (hasNext()) {
        return std::make_unique<T>(data_[index_++]);
      }
      return nullptr;
    }
    auto reset() -> void override { index_ = 0; }

  private:
    const std::vector<T>& data_;
    size_t index_ = 0;
  };

  class LambdaSinkFunction : public SinkFunction<T> {
  public:
    using SinkFunc = std::function<void(const T&)>;
    explicit LambdaSinkFunction(SinkFunc func) : func_(std::move(func)) {}
    
    void init() override {}
    void close() override {}
    void sink(const T& msg) override { func_(msg); }

  private:
    SinkFunc func_;
  };
};

template <typename T>
Stream<T> Stream<T>::from_vector(const std::vector<T>& data, std::shared_ptr<StreamEngine> engine) {
  if (!engine) {
    engine = std::make_shared<StreamEngine>();
  }
  auto graph = std::make_shared<ExecutionGraph>();
  auto source_op = std::make_shared<VectorSourceOperator>(data);
  graph->addOperator(std::dynamic_pointer_cast<BaseOperator<T, T>>(source_op));
  return Stream<T>(engine, graph);
}

template <typename T>
Stream<T> Stream<T>::map(std::function<T(const T&)> transform) {
  auto new_graph = std::make_shared<ExecutionGraph>(*graph_);
  auto map_op = std::make_shared<MapOperator<T, T>>("map", [transform](std::unique_ptr<T> input) {
    return std::make_unique<T>(transform(*input));
  });
  auto new_id = new_graph->addOperator(std::dynamic_pointer_cast<BaseOperator<T, T>>(map_op));
  if (last_operator_id_ != static_cast<ExecutionGraph::OperatorId>(-1)) {
    new_graph->connectOperators(last_operator_id_, new_id);
  }
  return Stream<T>(engine_, new_graph, new_id);
}

template <typename T>
Stream<T> Stream<T>::filter(std::function<bool(const T&)> predicate) {
  auto new_graph = std::make_shared<ExecutionGraph>(*graph_);
  auto filter_op = std::make_shared<FilterOperator<T>>("filter", [predicate](const T& input) {
    return predicate(input);
  });
  auto new_id = new_graph->addOperator(std::dynamic_pointer_cast<BaseOperator<T, T>>(filter_op));
  if (last_operator_id_ != static_cast<ExecutionGraph::OperatorId>(-1)) {
    new_graph->connectOperators(last_operator_id_, new_id);
  }
  return Stream<T>(engine_, new_graph, new_id);
}

template <typename T>
Stream<T> Stream<T>::sink(std::function<void(const T&)> sink_func) {
  auto new_graph = std::make_shared<ExecutionGraph>(*graph_);
  auto lambda_sink = std::make_unique<LambdaSinkFunction>(sink_func);
  auto sink_op = std::make_shared<SinkOperator<T>>("sink", std::move(lambda_sink));
  auto new_id = new_graph->addOperator(std::dynamic_pointer_cast<BaseOperator<T, T>>(sink_op));
  if (last_operator_id_ != static_cast<ExecutionGraph::OperatorId>(-1)) {
    new_graph->connectOperators(last_operator_id_, new_id);
  }
  return Stream<T>(engine_, new_graph, new_id);
}

template <typename T>
void Stream<T>::execute() {
  if (graph_) {
    graph_->run();
  }
}

}  // namespace sage_flow
