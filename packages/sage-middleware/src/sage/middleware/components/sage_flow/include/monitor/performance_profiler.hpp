#pragma once

#include <atomic>
#include <chrono>
#include <cstdint>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

namespace sage_flow {

/**
 * @brief Profiling granularity levels
 */
enum class ProfilingLevel : uint8_t {
  kOff,       // No profiling
  kBasic,     // Basic timing and counts
  kDetailed,  // Detailed per-operation profiling
  kVerbose    // Verbose profiling with full stack traces
};

/**
 * @brief Profile data point for a single operation
 */
struct ProfileDataPoint {
  std::chrono::system_clock::time_point start_time;
  std::chrono::system_clock::time_point end_time;
  std::chrono::milliseconds duration;
  std::string operation_name;
  std::string component_id;
  std::unordered_map<std::string, std::string> context;
  size_t memory_before_mb{0};
  size_t memory_after_mb{0};
  double cpu_usage_percent{0.0};

  ProfileDataPoint(std::string op, std::string comp)
      : start_time(std::chrono::system_clock::now()),
        operation_name(std::move(op)),
        component_id(std::move(comp)) {}
};

/**
 * @brief Aggregated profiling statistics
 */
struct ProfilingStats {
  uint64_t total_calls{0};
  std::chrono::milliseconds total_time{0};
  std::chrono::milliseconds min_time{std::chrono::milliseconds::max()};
  std::chrono::milliseconds max_time{0};
  std::chrono::milliseconds avg_time{0};
  std::chrono::milliseconds median_time{0};
  std::chrono::milliseconds p95_time{0};
  std::chrono::milliseconds p99_time{0};
  double calls_per_second{0.0};
  size_t avg_memory_delta_mb{0};
  double avg_cpu_usage{0.0};
};

/**
 * @brief Call stack frame for detailed profiling
 */
struct CallStackFrame {
  std::string function_name;
  std::string file_name;
  uint32_t line_number{0};
  std::chrono::milliseconds self_time{0};
  std::chrono::milliseconds total_time{0};
  std::vector<std::unique_ptr<CallStackFrame>> children;

  CallStackFrame(std::string func, std::string file, uint32_t line)
      : function_name(std::move(func)),
        file_name(std::move(file)),
        line_number(line) {}
};

/**
 * @brief Profiling session configuration
 */
struct ProfilingConfig {
  ProfilingLevel level{ProfilingLevel::kBasic};
  std::chrono::milliseconds sampling_interval{10};
  std::chrono::milliseconds session_duration{std::chrono::minutes(5)};
  size_t max_samples{100000};
  size_t max_stack_depth{32};
  bool enable_memory_profiling{true};
  bool enable_cpu_profiling{true};
  bool enable_call_graph{false};
  std::vector<std::string> target_components;
  std::vector<std::string> target_operations;
};

/**
 * @brief RAII profiling scope guard
 */
class ProfilingScope {
public:
  ProfilingScope(class PerformanceProfiler* profiler, std::string operation,
                 std::string component);
  ~ProfilingScope();

  // Prevent copying and moving
  ProfilingScope(const ProfilingScope&) = delete;
  ProfilingScope(ProfilingScope&&) = delete;
  auto operator=(const ProfilingScope&) -> ProfilingScope& = delete;
  auto operator=(ProfilingScope&&) -> ProfilingScope& = delete;

  auto addContext(const std::string& key, const std::string& value) -> void;
  auto recordCheckpoint(const std::string& checkpoint_name) -> void;

private:
  class PerformanceProfiler* profiler_;
  std::unique_ptr<ProfileDataPoint> data_point_;
  bool finished_{false};
};

/**
 * @brief Performance profiler for candyFlow integration
 *
 * Implements detailed performance profiling for SAGE flow pipelines.
 * This is an advanced component of the candyFlow streaming system, providing:
 * - Hierarchical performance profiling with call stacks
 * - Statistical analysis of operation performance
 * - Memory and CPU usage tracking per operation
 * - Bottleneck identification and analysis
 *
 * Based on candyFlow's PerformanceProfiler design with SAGE integration.
 */
class PerformanceProfiler {
public:
  /**
   * @brief Construct a performance profiler
   * @param config Profiling configuration
   */
  explicit PerformanceProfiler(
      const ProfilingConfig& config = ProfilingConfig{});

  /**
   * @brief Destructor - ensures clean shutdown
   */
  ~PerformanceProfiler();

  // Prevent copying
  PerformanceProfiler(const PerformanceProfiler&) = delete;
  auto operator=(const PerformanceProfiler&) -> PerformanceProfiler& = delete;

  // Allow moving
  PerformanceProfiler(PerformanceProfiler&&) = default;
  auto operator=(PerformanceProfiler&&) -> PerformanceProfiler& = default;

  /**
   * @brief Start a profiling session
   */
  auto startSession() -> void;

