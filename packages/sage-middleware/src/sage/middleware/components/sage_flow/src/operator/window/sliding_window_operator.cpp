#include "operator/window/sliding_window_operator.hpp"

#include <algorithm>
#include <chrono>
#include <string>
#include <utility>

#include "message/multimodal_message.hpp"
#include "operator/response.hpp"

namespace sage_flow {

SlidingWindowOperator::SlidingWindowOperator(
    std::string name, std::chrono::milliseconds window_size,
    std::chrono::milliseconds slide_interval, bool allow_late_data)
    : WindowOperator(std::move(name), WindowType::kSliding),
      window_size_(window_size),
      slide_interval_(slide_interval),
      allow_late_data_(allow_late_data),
      event_time_processing_(true),
      max_windows_in_memory_(1000),
      watermark_delay_(std::chrono::milliseconds(1000)),
      max_lateness_(std::chrono::milliseconds(5000)),
      current_watermark_(0),
      last_slide_time_(0),
      total_window_count_(0),
      late_data_count_(0),
      dropped_data_count_(0) {
  setWindowSize(window_size);
  setSlideInterval(slide_interval);
}

auto SlidingWindowOperator::processWindow(
    std::vector<std::unique_ptr<MultiModalMessage>> window_messages)
    -> std::vector<std::unique_ptr<MultiModalMessage>> {
  std::vector<std::unique_ptr<MultiModalMessage>> results;

  // For sliding windows, we create an aggregated result per window
  if (!window_messages.empty()) {
    auto first_message = std::move(window_messages[0]);

    // Create metadata about the sliding window
    first_message->setMetadata("window_type", "sliding");
    first_message->setMetadata("window_size_ms",
                               std::to_string(window_size_.count()));
    first_message->setMetadata("slide_interval_ms",
                               std::to_string(slide_interval_.count()));
    first_message->setMetadata("window_message_count",
                               std::to_string(window_messages.size()));
    first_message->setMetadata("window_id",
                               std::to_string(total_window_count_));

    // Add processing trace
    first_message->addProcessingStep("sliding_window_" +
                                     std::to_string(total_window_count_));

    results.push_back(std::move(first_message));
  }

  return results;
}

auto SlidingWindowOperator::setWatermarkDelay(std::chrono::milliseconds delay)
    -> void {
  watermark_delay_ = delay;
}

auto SlidingWindowOperator::setMaxLateness(
    std::chrono::milliseconds max_lateness) -> void {
  max_lateness_ = max_lateness;
}

auto SlidingWindowOperator::enableEventTimeProcessing(bool enable) -> void {
  event_time_processing_ = enable;
}

auto SlidingWindowOperator::setMaxWindowsInMemory(size_t max_windows) -> void {
  max_windows_in_memory_ = max_windows;
}

auto SlidingWindowOperator::getActiveWindowCount() const -> uint64_t {
  return active_windows_.size();
}

auto SlidingWindowOperator::getTotalWindowCount() const -> uint64_t {
  return total_window_count_;
}

auto SlidingWindowOperator::getLateDataCount() const -> uint64_t {
  return late_data_count_;
}

auto SlidingWindowOperator::getDroppedDataCount() const -> uint64_t {
  return dropped_data_count_;
}

auto SlidingWindowOperator::getMemoryUsage() const -> size_t {
  size_t total_size = 0;
  for (const auto& window : active_windows_) {
    total_size +=
        window.messages.size() * sizeof(std::unique_ptr<MultiModalMessage>);
  }
  return total_size;
}

auto SlidingWindowOperator::shouldCreateNewWindow(uint64_t message_timestamp)
    -> bool {
  if (active_windows_.empty()) {
    return true;
  }

  // Check if we need to create new sliding windows
  uint64_t current_time = getCurrentTimestamp();
  return (current_time - last_slide_time_) >=
         static_cast<uint64_t>(slide_interval_.count());
}

auto SlidingWindowOperator::getWindowStartsForTimestamp(uint64_t timestamp)
    -> std::vector<uint64_t> {
  std::vector<uint64_t> window_starts;

  // Calculate all possible window starts that would include this timestamp
  uint64_t slide_ms = slide_interval_.count();
  uint64_t window_ms = window_size_.count();

  // Find the latest window start that would include this timestamp
  uint64_t latest_start = timestamp - window_ms + 1;

  // Generate window starts at slide intervals
  for (uint64_t start = (latest_start / slide_ms) * slide_ms;
       start <= timestamp; start += slide_ms) {
    if (start + window_ms > timestamp) {
      window_starts.push_back(start);
    }
  }

  return window_starts;
}

auto SlidingWindowOperator::isLateData(uint64_t message_timestamp) -> bool {
  if (!event_time_processing_) {
    return false;  // In processing time mode, no data is considered late
  }

  return message_timestamp < (current_watermark_ - max_lateness_.count());
}

auto SlidingWindowOperator::processLateData(
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

  // Try to find overlapping windows for late data
  auto overlapping_windows = findOverlappingWindows(message_timestamp);
  bool added = false;

  for (auto* window : overlapping_windows) {
    if (!window->triggered) {
      window->messages.push_back(
          std::unique_ptr<MultiModalMessage>(message->clone().release()));
      added = true;
    }
  }

  if (added) {
    ++late_data_count_;
    return true;
  }

  ++dropped_data_count_;
  return false;
}

auto SlidingWindowOperator::findOverlappingWindows(uint64_t timestamp)
    -> std::vector<SlidingWindowState*> {
  std::vector<SlidingWindowState*> overlapping;

  for (auto& window : active_windows_) {
    if (timestamp >= window.window_start && timestamp < window.window_end) {
      overlapping.push_back(&window);
    }
  }

  return overlapping;
}

auto SlidingWindowOperator::triggerCompletedWindows() -> void {
  auto current_time = getCurrentTimestamp();

  for (auto& window : active_windows_) {
    if (!window.triggered) {
      bool should_trigger = false;

      if (event_time_processing_) {
        // Trigger based on watermark
        should_trigger = (current_watermark_ >= window.window_end);
      } else {
        // Trigger based on processing time
        should_trigger = (current_time >= window.window_end);
      }

      if (should_trigger) {
        emitWindow(window);
        window.triggered = true;
        ++total_window_count_;
      }
    }
  }

  cleanupOldWindows();
  manageMemoryUsage();
}

auto SlidingWindowOperator::emitWindow(SlidingWindowState& window) -> void {
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

auto SlidingWindowOperator::cleanupOldWindows() -> void {
  // Remove triggered windows that are older than max lateness
  auto cleanup_threshold = current_watermark_ - max_lateness_.count();

  active_windows_.erase(
      std::remove_if(active_windows_.begin(), active_windows_.end(),
                     [cleanup_threshold](const SlidingWindowState& window) {
                       return window.triggered &&
                              window.window_end < cleanup_threshold;
                     }),
      active_windows_.end());
}

auto SlidingWindowOperator::createWindowsForTimestamp(uint64_t timestamp)
    -> void {
  auto window_starts = getWindowStartsForTimestamp(timestamp);

  for (uint64_t start : window_starts) {
    // Check if window already exists
    bool exists = false;
    for (const auto& window : active_windows_) {
      if (window.window_start == start) {
        exists = true;
        break;
      }
    }

    if (!exists) {
      uint64_t end = start + window_size_.count();
      active_windows_.emplace_back(start, end);
    }
  }
}

auto SlidingWindowOperator::getCurrentTimestamp() -> uint64_t {
  auto now = std::chrono::system_clock::now();
  auto duration = now.time_since_epoch();
  return std::chrono::duration_cast<std::chrono::milliseconds>(duration)
      .count();
}

auto SlidingWindowOperator::updateWatermark(uint64_t message_timestamp)
    -> void {
  if (event_time_processing_) {
    uint64_t new_watermark = message_timestamp - watermark_delay_.count();
    if (new_watermark > current_watermark_) {
      current_watermark_ = new_watermark;
      triggerCompletedWindows();
    }
  }
}

auto SlidingWindowOperator::manageMemoryUsage() -> void {
  // If we have too many windows in memory, remove the oldest triggered ones
  while (active_windows_.size() > max_windows_in_memory_) {
    auto oldest_triggered = std::find_if(
        active_windows_.begin(), active_windows_.end(),
        [](const SlidingWindowState& window) { return window.triggered; });

    if (oldest_triggered != active_windows_.end()) {
      active_windows_.erase(oldest_triggered);
    } else {
      break;  // No triggered windows to remove
    }
  }
}

}  // namespace sage_flow