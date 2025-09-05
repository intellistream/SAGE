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
 * @brief Tumbling window operator for candyFlow integration
 *
 * Implements tumbling (non-overlapping) windows that trigger at fixed
 * intervals. This is a key component of the candyFlow streaming system,
 * providing:
 * - Fixed-size time windows
 * - Event-time and processing-time support
 * - Watermark handling for late data
 * - Memory-efficient window management
 *
 * Based on candyFlow's TumblingWindowOperator design with SAGE integration.
 */
class TumblingWindowOperator : public WindowOperator {
public:
  /**
   * @brief Construct a tumbling window operator
   * @param name Operator name for identification
   * @param window_size Size of each window in milliseconds
   * @param allow_late_data Whether to accept late arriving data
   */
  explicit TumblingWindowOperator(std::string name,
                                  std::chrono::milliseconds window_size,
                                  bool allow_late_data = true);

  // Prevent copying
  TumblingWindowOperator(const TumblingWindowOperator&) = delete;
  auto operator=(const TumblingWindowOperator&) -> TumblingWindowOperator& =
                                                       delete;

  // Allow moving
  TumblingWindowOperator(TumblingWindowOperator&&) = default;
  auto operator=(TumblingWindowOperator&&) -> TumblingWindowOperator& = default;

  // WindowOperator interface implementation
  auto processWindow(
      std::vector<std::unique_ptr<MultiModalMessage>> window_messages)
      -> std::vector<std::unique_ptr<MultiModalMessage>> override;

  // TumblingWindow-specific interface
  auto setWatermarkDelay(std::chrono::milliseconds delay) -> void;
  auto setMaxLateness(std::chrono::milliseconds max_lateness) -> void;
  auto enableEventTimeProcessing(bool enable) -> void;

  // Performance monitoring
  auto getWindowCount() const -> uint64_t;
  auto getLateDataCount() const -> uint64_t;
  auto getDroppedDataCount() const -> uint64_t;

protected:
  // Internal window management
  auto shouldCreateNewWindow(uint64_t message_timestamp) -> bool;
  auto getWindowIdForTimestamp(uint64_t timestamp) -> uint64_t;
  auto isLateData(uint64_t message_timestamp) -> bool;
  auto processLateData(std::unique_ptr<MultiModalMessage> message) -> bool;

private:
  // Window configuration
  std::chrono::milliseconds window_size_;
  bool allow_late_data_;
  bool event_time_processing_;

  // Watermark and late data handling
  std::chrono::milliseconds watermark_delay_;
  std::chrono::milliseconds max_lateness_;
  uint64_t current_watermark_;

  // Window state management
  struct WindowState {
    uint64_t window_id;
    uint64_t start_time;
    uint64_t end_time;
    std::vector<std::unique_ptr<MultiModalMessage>> messages;
    bool triggered;

    WindowState(uint64_t id, uint64_t start, uint64_t end)
        : window_id(id), start_time(start), end_time(end), triggered(false) {}
  };

  std::deque<WindowState> active_windows_;
  uint64_t next_window_id_;

  // Performance metrics
  mutable uint64_t window_count_;
  mutable uint64_t late_data_count_;
  mutable uint64_t dropped_data_count_;

  // Internal helpers
  auto findWindowForTimestamp(uint64_t timestamp) -> WindowState*;
  auto triggerCompletedWindows() -> void;
  auto emitWindow(WindowState& window) -> void;
  auto cleanupOldWindows() -> void;
  auto getCurrentTimestamp() -> uint64_t;
  auto updateWatermark(uint64_t message_timestamp) -> void;
};

}  // namespace sage_flow