  /**
   * @brief Stop the profiling session
   */
  auto stopSession() -> void;

  /**
   * @brief Check if profiling is active
   */
  auto isProfilingActive() const -> bool;

  // Profiling interface
  auto startOperation(const std::string& operation_name,
                      const std::string& component_id)
      -> std::unique_ptr<ProfilingScope>;
  auto recordOperation(std::unique_ptr<ProfileDataPoint> data_point) -> void;

  // Manual profiling points
  auto markProfilingPoint(const std::string& name,
                          const std::string& component_id) -> void;
  auto recordCustomMetric(const std::string& metric_name, double value,
                          const std::string& component_id) -> void;

  // Analysis and reporting
  auto getProfilingStats(const std::string& operation_name) -> ProfilingStats;
  auto getComponentStats(const std::string& component_id)
      -> std::unordered_map<std::string, ProfilingStats>;
  auto getTopBottlenecks(size_t top_n = 10)
      -> std::vector<std::pair<std::string, ProfilingStats>>;
  auto getCallGraph(const std::string& operation_name)
      -> std::unique_ptr<CallStackFrame>;

  // Configuration management
  auto updateConfig(const ProfilingConfig& config) -> void;
  auto getConfig() const -> const ProfilingConfig&;
  auto setProfilingLevel(ProfilingLevel level) -> void;
  auto enableComponent(const std::string& component_id, bool enable) -> void;

  // Data management
  auto clearProfilingData() -> void;
  auto clearComponentData(const std::string& component_id) -> void;
  auto getDataSize() const -> size_t;
  auto pruneOldData() -> void;

  // Export and visualization
  auto generateProfilingReport() -> std::string;
  auto exportFlameGraph() -> std::string;
  auto exportCallTree() -> std::string;
  auto exportToJSON() -> std::string;

  // Integration hooks
  auto onOperationStart(const std::string& operation,
                        const std::string& component) -> void;
  auto onOperationEnd(const std::string& operation,
                      const std::string& component,
                      std::chrono::milliseconds duration) -> void;
  auto onMemoryAllocation(const std::string& component, size_t bytes) -> void;
  auto onMemoryDeallocation(const std::string& component, size_t bytes) -> void;

private:
  // Configuration
  ProfilingConfig config_;

  // Session state
  std::atomic<bool> session_active_{false};
  std::chrono::system_clock::time_point session_start_time_;
  std::chrono::system_clock::time_point session_end_time_;

  // Profiling data
  std::vector<std::unique_ptr<ProfileDataPoint>> raw_data_;
  std::unordered_map<std::string, ProfilingStats> operation_stats_;
  std::unordered_map<std::string,
                     std::unordered_map<std::string, ProfilingStats>>
      component_stats_;

  // Call graph data
  std::unordered_map<std::string, std::unique_ptr<CallStackFrame>> call_graphs_;
  std::vector<std::string> current_call_stack_;

  // Thread safety
  mutable std::mutex data_mutex_;
  mutable std::mutex session_mutex_;

  // Performance tracking
  std::unordered_map<std::string, size_t> memory_usage_by_component_;
  std::unordered_map<std::string, std::chrono::system_clock::time_point>
      operation_start_times_;

  // Internal analysis methods
  auto calculateStatistics(const std::vector<std::unique_ptr<ProfileDataPoint>>&
                               data) -> ProfilingStats;
  auto updateOperationStats(const ProfileDataPoint& data_point) -> void;
  auto updateComponentStats(const ProfileDataPoint& data_point) -> void;
  auto buildCallGraph(
      const std::vector<std::unique_ptr<ProfileDataPoint>>& data) -> void;

  // Utility methods
  auto shouldProfile(const std::string& operation,
                     const std::string& component) const -> bool;
  auto getCurrentMemoryUsage() const -> size_t;
  auto getCurrentCPUUsage() const -> double;
  auto calculatePercentiles(std::vector<std::chrono::milliseconds> durations)
      -> std::tuple<std::chrono::milliseconds, std::chrono::milliseconds,
                    std::chrono::milliseconds>;

  // Data management helpers
  auto pruneBySize() -> void;
  auto pruneByTime() -> void;
  auto validateConfiguration(const ProfilingConfig& config) const -> bool;

  // Export helpers
  auto formatDuration(std::chrono::milliseconds duration) -> std::string;
  auto formatMemorySize(size_t bytes) -> std::string;
  auto generateHtmlReport() -> std::string;
  auto generateTextReport() -> std::string;

  friend class ProfilingScope;
};

// Convenience macros for profiling
#define PROFILE_SCOPE(profiler, operation, component) \
  auto _prof_scope = (profiler)->startOperation((operation), (component))

#define PROFILE_FUNCTION(profiler, component) \
  auto _prof_scope = (profiler)->startOperation(__FUNCTION__, (component))

}  // namespace sage_flow