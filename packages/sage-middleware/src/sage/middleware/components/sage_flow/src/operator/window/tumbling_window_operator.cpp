#include "operator/window/tumbling_window_operator.hpp"

#include <algorithm>
#include <chrono>
#include <string>
#include <utility>

#include "message/multimodal_message.hpp"
#include "operator/response.hpp"

namespace sage_flow {

TumblingWindowOperator::TumblingWindowOperator(
    std::string name, std::chrono::milliseconds window_size,
    bool allow_late_data)
    : WindowOperator(std::move(name), WindowType::kTumbling),
      window_size_(window_size),
      allow_late_data_(allow_late_data),
      event_time_processing_(true),
      watermark_delay_(std::chrono::milliseconds(1000)),
      max_lateness_(std::chrono::milliseconds(5000)),
      current_watermark_(0),
      next_window_id_(0),
      window_count_(0),
      late_data_count_(0),
      dropped_data_count_(0) {
  setWindowSize(window_size);
}

auto TumblingWindowOperator::processWindow(
    std::vector<std::unique_ptr<MultiModalMessage>> window_messages)
    -> std::vector<std::unique_ptr<MultiModalMessage>> {
  std::vector<std::unique_ptr<MultiModalMessage>> results;

  // For tumbling windows, we typically aggregate or transform the messages
  // For this base implementation, we'll create a single output message
  // containing information about the window
  if (!window_messages.empty()) {
    auto first_message = std::move(window_messages[0]);

    // Create metadata about the window
    first_message->setMetadata("window_type", "tumbling");
    first_message->setMetadata("window_size_ms",
                               std::to_string(window_size_.count()));
    first_message->setMetadata("window_message_count",
                               std::to_string(window_messages.size()));
    first_message->setMetadata("window_id", std::to_string(window_count_));

    // Add processing trace
    first_message->addProcessingStep("tumbling_window_" +
                                     std::to_string(window_count_));

    results.push_back(std::move(first_message));
    ++window_count_;
  }

  return results;
}

auto TumblingWindowOperator::setWatermarkDelay(std::chrono::milliseconds delay)
    -> void {
  watermark_delay_ = delay;
}

auto TumblingWindowOperator::setMaxLateness(
    std::chrono::milliseconds max_lateness) -> void {
  max_lateness_ = max_lateness;
}

auto TumblingWindowOperator::enableEventTimeProcessing(bool enable) -> void {
  event_time_processing_ = enable;
}

auto TumblingWindowOperator::getWindowCount() const -> uint64_t {
  return window_count_;
}

auto TumblingWindowOperator::getLateDataCount() const -> uint64_t {
  return late_data_count_;
}

auto TumblingWindowOperator::getDroppedDataCount() const -> uint64_t {
  return dropped_data_count_;
}

auto TumblingWindowOperator::shouldCreateNewWindow(uint64_t message_timestamp)
    -> bool {
  if (active_windows_.empty()) {
    return true;
  }

  // Check if message belongs to a new window
  uint64_t window_id = getWindowIdForTimestamp(message_timestamp);
  return findWindowForTimestamp(message_timestamp) == nullptr;
}

auto TumblingWindowOperator::getWindowIdForTimestamp(uint64_t timestamp)
    -> uint64_t {
  // For tumbling windows, window ID is based on window size alignment
  return timestamp / window_size_.count();
}

auto TumblingWindowOperator::isLateData(uint64_t message_timestamp) -> bool {
  if (!event_time_processing_) {
    return false;  // In processing time mode, no data is considered late
  }

  return message_timestamp < (current_watermark_ - max_lateness_.count());
}

auto TumblingWindowOperator::processLateData(
    std::unique_ptr<MultiModalMessage> message) -> bool {
  if (!allow_late_data_) {
    ++dropped_data_count_;
    return false;
  }

  uint64_t message_timestamp = static_cast<uint64_t>(message->getTimestamp());

  if (isLateData(message_timestamp)) {
    ++dropped_data_count_;
    return false;  // Too late, drop the message
  }

  // Try to find existing window for late data
  WindowState* target_window = findWindowForTimestamp(message_timestamp);
  if (target_window != nullptr && !target_window->triggered) {
    target_window->messages.push_back(std::move(message));
    ++late_data_count_;
    return true;
  }

  ++dropped_data_count_;
  return false;
}

auto TumblingWindowOperator::findWindowForTimestamp(uint64_t timestamp)
    -> WindowState* {
  uint64_t target_window_id = getWindowIdForTimestamp(timestamp);

  for (auto& window : active_windows_) {
    if (window.window_id == target_window_id) {
      return &window;
    }
  }

  return nullptr;
}

auto TumblingWindowOperator::triggerCompletedWindows() -> void {
  auto current_time = getCurrentTimestamp();

  for (auto& window : active_windows_) {
    if (!window.triggered) {
      bool should_trigger = false;

      if (event_time_processing_) {
        // Trigger based on watermark
        should_trigger = (current_watermark_ >= window.end_time);
      } else {
        // Trigger based on processing time
        should_trigger = (current_time >= window.end_time);
      }

      if (should_trigger) {
        emitWindow(window);
        window.triggered = true;
      }
    }
  }

  cleanupOldWindows();
}

auto TumblingWindowOperator::emitWindow(WindowState& window) -> void {
  if (window.messages.empty()) {
    return;
  }

  auto window_results = processWindow(std::move(window.messages));

  for (auto& result : window_results) {
    if (result) {
      Response output_record(std::move(result));
      emit(0, output_record);
      incrementOutputCount();
    }
  }
}

auto TumblingWindowOperator::cleanupOldWindows() -> void {
  // Remove triggered windows that are older than max lateness
  auto cleanup_threshold = current_watermark_ - max_lateness_.count();

  active_windows_.erase(
      std::remove_if(active_windows_.begin(), active_windows_.end(),
                     [cleanup_threshold](const WindowState& window) {
                       return window.triggered &&
                              window.end_time < cleanup_threshold;
                     }),
      active_windows_.end());
}

auto TumblingWindowOperator::getCurrentTimestamp() -> uint64_t {
  auto now = std::chrono::system_clock::now();
  auto duration = now.time_since_epoch();
  return std::chrono::duration_cast<std::chrono::milliseconds>(duration)
      .count();
}

auto TumblingWindowOperator::updateWatermark(uint64_t message_timestamp)
    -> void {
  if (event_time_processing_) {
    uint64_t new_watermark = message_timestamp - watermark_delay_.count();
    if (new_watermark > current_watermark_) {
      current_watermark_ = new_watermark;
      triggerCompletedWindows();
    }
  }
}

}  // namespace sage_flow