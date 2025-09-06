#pragma once

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <future>
#include <memory>
#include <mutex>
#include <queue>
#include <thread>
#include <unordered_map>
#include <vector>

#include <memory>  // For std::enable_shared_from_this

#include "execution_graph.hpp"
#include "stream_engine_config.hpp"
#include "stream_engine_enums.hpp"
#include "stream_engine_metrics.hpp"

// 前向声明以避免循环依赖
namespace sage_flow {
namespace integration {
class MessageBridge;
}
}  // namespace sage_flow

namespace sage_flow {

class BaseOperator;
class ExecutionGraph;

/**
 * @brief Stream processing engine for SAGE flow
 *
 * Manages the execution of stream processing operators and provides
 * different execution modes for optimal performance.
 */
class StreamEngine : public std::enable_shared_from_this<StreamEngine> {
public:
  using GraphId = size_t;
  using TaskId = size_t;
  using MessageCallback = std::function<void(const class MultiModalMessage&)>;
  using ErrorCallback = std::function<void(const std::string&, GraphId)>;
  using CompletionCallback = std::function<void(GraphId)>;

  // 构造函数
  StreamEngine();
  explicit StreamEngine(ExecutionMode mode);
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
  auto pause() -> void;
  auto resume() -> void;
  auto isRunning() const -> bool;
  auto isPaused() const -> bool;

  // Graph management
  auto createGraph() -> std::shared_ptr<ExecutionGraph>;
  auto submitGraph(const std::shared_ptr<ExecutionGraph>& graph) -> GraphId;
  auto executeGraph(GraphId graph_id) -> void;
  auto executeGraphAsync(GraphId graph_id) -> std::future<void>;
  auto executeGraphWithStrategy(GraphId graph_id,
                                ExecutionStrategy strategy) -> void;
  auto stopGraph(GraphId graph_id) -> void;
  auto pauseGraph(GraphId graph_id) -> void;
  auto resumeGraph(GraphId graph_id) -> void;
  auto restartGraph(GraphId graph_id) -> void;

  // SAGE 兼容的执行方法
  auto submit(std::shared_ptr<ExecutionGraph> graph)
      -> GraphId;  // SAGE 风格的提交
  auto executeWithCallback(GraphId graph_id,
                           CompletionCallback callback) -> void;
  auto executeStream(
      GraphId graph_id,
      const std::vector<std::unique_ptr<class MultiModalMessage>>&
          input_messages) -> void;

  // Configuration
  auto setExecutionMode(ExecutionMode mode) -> void;
  auto getExecutionMode() const -> ExecutionMode;
  auto setExecutionStrategy(ExecutionStrategy strategy) -> void;
  auto getExecutionStrategy() const -> ExecutionStrategy;
  auto setThreadCount(size_t thread_count) -> void;
  auto getThreadCount() const -> size_t;
  auto updateConfig(const EngineConfig& config) -> void;
  auto getConfig() const -> const EngineConfig&;

  // Performance monitoring
  auto getTotalProcessedMessages() const -> uint64_t;
  auto getThroughput() const -> double;  // messages per second
  auto getMetrics() const -> PerformanceMetrics;
  auto resetMetrics() -> void;
  auto getAverageProcessingTime() const -> double;
  auto getMemoryUsage() const -> uint64_t;

  // Graph state management
  auto getGraphState(GraphId graph_id) const -> GraphState;
  auto isGraphRunning(GraphId graph_id) const -> bool;
  auto isGraphPaused(GraphId graph_id) const -> bool;
  auto removeGraph(GraphId graph_id) -> void;
  auto getSubmittedGraphs() const -> std::vector<GraphId>;
  auto getRunningGraphs() const -> std::vector<GraphId>;
  auto getCompletedGraphs() const -> std::vector<GraphId>;

  // Callback management
  auto setMessageCallback(MessageCallback callback) -> void;
  auto setErrorCallback(ErrorCallback callback) -> void;
  auto setCompletionCallback(CompletionCallback callback) -> void;

  // Error handling and fault tolerance
  auto getLastError(GraphId graph_id) const -> std::string;
  auto enableFaultTolerance(bool enable) -> void;
  auto createCheckpoint(GraphId graph_id) -> std::string;
  auto restoreFromCheckpoint(GraphId graph_id,
                             const std::string& checkpoint_id) -> bool;

