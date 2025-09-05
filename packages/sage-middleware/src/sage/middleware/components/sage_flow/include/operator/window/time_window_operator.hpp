#pragma once

#include <chrono>
#include <deque>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "../window_operator.hpp"

namespace sage_flow {

class MultiModalMessage;

/**
 * @brief Time window operator for candyFlow integration
 *
 * Implements time-based windowing with flexible time handling.
 * This is a versatile component of the candyFlow streaming system, providing:
 * - Flexible time-based windowing strategies
 * - Event-time and processing-time support
 * - Custom time extraction from messages
 * - Watermark handling for late data
 *
 * Based on candyFlow's TimeWindowOperator design with SAGE integration.
 */
class TimeWindowOperator : public WindowOperator {
public:
  enum class TimeMode : std::uint8_t {
    kEventTime,       // Use event timestamps from messages
    kProcessingTime,  // Use processing time when message arrives
    kIngestionTime    // Use time when message enters the system
  };

  /**
   * @brief Construct a time window operator
   * @param name Operator name for identification
   * @param window_size Size of each window in milliseconds
   * @param time_mode Time mode for windowing
   * @param allow_late_data Whether to accept late arriving data
   */
  explicit TimeWindowOperator(std::string name,
                              std::chrono::milliseconds window_size,
                              TimeMode time_mode = TimeMode::kEventTime,
                              bool allow_late_data = true);

  // Prevent copying
  TimeWindowOperator(const TimeWindowOperator&) = delete;
  auto operator=(const TimeWindowOperator&) -> TimeWindowOperator& = delete;

  // Allow moving
  TimeWindowOperator(TimeWindowOperator&&) = default;
  auto operator=(TimeWindowOperator&&) -> TimeWindowOperator& = default;

  // WindowOperator interface implementation
  auto processWindow(
      std::vector<std::unique_ptr<MultiModalMessage>> window_messages)
      -> std::vector<std::unique_ptr<MultiModalMessage>> override;

  // TimeWindow-specific interface
  auto setTimeMode(TimeMode mode) -> void;
  auto setWatermarkDelay(std::chrono::milliseconds delay) -> void;
  auto setMaxLateness(std::chrono::milliseconds max_lateness) -> void;
  auto setTimeExtractor(
      std::function<uint64_t(const MultiModalMessage&)> extractor) -> void;
  auto setWindowAlignment(std::chrono::milliseconds alignment) -> void;

  // Performance monitoring
  auto getActiveWindowCount() const -> uint64_t;
  auto getTotalWindowCount() const -> uint64_t;
  auto getLateDataCount() const -> uint64_t;
  auto getDroppedDataCount() const -> uint64_t;
  auto getWatermarkLag() const -> std::chrono::milliseconds;

protected:
  // Internal time management
  auto extractTimestamp(const MultiModalMessage& message) -> uint64_t;
  auto alignTimestamp(uint64_t timestamp) -> uint64_t;
  auto getWindowIdForTimestamp(uint64_t timestamp) -> uint64_t;
  auto isLateData(uint64_t message_timestamp) -> bool;
  auto processLateData(std::unique_ptr<MultiModalMessage> message) -> bool;

private:
  // Time configuration
  TimeMode time_mode_;
  std::chrono::milliseconds window_size_;
  std::chrono::milliseconds window_alignment_;
  bool allow_late_data_;
  std::function<uint64_t(const MultiModalMessage&)> time_extractor_;

  // Watermark and late data handling
  std::chrono::milliseconds watermark_delay_;
  std::chrono::milliseconds max_lateness_;
  uint64_t current_watermark_;
  uint64_t last_event_time_;

  // Window state management
  struct TimeWindowState {
    uint64_t window_id;
    uint64_t window_start;
    uint64_t window_end;
    std::vector<std::unique_ptr<MultiModalMessage>> messages;
    bool triggered;
    uint64_t creation_time;

    TimeWindowState(uint64_t id, uint64_t start, uint64_t end)
        : window_id(id),
          window_start(start),
          window_end(end),
          triggered(false),
          creation_time(start) {}
  };

  std::deque<TimeWindowState> active_windows_;
  uint64_t next_window_id_;

  // Performance metrics
  mutable uint64_t total_window_count_;
  mutable uint64_t late_data_count_;
  mutable uint64_t dropped_data_count_;

  // Internal helpers
  auto findWindowForTimestamp(uint64_t timestamp) -> TimeWindowState*;
  auto createWindowForTimestamp(uint64_t timestamp) -> TimeWindowState*;
  auto triggerCompletedWindows() -> void;
  auto emitWindow(TimeWindowState& window) -> void;
  auto cleanupOldWindows() -> void;
  auto getCurrentTimestamp() -> uint64_t;
  auto updateWatermark(uint64_t message_timestamp) -> void;
  auto defaultTimeExtractor(const MultiModalMessage& message) -> uint64_t;
};

}  // namespace sage_flow