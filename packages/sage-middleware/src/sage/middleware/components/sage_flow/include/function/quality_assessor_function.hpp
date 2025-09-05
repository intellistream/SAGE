#pragma once

#include <string>
#include <vector>

#include "base_function.hpp"
#include "function_response.hpp"
#include "function_type.hpp"

namespace sage_flow {

/**
 * @brief Quality Assessor Function class
 *
 * Function for assessing the quality of processed data and providing quality
 * metrics. Supports configurable quality thresholds and scoring algorithms.
 */
class QualityAssessorFunction : public BaseFunction {
public:
  explicit QualityAssessorFunction(const std::string& name)
      : BaseFunction(name, FunctionType::Map) {}

  ~QualityAssessorFunction() override = default;

  /**
   * @brief Execute quality assessment on input response
   * @param response Input response containing data to assess
   * @return Response with quality assessment results
   */
  auto execute(FunctionResponse& response) -> FunctionResponse override;

  /**
   * @brief Execute with two inputs (not supported for quality assessment)
   * @param left Left input response
   * @param right Right input response
   * @return Processed response
   */
  auto execute(FunctionResponse& left,
               FunctionResponse& right) -> FunctionResponse override;

  /**
   * @brief Set quality assessment configuration
   * @param config Configuration string for quality assessment
   */
  void setConfig(const std::string& config);

  /**
   * @brief Get current quality assessment configuration
   * @return Configuration string
   */
  auto getConfig() const -> const std::string&;

  /**
   * @brief Set quality threshold
   * @param threshold Quality threshold value (0.0 to 1.0)
   */
  void setThreshold(double threshold);

  /**
   * @brief Get current quality threshold
   * @return Quality threshold value
   */
  auto getThreshold() const -> double;

private:
  std::string config_;
  double threshold_ = 0.5;

  /**
   * @brief Assess quality of text content
   * @param content Text content to assess
   * @return Quality score (0.0 to 1.0)
   */
  auto assessTextQuality(const std::string& content) const -> double;

  /**
   * @brief Assess quality of structured data
   * @param data Structured data to assess
   * @return Quality score (0.0 to 1.0)
   */
  auto assessStructuredQuality(const std::vector<std::string>& data) const
      -> double;
};

}  // namespace sage_flow