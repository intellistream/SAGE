#pragma once

#include <chrono>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "base_operator.hpp"

namespace sage_flow {

#include "message/multimodal_message.hpp"
#include "operator/response.hpp"

/**
 * @brief Window operator for time-based or count-based windowing
 *
 * Groups messages into windows for batch processing or aggregation.
 * Supports tumbling, sliding, and session windows.
 */
template <typename InputType = MultiModalMessage, typename OutputType = MultiModalMessage>
class WindowOperator : public BaseOperator<InputType, OutputType> {
public:
  enum class WindowType : std::uint8_t { kTumbling, kSliding, kSession };

  explicit WindowOperator(std::string name, WindowType window_type, OperatorType type = OperatorType::kWindow);

  // Prevent copying
  WindowOperator(const WindowOperator&) = delete;
  auto operator=(const WindowOperator&) -> WindowOperator& = delete;

  // Allow moving
  WindowOperator(WindowOperator&&) = default;
  auto operator=(WindowOperator&&) -> WindowOperator& = default;

  auto process(const std::vector<std::shared_ptr<InputType>>& input) -> std::optional<Response<OutputType>>;

  // Window-specific interface
  virtual auto processWindow(
      const std::vector<std::shared_ptr<InputType>>& window_messages)
      -> std::vector<std::shared_ptr<OutputType>> = 0;
  auto setWindowSize(std::chrono::milliseconds size) -> void;
  auto setSlideInterval(std::chrono::milliseconds interval) -> void;

private:
  WindowType window_type_;
  std::chrono::milliseconds window_size_ = std::chrono::milliseconds(1000);
  std::chrono::milliseconds slide_interval_ = std::chrono::milliseconds(1000);
  std::vector<std::shared_ptr<InputType>> current_window_;
  std::chrono::system_clock::time_point window_start_time_;

  auto shouldTriggerWindow() -> bool;
  auto emitWindow() -> void;
  auto resetWindow() -> void;
};

}  // namespace sage_flow
