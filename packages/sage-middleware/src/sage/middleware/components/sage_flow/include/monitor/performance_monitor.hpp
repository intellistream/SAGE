#pragma once

#include <atomic>
#include <chrono>
#include <cstdint>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

namespace sage_flow {

class MetricsCollector;
class PerformanceProfiler;
class ResourceTracker;

/**
 * @brief Performance alert severity levels
 */
enum class AlertSeverity : uint8_t { kInfo, kWarning, kError, kCritical };

/**
 * @brief Performance alert information
 */
struct PerformanceAlert {
  std::string alert_id;
  AlertSeverity severity;
  std::string component;
  std::string message;
  std::chrono::system_clock::time_point timestamp;
  std::unordered_map<std::string, std::string> metadata;

  PerformanceAlert(std::string id, AlertSeverity sev, std::string comp,
                   std::string msg)
      : alert_id(std::move(id)),
        severity(sev),
        component(std::move(comp)),
        message(std::move(msg)),
        timestamp(std::chrono::system_clock::now()) {}
};

/**
 * @brief Performance threshold configuration
 */
struct PerformanceThreshold {
  std::string metric_name;
  double warning_threshold;
  double error_threshold;
  double critical_threshold;
  std::chrono::milliseconds check_interval{1000};
  bool enabled{true};

  PerformanceThreshold(std::string name, double warn, double err, double crit)
      : metric_name(std::move(name)),
        warning_threshold(warn),
        error_threshold(err),
        critical_threshold(crit) {}
};

/**
 * @brief Performance monitoring configuration
 */
struct MonitoringConfig {
  std::chrono::milliseconds sampling_interval{100};
  std::chrono::milliseconds alert_check_interval{1000};
  std::chrono::milliseconds report_interval{60000};
  size_t max_alerts_in_memory{1000};
  size_t max_metrics_history{10000};
  bool enable_profiling{true};
  bool enable_resource_tracking{true};
  bool enable_automatic_alerting{true};
  std::string log_level{"INFO"};
};

/**
 * @brief Performance monitor for candyFlow integration
 *
 * Implements comprehensive performance monitoring for SAGE flow pipelines.
 * This is a critical component of the candyFlow streaming system, providing:
 * - Real-time performance metrics collection
 * - Automatic alerting and threshold monitoring
 * - Resource usage tracking and analysis
 * - Performance profiling and bottleneck detection
 *
 * Based on candyFlow's PerformanceMonitor design with SAGE integration.
 */
class PerformanceMonitor {
public:
  using AlertCallback = std::function<void(const PerformanceAlert&)>;
  using MetricCallback = std::function<void(
      const std::string&, double, std::chrono::system_clock::time_point)>;

  /**
   * @brief Construct a performance monitor
   * @param config Monitoring configuration
   */
  explicit PerformanceMonitor(
      const MonitoringConfig& config = MonitoringConfig{});

  /**
   * @brief Destructor - ensures clean shutdown
   */
  ~PerformanceMonitor();

  // Prevent copying
  PerformanceMonitor(const PerformanceMonitor&) = delete;
  auto operator=(const PerformanceMonitor&) -> PerformanceMonitor& = delete;

  // Allow moving
  PerformanceMonitor(PerformanceMonitor&&) = default;
  auto operator=(PerformanceMonitor&&) -> PerformanceMonitor& = default;

  /**
   * @brief Start the performance monitor
   */
  auto start() -> void;

  /**
   * @brief Stop the performance monitor
   */
  auto stop() -> void;

  /**
   * @brief Check if monitor is running
   */
  auto isRunning() const -> bool;

  // Metrics collection interface
  auto recordMetric(const std::string& name, double value) -> void;
  auto recordLatency(const std::string& operation,
                     std::chrono::milliseconds latency) -> void;
  auto recordThroughput(const std::string& operation, uint64_t count) -> void;
  auto recordError(const std::string& operation,
                   const std::string& error_type) -> void;

