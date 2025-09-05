#pragma once

#include <chrono>
#include <deque>
#include <memory>
#include <string>
#include <vector>

#include "../window_operator.hpp"

namespace sage_flow {

class MultiModalMessage;

/**
 * @brief Sliding window operator for candyFlow integration
 *
 * Implements sliding (overlapping) windows that trigger at regular intervals.
 * This is a core component of the candyFlow streaming system, providing:
 * - Overlapping time windows with configurable slide interval
 * - Event-time and processing-time support
 * - Watermark handling for late data
 * - Efficient memory management for overlapping data
 *
 * Based on candyFlow's SlidingWindowOperator design with SAGE integration.
 */
class SlidingWindowOperator : public WindowOperator {
public:
  /**
   * @brief Construct a sliding window operator
   * @param name Operator name for identification
   * @param window_size Size of each window in milliseconds
   * @param slide_interval Interval between window starts in milliseconds
   * @param allow_late_data Whether to accept late arriving data
   */
  explicit SlidingWindowOperator(std::string name,
                                 std::chrono::milliseconds window_size,
                                 std::chrono::milliseconds slide_interval,
                                 bool allow_late_data = true);

  // Prevent copying
  SlidingWindowOperator(const SlidingWindowOperator&) = delete;
  auto operator=(const SlidingWindowOperator&) -> SlidingWindowOperator& =
                                                      delete;

  // Allow moving
  SlidingWindowOperator(SlidingWindowOperator&&) = default;
  auto operator=(SlidingWindowOperator&&) -> SlidingWindowOperator& = default;

  // WindowOperator interface implementation
  auto processWindow(
      std::vector<std::unique_ptr<MultiModalMessage>> window_messages)
      -> std::vector<std::unique_ptr<MultiModalMessage>> override;

  // SlidingWindow-specific interface
  auto setWatermarkDelay(std::chrono::milliseconds delay) -> void;
  auto setMaxLateness(std::chrono::milliseconds max_lateness) -> void;
  auto enableEventTimeProcessing(bool enable) -> void;
  auto setMaxWindowsInMemory(size_t max_windows) -> void;

  // Performance monitoring
  auto getActiveWindowCount() const -> uint64_t;
  auto getTotalWindowCount() const -> uint64_t;
  auto getLateDataCount() const -> uint64_t;
  auto getDroppedDataCount() const -> uint64_t;
  auto getMemoryUsage() const -> size_t;

protected:
  // Internal window management
  auto shouldCreateNewWindow(uint64_t message_timestamp) -> bool;
  auto getWindowStartsForTimestamp(uint64_t timestamp) -> std::vector<uint64_t>;
  auto isLateData(uint64_t message_timestamp) -> bool;
  auto processLateData(std::unique_ptr<MultiModalMessage> message) -> bool;

private:
  // Window configuration
  std::chrono::milliseconds window_size_;
  std::chrono::milliseconds slide_interval_;
  bool allow_late_data_;
  bool event_time_processing_;
  size_t max_windows_in_memory_;

  // Watermark and late data handling
  std::chrono::milliseconds watermark_delay_;
  std::chrono::milliseconds max_lateness_;
  uint64_t current_watermark_;

  // Window state management for sliding windows
  struct SlidingWindowState {
    uint64_t window_start;
    uint64_t window_end;
    std::vector<std::unique_ptr<MultiModalMessage>> messages;
    bool triggered;
    uint64_t creation_time;

    SlidingWindowState(uint64_t start, uint64_t end)
        : window_start(start),
          window_end(end),
          triggered(false),
          creation_time(start) {}
  };

  std::deque<SlidingWindowState> active_windows_;
  uint64_t last_slide_time_;

  // Performance metrics
  mutable uint64_t total_window_count_;
  mutable uint64_t late_data_count_;
  mutable uint64_t dropped_data_count_;

  // Internal helpers
  auto findOverlappingWindows(uint64_t timestamp)
      -> std::vector<SlidingWindowState*>;
  auto triggerCompletedWindows() -> void;
  auto emitWindow(SlidingWindowState& window) -> void;
  auto cleanupOldWindows() -> void;
  auto createWindowsForTimestamp(uint64_t timestamp) -> void;
  auto getCurrentTimestamp() -> uint64_t;
  auto updateWatermark(uint64_t message_timestamp) -> void;
  auto manageMemoryUsage() -> void;
};

}  // namespace sage_flow