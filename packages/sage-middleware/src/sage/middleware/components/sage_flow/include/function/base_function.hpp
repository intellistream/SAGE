#pragma once

#include <string>

#include "function_response.hpp"
#include "function_type.hpp"

namespace sage_flow {

/**
 * @brief Base Function class
 *
 * Based on candyFlow's Function design, adapted for SAGE Flow.
 * Functions are independent processing units that do NOT inherit from
 * operators. They are used BY operators to perform actual data processing.
 */
template <typename InType, typename OutType>
class BaseFunction {
public:
  explicit BaseFunction(std::string name, FunctionType type);
  virtual ~BaseFunction() = default;

  // Getters and setters
  auto getName() const -> const std::string&;
  auto getType() const -> FunctionType;
  void setName(const std::string& name);
  void setType(FunctionType type);

  // Main execution methods (based on candyFlow pattern)

  /**
   * @brief Execute function with single input
   * @param response Input response containing messages to process
   * @return Processed response
   */
  virtual auto execute(FunctionResponse& response) -> FunctionResponse;

  /**
   * @brief Execute function with two inputs (for join operations)
   * @param left Left input response
   * @param right Right input response
   * @return Processed response
   */
  virtual auto execute(FunctionResponse& left,
                       FunctionResponse& right) -> FunctionResponse;

protected:
  std::string name_;
  FunctionType type_ = FunctionType::None;
};

}  // namespace sage_flow
