#pragma once

#include "base_function.hpp"
#include "function_response.hpp"
#include "function_type.hpp"

namespace sage_flow {

/**
 * @brief Source Function class
 *
 * Abstract base class for data source functions.
 * Based on candyFlow's SourceFunction design.
 */
class SourceFunction : public BaseFunction {
public:
  explicit SourceFunction(const std::string& name)
      : BaseFunction(name, FunctionType::Source) {}

  ~SourceFunction() override = default;

  /**
   * @brief Initialize the source (e.g., open files, connect to streams)
   */
  virtual void init() = 0;

  /**
   * @brief Execute returns a batch of messages. Empty response means no more
   * data.
   * @param response Input response (typically empty for sources)
   * @return Response containing generated messages
   */
  auto execute(FunctionResponse& response) -> FunctionResponse override = 0;

  /**
   * @brief Close the source and cleanup resources
   */
  virtual void close() = 0;

  /**
   * @brief Check if the source has more data
   * @return true if more data is available
   */
  virtual auto hasNext() -> bool = 0;
};

}  // namespace sage_flow
