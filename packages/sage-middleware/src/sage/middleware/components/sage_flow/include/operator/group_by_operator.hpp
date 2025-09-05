#pragma once

#include <chrono>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

#include "base_operator.hpp"

namespace sage_flow {

class MultiModalMessage;
class Response;

/**
 * @brief Group-by key extraction result
 */
struct GroupKey {
  std::string string_key;
  std::vector<std::string> composite_keys;
  bool is_composite{false};

  explicit GroupKey(std::string key) : string_key(std::move(key)) {}
  explicit GroupKey(std::vector<std::string> keys)
      : composite_keys(std::move(keys)), is_composite(true) {}

  auto toString() const -> std::string {
    if (is_composite) {
      std::string result;
      for (size_t i = 0; i < composite_keys.size(); ++i) {
        if (i > 0) result += "|";
        result += composite_keys[i];
      }
      return result;
    }
    return string_key;
  }

  auto operator==(const GroupKey& other) const -> bool {
    return toString() == other.toString();
  }
};

/**
 * @brief Group aggregation statistics
 */
struct GroupStats {
  size_t message_count{0};
  std::chrono::system_clock::time_point first_message_time;
  std::chrono::system_clock::time_point last_message_time;
  size_t total_data_size{0};
  std::unordered_map<std::string, double> custom_metrics;
};

/**
 * @brief Group-by configuration
 */
struct GroupByConfig {
  std::chrono::milliseconds group_timeout{std::chrono::minutes(5)};
  size_t max_groups_in_memory{10000};
  size_t max_messages_per_group{1000};
  bool enable_group_statistics{true};
  bool enable_late_data_handling{true};
  bool enable_incremental_aggregation{false};
  std::string group_timeout_action{"emit"};  // "emit", "discard", "extend"
};

/**
 * @brief Group-by operator for candyFlow integration
 *
 * Implements advanced group-by functionality for SAGE flow pipelines.
 * This is a sophisticated component of the candyFlow streaming system,
 * providing:
 * - Flexible key extraction from multi-modal messages
 * - Composite key support for complex grouping
 * - Memory-efficient group management with timeouts
 * - Incremental aggregation capabilities
 * - Statistical analysis per group
 *
 * Based on candyFlow's GroupByOperator design with SAGE integration.
 */
class GroupByOperator : public BaseOperator {
public:
  using KeyExtractor = std::function<GroupKey(const MultiModalMessage&)>;
  using GroupProcessor = std::function<std::unique_ptr<MultiModalMessage>(
      const GroupKey&, std::vector<std::unique_ptr<MultiModalMessage>>)>;
  using GroupTimeoutHandler = std::function<void(
      const GroupKey&, std::vector<std::unique_ptr<MultiModalMessage>>)>;

  /**
   * @brief Construct a group-by operator
   * @param name Operator name for identification
   * @param key_extractor Function to extract grouping keys from messages
   * @param config Group-by configuration
   */
  explicit GroupByOperator(std::string name, KeyExtractor key_extractor,
                           const GroupByConfig& config = GroupByConfig{});

  // Prevent copying
  GroupByOperator(const GroupByOperator&) = delete;
  auto operator=(const GroupByOperator&) -> GroupByOperator& = delete;

  // Allow moving
  GroupByOperator(GroupByOperator&&) = default;
  auto operator=(GroupByOperator&&) -> GroupByOperator& = default;

  // Operator interface implementation
  auto process(Response& input_record, int slot) -> bool override;

  // Group-by specific interface
  auto setKeyExtractor(KeyExtractor extractor) -> void;
  auto setGroupProcessor(GroupProcessor processor) -> void;
  auto setTimeoutHandler(GroupTimeoutHandler handler) -> void;
  auto setConfig(const GroupByConfig& config) -> void;

  // Group management
  auto flushGroup(const GroupKey& key) -> void;
  auto flushAllGroups() -> void;
  auto getGroupCount() const -> size_t;
  auto getGroupStats(const GroupKey& key) const -> GroupStats;
  auto getAllGroupStats() const -> std::unordered_map<std::string, GroupStats>;

  // Advanced grouping features
  auto enableIncrementalAggregation(bool enable) -> void;
  auto setGroupSizeLimit(size_t max_size) -> void;
  auto setMemoryLimit(size_t max_memory_mb) -> void;
  auto enableGroupStatistics(bool enable) -> void;