  // Component monitoring
  auto startOperatorMonitoring(const std::string& operator_id) -> void;
  auto stopOperatorMonitoring(const std::string& operator_id) -> void;
  auto recordOperatorMetrics(
      const std::string& operator_id,
      const std::unordered_map<std::string, double>& metrics) -> void;

  // Threshold and alerting
  auto setThreshold(const PerformanceThreshold& threshold) -> void;
  auto removeThreshold(const std::string& metric_name) -> void;
  auto setAlertCallback(AlertCallback callback) -> void;
  auto setMetricCallback(MetricCallback callback) -> void;

  // Performance analysis
  auto getMetricHistory(const std::string& metric_name,
                        std::chrono::system_clock::time_point start_time,
                        std::chrono::system_clock::time_point end_time)
      -> std::vector<std::pair<std::chrono::system_clock::time_point, double>>;
  auto getPerformanceSummary() -> std::unordered_map<std::string, double>;
  auto getActiveAlerts() -> std::vector<PerformanceAlert>;
  auto getBottlenecks() -> std::vector<std::string>;

  // Configuration management
  auto updateConfig(const MonitoringConfig& config) -> void;
  auto getConfig() const -> const MonitoringConfig&;
  auto enableComponent(const std::string& component, bool enable) -> void;

  // Report generation
  auto generatePerformanceReport() -> std::string;
  auto exportMetrics(const std::string& format)
      -> std::string;  // JSON, CSV, etc.
  auto clearHistory() -> void;
  auto clearAlerts() -> void;

  // Integration with other monitoring components
  auto setMetricsCollector(std::shared_ptr<MetricsCollector> collector) -> void;
  auto setPerformanceProfiler(std::shared_ptr<PerformanceProfiler> profiler)
      -> void;
  auto setResourceTracker(std::shared_ptr<ResourceTracker> tracker) -> void;

private:
  // Configuration
  MonitoringConfig config_;

  // Component integration
  std::shared_ptr<MetricsCollector> metrics_collector_;
  std::shared_ptr<PerformanceProfiler> profiler_;
  std::shared_ptr<ResourceTracker> resource_tracker_;

  // Threading and control
  std::atomic<bool> running_{false};
  std::unique_ptr<std::thread> monitoring_thread_;
  std::unique_ptr<std::thread> alert_thread_;

  // Callbacks
  AlertCallback alert_callback_;
  MetricCallback metric_callback_;

  // Thresholds and alerts
  std::unordered_map<std::string, PerformanceThreshold> thresholds_;
  std::vector<PerformanceAlert> active_alerts_;
  mutable std::mutex alerts_mutex_;

  // Monitored components
  std::unordered_map<std::string, bool> monitored_operators_;
  mutable std::mutex operators_mutex_;

  // Performance tracking
  std::chrono::system_clock::time_point start_time_;
  std::atomic<uint64_t> total_operations_{0};
  std::atomic<uint64_t> total_errors_{0};

  // Internal monitoring methods
  auto monitoringLoop() -> void;
  auto alertingLoop() -> void;
  auto checkThresholds() -> void;
  auto processMetrics() -> void;
  auto detectBottlenecks() -> void;

  // Alert management
  auto triggerAlert(const PerformanceAlert& alert) -> void;
  auto resolveAlert(const std::string& alert_id) -> void;
  auto pruneOldAlerts() -> void;

  // Utility methods
  auto getCurrentMetricValue(const std::string& metric_name) -> double;
  auto calculateAverageLatency(const std::string& operation) -> double;
  auto calculateThroughput(const std::string& operation) -> double;
  auto calculateErrorRate(const std::string& operation) -> double;

  // Default thresholds
  auto initializeDefaultThresholds() -> void;
  auto createSystemMetricsThresholds() -> void;
  auto createOperatorMetricsThresholds() -> void;
};

}  // namespace sage_flow