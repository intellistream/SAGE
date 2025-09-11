#pragma once

#include <chrono>

#include "base_operator.hpp"
#include "data_stream/response.hpp"

namespace sage_flow {

template <typename InputType, typename OutputType>
class WindowOperator : public BaseOperator<InputType, OutputType> {
public:
  enum class WindowType {
    Sliding,
    Tumbling
  };
  
  WindowOperator(std::string name, WindowType window_type, std::chrono::milliseconds window_size);
  WindowOperator(std::string name, WindowType window_type, std::chrono::milliseconds window_size, std::string description);
  
  // Prevent copying
  WindowOperator(const WindowOperator&) = delete;
  auto operator=(const WindowOperator&) -> WindowOperator& = delete;
  
  // Allow moving
  WindowOperator(WindowOperator&&) = default;
  auto operator=(WindowOperator&&) -> WindowOperator& = default;
  
  auto process(const std::vector<std::unique_ptr<InputType>>& input) -> std::optional<Response<OutputType>> override;
  
  auto getWindowType() const -> WindowType;
  auto getWindowSize() const -> std::chrono::milliseconds;
  
private:
  WindowType window_type_;
  std::chrono::milliseconds window_size_;
  // Window state management
  std::unordered_map<std::string, std::vector<std::unique_ptr<InputType>>> window_buffer_;
};

}  // namespace sage_flow