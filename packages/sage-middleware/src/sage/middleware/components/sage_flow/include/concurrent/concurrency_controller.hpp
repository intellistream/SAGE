#pragma once

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

namespace sage_flow {

class LockFreeQueue;
class WorkStealingExecutor;

/**
 * @brief Concurrency strategy enumeration
 */
enum class ConcurrencyStrategy : uint8_t {
  kSingleThreaded,  // No concurrency
  kThreadPool,      // Traditional thread pool
  kWorkStealing,    // Work-stealing scheduler
  kActorModel,      // Actor-based concurrency
  kPipelined,       // Pipeline parallelism
  kDataParallel     // Data parallelism
};

/**
 * @brief Task priority levels
 */
enum class TaskPriority : uint8_t {
  kLow = 0,
  kNormal = 1,
  kHigh = 2,
  kCritical = 3
};

/**
 * @brief Task execution context
 */
struct TaskContext {
  std::string task_id;
  TaskPriority priority{TaskPriority::kNormal};
  std::chrono::system_clock::time_point submit_time;
  std::chrono::system_clock::time_point start_time;
  std::chrono::milliseconds deadline{0};
  std::unordered_map<std::string, std::string> metadata;
  std::string component_id;

  TaskContext(std::string id, std::string comp_id)
      : task_id(std::move(id)),
        submit_time(std::chrono::system_clock::now()),
        component_id(std::move(comp_id)) {}
};

/**
 * @brief Task execution statistics
 */
struct TaskStats {
  uint64_t total_submitted{0};
  uint64_t total_completed{0};
  uint64_t total_failed{0};
  uint64_t total_cancelled{0};
  std::chrono::milliseconds total_execution_time{0};
  std::chrono::milliseconds avg_execution_time{0};
  std::chrono::milliseconds max_execution_time{0};
  std::chrono::milliseconds min_execution_time{
      std::chrono::milliseconds::max()};
  uint64_t queue_size{0};
  uint64_t active_workers{0};
  double throughput_per_second{0.0};
};

/**
 * @brief Deadlock detection result
 */
struct DeadlockInfo {
  bool has_deadlock{false};
  std::vector<std::string> involved_threads;
  std::vector<std::string> involved_resources;
  std::chrono::system_clock::time_point detection_time;
  std::string description;
};

/**
 * @brief Concurrency configuration
 */
struct ConcurrencyConfig {
  ConcurrencyStrategy strategy{ConcurrencyStrategy::kWorkStealing};
  size_t thread_pool_size{std::thread::hardware_concurrency()};
  size_t max_queue_size{10000};
  std::chrono::milliseconds task_timeout{std::chrono::seconds(30)};
  std::chrono::milliseconds deadlock_check_interval{std::chrono::seconds(5)};
  bool enable_work_stealing{true};
  bool enable_deadlock_detection{true};
  bool enable_load_balancing{true};
  bool enable_priority_scheduling{true};
  double load_balance_threshold{0.8};
  size_t work_stealing_attempts{3};
};

/**
 * @brief Concurrency controller for candyFlow integration
 *
 * Implements advanced concurrency control for SAGE flow pipelines.
 * This is a crucial component of the candyFlow streaming system, providing:
 * - Multiple concurrency strategies (thread pools, work stealing, actor model)
 * - Advanced task scheduling with priorities and deadlines
 * - Deadlock detection and prevention
 * - Load balancing and work stealing
 * - Thread-safe execution coordination
 *
 * Based on candyFlow's ConcurrencyController design with SAGE integration.
 */
class ConcurrencyController {
public:
  using Task = std::function<void(const TaskContext&)>;
  using TaskCallback = std::function<void(const TaskContext&, bool success)>;
  using DeadlockCallback = std::function<void(const DeadlockInfo&)>;

  /**
   * @brief Construct a concurrency controller
   * @param config Concurrency configuration
   */
  explicit ConcurrencyController(
      const ConcurrencyConfig& config = ConcurrencyConfig{});

  /**
   * @brief Destructor - ensures clean shutdown
   */
  ~ConcurrencyController();

  // Prevent copying
  ConcurrencyController(const ConcurrencyController&) = delete;
  auto operator=(const ConcurrencyController&) -> ConcurrencyController& =
                                                      delete;

  // Allow moving
  ConcurrencyController(ConcurrencyController&&) = default;
  auto operator=(ConcurrencyController&&) -> ConcurrencyController& = default;

  /**
   * @brief Start the concurrency controller
   */
  auto start() -> void;

  /**
   * @brief Stop the concurrency controller
   */
  auto stop() -> void;

  /**
   * @brief Check if controller is running
   */
  auto isRunning() const -> bool;

  // Task execution interface
  auto submitTask(Task task, const TaskContext& context) -> std::string;
  auto submitTask(Task task, const std::string& task_id,
                  const std::string& component_id,
                  TaskPriority priority = TaskPriority::kNormal) -> std::string;
  auto submitTaskWithCallback(Task task, TaskCallback callback,
                              const TaskContext& context) -> std::string;
  auto submitTaskWithDeadline(Task task, const TaskContext& context,
                              std::chrono::milliseconds deadline)
      -> std::string;

