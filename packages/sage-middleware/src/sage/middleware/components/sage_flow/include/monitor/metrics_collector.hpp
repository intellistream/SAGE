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
 * @brief Metric data types
 */
enum class MetricType : uint8_t {
  kCounter,    // Monotonically increasing counter
  kGauge,      // Current value that can go up or down
  kHistogram,  // Distribution of values
  kTimer,      // Timing measurements
  kRate        // Rate of events per time unit
};

/**
 * @brief Time series data point
 */
struct MetricDataPoint {
  std::chrono::system_clock::time_point timestamp;
  double value;
  std::unordered_map<std::string, std::string> tags;

  MetricDataPoint(double val)
      : timestamp(std::chrono::system_clock::now()), value(val) {}

  MetricDataPoint(double val, std::unordered_map<std::string, std::string> t)
      : timestamp(std::chrono::system_clock::now()),
        value(val),
        tags(std::move(t)) {}
};

/**
 * @brief Metric metadata and configuration
 */
struct MetricMetadata {
  std::string name;
  MetricType type;
  std::string description;
  std::string unit;
  std::vector<std::string> tag_keys;
  std::chrono::milliseconds retention_period{std::chrono::hours(24)};
  size_t max_data_points{10000};
  bool enabled{true};

  MetricMetadata(std::string n, MetricType t, std::string desc = "",
                 std::string u = "")
      : name(std::move(n)),
        type(t),
        description(std::move(desc)),
        unit(std::move(u)) {}
};

/**
 * @brief Histogram bucket configuration
 */
struct HistogramBucket {
  double upper_bound;
  std::atomic<uint64_t> count{0};

  explicit HistogramBucket(double bound) : upper_bound(bound) {}
};

/**
 * @brief Histogram metric implementation
 */
class HistogramMetric {
public:
  explicit HistogramMetric(std::vector<double> buckets);

  auto record(double value) -> void;
  auto getPercentile(double percentile) -> double;
  auto getBucketCounts() const -> std::vector<uint64_t>;
  auto getTotalCount() const -> uint64_t;
  auto getSum() const -> double;
  auto reset() -> void;

private:
  std::vector<HistogramBucket> buckets_;
  std::atomic<uint64_t> total_count_{0};
  std::atomic<double> total_sum_{0.0};
  mutable std::mutex mutex_;
};

/**
 * @brief Rate metric for tracking events per time unit
 */
class RateMetric {
public:
  explicit RateMetric(
      std::chrono::milliseconds window_size = std::chrono::minutes(1));

  auto mark(uint64_t count = 1) -> void;
  auto getRate() const -> double;  // events per second
  auto getTotalCount() const -> uint64_t;
  auto reset() -> void;

private:
  std::chrono::milliseconds window_size_;
  std::vector<std::pair<std::chrono::system_clock::time_point, uint64_t>>
      events_;
  std::atomic<uint64_t> total_count_{0};
  mutable std::mutex mutex_;

  auto pruneOldEvents() -> void;
};

/**
 * @brief Metrics collector for candyFlow integration
 *
 * Implements comprehensive metrics collection for SAGE flow pipelines.
 * This is a fundamental component of the candyFlow streaming system, providing:
 * - Multi-type metric collection (counters, gauges, histograms, timers, rates)
 * - Time-series data storage and retrieval
 * - Metric aggregation and statistical analysis
 * - Efficient memory management with retention policies
 *
 * Based on candyFlow's MetricsCollector design with SAGE integration.
 */
class MetricsCollector {
public:
  /**
   * @brief Construct a metrics collector
   */
  explicit MetricsCollector();

  /**
   * @brief Destructor - ensures clean shutdown
   */
  ~MetricsCollector();

  // Prevent copying
  MetricsCollector(const MetricsCollector&) = delete;
  auto operator=(const MetricsCollector&) -> MetricsCollector& = delete;

  // Allow moving
  MetricsCollector(MetricsCollector&&) = default;
  auto operator=(MetricsCollector&&) -> MetricsCollector& = default;

  // Metric registration
  auto registerMetric(const MetricMetadata& metadata) -> void;
  auto unregisterMetric(const std::string& name) -> void;
  auto isMetricRegistered(const std::string& name) const -> bool;
  auto getMetricMetadata(const std::string& name) const
      -> const MetricMetadata*;

