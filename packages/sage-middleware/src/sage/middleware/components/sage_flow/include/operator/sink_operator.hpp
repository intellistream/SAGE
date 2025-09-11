#pragma once

#include <memory>
#include <string>

#include "data_stream/response.hpp"
#include "operator/base_operator.hpp"
#include "function/sink_function.hpp"

namespace sage_flow {

class MultiModalMessage;
// class Response; // Already defined in response.hpp

/**
 * @brief Sink operator for data output
 *
 * Consumes processed messages and performs final operations such as
 * writing to files, databases, or external systems. Uses composition pattern
 * with SinkFunction.
 */
template <typename InputType>
class SinkOperator final : public BaseOperator<InputType, InputType> {
public:
  explicit SinkOperator(std::string name);

  /**
   * @brief Constructor with SinkFunction
   * @param name Operator name
   * @param sink_function SinkFunction instance to handle processing logic
   */
  SinkOperator(std::string name, std::unique_ptr<SinkFunction<InputType>> sink_function);

  // Prevent copying
  SinkOperator(const SinkOperator&) = delete;
  auto operator=(const SinkOperator&) -> SinkOperator& = delete;

  // Allow moving
  SinkOperator(SinkOperator&&) = default;
  auto operator=(SinkOperator&&) -> SinkOperator& = default;

  auto process(const std::vector<std::shared_ptr<InputType>>& input) -> std::optional<Response<InputType>>;

  /**
   * @brief Set the sink function
   * @param sink_function SinkFunction instance to handle processing logic
   */
  void setSinkFunction(std::unique_ptr<SinkFunction<InputType>> sink_function);

  /**
   * @brief Get the sink function
   * @return Reference to the contained SinkFunction
   */
  auto getSinkFunction() -> SinkFunction<InputType>&;

  /**
   * @brief Flush any buffered data
   */
  void flush();

private:
  std::unique_ptr<SinkFunction<InputType>> sink_function_;
};

}  // namespace sage_flow