  // Task management
  auto cancelTask(const std::string& task_id) -> bool;
  auto getTaskStatus(const std::string& task_id)
      -> std::string;  // "pending", "running", "completed", "failed",
                       // "cancelled"
  auto waitForTask(const std::string& task_id,
                   std::chrono::milliseconds timeout =
                       std::chrono::milliseconds::max()) -> bool;
  auto waitForAllTasks(std::chrono::milliseconds timeout =
                           std::chrono::milliseconds::max()) -> bool;

  // Resource management
  auto acquireResource(const std::string& resource_id,
                       const std::string& thread_id,
                       std::chrono::milliseconds timeout =
                           std::chrono::milliseconds::max()) -> bool;
  auto releaseResource(const std::string& resource_id,
                       const std::string& thread_id) -> void;
  auto tryAcquireResource(const std::string& resource_id,
                          const std::string& thread_id) -> bool;

  // Scheduling control
  auto pauseScheduling() -> void;
  auto resumeScheduling() -> void;
  auto isSchedulingPaused() const -> bool;
  auto setThreadPoolSize(size_t size) -> void;
  auto getThreadPoolSize() const -> size_t;

  // Monitoring and statistics
  auto getTaskStats() -> TaskStats;
  auto getComponentStats(const std::string& component_id) -> TaskStats;
  auto getActiveTaskCount() -> uint64_t;
  auto getPendingTaskCount() -> uint64_t;
  auto getWorkerUtilization() -> std::vector<double>;

  // Deadlock detection
  auto checkForDeadlocks() -> DeadlockInfo;
  auto setDeadlockCallback(DeadlockCallback callback) -> void;
  auto enableDeadlockDetection(bool enable) -> void;

  // Configuration management
  auto updateConfig(const ConcurrencyConfig& config) -> void;
  auto getConfig() const -> const ConcurrencyConfig&;
  auto setConcurrencyStrategy(ConcurrencyStrategy strategy) -> void;

  // Advanced features
  auto createTaskGroup(const std::string& group_id) -> void;
  auto addTaskToGroup(const std::string& task_id,
                      const std::string& group_id) -> void;
  auto waitForTaskGroup(const std::string& group_id,
                        std::chrono::milliseconds timeout =
                            std::chrono::milliseconds::max()) -> bool;
  auto cancelTaskGroup(const std::string& group_id) -> void;

  // Performance tuning
  auto enableWorkStealing(bool enable) -> void;
  auto setLoadBalanceThreshold(double threshold) -> void;
  auto forceLoadBalance() -> void;
  auto getLoadBalance() -> std::vector<double>;  // load per thread

private:
  // Configuration
  ConcurrencyConfig config_;

  // Core state
  std::atomic<bool> running_{false};
  std::atomic<bool> scheduling_paused_{false};

  // Execution components
  std::unique_ptr<WorkStealingExecutor> work_stealing_executor_;
  std::vector<std::unique_ptr<std::thread>> worker_threads_;
  std::unique_ptr<LockFreeQueue> task_queue_;

  // Task management
  std::unordered_map<std::string, std::unique_ptr<TaskContext>> active_tasks_;
  std::unordered_map<std::string, std::string> task_status_;
  std::unordered_map<std::string, TaskCallback> task_callbacks_;
  std::unordered_map<std::string, std::vector<std::string>> task_groups_;

  // Resource management
  std::unordered_map<std::string, std::string>
      resource_owners_;  // resource_id -> thread_id
  std::unordered_map<std::string, std::vector<std::string>>
      resource_waiters_;  // resource_id -> [thread_ids]

  // Statistics
  mutable TaskStats global_stats_;
  std::unordered_map<std::string, TaskStats> component_stats_;

  // Callbacks
  DeadlockCallback deadlock_callback_;

  // Thread safety
  mutable std::mutex tasks_mutex_;
  mutable std::mutex resources_mutex_;
  mutable std::mutex stats_mutex_;
  mutable std::mutex config_mutex_;
  std::condition_variable task_completion_cv_;

  // Internal execution methods
  auto workerLoop(size_t worker_id) -> void;
  auto executeTask(Task task, std::unique_ptr<TaskContext> context) -> void;
  auto scheduleTask(Task task, std::unique_ptr<TaskContext> context) -> void;
  auto selectWorkerThread() -> size_t;

  // Deadlock detection
  auto deadlockDetectionLoop() -> void;
  auto buildResourceGraph()
      -> std::unordered_map<std::string, std::vector<std::string>>;
  auto detectCycle(
      const std::unordered_map<std::string, std::vector<std::string>>& graph)
      -> std::vector<std::string>;
  auto resolveDeadlock(const DeadlockInfo& deadlock_info) -> void;

  // Load balancing
  auto performLoadBalancing() -> void;
  auto calculateWorkerLoad(size_t worker_id) -> double;
  auto redistributeTasks() -> void;

  // Statistics tracking
  auto updateTaskStats(const TaskContext& context, bool success,
                       std::chrono::milliseconds execution_time) -> void;
  auto updateComponentStats(const std::string& component_id, bool success,
                            std::chrono::milliseconds execution_time) -> void;

  // Utility methods
  auto generateTaskId() -> std::string;
  auto getCurrentThreadId() -> std::string;
  auto isValidTaskId(const std::string& task_id) -> bool;
  auto cleanupCompletedTasks() -> void;
  auto notifyTaskCompletion(const std::string& task_id) -> void;

  // Strategy implementations
  auto initializeThreadPool() -> void;
  auto initializeWorkStealing() -> void;
  auto initializeActorModel() -> void;
  auto shutdownExecutors() -> void;
};

}  // namespace sage_flow