#include "../../include/data_stream/data_stream.hpp"
#include "../../include/engine/execution_graph.hpp"
#include "../../include/engine/stream_engine.hpp"
#include "../../include/function/base_function.hpp"
#include "../../include/function/map_function.hpp"
#include "../../include/function/filter_function.hpp"
#include "../../include/function/sink_function.hpp"
#include "../../include/operator/map_operator.hpp"
#include "../../include/operator/filter_operator.hpp"
#include "../../include/operator/source_operator.hpp"
#include "../../include/operator/sink_operator.hpp"
#include "../../include/message/multimodal_message.hpp"

#include <iostream>

namespace sage_flow {

// Static factory method to create DataStream from list
auto DataStream::from_list(const std::vector<std::unordered_map<std::string, std::variant<std::string, int64_t, double, bool>>>& data,
                           std::shared_ptr<StreamEngine> engine) -> DataStream {
  // Create default engine if not provided
  if (!engine) {
    engine = std::make_shared<StreamEngine>();
  }
  // Create default engine if not provided
  if (!engine) {
    engine = std::make_shared<StreamEngine>();
  }

  // Create execution graph
  auto graph = std::make_shared<ExecutionGraph>();

  // Create DataStream instance
  DataStream stream(engine, graph, static_cast<ExecutionGraph::OperatorId>(-1));

  // Create a source function that yields messages from the data list
  size_t index = 0;
  auto source_func = [&data, &index]() -> std::unique_ptr<MultiModalMessage> {
    if (index < data.size()) {
      // Convert data item to JSON-like string for the message content
      std::string content = "{";
      bool first = true;
      for (const auto& [key, value] : data[index]) {
        if (!first) content += ",";
        content += "\"" + key + "\":";
        // Simple conversion to string - in practice you'd want proper JSON serialization
        if (std::holds_alternative<std::string>(value)) {
          content += "\"" + std::get<std::string>(value) + "\"";
        } else if (std::holds_alternative<int64_t>(value)) {
          content += std::to_string(std::get<int64_t>(value));
        } else if (std::holds_alternative<double>(value)) {
          content += std::to_string(std::get<double>(value));
        } else if (std::holds_alternative<bool>(value)) {
          content += std::get<bool>(value) ? "true" : "false";
        } else {
          content += "\"unknown\"";
        }
        first = false;
      }
      content += "}";

      auto msg = std::make_unique<MultiModalMessage>(
          static_cast<uint64_t>(index),
          ContentType::kText,
          MultiModalMessage::ContentVariant(content)
      );

      index++;
      return msg;
    }
    return nullptr;
  };

  // Add the source to the stream
  stream.from_source(source_func);

  return stream;
}

// Constructor
DataStream::DataStream(std::shared_ptr<StreamEngine> engine,
                       std::shared_ptr<ExecutionGraph> graph,
                       ExecutionGraph::OperatorId last_operator_id)
    : engine_(std::move(engine)),
      graph_(std::move(graph)),
      last_operator_id_(last_operator_id) {}

// Non-template method implementations
auto DataStream::from_source(
    const std::function<std::unique_ptr<MultiModalMessage>()>& source_func)
    -> DataStream& {
  // Create a simple source operator that uses the provided function
  class LambdaSourceOperator : public SourceOperator {
  public:
    LambdaSourceOperator(std::string name,
                        std::function<std::unique_ptr<MultiModalMessage>()> func)
        : SourceOperator(std::move(name)), source_func_(std::move(func)), message_count_(0), max_messages_(10), messages_generated_(false) {}

    auto hasNext() -> bool override {
      // If we haven't generated messages yet, generate them all at once
      if (!messages_generated_ && source_func_) {
        generateAllMessages();
        messages_generated_ = true;
      }

      // Check if we have messages available
      return message_count_ < messages_.size();
    }

    auto next() -> std::unique_ptr<MultiModalMessage> override {
      if (message_count_ < messages_.size()) {
        return std::move(messages_[message_count_++]);
      }
      return nullptr;
    }

    auto reset() -> void override {
      message_count_ = 0;
      messages_generated_ = false;
      messages_.clear();
    }

  private:
    auto generateAllMessages() -> void {
      messages_.clear();
      for (size_t i = 0; i < max_messages_; ++i) {
        auto msg = source_func_();
        if (msg) {
          messages_.push_back(std::move(msg));
        } else {
          break; // Stop if source function returns nullptr
        }
      }
    }

    std::function<std::unique_ptr<MultiModalMessage>()> source_func_;
    std::vector<std::unique_ptr<MultiModalMessage>> messages_;
    size_t message_count_;
    size_t max_messages_;
    bool messages_generated_;
  };

  // Create the source operator
  auto source_op = std::make_unique<LambdaSourceOperator>(
      "lambda_source", source_func);

  // Add to execution graph
  auto op_id = graph_->addOperator(std::shared_ptr<BaseOperator>(std::move(source_op)));
  last_operator_id_ = op_id;
  source_operator_id_ = op_id;  // Track the source operator

  return *this;
}

auto DataStream::map(const std::function<std::unique_ptr<MultiModalMessage>(
                         std::unique_ptr<MultiModalMessage>)>& func)
    -> DataStream& {
  // Create a MapFunction from the lambda
  auto map_func = std::make_unique<MapFunction>("lambda_map");

  // Adapt the lambda to MapFunc signature
  MapFunc adapted_func = [func](std::unique_ptr<MultiModalMessage>& message) {
    if (message) {
      // Apply the transformation and replace the message
      message = func(std::move(message));
    }
  };

  map_func->setMapFunc(std::move(adapted_func));

  // Create MapOperator with the function
  auto map_op = std::make_unique<MapOperator>("map_operator", std::move(map_func));

  // Add to execution graph
  auto op_id = graph_->addOperator(std::move(map_op));
  connectToLastOperator(op_id);
  last_operator_id_ = op_id;

  return *this;
}

auto DataStream::filter(
    const std::function<bool(const MultiModalMessage&)>& predicate)
    -> DataStream& {
  // Create a FilterFunction from the lambda
  auto filter_func = std::make_unique<FilterFunction>("lambda_filter");
  filter_func->setFilterFunc(predicate);

  // Create FilterOperator with the function
  auto filter_op = std::make_unique<FilterOperator>("filter_operator", std::move(filter_func));

  // Add to execution graph
  auto op_id = graph_->addOperator(std::move(filter_op));
  connectToLastOperator(op_id);
  last_operator_id_ = op_id;

  return *this;
}

auto DataStream::connect(const DataStream& /*other*/) -> DataStream {
  // Simplified implementation
  // TODO: Implement actual stream connection logic
  return DataStream(engine_, graph_, last_operator_id_);
}

auto DataStream::union_(const DataStream& other) -> DataStream {
  // Create a new DataStream for the union result
  DataStream result(engine_, graph_, last_operator_id_);

  // For now, create a simple union that combines both streams
  // In practice, this would require more complex operator logic
  // TODO: Implement proper union operator

  return result;
}

auto DataStream::sink(
    const std::function<void(const MultiModalMessage&)>& sink_func)
    -> void {
  // Create a simple sink function that uses the provided function
  class LambdaSinkFunction : public SinkFunction {
  public:
    LambdaSinkFunction(std::string name,
                      std::function<void(const MultiModalMessage&)> func)
        : SinkFunction(std::move(name), func) {}

    void init() override {
      // Initialize if needed
    }

    void close() override {
      // Cleanup if needed
    }

  private:
    // Note: sink_func_ is inherited from SinkFunction
  };

  // Create the sink function
  auto sink_function = std::make_unique<LambdaSinkFunction>(
      "lambda_sink", sink_func);

  // Create the sink operator
  auto sink_op = std::make_unique<SinkOperator>(
      "sink_operator", std::move(sink_function));

  // Add to execution graph
  auto sink_id = graph_->addOperator(std::shared_ptr<BaseOperator>(std::move(sink_op)));
  connectToLastOperator(sink_id);

  finalizeGraph();

  // Execute the data stream immediately
  execute();
}

auto DataStream::execute() -> void {
    // 检查是否可以执行
    if (!canExecute()) {
      throw std::runtime_error("Cannot execute DataStream: invalid state or no operators defined");
    }

    // 如果graph还没有被finalize，先finalize它
    if (!is_finalized_) {
      finalizeGraph();
    }

    // 确保graph_id_存在
    if (graph_id_.has_value()) {
      // 直接调用engine的executeGraph，让异常自然传播
      engine_->executeGraph(graph_id_.value());
    } else {
      throw std::runtime_error("Failed to finalize graph for execution");
    }
}

auto DataStream::executeAsync() -> void {
   // 检查是否可以执行
   if (!canExecute()) {
     throw std::runtime_error("Cannot execute DataStream asynchronously: invalid state or no operators defined");
   }

   // 如果graph还没有被finalize，先finalize它
   if (!is_finalized_) {
     finalizeGraph();
   }

   // 确保graph_id_存在
   if (graph_id_.has_value()) {
     engine_->executeGraphAsync(graph_id_.value());
   } else {
     throw std::runtime_error("Failed to finalize graph for async execution");
   }
}

auto DataStream::stop() -> void {
   // 如果graph还没有被finalize但有graph_id_，说明可能正在运行
   if (!is_finalized_ && graph_id_.has_value()) {
     engine_->stopGraph(graph_id_.value());
   } else if (graph_id_.has_value()) {
     engine_->stopGraph(graph_id_.value());
   }
   // 如果没有graph_id_，说明graph没有被提交，无需停止
}

auto DataStream::getOperatorCount() const -> size_t { return graph_->size(); }

auto DataStream::isExecuting() const -> bool {
  if (graph_id_.has_value()) {
    return engine_->isGraphRunning(graph_id_.value());
  }
  return false;
}

auto DataStream::getLastOperatorId() const -> ExecutionGraph::OperatorId {
  return last_operator_id_;
}

auto DataStream::setLastOperatorId(ExecutionGraph::OperatorId id) -> void {
  last_operator_id_ = id;
}

auto DataStream::getGraph() const -> std::shared_ptr<ExecutionGraph> {
  return graph_;
}

auto DataStream::getEngine() const -> std::shared_ptr<StreamEngine> {
  return engine_;
}

// Private helper methods
auto DataStream::connectToLastOperator(
    ExecutionGraph::OperatorId new_operator_id) -> void {
  if (last_operator_id_ != static_cast<ExecutionGraph::OperatorId>(-1)) {
    graph_->connectOperators(last_operator_id_, new_operator_id);
  }
}

auto DataStream::finalizeGraph() -> void {
   if (!is_finalized_) {
     // 检查是否有operators
     if (graph_->size() == 0) {
       throw std::runtime_error("Cannot finalize empty graph: no operators defined");
     }

     // 检查是否有有效的engine
     if (!engine_) {
       throw std::runtime_error("Cannot finalize graph: no stream engine available");
     }

     // finalize graph
     graph_->finalize();

     // submit graph to engine
     graph_id_ = engine_->submitGraph(graph_);

     // 检查是否成功提交
     if (!graph_id_.has_value()) {
       throw std::runtime_error("Failed to submit graph to stream engine");
     }

     is_finalized_ = true;
   }
}

auto DataStream::validateConfig(
     const std::unordered_map<std::string, std::any>& config) -> bool {
   // Basic validation - in practice, you'd validate specific configuration
   // parameters
   return !config.empty() || config.empty();  // Always return true for now
}

auto DataStream::canExecute() const -> bool {
    return graph_ && engine_ && graph_->size() > 0;
}

// ===============================
// Python-friendly method implementations
// ===============================

auto DataStream::collect() -> std::vector<std::unique_ptr<MultiModalMessage>> {
    std::vector<std::unique_ptr<MultiModalMessage>> results;

    // For now, create a simple collection mechanism
    // This would need to be enhanced with proper execution and result collection
    if (canExecute()) {
        // Execute the stream and collect results
        // This is a simplified implementation
        execute();

        // In a real implementation, we would collect results from the sink operators
        // For now, return empty vector as placeholder
    }

    return results;
}

auto DataStream::take(size_t n) -> DataStream {
    // Create a new DataStream with a take operator
    // This is a simplified implementation
    auto new_graph = std::make_shared<ExecutionGraph>();
    DataStream result_stream(engine_, new_graph, static_cast<ExecutionGraph::OperatorId>(-1));

    // Copy current operators up to the limit
    // This would need proper implementation of a take operator

    return result_stream;
}

auto DataStream::count() -> size_t {
    // For now, return operator count as a simple metric
    // In a real implementation, this would count actual messages
    return getOperatorCount();
}

auto DataStream::empty() const -> bool {
    // Check if the stream has any operators configured
    return getOperatorCount() == 0;
}

}  // namespace sage_flow