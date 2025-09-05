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

/**
 * @brief System resource types
 */
enum class ResourceType : uint8_t {
  kCPU,
  kMemory,
  kDisk,
  kNetwork,
  kGPU,
  kCustom
};

/**
 * @brief Resource usage snapshot
 */
struct ResourceSnapshot {
  std::chrono::system_clock::time_point timestamp;
  ResourceType type;
  std::string resource_id;
  double usage_percent{0.0};
  uint64_t total_capacity{0};
  uint64_t used_amount{0};
  uint64_t available_amount{0};
  std::unordered_map<std::string, double> additional_metrics;

  ResourceSnapshot(ResourceType t, std::string id)
      : timestamp(std::chrono::system_clock::now()),
        type(t),
        resource_id(std::move(id)) {}
};

/**
 * @brief Process-specific resource usage
 */
struct ProcessResourceUsage {
  uint32_t process_id;
  std::string process_name;
  double cpu_usage_percent{0.0};
  uint64_t memory_usage_bytes{0};
  uint64_t virtual_memory_bytes{0};
  uint64_t disk_read_bytes{0};
  uint64_t disk_write_bytes{0};
  uint64_t network_rx_bytes{0};
  uint64_t network_tx_bytes{0};
  uint32_t thread_count{0};
  uint32_t handle_count{0};
  std::chrono::system_clock::time_point timestamp;

  ProcessResourceUsage(uint32_t pid, std::string name)
      : process_id(pid),
        process_name(std::move(name)),
        timestamp(std::chrono::system_clock::now()) {}
};

/**
 * @brief Resource threshold configuration
 */
struct ResourceThreshold {
  ResourceType type;
  std::string resource_id;
  double warning_threshold{80.0};
  double critical_threshold{95.0};
  std::chrono::milliseconds check_interval{1000};
  bool enabled{true};
  std::string notification_target;

  ResourceThreshold(ResourceType t, std::string id)
      : type(t), resource_id(std::move(id)) {}
};

/**
 * @brief Resource alert information
 */
struct ResourceAlert {
  std::string alert_id;
  ResourceType resource_type;
  std::string resource_id;
  double current_usage{0.0};
  double threshold_breached{0.0};
  std::string severity;  // "warning" or "critical"
  std::chrono::system_clock::time_point alert_time;
  std::chrono::system_clock::time_point resolved_time;
  bool is_resolved{false};
  std::string description;

  ResourceAlert(std::string id, ResourceType type, std::string res_id)
      : alert_id(std::move(id)),
        resource_type(type),
        resource_id(std::move(res_id)),
        alert_time(std::chrono::system_clock::now()) {}
};

/**
 * @brief Resource tracking configuration
 */
struct ResourceTrackingConfig {
  std::chrono::milliseconds sampling_interval{1000};
  std::chrono::milliseconds history_retention{std::chrono::hours(24)};
  size_t max_history_points{86400};  // 24 hours at 1 second intervals
  bool track_system_resources{true};
  bool track_process_resources{true};
  bool track_custom_resources{false};
  bool enable_alerting{true};
  bool enable_predictions{false};
  std::vector<std::string> monitored_processes;
  std::vector<std::string> monitored_devices;
};

/**
 * @brief Resource prediction model result
 */
struct ResourcePrediction {
  ResourceType type;
  std::string resource_id;
  std::chrono::system_clock::time_point prediction_time;
  std::chrono::minutes forecast_horizon{60};
  double predicted_usage{0.0};
  double confidence{0.0};  // 0.0 to 1.0
  std::string prediction_model;
  std::unordered_map<std::string, double> model_parameters;
};

/**
 * @brief Resource tracker for candyFlow integration
 *
 * Implements comprehensive resource monitoring and tracking for SAGE flow
 * pipelines. This is a vital component of the candyFlow streaming system,
 * providing:
 * - Real-time system resource monitoring (CPU, Memory, Disk, Network)
 * - Process-level resource tracking
 * - Resource usage predictions and trend analysis
 * - Automatic alerting on resource threshold breaches
 *
 * Based on candyFlow's ResourceTracker design with SAGE integration.
 */
