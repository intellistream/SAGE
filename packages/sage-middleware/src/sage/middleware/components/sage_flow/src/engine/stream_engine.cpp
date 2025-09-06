#include <algorithm>
#include <future>
#include <iostream>
#include <stdexcept>
#include <thread>

#include "engine/execution_graph.hpp"
#include "engine/stream_engine.hpp"
#include "message/message_bridge.hpp"
#include "message/multimodal_message.hpp"
#include "operator/operator.hpp"

namespace sage_flow {

// =============================================================================
// ThreadPool 内部实现
// =============================================================================

class ThreadPool {
public:
  explicit ThreadPool(size_t num_threads) : stop_(false) {
    for (size_t i = 0; i < num_threads; ++i) {
      workers_.emplace_back([this] {
        for (;;) {
          std::function<void()> task;
          {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            condition_.wait(lock, [this] { return stop_ || !tasks_.empty(); });

            if (stop_ && tasks_.empty()) {
              return;
            }

            task = std::move(tasks_.front());
            tasks_.pop();
          }
          task();
        }
      });
    }
  }

  ~ThreadPool() {
    {
      std::unique_lock<std::mutex> lock(queue_mutex_);
      stop_ = true;
    }

    condition_.notify_all();

    for (std::thread& worker : workers_) {
      worker.join();
    }
  }

