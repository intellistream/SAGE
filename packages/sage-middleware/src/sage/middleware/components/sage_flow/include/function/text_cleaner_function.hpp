#pragma once

#include <string>
#include <vector>

#include "base_function.hpp"
#include "function_type.hpp"

namespace sage_flow {

/**
 * @brief Text Cleaner Function class
 *
 * Function for cleaning and preprocessing text data.
 * Supports various text cleaning operations and normalization.
 */
class TextCleanerFunction : public BaseFunction {
public:
  explicit TextCleanerFunction(const std::string& name)
      : BaseFunction(name, FunctionType::Map) {}

  ~TextCleanerFunction() override = default;

  /**
   * @brief Execute text cleaning on input response
   * @param response Input response containing text messages
   * @return Response with cleaned text data
   */
  auto execute(FunctionResponse& response) -> FunctionResponse override;

  /**
   * @brief Execute with two inputs (not supported for text cleaning)
   * @param left Left input response
   * @param right Right input response
   * @return Processed response
   */
  auto execute(FunctionResponse& left,
               FunctionResponse& right) -> FunctionResponse override;

  /**
   * @brief Set cleaning configuration
   * @param config Configuration string for text cleaning
   */
  void setConfig(const std::string& config);

  /**
   * @brief Get current cleaning configuration
   * @return Configuration string
   */
  auto getConfig() const -> const std::string&;

  /**
   * @brief Enable/disable specific cleaning operations
   * @param remove_whitespace Remove extra whitespace
   * @param remove_punctuation Remove punctuation
   * @param to_lowercase Convert to lowercase
   */
  void setCleaningOptions(bool remove_whitespace, bool remove_punctuation,
                          bool to_lowercase);

private:
  std::string config_;
  bool remove_whitespace_ = true;
  bool remove_punctuation_ = false;
  bool to_lowercase_ = true;

  /**
   * @brief Clean text content
   * @param text Input text to clean
   * @return Cleaned text
   */
  auto cleanText(const std::string& text) const -> std::string;
};

}  // namespace sage_flow