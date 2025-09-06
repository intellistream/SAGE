#include "operator/window_operator.hpp"

#include "operator/base_operator.hpp"
#include "message/multimodal_message.hpp"
#include "operator/response.hpp"
#include <utility>

namespace sage_flow {
template <typename InputType, typename OutputType>
WindowOperator<InputType, OutputType>::WindowOperator(std::string name, WindowType window_type, OperatorType type)
    : BaseOperator<InputType, OutputType>(type, std::move(name)),
      window_type_(window_type),
      window_start_time_(std::chrono::system_clock::now()) {}

template <typename InputType, typename OutputType>
auto WindowOperator<InputType, OutputType>::process(const std::vector<std::shared_ptr<InputType>>& input) -> std::optional<Response<OutputType>> {
  for (const auto& message : input) {
    if (message) {
      this->incrementProcessedCount();
      current_window_.push_back(message);
      
      if (shouldTriggerWindow()) {
        emitWindow();
        resetWindow();
      }
    }
  }
  return std::nullopt;
}

template <typename InputType, typename OutputType>
auto WindowOperator<InputType, OutputType>::setWindowSize(std::chrono::milliseconds size) -> void {
  window_size_ = size;
}

template <typename InputType, typename OutputType>
auto WindowOperator<InputType, OutputType>::setSlideInterval(std::chrono::milliseconds interval)
    -> void {
  slide_interval_ = interval;
}

template <typename InputType, typename OutputType>
auto WindowOperator<InputType, OutputType>::shouldTriggerWindow() -> bool {
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

template <typename InputType, typename OutputType>
auto WindowOperator<InputType, OutputType>::emitWindow() -> void {
  if (current_window_.empty()) {
    return;
  }

  auto window_results = processWindow(current_window_);

  std::vector<std::shared_ptr<OutputType>> output_messages;
  for (auto& result : window_results) {
    if (result) {
      output_messages.push_back(std::move(result));
    }
  }

  if (!output_messages.empty()) {
    Response<OutputType> output_record(std::move(output_messages));
    this->emit(0, output_record);
    this->incrementOutputCount();
  }
}

template <typename InputType, typename OutputType>
auto WindowOperator<InputType, OutputType>::resetWindow() -> void {
  current_window_.clear();
  window_start_time_ = std::chrono::system_clock::now();
}

// Explicit template instantiation for MultiModalMessage
template class WindowOperator<MultiModalMessage, MultiModalMessage>;

}  // namespace sage_flow