  // SAGE 集成
  auto enableSageCompatibility(bool enable) -> void;
  auto isSageCompatibilityEnabled() const -> bool;
  auto getMessageBridge() -> integration::MessageBridge&;
  auto setMessageBridge(std::unique_ptr<integration::MessageBridge> bridge)
      -> void;

  // 资源管理
  auto getResourceUsage() const -> std::unordered_map<std::string, double>;
  auto optimizeResourceAllocation() -> void;
  auto cleanupResources() -> void;

private:
  // 配置和状态
  EngineConfig config_;
  ExecutionMode execution_mode_ = ExecutionMode::SINGLE_THREADED;
  std::atomic<bool> is_running_{false};
  std::atomic<bool> is_paused_{false};
  PerformanceMetrics metrics_;

  // 线程管理
  std::vector<std::thread> worker_threads_;
  // std::unique_ptr<class ThreadPool> thread_pool_;  // Temporarily disabled
  // due to incomplete type

  // 图管理
  GraphId next_graph_id_ = 0;
  std::unordered_map<GraphId, std::shared_ptr<ExecutionGraph>>
      submitted_graphs_;
  std::unordered_map<GraphId, GraphState> graph_states_;
  std::unordered_map<GraphId, std::string> graph_errors_;
  std::unordered_map<GraphId, std::chrono::steady_clock::time_point>
      graph_start_times_;
  mutable std::mutex graphs_mutex_;

  // 任务队列
  std::queue<std::function<void()>> task_queue_;
  std::mutex queue_mutex_;
  std::condition_variable queue_condition_;

  // 回调函数
  MessageCallback message_callback_;
  ErrorCallback error_callback_;
  CompletionCallback completion_callback_;
  std::mutex callback_mutex_;

  // SAGE 集成
  // std::unique_ptr<integration::MessageBridge> message_bridge_;  //
  // Temporarily disabled due to incomplete type
  bool sage_compatibility_enabled_ = true;

  // 容错和检查点
  std::unordered_map<GraphId, std::string> checkpoints_;
  std::mutex checkpoint_mutex_;

  // 中间结果存储（用于操作符链消息传递）
  std::shared_ptr<std::unordered_map<ExecutionGraph::OperatorId, std::vector<std::unique_ptr<class MultiModalMessage>>>> intermediate_results_;

  // Internal execution methods
  auto executeSingleThreaded(std::shared_ptr<ExecutionGraph> graph) -> void;
  auto executeMultiThreaded(std::shared_ptr<ExecutionGraph> graph) -> void;
  auto executeAsync(std::shared_ptr<ExecutionGraph> graph) -> void;
  auto executeDistributed(std::shared_ptr<ExecutionGraph> graph) -> void;
  auto executeHybrid(std::shared_ptr<ExecutionGraph> graph) -> void;
  auto executeWithStrategy(std::shared_ptr<ExecutionGraph> graph,
                           ExecutionStrategy strategy) -> void;

  // Internal helper methods
  auto getGraphForExecution(GraphId graph_id)
      -> std::shared_ptr<ExecutionGraph>;

  auto workerThreadFunc(std::shared_ptr<ExecutionGraph> graph,
                        size_t thread_id) -> void;
  auto taskProcessorLoop() -> void;
  auto processTaskQueue() -> void;

  // 内部辅助方法
  auto updateMetrics(uint64_t processed_messages,
                     double processing_time_ms) -> void;
  auto handleError(GraphId graph_id, const std::string& error_message) -> void;
  auto notifyCompletion(GraphId graph_id) -> void;
  auto initializeThreadPool() -> void;
  auto cleanupThreadPool() -> void;
  auto validateGraph(const std::shared_ptr<ExecutionGraph>& graph) -> bool;
  auto validateStateTransition(GraphId graph_id, GraphState new_state) const -> bool;
  auto updateGraphState(GraphId graph_id, GraphState new_state) -> bool;
  auto createGraphCheckpoint(GraphId graph_id) -> std::string;
  auto loadGraphFromCheckpoint(GraphId graph_id,
                               const std::string& checkpoint_id) -> bool;
};

}  // namespace sage_flow