  // Counter metrics
  auto incrementCounter(
      const std::string& name, uint64_t delta = 1,
      const std::unordered_map<std::string, std::string>& tags = {}) -> void;
  auto getCounterValue(const std::string& name) const -> uint64_t;

  // Gauge metrics
  auto setGauge(const std::string& name, double value,
                const std::unordered_map<std::string, std::string>& tags = {})
      -> void;
  auto incrementGauge(
      const std::string& name, double delta,
      const std::unordered_map<std::string, std::string>& tags = {}) -> void;
  auto getGaugeValue(const std::string& name) const -> double;

  // Histogram metrics
  auto recordHistogram(
      const std::string& name, double value,
      const std::unordered_map<std::string, std::string>& tags = {}) -> void;
  auto getHistogramPercentile(const std::string& name,
                              double percentile) -> double;
  auto getHistogramStats(const std::string& name)
      -> std::tuple<uint64_t, double, double>;  // count, sum, avg

  // Timer metrics
  auto recordTimer(
      const std::string& name, std::chrono::milliseconds duration,
      const std::unordered_map<std::string, std::string>& tags = {}) -> void;
  auto startTimer(const std::string& name)
      -> std::chrono::system_clock::time_point;
  auto stopTimer(
      const std::string& name, std::chrono::system_clock::time_point start_time,
      const std::unordered_map<std::string, std::string>& tags = {}) -> void;

  // Rate metrics
  auto markRate(const std::string& name, uint64_t count = 1,
                const std::unordered_map<std::string, std::string>& tags = {})
      -> void;
  auto getRateValue(const std::string& name) const -> double;

  // Time series data access
  auto getTimeSeries(const std::string& name,
                     std::chrono::system_clock::time_point start_time,
                     std::chrono::system_clock::time_point end_time)
      -> std::vector<MetricDataPoint>;
  auto getLatestValue(const std::string& name)
      -> std::pair<std::chrono::system_clock::time_point, double>;

  // Aggregation and analysis
  auto getMetricSummary(const std::string& name)
      -> std::unordered_map<std::string, double>;
  auto getSystemMetrics() -> std::unordered_map<std::string, double>;
  auto getAllMetricNames() const -> std::vector<std::string>;

  // Data management
  auto pruneOldData() -> void;
  auto clearMetricData(const std::string& name) -> void;
  auto clearAllData() -> void;
  auto getDataSize() const -> size_t;

  // Export and serialization
  auto exportMetrics(const std::string& format)
      -> std::string;  // JSON, Prometheus, CSV
  auto importMetrics(const std::string& data,
                     const std::string& format) -> bool;

  // Configuration
  auto setRetentionPolicy(const std::string& name,
                          std::chrono::milliseconds retention) -> void;
  auto setMaxDataPoints(const std::string& name, size_t max_points) -> void;
  auto enableMetric(const std::string& name, bool enable) -> void;

private:
  // Metric storage
  std::unordered_map<std::string, MetricMetadata> metric_metadata_;
  std::unordered_map<std::string, std::atomic<uint64_t>> counters_;
  std::unordered_map<std::string, std::atomic<double>> gauges_;
  std::unordered_map<std::string, std::unique_ptr<HistogramMetric>> histograms_;
  std::unordered_map<std::string, std::unique_ptr<RateMetric>> rates_;
  std::unordered_map<std::string, std::vector<MetricDataPoint>> time_series_;

  // Thread safety
  mutable std::mutex metadata_mutex_;
  mutable std::mutex time_series_mutex_;

  // Configuration
  std::chrono::milliseconds default_retention_{std::chrono::hours(24)};
  size_t default_max_points_{10000};

  // Internal helpers
  auto validateMetricName(const std::string& name) const -> bool;
  auto addDataPoint(const std::string& name, double value,
                    const std::unordered_map<std::string, std::string>& tags)
      -> void;
  auto pruneMetricData(const std::string& name) -> void;
  auto calculateStatistics(const std::vector<MetricDataPoint>& data)
      -> std::unordered_map<std::string, double>;

  // Export formats
  auto exportToJSON() -> std::string;
  auto exportToPrometheus() -> std::string;
  auto exportToCSV() -> std::string;

  // System metrics collection
  auto collectSystemMetrics() -> void;
  auto getMemoryUsage() -> double;
  auto getCPUUsage() -> double;
  auto getDiskUsage() -> double;

  // Default histogram buckets
  auto getDefaultHistogramBuckets() -> std::vector<double>;
};

}  // namespace sage_flow