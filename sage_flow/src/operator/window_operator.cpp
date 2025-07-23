#include "operator/window_operator.h"

#include "operator/response.h"
#include <utility>

namespace sage_flow {

WindowOperator::WindowOperator(std::string name, WindowType window_type)
    : Operator(OperatorType::kWindow, std::move(name)), 
      window_type_(window_type),
      window_start_time_(std::chrono::system_clock::now()) {}

auto WindowOperator::process(Response& input_record, int slot) -> bool {
  (void)slot; // Suppress unused parameter warning
  
  if (!input_record.hasMessage()) {
    return false;
  }
  
  auto input_message = input_record.getMessage();
  if (!input_message) {
    return false;
  }
  
  incrementProcessedCount();
  current_window_.push_back(std::move(input_message));
  
  if (shouldTriggerWindow()) {
    emitWindow();
    resetWindow();
  }
  
  return true;
}

auto WindowOperator::setWindowSize(std::chrono::milliseconds size) -> void {
  window_size_ = size;
}

auto WindowOperator::setSlideInterval(std::chrono::milliseconds interval) -> void {
  slide_interval_ = interval;
}

auto WindowOperator::shouldTriggerWindow() -> bool {
  auto current_time = std::chrono::system_clock::now();
  auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(
      current_time - window_start_time_);
  
  switch (window_type_) {
    case WindowType::kTumbling:
      return elapsed >= window_size_;
    case WindowType::kSliding:
      return elapsed >= slide_interval_;
    case WindowType::kSession:
      // For session windows, trigger based on inactivity
      // This is a simplified implementation
      return elapsed >= window_size_;
  }
  
  return false;
}

auto WindowOperator::emitWindow() -> void {
  if (current_window_.empty()) {
    return;
  }
  
  auto window_results = processWindow(std::move(current_window_));
  
  for (auto& result : window_results) {
    if (result) {
      Response output_record(std::move(result));
      emit(0, output_record);
      incrementOutputCount();
    }
  }
}

auto WindowOperator::resetWindow() -> void {
  current_window_.clear();
  window_start_time_ = std::chrono::system_clock::now();
}

}  // namespace sage_flow
