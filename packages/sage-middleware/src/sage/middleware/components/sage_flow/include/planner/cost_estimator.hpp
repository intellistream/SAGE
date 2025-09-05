#pragma once

#include <chrono>
#include <cstdint>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

namespace sage_flow {

class ExecutionPlan;
class PlanNode;
class Operator;

/**
 * @brief Cost model for different types of operations
 */
struct CostModel {
  double cpu_cost_per_row{1.0};
  double memory_cost_per_mb{0.1};
  double io_cost_per_mb{10.0};
  double network_cost_per_mb{5.0};
  double startup_cost{100.0};
  double parallelism_overhead{0.2};
};

/**
 * @brief Resource usage statistics
 */
struct ResourceStats {
  uint64_t rows_processed{0};
  uint64_t bytes_processed{0};
  std::chrono::milliseconds processing_time{0};
  size_t memory_peak_mb{0};
  size_t memory_average_mb{0};
  double cpu_utilization{0.0};
};

/**
 * @brief Cost estimation result
 */
struct CostEstimate {
  double total_cost{0.0};
  double cpu_cost{0.0};
  double memory_cost{0.0};
  double io_cost{0.0};
  double network_cost{0.0};
  std::chrono::milliseconds estimated_time{0};
  size_t estimated_memory_mb{0};
  double confidence{1.0};  // 0.0 to 1.0
};

/**
 * @brief Cost estimator for candyFlow integration
 *
 * Implements cost estimation for SAGE flow operations and plans.
 * This is a key component of the candyFlow streaming system, providing:
 * - Accurate cost modeling for different operators
 * - Resource usage prediction
 * - Performance-based optimization guidance
 * - Historical statistics integration
 *
 * Based on candyFlow's CostEstimator design with SAGE integration.
 */
class CostEstimator {
public:
  /**
   * @brief Construct a cost estimator
   */
  explicit CostEstimator();

  // Prevent copying
  CostEstimator(const CostEstimator&) = delete;
  auto operator=(const CostEstimator&) -> CostEstimator& = delete;

  // Allow moving
  CostEstimator(CostEstimator&&) = default;
  auto operator=(CostEstimator&&) -> CostEstimator& = default;

  /**
   * @brief Estimate cost for an execution plan
   * @param plan Execution plan to estimate
   * @return Cost estimate for the entire plan
   */
  auto estimatePlanCost(const ExecutionPlan& plan) -> CostEstimate;

  /**
   * @brief Estimate cost for a single operator
   * @param node Plan node containing the operator
   * @param input_size Expected input data size
   * @return Cost estimate for the operator
   */
  auto estimateOperatorCost(const PlanNode& node,
                            uint64_t input_size) -> CostEstimate;

  /**
   * @brief Compare costs of two execution plans
   * @param plan1 First plan to compare
   * @param plan2 Second plan to compare
   * @return Negative if plan1 is cheaper, positive if plan2 is cheaper, 0 if
   * equal
   */
  auto comparePlans(const ExecutionPlan& plan1,
                    const ExecutionPlan& plan2) -> int;

  // Cost model configuration
  auto setCostModel(const std::string& operator_type,
                    const CostModel& model) -> void;
  auto getCostModel(const std::string& operator_type) const -> const CostModel&;
  auto updateCostModel(const std::string& operator_type,
                       const ResourceStats& stats) -> void;

  // Historical statistics
  auto recordOperatorExecution(const std::string& operator_type,
                               const ResourceStats& stats) -> void;
  auto getHistoricalStats(const std::string& operator_type) const
      -> std::vector<ResourceStats>;
  auto clearHistoricalStats() -> void;

  // Calibration and learning
  auto calibrateModel(const std::string& operator_type,
                      const std::vector<ResourceStats>& training_data) -> void;
  auto enableAdaptiveLearning(bool enable) -> void;
  auto isAdaptiveLearningEnabled() const -> bool;

  // Performance monitoring
  auto getEstimationAccuracy() const -> double;
  auto getEstimationCount() const -> uint64_t;
  auto resetEstimationStats() -> void;

private:
  // Cost models for different operator types
  std::unordered_map<std::string, CostModel> cost_models_;

  // Historical execution statistics
  std::unordered_map<std::string, std::vector<ResourceStats>> historical_stats_;

  // Adaptive learning configuration
  bool adaptive_learning_enabled_;
  size_t max_historical_records_;

  // Estimation accuracy tracking
  mutable uint64_t estimation_count_;
  mutable double total_accuracy_;

  // Internal estimation methods
  auto estimateSourceCost(const PlanNode& node,
                          uint64_t input_size) -> CostEstimate;
  auto estimateMapCost(const PlanNode& node,
                       uint64_t input_size) -> CostEstimate;
  auto estimateFilterCost(const PlanNode& node,
                          uint64_t input_size) -> CostEstimate;
  auto estimateJoinCost(const PlanNode& node,
                        uint64_t input_size) -> CostEstimate;
  auto estimateAggregateCost(const PlanNode& node,
                             uint64_t input_size) -> CostEstimate;
  auto estimateWindowCost(const PlanNode& node,
                          uint64_t input_size) -> CostEstimate;
  auto estimateSinkCost(const PlanNode& node,
                        uint64_t input_size) -> CostEstimate;

  // Utility methods
  auto getDefaultCostModel(const std::string& operator_type) -> CostModel;
  auto calculateSelectivity(const PlanNode& node) -> double;
  auto estimateOutputSize(const PlanNode& node,
                          uint64_t input_size) -> uint64_t;
  auto applyParallelismCost(const CostEstimate& base_cost,
                            size_t parallelism) -> CostEstimate;
  auto combineChildCosts(const std::vector<CostEstimate>& child_costs)
      -> CostEstimate;

  // Learning and adaptation
  auto updateModelFromStats(const std::string& operator_type,
                            const ResourceStats& stats) -> void;
  auto calculateAccuracy(const CostEstimate& estimate,
                         const ResourceStats& actual) -> double;
  auto pruneHistoricalStats() -> void;

  // Default cost models initialization
  auto initializeDefaultModels() -> void;
};

}  // namespace sage_flow