  // Monitoring and debugging
  auto getActiveGroups() const -> std::vector<std::string>;
  auto getMemoryUsage() const -> size_t;
  auto getTotalMessagesProcessed() const -> uint64_t;
  auto getGroupTimeouts() const -> uint64_t;

private:
  // Group data structure
  struct Group {
    GroupKey key;
    std::vector<std::unique_ptr<MultiModalMessage>> messages;
    GroupStats stats;
    std::chrono::system_clock::time_point creation_time;
    std::chrono::system_clock::time_point last_access_time;
    bool is_incremental{false};
    std::unique_ptr<MultiModalMessage> incremental_result;

    explicit Group(GroupKey k)
        : key(std::move(k)),
          creation_time(std::chrono::system_clock::now()),
          last_access_time(std::chrono::system_clock::now()) {
      stats.first_message_time = creation_time;
    }
  };

  // Configuration and state
  GroupByConfig config_;
  KeyExtractor key_extractor_;
  GroupProcessor group_processor_;
  GroupTimeoutHandler timeout_handler_;

  // Group storage
  std::unordered_map<std::string, std::unique_ptr<Group>> active_groups_;
  mutable std::mutex groups_mutex_;

  // Performance tracking
  mutable uint64_t total_messages_processed_{0};
  mutable uint64_t total_groups_created_{0};
  mutable uint64_t total_group_timeouts_{0};
  mutable size_t current_memory_usage_{0};

  // Timeout management
  std::chrono::system_clock::time_point last_timeout_check_;

  // Internal methods
  auto addMessageToGroup(const GroupKey& key,
                         std::unique_ptr<MultiModalMessage> message) -> void;
  auto createNewGroup(const GroupKey& key) -> Group*;
  auto processGroup(Group& group) -> void;
  auto checkGroupTimeouts() -> void;
  auto handleGroupTimeout(Group& group) -> void;
  auto evictOldestGroups() -> void;
  auto updateGroupStats(Group& group, const MultiModalMessage& message) -> void;
  auto estimateMessageSize(const MultiModalMessage& message) -> size_t;
  auto shouldEvictGroup(const Group& group) const -> bool;
  auto getDefaultGroupProcessor() -> GroupProcessor;
  auto getDefaultTimeoutHandler() -> GroupTimeoutHandler;

  // Memory management
  auto calculateTotalMemoryUsage() -> size_t;
  auto freeGroupMemory(Group& group) -> void;
  auto enforceMemoryLimits() -> void;

  // Incremental aggregation support
  auto processIncrementalMessage(
      Group& group, std::unique_ptr<MultiModalMessage> message) -> void;
  auto mergeIncrementalResult(
      Group& group, std::unique_ptr<MultiModalMessage> new_result) -> void;

  // Statistics and monitoring
  auto updatePerformanceMetrics() -> void;
  auto logGroupActivity(const std::string& action, const GroupKey& key) -> void;

  // Key extraction helpers
  auto extractStringKey(const MultiModalMessage& message,
                        const std::string& field_name) -> std::string;
  auto extractCompositeKey(const MultiModalMessage& message,
                           const std::vector<std::string>& field_names)
      -> std::vector<std::string>;
  auto createDefaultKeyExtractor() -> KeyExtractor;
};

/**
 * @brief Factory class for creating common group-by operators
 */
class GroupByOperatorFactory {
public:
  /**
   * @brief Create a group-by operator for text content grouping
   */
  static auto createTextGroupBy(const std::string& name,
                                const std::string& field_name)
      -> std::unique_ptr<GroupByOperator>;

  /**
   * @brief Create a group-by operator for source-based grouping
   */
  static auto createSourceGroupBy(const std::string& name)
      -> std::unique_ptr<GroupByOperator>;

  /**
   * @brief Create a group-by operator for timestamp-based grouping
   */
  static auto createTimeBasedGroupBy(const std::string& name,
                                     std::chrono::milliseconds time_window)
      -> std::unique_ptr<GroupByOperator>;

  /**
   * @brief Create a group-by operator for content type grouping
   */
  static auto createContentTypeGroupBy(const std::string& name)
      -> std::unique_ptr<GroupByOperator>;

  /**
   * @brief Create a group-by operator with composite keys
   */
  static auto createCompositeGroupBy(
      const std::string& name, const std::vector<std::string>& field_names)
      -> std::unique_ptr<GroupByOperator>;

private:
  static auto createTimeWindowKey(std::chrono::milliseconds window_size)
      -> GroupByOperator::KeyExtractor;
  static auto createFieldBasedKey(const std::string& field_name)
      -> GroupByOperator::KeyExtractor;
  static auto createCompositeKey(const std::vector<std::string>& field_names)
      -> GroupByOperator::KeyExtractor;
};

}  // namespace sage_flow