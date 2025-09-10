#pragma once

#include <atomic>
#include <chrono>
#include <cstdint>
#include <memory>
#include <mutex>
#include <unordered_map>
#include <vector>

#include <memory> 

#include "execution_graph.hpp"

namespace sage_flow {

/**
 * @brief Execution modes for the stream engine
 */
enum class ExecutionMode : std::uint8_t {
  SINGLE_THREADED = 0,
  MULTI_THREADED = 1,
  ASYNC = 2,
  DISTRIBUTED = 3,  // SAGE compatible distributed mode
  HYBRID = 4        // Hybrid Python/C++ execution mode
};

/**
 * @brief States for execution graphs
 */
enum class GraphState : std::uint8_t {
  UNKNOWN = 0,
  SUBMITTED = 1,
  RUNNING = 2,
  COMPLETED = 3,
  STOPPED = 4,
  ERROR = 5,
  PAUSED = 6,     // Paused state
  RECOVERING = 7  // Recovery state
};

/**
 * @brief Execution strategies compatible with SAGE
 */
enum class ExecutionStrategy : std::uint8_t {
  EAGER = 0,      // Immediate execution
  LAZY = 1,       // Lazy loading execution
  STREAMING = 2,  // Streaming execution
  BATCH = 3,      // Batch processing execution
  ADAPTIVE = 4    // Adaptive execution
};

/**
 * @brief Configuration for the stream engine
 */
struct EngineConfig {
  ExecutionMode execution_mode = ExecutionMode::MULTI_THREADED;
  ExecutionStrategy execution_strategy = ExecutionStrategy::STREAMING;
  size_t thread_pool_size = 4;
  size_t max_queue_size = 10000;
  size_t batch_size = 100;
  std::chrono::milliseconds timeout = std::chrono::milliseconds(30000);
  bool enable_checkpointing = false;
  bool enable_fault_tolerance = true;
  bool enable_sage_compatibility = true;
  std::string checkpoint_directory = "./checkpoints";
};

/**
 * @brief Stream processing engine for SAGE flow
 *
 * Manages the execution of stream processing operators and provides
 * different execution modes for optimal performance.
 */
class StreamEngine : public std::enable_shared_from_this<StreamEngine> {
public:
  using GraphId = size_t;

  // 构造函数
  StreamEngine();
  explicit StreamEngine(const EngineConfig& config);
  ~StreamEngine();

  // Prevent copying
  StreamEngine(const StreamEngine&) = delete;
  auto operator=(const StreamEngine&) -> StreamEngine& = delete;

  // Delete moving due to atomic members
  StreamEngine(StreamEngine&&) = delete;
  auto operator=(StreamEngine&&) -> StreamEngine& = delete;

  // Core execution methods
  auto execute(std::shared_ptr<ExecutionGraph> graph) -> void;
  auto start() -> void;
  auto stop() -> void;
  auto isRunning() const -> bool;

  // Graph management
  auto createGraph() -> std::shared_ptr<ExecutionGraph>;
  auto submit(std::shared_ptr<ExecutionGraph> graph) -> GraphId;
  auto executeGraph(GraphId graph_id) -> void;
  auto stopGraph(GraphId graph_id) -> void;

  // Configuration
  auto setExecutionMode(ExecutionMode mode) -> void;
  auto getExecutionMode() const -> ExecutionMode;
  auto updateConfig(const EngineConfig& config) -> void;
  auto getConfig() const -> const EngineConfig&;

  // Graph state management
  auto getGraphState(GraphId graph_id) const -> GraphState;
  auto isGraphRunning(GraphId graph_id) const -> bool;

  // Error handling
  auto getLastError(GraphId graph_id) const -> std::string;

private:
  // 配置和状态
  EngineConfig config_;
  ExecutionMode execution_mode_ = ExecutionMode::SINGLE_THREADED;
  std::atomic<bool> is_running_{false};

  // 图管理
  GraphId next_graph_id_ = 0;
  std::unordered_map<GraphId, std::shared_ptr<ExecutionGraph>> submitted_graphs_;
  std::unordered_map<GraphId, GraphState> graph_states_;
  std::unordered_map<GraphId, std::string> graph_errors_;
  mutable std::mutex graphs_mutex_;

  // 中间结果存储（用于操作符链消息传递）
  std::shared_ptr<std::unordered_map<ExecutionGraph::OperatorId, std::vector<std::shared_ptr<MultiModalMessage>>>> intermediate_results_;

  // Internal execution methods
  auto executeSingleThreaded(std::shared_ptr<ExecutionGraph> graph) -> void;

  // Internal helper methods
  auto getGraphForExecution(GraphId graph_id) -> std::shared_ptr<ExecutionGraph>;

  // 内部辅助方法
  auto handleError(GraphId graph_id, const std::string& error_message) -> void;
  auto validateGraph(const std::shared_ptr<ExecutionGraph>& graph) -> bool;
};

}  // namespace sage_flow
