#pragma once

#include "base_function.hpp"
#include "function/dummy_input.hpp"

namespace sage_flow {

/**
 * @brief Source Function class
 *
 * Abstract base class for data source functions.
 * Based on candyFlow's SourceFunction design.
 */
template <typename OutType>
class SourceFunction : public BaseFunction<DummyInput, OutType> {
public:
  explicit SourceFunction(std::string name);
  
  virtual ~SourceFunction() override = default;

  /**
   * @brief Initialize the source (e.g., open files, connect to streams)
   */
  virtual void init() = 0;

  /**
   * @brief Generate next batch of messages
   * @return Batch of generated messages
   */
  virtual std::vector<OutType> generate_batch() = 0;

  /**
   * @brief Close the source and cleanup resources
   */
  virtual void close() = 0;

  /**
   * @brief Check if the source has more data
   * @return true if more data is available
   */
  virtual auto hasNext() -> bool = 0;

  // BaseFunction interface implementation - dummy input for sources
  std::optional<OutType> execute(const DummyInput& input) override;
  void execute_batch(const std::vector<DummyInput>& inputs, std::vector<OutType>& outputs) override;

private:
  bool has_more_data_ = true;
};

}  // namespace sage_flow
