#pragma once

#include "operator/operator.h"

namespace sage_flow {

/**
 * @brief Quality assessor function for data quality evaluation
 * 
 * Evaluates the quality of processed data based on various metrics
 * including completeness, consistency, and relevance.
 */
class QualityAssessorFunction final : public MapOperator {
 public:
  struct QualityMetrics {
    float completeness_score_ = 0.0F;
    float consistency_score_ = 0.0F;
    float relevance_score_ = 0.0F;
    float overall_score_ = 0.0F;
  };
  
  struct AssessmentConfig {
    float completeness_weight_ = 0.4F;
    float consistency_weight_ = 0.3F;
    float relevance_weight_ = 0.3F;
    float min_acceptable_score_ = 0.5F;
  };
  
  explicit QualityAssessorFunction(AssessmentConfig config);
  
  auto map(std::unique_ptr<MultiModalMessage> input)
      -> std::unique_ptr<MultiModalMessage> override;
  
  auto assessQuality(const MultiModalMessage& message) const -> QualityMetrics;
  
 private:
  AssessmentConfig config_;
  
  auto assessCompleteness(const MultiModalMessage& message) const -> float;
  auto assessConsistency(const MultiModalMessage& message) const -> float;
  auto assessRelevance(const MultiModalMessage& message) const -> float;
  auto calculateOverallScore(const QualityMetrics& metrics) const -> float;
};

}  // namespace sage_flow
