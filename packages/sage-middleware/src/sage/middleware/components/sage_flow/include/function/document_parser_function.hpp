#pragma once

#include <string>

#include "base_function.hpp"
#include "function_response.hpp"
#include "function_type.hpp"

namespace sage_flow {

/**
 * @brief Document Parser Function class
 *
 * Function for parsing documents and extracting structured data.
 * Supports various document formats and provides configurable parsing options.
 */
class DocumentParserFunction : public BaseFunction {
public:
  explicit DocumentParserFunction(const std::string& name)
      : BaseFunction(name, FunctionType::Map) {}

  ~DocumentParserFunction() override = default;

  /**
   * @brief Execute document parsing on input response
   * @param response Input response containing document messages
   * @return Response with parsed document data
   */
  auto execute(FunctionResponse& response) -> FunctionResponse override;

  /**
   * @brief Execute with two inputs (not supported for document parsing)
   * @param left Left input response
   * @param right Right input response
   * @return Processed response
   */
  auto execute(FunctionResponse& left,
               FunctionResponse& right) -> FunctionResponse override;

  /**
   * @brief Set parsing configuration
   * @param config Configuration string for parser
   */
  void setConfig(const std::string& config);

  /**
   * @brief Get current parsing configuration
   * @return Configuration string
   */
  auto getConfig() const -> const std::string&;

private:
  std::string config_;
};

}  // namespace sage_flow