class ResourceTracker {
public:
  using ResourceAlertCallback = std::function<void(const ResourceAlert&)>;
  using ResourceUpdateCallback = std::function<void(const ResourceSnapshot&)>;

  /**
   * @brief Construct a resource tracker
   * @param config Resource tracking configuration
   */
  explicit ResourceTracker(
      const ResourceTrackingConfig& config = ResourceTrackingConfig{});

  /**
   * @brief Destructor - ensures clean shutdown
   */
  ~ResourceTracker();

  // Prevent copying
  ResourceTracker(const ResourceTracker&) = delete;
  auto operator=(const ResourceTracker&) -> ResourceTracker& = delete;

  // Allow moving
  ResourceTracker(ResourceTracker&&) = default;
  auto operator=(ResourceTracker&&) -> ResourceTracker& = default;

  /**
   * @brief Start resource tracking
   */
  auto startTracking() -> void;

  /**
   * @brief Stop resource tracking
   */
  auto stopTracking() -> void;

  /**
   * @brief Check if tracking is active
   */
  auto isTrackingActive() const -> bool;

  // Resource monitoring interface
  auto getCurrentSystemResources() -> std::vector<ResourceSnapshot>;
  auto getCurrentProcessResources() -> std::vector<ProcessResourceUsage>;
  auto getResourceSnapshot(ResourceType type,
                           const std::string& resource_id) -> ResourceSnapshot;

  // Historical data access
  auto getResourceHistory(ResourceType type, const std::string& resource_id,
                          std::chrono::system_clock::time_point start_time,
                          std::chrono::system_clock::time_point end_time)
      -> std::vector<ResourceSnapshot>;
  auto getProcessHistory(uint32_t process_id,
                         std::chrono::system_clock::time_point start_time,
                         std::chrono::system_clock::time_point end_time)
      -> std::vector<ProcessResourceUsage>;

  // Threshold and alerting
  auto setResourceThreshold(const ResourceThreshold& threshold) -> void;
  auto removeResourceThreshold(ResourceType type,
                               const std::string& resource_id) -> void;
  auto getActiveAlerts() -> std::vector<ResourceAlert>;
  auto getAlertHistory() -> std::vector<ResourceAlert>;
  auto setAlertCallback(ResourceAlertCallback callback) -> void;
  auto setUpdateCallback(ResourceUpdateCallback callback) -> void;

  // Custom resource tracking
  auto registerCustomResource(const std::string& resource_id,
                              const std::string& description) -> void;
  auto updateCustomResource(
      const std::string& resource_id, double usage_percent,
      const std::unordered_map<std::string, double>& metrics = {}) -> void;
  auto unregisterCustomResource(const std::string& resource_id) -> void;

  // Process monitoring
  auto addProcessToMonitor(uint32_t process_id,
                           const std::string& process_name) -> void;
  auto removeProcessFromMonitor(uint32_t process_id) -> void;
  auto getMonitoredProcesses() const -> std::vector<uint32_t>;

  // Analysis and predictions
  auto getResourceTrends(ResourceType type, const std::string& resource_id,
                         std::chrono::minutes time_window)
      -> std::unordered_map<std::string, double>;
  auto predictResourceUsage(ResourceType type, const std::string& resource_id,
                            std::chrono::minutes forecast_horizon)
      -> ResourcePrediction;
  auto detectResourceAnomalies(ResourceType type,
                               const std::string& resource_id)
      -> std::vector<std::chrono::system_clock::time_point>;

  // Configuration management
  auto updateConfig(const ResourceTrackingConfig& config) -> void;
  auto getConfig() const -> const ResourceTrackingConfig&;
  auto enableResourceType(ResourceType type, bool enable) -> void;

  // Data management
  auto clearHistory() -> void;
  auto clearAlerts() -> void;
  auto pruneOldData() -> void;
  auto getDataSize() const -> size_t;