  template <class F, class... Args>
  auto enqueue(F&& f, Args&&... args)
      -> std::future<typename std::invoke_result<F(Args...)>::type> {
    using return_type = typename std::invoke_result<F(Args...)>::type;

    auto task = std::make_shared<std::packaged_task<return_type()>>(
        std::bind(std::forward<F>(f), std::forward<Args>(args)...));

    std::future<return_type> res = task->get_future();

    {
      std::unique_lock<std::mutex> lock(queue_mutex_);

      if (stop_) {
        throw std::runtime_error("enqueue on stopped ThreadPool");
      }

      tasks_.emplace([task]() { (*task)(); });
    }

    condition_.notify_one();
    return res;
  }

private:
  std::vector<std::thread> workers_;
  std::queue<std::function<void()>> tasks_;
  std::mutex queue_mutex_;
  std::condition_variable condition_;
  bool stop_;
};

// =============================================================================
// StreamEngine 增强实现
// =============================================================================

StreamEngine::StreamEngine() : StreamEngine(EngineConfig{}) {}

StreamEngine::StreamEngine(ExecutionMode mode) {
  EngineConfig config;
  config.execution_mode = mode;
  config_ = config;
  // initializeThreadPool();  // Temporarily disabled

  if (config_.enable_sage_compatibility) {
    // message_bridge_ = std::make_unique<integration::MessageBridge>();  //
    // Temporarily disabled
  }
}

StreamEngine::StreamEngine(const EngineConfig& config) : config_(config) {
  // initializeThreadPool();  // Temporarily disabled

  if (config_.enable_sage_compatibility) {
    // message_bridge_ = std::make_unique<integration::MessageBridge>();  //
    // Temporarily disabled
  }
}

StreamEngine::~StreamEngine() {
  stop();
  cleanupThreadPool();
}

auto StreamEngine::start() -> void {
  if (is_running_.load()) {
    return;
  }

  is_running_.store(true);
  is_paused_.store(false);
  metrics_.reset();

  // 启动任务处理循环
  worker_threads_.emplace_back(&StreamEngine::taskProcessorLoop, this);

  std::cout << "[StreamEngine] Engine started with " << config_.thread_pool_size
            << " threads\n";
}

auto StreamEngine::stop() -> void {
  if (!is_running_.load()) {
    return;
  }

  is_running_.store(false);
  is_paused_.store(false);

  // 停止所有正在运行的图
  std::lock_guard<std::mutex> lock(graphs_mutex_);
  for (auto& [graph_id, state] : graph_states_) {
    if (state == GraphState::RUNNING) {
      graph_states_[graph_id] = GraphState::STOPPED;
    }
  }

  // 通知任务队列
  queue_condition_.notify_all();

  // 等待工作线程完成
  for (auto& thread : worker_threads_) {
    if (thread.joinable()) {
      thread.join();
    }
  }
  worker_threads_.clear();

  std::cout << "[StreamEngine] Engine stopped\n";
}

auto StreamEngine::pause() -> void {
  if (!is_running_.load() || is_paused_.load()) {
    return;
  }

  is_paused_.store(true);
  std::cout << "[StreamEngine] Engine paused\n";
}

auto StreamEngine::resume() -> void {
  if (!is_running_.load() || !is_paused_.load()) {
    return;
  }

  is_paused_.store(false);
  queue_condition_.notify_all();
  std::cout << "[StreamEngine] Engine resumed\n";
}

auto StreamEngine::isRunning() const -> bool { return is_running_.load(); }

auto StreamEngine::isPaused() const -> bool { return is_paused_.load(); }

auto StreamEngine::createGraph() -> std::shared_ptr<ExecutionGraph> {
  return std::make_shared<ExecutionGraph>();
}

auto StreamEngine::submitGraph(const std::shared_ptr<ExecutionGraph>& graph)
    -> GraphId {
  return submit(graph);
}

auto StreamEngine::submit(std::shared_ptr<ExecutionGraph> graph) -> GraphId {
  if (!graph || !validateGraph(graph)) {
    throw std::runtime_error("Invalid execution graph");
  }

  std::lock_guard<std::mutex> lock(graphs_mutex_);

  GraphId id = next_graph_id_++;
  submitted_graphs_[id] = graph;
  graph_states_[id] = GraphState::SUBMITTED;
  graph_start_times_[id] = std::chrono::steady_clock::now();

  std::cout << "[StreamEngine] Graph " << id << " submitted with "
            << graph->getOperatorCount() << " operators\n";

  return id;
}

auto StreamEngine::executeGraph(GraphId graph_id) -> void {
  auto graph = getGraphForExecution(graph_id);
  if (!graph) {
    std::string error_msg = "Graph " + std::to_string(graph_id) + " not found or not in executable state";
    std::cout << "[StreamEngine] " << error_msg << std::endl;
    handleError(graph_id, error_msg);
    return;
  }

  // Validate graph state transition
  {
    std::lock_guard<std::mutex> lock(graphs_mutex_);
    auto current_state = graph_states_[graph_id];
    if (current_state != GraphState::SUBMITTED && current_state != GraphState::PAUSED) {
      std::string error_msg = "Graph " + std::to_string(graph_id) + " is in invalid state for execution: " +
                             std::to_string(static_cast<int>(current_state));
      std::cout << "[StreamEngine] " << error_msg << std::endl;
      handleError(graph_id, error_msg);
      return;
    }
  }

  std::cout << "[StreamEngine] Starting execution of graph " << graph_id << std::endl;

  // Set execution start time
  {
    std::lock_guard<std::mutex> lock(graphs_mutex_);
    graph_states_[graph_id] = GraphState::RUNNING;
    graph_start_times_[graph_id] = std::chrono::steady_clock::now();
  }

  try {
    // Execute based on current execution mode
    switch (execution_mode_) {
      case ExecutionMode::SINGLE_THREADED:
        executeSingleThreaded(graph);
        break;
      case ExecutionMode::MULTI_THREADED:
        executeMultiThreaded(graph);
        break;
      case ExecutionMode::ASYNC:
        executeAsync(graph);
        break;
      case ExecutionMode::DISTRIBUTED:
        executeDistributed(graph);
        break;
      case ExecutionMode::HYBRID:
        executeHybrid(graph);
        break;
      default:
        throw std::runtime_error("Unsupported execution mode: " +
                               std::to_string(static_cast<int>(execution_mode_)));
    }

    // Check for timeout
    {
      std::lock_guard<std::mutex> lock(graphs_mutex_);
      auto start_time_it = graph_start_times_.find(graph_id);
      if (start_time_it != graph_start_times_.end()) {
        auto elapsed = std::chrono::steady_clock::now() - start_time_it->second;
        if (elapsed > config_.timeout) {
          std::string timeout_msg = "Graph " + std::to_string(graph_id) + " execution timed out after " +
                                   std::to_string(std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count()) + "ms";
          std::cout << "[StreamEngine] " << timeout_msg << std::endl;
          handleError(graph_id, timeout_msg);
          return;
        }
      }
    }

    // Mark as completed
    {
      std::lock_guard<std::mutex> lock(graphs_mutex_);
      graph_states_[graph_id] = GraphState::COMPLETED;
    }

    std::cout << "[StreamEngine] Completed execution of graph " << graph_id << std::endl;

    // Notify completion
    notifyCompletion(graph_id);

  } catch (const std::exception& e) {
    std::string error_msg = "Graph " + std::to_string(graph_id) + " execution failed: " + e.what();
    std::cout << "[StreamEngine] " << error_msg << std::endl;
    handleError(graph_id, error_msg);
    throw; // Re-throw the exception to propagate it to the caller
  } catch (...) {
    std::string error_msg = "Graph " + std::to_string(graph_id) + " execution failed with unknown error";
    std::cout << "[StreamEngine] " << error_msg << std::endl;
    handleError(graph_id, error_msg);
    throw; // Re-throw the exception to propagate it to the caller
  }
}

auto StreamEngine::executeGraphAsync(GraphId graph_id) -> std::future<void> {
  // Simplified async execution without thread pool
  auto promise = std::make_shared<std::promise<void>>();
  std::future<void> future = promise->get_future();

  // Execute synchronously for now
  try {
    executeGraph(graph_id);
    promise->set_value();
  } catch (const std::exception& e) {
    promise->set_exception(std::current_exception());
  }

  return future;
}

auto StreamEngine::executeGraphWithStrategy(
    GraphId graph_id, ExecutionStrategy strategy) -> void {
  auto graph = getGraphForExecution(graph_id);
  if (!graph) {
    throw std::runtime_error("Graph not found or not in submittable state");
  }

  {
    std::lock_guard<std::mutex> lock(graphs_mutex_);
    graph_states_[graph_id] = GraphState::RUNNING;
  }

  try {
    executeWithStrategy(graph, strategy);

    std::lock_guard<std::mutex> lock(graphs_mutex_);
    graph_states_[graph_id] = GraphState::COMPLETED;

    notifyCompletion(graph_id);
  } catch (const std::exception& e) {
    handleError(graph_id, e.what());
  }
}

auto StreamEngine::stopGraph(GraphId graph_id) -> void {
  if (!updateGraphState(graph_id, GraphState::STOPPED)) {
    std::cout << "[StreamEngine] Failed to stop graph " << graph_id
              << ": invalid state transition" << std::endl;
  } else {
    std::cout << "[StreamEngine] Graph " << graph_id << " stopped" << std::endl;
  }
}

auto StreamEngine::pauseGraph(GraphId graph_id) -> void {
  if (!updateGraphState(graph_id, GraphState::PAUSED)) {
    std::cout << "[StreamEngine] Failed to pause graph " << graph_id
              << ": invalid state transition" << std::endl;
  } else {
    std::cout << "[StreamEngine] Graph " << graph_id << " paused" << std::endl;
  }
}

auto StreamEngine::resumeGraph(GraphId graph_id) -> void {
  if (!updateGraphState(graph_id, GraphState::RUNNING)) {
    std::cout << "[StreamEngine] Failed to resume graph " << graph_id
              << ": invalid state transition" << std::endl;
  } else {
    std::cout << "[StreamEngine] Graph " << graph_id << " resumed" << std::endl;
  }
}

auto StreamEngine::restartGraph(GraphId graph_id) -> void {
  // First check if graph exists and can be restarted
  {
    std::lock_guard<std::mutex> lock(graphs_mutex_);
    auto it = graph_states_.find(graph_id);
    if (it == graph_states_.end()) {
      std::cout << "[StreamEngine] Cannot restart graph " << graph_id
                << ": graph not found" << std::endl;
      return;
    }

    GraphState current_state = it->second;
    if (current_state != GraphState::COMPLETED && current_state != GraphState::STOPPED &&
        current_state != GraphState::ERROR) {
      std::cout << "[StreamEngine] Cannot restart graph " << graph_id
                << ": invalid state " << static_cast<int>(current_state) << std::endl;
      return;
    }
  }

  // Reset to submitted state first, then to running
  if (updateGraphState(graph_id, GraphState::SUBMITTED)) {
    updateGraphState(graph_id, GraphState::RUNNING);
    std::cout << "[StreamEngine] Graph " << graph_id << " restarted" << std::endl;
  } else {
    std::cout << "[StreamEngine] Failed to restart graph " << graph_id << std::endl;
  }
}

auto StreamEngine::executeWithCallback(GraphId graph_id,
                                       CompletionCallback callback) -> void {
  {
    std::lock_guard<std::mutex> lock(callback_mutex_);
    completion_callback_ = callback;
  }
  executeGraph(graph_id);
}

auto StreamEngine::executeStream(
    GraphId graph_id,
    const std::vector<std::unique_ptr<MultiModalMessage>>& input_messages)
    -> void {
  auto graph = getGraphForExecution(graph_id);
  if (!graph) {
    throw std::runtime_error("Graph not found");
  }

  // 流式处理实现
  auto source_operators = graph->getSourceOperators();
  if (source_operators.empty()) {
    throw std::runtime_error("No source operators found in graph");
  }

  // 将输入消息分发给源操作符
  for (const auto& message : input_messages) {
    if (message) {
      // 这里会将消息注入到源操作符中
      metrics_.total_processed_messages++;
    }
  }

  executeGraph(graph_id);
}

// =============================================================================
// 配置管理
// =============================================================================

auto StreamEngine::setExecutionMode(ExecutionMode mode) -> void {
  config_.execution_mode = mode;
  if (is_running_.load()) {
    // 运行时模式切换需要重新初始化
    std::cout << "[StreamEngine] Execution mode changed, reinitializing...\n";
  }
}

auto StreamEngine::getExecutionMode() const -> ExecutionMode {
  return config_.execution_mode;
}

auto StreamEngine::setExecutionStrategy(ExecutionStrategy strategy) -> void {
  config_.execution_strategy = strategy;
}

auto StreamEngine::getExecutionStrategy() const -> ExecutionStrategy {
  return config_.execution_strategy;
}

auto StreamEngine::setThreadCount(size_t thread_count) -> void {
  config_.thread_pool_size = thread_count;
  if (is_running_.load()) {
    cleanupThreadPool();
    initializeThreadPool();
  }
}

auto StreamEngine::getThreadCount() const -> size_t {
  return config_.thread_pool_size;
}

auto StreamEngine::updateConfig(const EngineConfig& config) -> void {
  bool need_restart = (config.thread_pool_size != config_.thread_pool_size) ||
                      (config.execution_mode != config_.execution_mode);

  config_ = config;

  if (need_restart && is_running_.load()) {
    std::cout << "[StreamEngine] Configuration changed, restarting engine...\n";
    stop();
    start();
  }
}

auto StreamEngine::getConfig() const -> const EngineConfig& { return config_; }

// =============================================================================
// 性能监控
// =============================================================================

auto StreamEngine::getTotalProcessedMessages() const -> uint64_t {
  return metrics_.total_processed_messages.load();
}

auto StreamEngine::getThroughput() const -> double {
  return metrics_.current_throughput.load();
}

auto StreamEngine::getMetrics() const -> PerformanceMetrics { return metrics_; }

auto StreamEngine::resetMetrics() -> void { metrics_.reset(); }

auto StreamEngine::getAverageProcessingTime() const -> double {
  return metrics_.avg_processing_time_ms.load();
}

auto StreamEngine::getMemoryUsage() const -> uint64_t {
  return metrics_.memory_usage_bytes.load();
}

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

auto StreamEngine::isGraphPaused(GraphId graph_id) const -> bool {
  return getGraphState(graph_id) == GraphState::PAUSED;
}

auto StreamEngine::getSubmittedGraphs() const -> std::vector<GraphId> {
  std::lock_guard<std::mutex> lock(graphs_mutex_);
  std::vector<GraphId> graph_ids;
  graph_ids.reserve(submitted_graphs_.size());
  for (const auto& [id, graph] : submitted_graphs_) {
    graph_ids.push_back(id);
  }
  return graph_ids;
}

auto StreamEngine::getRunningGraphs() const -> std::vector<GraphId> {
  std::lock_guard<std::mutex> lock(graphs_mutex_);
  std::vector<GraphId> running_graphs;
  for (const auto& [id, state] : graph_states_) {
    if (state == GraphState::RUNNING) {
      running_graphs.push_back(id);
    }
  }
  return running_graphs;
}

auto StreamEngine::getCompletedGraphs() const -> std::vector<GraphId> {
  std::lock_guard<std::mutex> lock(graphs_mutex_);
  std::vector<GraphId> completed_graphs;
  for (const auto& [id, state] : graph_states_) {
    if (state == GraphState::COMPLETED) {
      completed_graphs.push_back(id);
    }
  }
  return completed_graphs;
}

// =============================================================================
// 私有辅助方法
// =============================================================================

auto StreamEngine::initializeThreadPool() -> void {
  // if (config_.thread_pool_size > 0) {
  //   thread_pool_ = std::make_unique<ThreadPool>(config_.thread_pool_size);
  // }
}

auto StreamEngine::cleanupThreadPool() -> void {
  // thread_pool_.reset();
}

auto StreamEngine::validateGraph(const std::shared_ptr<ExecutionGraph>& graph)
    -> bool {
  return graph && graph->validate() && !graph->empty();
}

// Validate state transition for a graph
auto StreamEngine::validateStateTransition(GraphId graph_id, GraphState new_state) const -> bool {
  std::lock_guard<std::mutex> lock(graphs_mutex_);
  auto it = graph_states_.find(graph_id);
  if (it == graph_states_.end()) {
    return false; // Graph doesn't exist
  }

  GraphState current_state = it->second;

  // Define valid state transitions
  switch (current_state) {
    case GraphState::UNKNOWN:
      return new_state == GraphState::SUBMITTED;
    case GraphState::SUBMITTED:
      return new_state == GraphState::RUNNING || new_state == GraphState::STOPPED;
    case GraphState::RUNNING:
      return new_state == GraphState::COMPLETED || new_state == GraphState::ERROR ||
             new_state == GraphState::STOPPED || new_state == GraphState::PAUSED;
    case GraphState::COMPLETED:
      return new_state == GraphState::SUBMITTED; // Allow restart
    case GraphState::STOPPED:
      return new_state == GraphState::SUBMITTED; // Allow restart
    case GraphState::ERROR:
      return new_state == GraphState::SUBMITTED; // Allow retry
    case GraphState::PAUSED:
      return new_state == GraphState::RUNNING || new_state == GraphState::STOPPED;
    case GraphState::RECOVERING:
      return new_state == GraphState::RUNNING || new_state == GraphState::ERROR;
    default:
      return false;
  }
}

// Safely update graph state with validation
auto StreamEngine::updateGraphState(GraphId graph_id, GraphState new_state) -> bool {
  if (!validateStateTransition(graph_id, new_state)) {
    std::cout << "[StreamEngine] Invalid state transition for graph " << graph_id << std::endl;
    return false;
  }

  std::lock_guard<std::mutex> lock(graphs_mutex_);
  graph_states_[graph_id] = new_state;
  return true;
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
      (state_it->second != GraphState::SUBMITTED &&
       state_it->second != GraphState::PAUSED)) {
    return nullptr;
  }

