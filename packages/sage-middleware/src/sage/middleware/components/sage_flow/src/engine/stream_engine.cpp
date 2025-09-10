#include <algorithm>
#include <stdexcept>

#include "engine/execution_graph.hpp"
#include "engine/stream_engine.hpp"
#include "message/multimodal_message.hpp"
#include "operator/operator.hpp"
namespace sage_flow {

StreamEngine::StreamEngine() : StreamEngine(EngineConfig{}) {}
 
StreamEngine::StreamEngine(const EngineConfig& config) : config_(config) {}
 
StreamEngine::~StreamEngine() {
  stop();
}

auto StreamEngine::start() -> void {
  if (is_running_.load()) {
    return;
  }

  is_running_.store(true);
}

auto StreamEngine::stop() -> void {
  if (!is_running_.load()) {
    return;
  }

  is_running_.store(false);

  // 停止所有正在运行的图
  std::lock_guard<std::mutex> lock(graphs_mutex_);
  for (auto& [graph_id, state] : graph_states_) {
    if (state == GraphState::RUNNING) {
      graph_states_[graph_id] = GraphState::STOPPED;
    }
  }
}

auto StreamEngine::isRunning() const -> bool { return is_running_.load(); }

auto StreamEngine::createGraph() -> std::shared_ptr<ExecutionGraph> {
  return std::make_shared<ExecutionGraph>();
}
 
auto StreamEngine::submit(std::shared_ptr<ExecutionGraph> graph) -> GraphId {
  if (!graph || !validateGraph(graph)) {
    throw std::runtime_error("Invalid execution graph");
  }

  std::lock_guard<std::mutex> lock(graphs_mutex_);

  GraphId id = next_graph_id_++;
  submitted_graphs_[id] = graph;
  graph_states_[id] = GraphState::SUBMITTED;

  return id;
}

auto StreamEngine::executeGraph(GraphId graph_id) -> void {
  auto graph = getGraphForExecution(graph_id);
  if (!graph) {
    std::string error_msg = "Graph " + std::to_string(graph_id) + " not found";
    handleError(graph_id, error_msg);
    return;
  }

  {
    std::lock_guard<std::mutex> lock(graphs_mutex_);
    graph_states_[graph_id] = GraphState::RUNNING;
  }

  try {
    executeSingleThreaded(graph);

    {
      std::lock_guard<std::mutex> lock(graphs_mutex_);
      graph_states_[graph_id] = GraphState::COMPLETED;
    }

  } catch (const std::exception& e) {
    std::string error_msg = "Graph " + std::to_string(graph_id) + " execution failed: " + e.what();
    handleError(graph_id, error_msg);
    throw;
  } catch (...) {
    std::string error_msg = "Graph " + std::to_string(graph_id) + " execution failed";
    handleError(graph_id, error_msg);
    throw;
  }
}

auto StreamEngine::stopGraph(GraphId graph_id) -> void {
  std::lock_guard<std::mutex> lock(graphs_mutex_);
  auto it = graph_states_.find(graph_id);
  if (it != graph_states_.end()) {
    it->second = GraphState::STOPPED;
  }
}
 
// =============================================================================
// 配置管理
// =============================================================================

auto StreamEngine::setExecutionMode(ExecutionMode mode) -> void {
  config_.execution_mode = mode;
}
 
auto StreamEngine::getExecutionMode() const -> ExecutionMode {
  return config_.execution_mode;
}
 
auto StreamEngine::updateConfig(const EngineConfig& config) -> void {
  config_ = config;
}
 
auto StreamEngine::getConfig() const -> const EngineConfig& { return config_; }
 
// =============================================================================
// 图状态管理
// =============================================================================
 
auto StreamEngine::getGraphState(GraphId graph_id) const -> GraphState {
  std::lock_guard<std::mutex> lock(graphs_mutex_);
  auto it = graph_states_.find(graph_id);
  return (it != graph_states_.end()) ? it->second : GraphState::UNKNOWN;
}
 
auto StreamEngine::isGraphRunning(GraphId graph_id) const -> bool {
  return getGraphState(graph_id) == GraphState::RUNNING;
}
 
auto StreamEngine::getLastError(GraphId graph_id) const -> std::string {
  std::lock_guard<std::mutex> lock(graphs_mutex_);
  auto it = graph_errors_.find(graph_id);
  return (it != graph_errors_.end()) ? it->second : "";
}
 
// =============================================================================
// 私有辅助方法
// =============================================================================
 
auto StreamEngine::validateGraph(const std::shared_ptr<ExecutionGraph>& graph)
  -> bool {
  return graph && graph->validate() && !graph->empty();
}
 
auto StreamEngine::getGraphForExecution(GraphId graph_id)
  -> std::shared_ptr<ExecutionGraph> {
  std::lock_guard<std::mutex> lock(graphs_mutex_);
  auto it = submitted_graphs_.find(graph_id);
  if (it == submitted_graphs_.end()) {
    return nullptr;
  }

  auto state_it = graph_states_.find(graph_id);
  if (state_it == graph_states_.end() ||
      (state_it->second != GraphState::SUBMITTED)) {
    return nullptr;
  }

  return it->second;
}
 
auto StreamEngine::handleError(GraphId graph_id,
                               const std::string& error_message) -> void {
  {
    std::lock_guard<std::mutex> lock(graphs_mutex_);
    graph_states_[graph_id] = GraphState::ERROR;
    graph_errors_[graph_id] = error_message;
  }
}
 
// Core single-threaded execution
auto StreamEngine::executeSingleThreaded(std::shared_ptr<ExecutionGraph> graph)
  -> void {
  if (!graph || graph->empty()) {
    return;
  }

  auto operators = graph->getTopologicalOrder();

  // Initialize intermediate results storage
  intermediate_results_ = std::make_shared<std::unordered_map<ExecutionGraph::OperatorId, std::vector<std::shared_ptr<MultiModalMessage>>>>();

  for (auto op_id : operators) {
    try {
      auto op = graph->getOperator(op_id);
      if (!op) {
        continue;
      }

      // Set up emit callback to collect output messages
      op->setEmitCallback([&](int, Response<MultiModalMessage>& output_record) {
        if (output_record.hasMessages()) {
          auto output_msg = output_record.getMessage();
          if (output_msg) {
            if (intermediate_results_->find(op_id) == intermediate_results_->end()) {
              (*intermediate_results_)[op_id] = std::vector<std::shared_ptr<MultiModalMessage>>();
            }
            (*intermediate_results_)[op_id].push_back(output_msg);
          }
        }
      });

      op->open();

      if (op->getType() == OperatorType::kSource) {
        auto source_op = std::dynamic_pointer_cast<SourceOperator>(op);
        if (source_op) {
          std::vector<std::shared_ptr<MultiModalMessage>> input;
          while (source_op->hasNext()) {
            source_op->process(input);
          }
        }
      } else if (op->getType() == OperatorType::kSink) {
        auto predecessors = graph->getPredecessors(op_id);
        std::vector<std::shared_ptr<MultiModalMessage>> input_messages;
        if (intermediate_results_) {
          for (auto pred_id : predecessors) {
            auto it = intermediate_results_->find(pred_id);
            if (it != intermediate_results_->end()) {
              for (auto& msg : it->second) {
                if (msg) {
                  input_messages.push_back(msg);
                }
              }
            }
          }
        }
        for (auto& msg : input_messages) {
          if (msg) {
            std::vector<std::shared_ptr<MultiModalMessage>> input;
            input.push_back(msg);
            op->process(input);
          }
        }
      } else {
        auto predecessors = graph->getPredecessors(op_id);
        std::vector<std::shared_ptr<MultiModalMessage>> input_messages;
        if (intermediate_results_) {
          for (auto pred_id : predecessors) {
            auto it = intermediate_results_->find(pred_id);
            if (it != intermediate_results_->end()) {
              for (auto& msg : it->second) {
                if (msg) {
                  input_messages.push_back(msg);
                }
              }
            }
          }
        }
        for (auto& msg : input_messages) {
          if (msg) {
            std::vector<std::shared_ptr<MultiModalMessage>> input;
            input.push_back(msg);
            op->process(input);
          }
        }
      }

      op->close();

    } catch (const std::exception& e) {
      throw;
    } catch (...) {
      throw;
    }
  }
}
 
}  // namespace sage_flow