  // Export and reporting
  auto generateResourceReport() -> std::string;
  auto exportResourceData(const std::string& format)
      -> std::string;  // JSON, CSV
  auto getResourceSummary() -> std::unordered_map<std::string, double>;

private:
  // Configuration
  ResourceTrackingConfig config_;

  // Threading and control
  std::atomic<bool> tracking_active_{false};
  std::unique_ptr<std::thread> tracking_thread_;
  std::unique_ptr<std::thread> alert_thread_;

  // Data storage
  std::unordered_map<std::string, std::vector<ResourceSnapshot>>
      resource_history_;
  std::unordered_map<uint32_t, std::vector<ProcessResourceUsage>>
      process_history_;
  std::unordered_map<std::string, ResourceThreshold> thresholds_;
  std::vector<ResourceAlert> alert_history_;
  std::vector<ResourceAlert> active_alerts_;

  // Custom resources
  std::unordered_map<std::string, std::string> custom_resources_;

  // Monitored processes
  std::unordered_map<uint32_t, std::string> monitored_processes_;

  // Callbacks
  ResourceAlertCallback alert_callback_;
  ResourceUpdateCallback update_callback_;

  // Thread safety
  mutable std::mutex data_mutex_;
  mutable std::mutex alerts_mutex_;
  mutable std::mutex config_mutex_;

  // Internal tracking methods
  auto trackingLoop() -> void;
  auto alertingLoop() -> void;
  auto collectSystemResources() -> void;
  auto collectProcessResources() -> void;
  auto checkThresholds() -> void;

  // System resource collection
  auto getCPUUsage() -> ResourceSnapshot;
  auto getMemoryUsage() -> ResourceSnapshot;
  auto getDiskUsage(const std::string& device = "")
      -> std::vector<ResourceSnapshot>;
  auto getNetworkUsage() -> std::vector<ResourceSnapshot>;
  auto getGPUUsage() -> std::vector<ResourceSnapshot>;

  // Process resource collection
  auto getProcessResourceUsage(uint32_t process_id) -> ProcessResourceUsage;
  auto getAllProcesses() -> std::vector<uint32_t>;
  auto isProcessRunning(uint32_t process_id) -> bool;

  // Alert management
  auto triggerAlert(const ResourceAlert& alert) -> void;
  auto resolveAlert(const std::string& alert_id) -> void;
  auto checkAlertConditions() -> void;
  auto generateAlertId(ResourceType type,
                       const std::string& resource_id) -> std::string;

  // Data management
  auto pruneResourceHistory() -> void;
  auto pruneProcessHistory() -> void;
  auto pruneAlertHistory() -> void;
  auto getHistoryKey(ResourceType type,
                     const std::string& resource_id) -> std::string;

  // Analysis helpers
  auto calculateTrend(const std::vector<ResourceSnapshot>& history) -> double;
  auto calculateAverage(const std::vector<ResourceSnapshot>& history) -> double;
  auto detectSpikes(const std::vector<ResourceSnapshot>& history)
      -> std::vector<size_t>;
  auto performLinearRegression(const std::vector<double>& values)
      -> std::pair<double, double>;

  // Platform-specific implementations
  auto getPlatformCPUUsage() -> double;
  auto getPlatformMemoryUsage()
      -> std::pair<uint64_t, uint64_t>;  // used, total
  auto getPlatformDiskUsage(const std::string& path)
      -> std::tuple<uint64_t, uint64_t, uint64_t>;  // used, free, total
  auto getPlatformNetworkStats()
      -> std::unordered_map<
          std::string, std::pair<uint64_t, uint64_t>>;  // interface -> (rx, tx)
  auto getPlatformProcessInfo(uint32_t pid) -> ProcessResourceUsage;

  // Utility methods
  auto formatBytes(uint64_t bytes) -> std::string;
  auto formatPercentage(double percent) -> std::string;
  auto getResourceTypeName(ResourceType type) -> std::string;
  auto getCurrentTime() -> std::chrono::system_clock::time_point;
};

}  // namespace sage_flow