#pragma once

#include <functional>

#include "base_function.hpp"
#include "data_stream/response.hpp"

namespace sage_flow {

/**
 * @brief Sink function type definition
 *
 * Function that processes messages for output/storage
 */

/**
 * @brief Sink Function class
 *
 * Abstract base class for data sink functions.
 * Based on candyFlow's SinkFunction design.
 */
template <typename InType>
class SinkFunction : public BaseFunction<InType, InType> {
public:
  using SinkFunc = std::function<void(const InType&)>;

  explicit SinkFunction(std::string name);
  SinkFunction(std::string name, SinkFunc sink_func);

  ~SinkFunction() override = default;

  // Core sink interface - consumes messages, returns optional for single sink
  std::optional<InType> execute(const InType& input) override;
  void execute_batch(const std::vector<InType>& inputs, std::vector<InType>& outputs) override;

  /**
   * @brief Initialize the sink (e.g., open files, connect to external systems)
   */
  virtual void init() = 0;

  /**
   * @brief Close the sink and cleanup resources
   */
  virtual void close() = 0;

  /**
   * @brief Sink a single message - core sink operation
   */
  virtual void sink(const InType& message);

  /**
   * @brief Set the sink function
   * @param sink_func Function to process each message
   */
  void setSinkFunc(SinkFunc sink_func);

private:
  SinkFunc sink_func_;
};

}  // namespace sage_flow