  return it->second;
}

auto StreamEngine::executeWithStrategy(std::shared_ptr<ExecutionGraph> graph,
                                       ExecutionStrategy strategy) -> void {
  switch (strategy) {
    case ExecutionStrategy::EAGER:
      executeMultiThreaded(graph);
      break;
    case ExecutionStrategy::LAZY:
      executeSingleThreaded(graph);
      break;
    case ExecutionStrategy::STREAMING:
      executeAsync(graph);
      break;
    case ExecutionStrategy::BATCH:
      executeMultiThreaded(graph);
      break;
    case ExecutionStrategy::ADAPTIVE:
      // 根据图的复杂度选择策略
      if (graph->size() > 10) {
        executeMultiThreaded(graph);
      } else {
        executeSingleThreaded(graph);
      }
      break;
  }
}

auto StreamEngine::taskProcessorLoop() -> void {
  while (is_running_.load()) {
    if (is_paused_.load()) {
      std::unique_lock<std::mutex> lock(queue_mutex_);
      queue_condition_.wait(
          lock, [this] { return !is_paused_.load() || !is_running_.load(); });
    }

    processTaskQueue();
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
}

auto StreamEngine::processTaskQueue() -> void {
  std::unique_lock<std::mutex> lock(queue_mutex_);
  while (!task_queue_.empty() && is_running_.load() && !is_paused_.load()) {
    auto task = std::move(task_queue_.front());
    task_queue_.pop();
    lock.unlock();

    try {
      task();
    } catch (const std::exception& e) {
      std::cerr << "[StreamEngine] Task execution failed: " << e.what()
                << std::endl;
    }

    lock.lock();
  }
}

auto StreamEngine::handleError(GraphId graph_id,
                               const std::string& error_message) -> void {
  {
    std::lock_guard<std::mutex> lock(graphs_mutex_);
    graph_states_[graph_id] = GraphState::ERROR;
    graph_errors_[graph_id] = error_message;
  }

  std::cout << "[StreamEngine] Graph " << graph_id
            << " failed: " << error_message << std::endl;

  // 调用错误回调
  std::lock_guard<std::mutex> callback_lock(callback_mutex_);
  if (error_callback_) {
    error_callback_(error_message, graph_id);
  }
}

auto StreamEngine::notifyCompletion(GraphId graph_id) -> void {
  std::cout << "[StreamEngine] Graph " << graph_id << " completed successfully"
            << std::endl;

  // 调用完成回调
  std::lock_guard<std::mutex> lock(callback_mutex_);
  if (completion_callback_) {
    completion_callback_(graph_id);
  }
}

auto StreamEngine::updateMetrics(uint64_t processed_messages,
                                [[maybe_unused]] double processing_time_ms) -> void {
  metrics_.total_processed_messages += processed_messages;
  // Update other metrics as needed
}

// Enhanced single-threaded execution with proper error handling and limits
auto StreamEngine::executeSingleThreaded(std::shared_ptr<ExecutionGraph> graph)
    -> void {
  // Execute operators in topological order with proper error handling and limits
  if (!graph || graph->empty()) {
    return;
  }

  std::cout << "[StreamEngine] Executing graph with " << graph->size() << " operators" << std::endl;
  auto operators = graph->getTopologicalOrder();

  // Initialize intermediate results storage
  intermediate_results_ = std::make_shared<std::unordered_map<ExecutionGraph::OperatorId, std::vector<std::shared_ptr<MultiModalMessage>>>>();
  std::cout << "[StreamEngine] executeSingleThreaded: intermediate_results_ address: " << intermediate_results_.get() << std::endl;

  // Get configuration limits
  size_t max_messages_per_operator = config_.max_queue_size > 0 ? config_.max_queue_size : 1000;
  auto timeout_duration = config_.timeout;

  for (auto op_id : operators) {
    try {
      auto op = graph->getOperator(op_id);
      if (!op) {
        std::cout << "[StreamEngine] Warning: Operator " << static_cast<size_t>(op_id) << " not found, skipping" << std::endl;
        continue;
      }

      // Save operator type for error handling (unused but kept for future debugging)
      [[maybe_unused]] OperatorType op_type = op->getType();

      // Set up emit callback for this operator to collect output messages
      // Use weak_ptr to avoid dangling reference and potential segfaults
      std::weak_ptr<StreamEngine> weak_self;
      try {
        auto self = shared_from_this();
        weak_self = self;
      } catch (const std::bad_weak_ptr&) {
        // Object not managed by shared_ptr, use raw this pointer with caution
        // This is a fallback for cases where StreamEngine is not created with shared_ptr
        std::cout << "[StreamEngine] Warning: StreamEngine not managed by shared_ptr, using raw pointer" << std::endl;
      }
    #pragma GCC diagnostic push
    #pragma GCC diagnostic ignored "-Wunused-parameter"
    op->setEmitCallback([&](int output_id, Response<MultiModalMessage>& output_record) {
        (void)output_id;
        // Try to get shared_ptr first
        std::shared_ptr<StreamEngine> self;
        if (!weak_self.expired()) {
          self = weak_self.lock();
        }

        // If weak_ptr failed, check if 'this' is still valid (fallback for non-shared_ptr usage)
        if (!self) {
          if (!intermediate_results_) {
            std::cout << "[StreamEngine] Lambda: StreamEngine has been destroyed or intermediate_results_ is null, skipping callback" << std::endl;
            return;
          }
          // Use raw this pointer as fallback (less safe but better than crash)
          std::cout << "[StreamEngine] Lambda: Using raw pointer fallback" << std::endl;
        }

        std::cout << "[StreamEngine] Lambda callback executed for operator " << op_id << ", intermediate_results_ address: " << intermediate_results_.get() << std::endl;
        if (!intermediate_results_) {
          std::cout << "[StreamEngine] Lambda: intermediate_results_ is null, skipping" << std::endl;
          return;
        }
        if (output_record.hasMessages()) {
          std::cout << "[StreamEngine] Lambda: output_record has message" << std::endl;
          auto output_msg = output_record.getMessage();
          if (output_msg) {
            std::cout << "[StreamEngine] Lambda: output_msg is valid, storing in intermediate_results_[" << op_id << "]" << std::endl;
            // Ensure the intermediate_results_ entry exists
            if (intermediate_results_->find(op_id) == intermediate_results_->end()) {
              (*intermediate_results_)[op_id] = std::vector<std::shared_ptr<MultiModalMessage>>();
              std::cout << "[StreamEngine] Lambda: Created new entry for operator " << op_id << std::endl;
            }
            (*intermediate_results_)[op_id].push_back(output_msg);
            metrics_.total_processed_messages++;
            std::cout << "[StreamEngine] Lambda: Stored message, intermediate_results_[" << op_id << "] now has " << (*intermediate_results_)[op_id].size() << " messages" << std::endl;
          } else {
            std::cout << "[StreamEngine] Lambda: output_msg is null" << std::endl;
          }
        } else {
          std::cout << "[StreamEngine] Lambda: output_record has no message" << std::endl;
        }
      });

    #pragma GCC diagnostic pop

      // Open the operator with timeout
      auto start_time = std::chrono::steady_clock::now();
      op->open();

      if (op->getType() == OperatorType::kSource) {
        // For source operators, generate messages with limits
        auto source_op = std::dynamic_pointer_cast<SourceOperator>(op);
        if (source_op) {
          std::vector<std::unique_ptr<MultiModalMessage>> messages;

          // Generate messages from source with configurable limit
          size_t message_count = 0;
          while (source_op->hasNext() && message_count < max_messages_per_operator) {
            // Check timeout
            auto current_time = std::chrono::steady_clock::now();
            if (std::chrono::duration_cast<std::chrono::milliseconds>(current_time - start_time) > timeout_duration) {
              std::cout << "[StreamEngine] Timeout reached for operator " << static_cast<size_t>(op_id) << std::endl;
              break;
            }

            // Create input vector for source operators
            std::vector<std::shared_ptr<MultiModalMessage>> input;
            
            // Process through the standard process method to trigger emit callback
            if (auto result = source_op->process(input); result) {
              // Success, continue processing
            } else {
              break; // No more messages or processing failed
            }

            message_count++;
          }

          if (message_count >= max_messages_per_operator) {
            std::cout << "[StreamEngine] Message limit (" << max_messages_per_operator << ") reached for operator " << static_cast<size_t>(op_id) << std::endl;
          }

          if (intermediate_results_ && intermediate_results_->find(op_id) != intermediate_results_->end()) {
            std::cout << "[StreamEngine] Source operator " << static_cast<size_t>(op_id) << " produced " << (*intermediate_results_)[op_id].size() << " messages" << std::endl;
          } else {
            std::cout << "[StreamEngine] Source operator " << static_cast<size_t>(op_id) << " produced messages (count unavailable)" << std::endl;
          }
        }
      } else if (op->getType() == OperatorType::kSink) {
        // For sink operators, process messages from predecessors
        auto predecessors = graph->getPredecessors(op_id);
        std::vector<std::shared_ptr<MultiModalMessage>> input_messages;

        // Collect messages from all predecessors with size limit
        size_t total_messages = 0;
        if (intermediate_results_) {
          for (auto pred_id : predecessors) {
            auto it = intermediate_results_->find(pred_id);
            if (it != intermediate_results_->end()) {
              std::cout << "[StreamEngine] Sink operator " << static_cast<size_t>(op_id) << " found " << it->second.size() << " messages from predecessor " << static_cast<size_t>(pred_id) << std::endl;
              for (auto& msg : it->second) {
                if (msg && total_messages < max_messages_per_operator) {
                  input_messages.push_back(msg);
                  total_messages++;
                }
              }
            } else {
              std::cout << "[StreamEngine] Sink operator " << static_cast<size_t>(op_id) << " found no messages from predecessor " << static_cast<size_t>(pred_id) << std::endl;
            }
          }
        } else {
          std::cout << "[StreamEngine] Sink operator " << static_cast<size_t>(op_id) << " cannot access intermediate results (null)" << std::endl;
        }
        std::cout << "[StreamEngine] Sink operator " << static_cast<size_t>(op_id) << " collected " << total_messages << " messages to process" << std::endl;

        // Process each message with the sink
        for (auto& msg : input_messages) {
          if (msg) {
            // Check timeout
            auto current_time = std::chrono::steady_clock::now();
            if (std::chrono::duration_cast<std::chrono::milliseconds>(current_time - start_time) > timeout_duration) {
              std::cout << "[StreamEngine] Timeout reached while processing messages for operator " << static_cast<size_t>(op_id) << std::endl;
              break;
            }

            // Create input vector for the message
            std::vector<std::shared_ptr<MultiModalMessage>> input;
            input.push_back(msg);
            
            // Process the message (sink will consume it)
            if (auto result = op->process(input); !result) {
              std::cout << "[StreamEngine] Failed to process message in sink operator " << static_cast<size_t>(op_id) << std::endl;
            }
          }
        }

        // Sink operators don't produce output
        // Note: Don't overwrite intermediate_results[op_id] as it might be needed by other operators
        // intermediate_results[op_id] = std::vector<std::unique_ptr<MultiModalMessage>>{};
      } else {
        // For other operators (filter, map, etc.), process messages from predecessors
        auto predecessors = graph->getPredecessors(op_id);
        std::vector<std::shared_ptr<MultiModalMessage>> input_messages;

        // Collect messages from all predecessors with size limit
        std::cout << "[StreamEngine] Operator " << static_cast<size_t>(op_id) << " has " << predecessors.size() << " predecessors: ";
        for (auto pred_id : predecessors) {
          std::cout << static_cast<size_t>(pred_id) << " ";
        }
        std::cout << std::endl;

        size_t total_messages = 0;
        if (intermediate_results_) {
          for (auto pred_id : predecessors) {
            auto it = intermediate_results_->find(pred_id);
            if (it != intermediate_results_->end()) {
              std::cout << "[StreamEngine] Operator " << static_cast<size_t>(op_id) << " found " << it->second.size() << " messages from predecessor " << static_cast<size_t>(pred_id) << std::endl;
              for (auto& msg : it->second) {
                if (msg && total_messages < max_messages_per_operator) {
                  input_messages.push_back(msg);
                  total_messages++;
                }
              }
            } else {
              std::cout << "[StreamEngine] Operator " << static_cast<size_t>(op_id) << " found no messages from predecessor " << static_cast<size_t>(pred_id) << std::endl;
              // Debug: print all available intermediate results
              std::cout << "[StreamEngine] Available intermediate results: ";
              for (const auto& pair : *intermediate_results_) {
                std::cout << pair.first << "(" << pair.second.size() << ") ";
              }
              std::cout << std::endl;
              std::cout << "[StreamEngine] Looking for predecessor " << static_cast<size_t>(pred_id) << " in intermediate_results_" << std::endl;
              auto search_it = intermediate_results_->find(pred_id);
              if (search_it != intermediate_results_->end()) {
                std::cout << "[StreamEngine] Found predecessor " << static_cast<size_t>(pred_id) << " with " << search_it->second.size() << " messages" << std::endl;
              } else {
                std::cout << "[StreamEngine] Predecessor " << static_cast<size_t>(pred_id) << " NOT found in intermediate_results_" << std::endl;
              }
            }
          }
        } else {
          std::cout << "[StreamEngine] Operator " << static_cast<size_t>(op_id) << " cannot access intermediate results (null)" << std::endl;
        }
        std::cout << "[StreamEngine] Operator " << static_cast<size_t>(op_id) << " collected " << total_messages << " messages to process" << std::endl;

        // Process each message - emit callback will collect outputs automatically
        for (auto& msg : input_messages) {
          if (msg) {
            // Check timeout
            auto current_time = std::chrono::steady_clock::now();
            if (std::chrono::duration_cast<std::chrono::milliseconds>(current_time - start_time) > timeout_duration) {
              std::cout << "[StreamEngine] Timeout reached while processing messages for operator " << static_cast<size_t>(op_id) << std::endl;
              break;
            }

            // Create input vector for the message
            std::vector<std::shared_ptr<MultiModalMessage>> input;
            input.push_back(std::move(msg));
            
            // Process the message - operator will emit outputs via callback
            if (auto result = op->process(input); !result) {
              std::cout << "[StreamEngine] Failed to process message in operator " << static_cast<size_t>(op_id) << std::endl;
            }
          }
        }

        // Output messages are already collected by the emit callback
        // intermediate_results[op_id] is populated by the callback
      }

      // Close the operator
      op->close();

      // Update processing time metrics
      auto end_time = std::chrono::steady_clock::now();
      auto processing_time = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
      updateMetrics(metrics_.total_processed_messages.load(), processing_time.count());

    } catch (const std::exception& e) {
      std::cout << "[StreamEngine] Error processing operator " << static_cast<size_t>(op_id) << ": " << e.what() << std::endl;
      // Re-throw exceptions for proper error propagation in tests
      throw;
    } catch (...) {
      std::cout << "[StreamEngine] Unknown error processing operator " << static_cast<size_t>(op_id) << std::endl;
      // Re-throw exceptions for proper error propagation in tests
      throw;
    }
  }
}

auto StreamEngine::executeMultiThreaded(std::shared_ptr<ExecutionGraph> graph)
    -> void {
  // 简化的多线程执行
  executeSingleThreaded(graph);
}

auto StreamEngine::executeAsync(std::shared_ptr<ExecutionGraph> graph) -> void {
  // 简化的异步执行
  executeSingleThreaded(graph);
}

auto StreamEngine::executeDistributed(std::shared_ptr<ExecutionGraph> graph)
    -> void {
  // 简化的分布式执行 - 目前使用单线程执行
  executeSingleThreaded(graph);
}

auto StreamEngine::executeHybrid(std::shared_ptr<ExecutionGraph> graph)
    -> void {
  // 简化的混合执行 - 目前使用单线程执行
  executeSingleThreaded(graph);
}

}  // namespace sage_flow