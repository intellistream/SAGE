#pragma once

#include <chrono>
#include <cstdint>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

namespace sage_flow {

class Operator;

/**
 * @brief Query constraints for execution planning
 */
struct QueryConstraints {
  std::chrono::milliseconds max_latency{1000};
  size_t max_memory_mb{1024};
  size_t max_parallelism{4};
  bool requires_ordering{false};
  bool requires_consistency{true};
  std::unordered_map<std::string, std::string> custom_constraints;
};

/**
 * @brief Optimization rule base class
 */
class OptimizationRule {
public:
  virtual ~OptimizationRule() = default;
  virtual auto getName() const -> std::string = 0;
  virtual auto apply(class ExecutionPlan& plan) -> bool = 0;
  virtual auto isApplicable(const class ExecutionPlan& plan) -> bool = 0;
};

/**
 * @brief Planning statistics for monitoring
 */
struct PlanningStatistics {
  uint64_t plans_generated{0};
  uint64_t optimizations_applied{0};
  uint64_t rules_executed{0};
  std::chrono::milliseconds total_planning_time{0};
  std::chrono::milliseconds average_planning_time{0};
  double cost_improvement_ratio{0.0};
};

/**
 * @brief Execution plan node representing an operator in the plan
 */
struct PlanNode {
  std::string operator_id;
  std::string operator_type;
  std::unique_ptr<Operator> op;
  std::vector<std::unique_ptr<PlanNode>> children;
  std::unordered_map<std::string, std::string> properties;
  double estimated_cost{0.0};
  size_t estimated_memory_usage{0};
  size_t parallelism_degree{1};

  explicit PlanNode(std::string id, std::string type)
      : operator_id(std::move(id)), operator_type(std::move(type)) {}
};

/**
 * @brief Execution plan for candyFlow integration
 *
 * Represents an optimized execution plan for SAGE flow pipelines.
 * This is a core component of the candyFlow streaming system, providing:
 * - Operator execution order and dependencies
 * - Cost and resource estimates
 * - Parallelism and optimization metadata
 * - Runtime execution guidance
 *
 * Based on candyFlow's ExecutionPlan design with SAGE integration.
 */
class ExecutionPlan {
public:
  /**
   * @brief Construct an execution plan
   * @param plan_id Unique identifier for this plan
   */
  explicit ExecutionPlan(std::string plan_id);

  // Prevent copying
  ExecutionPlan(const ExecutionPlan&) = delete;
  auto operator=(const ExecutionPlan&) -> ExecutionPlan& = delete;

  // Allow moving
  ExecutionPlan(ExecutionPlan&&) = default;
  auto operator=(ExecutionPlan&&) -> ExecutionPlan& = default;

  // Plan structure management
  auto addOperator(std::unique_ptr<PlanNode> node) -> void;
  auto removeOperator(const std::string& operator_id) -> void;
  auto getOperator(const std::string& operator_id) -> PlanNode*;
  auto getOperator(const std::string& operator_id) const -> const PlanNode*;
  auto getRootOperators() const -> std::vector<const PlanNode*>;
  auto getLeafOperators() const -> std::vector<const PlanNode*>;

  // Plan properties
  auto getPlanId() const -> const std::string&;
  auto getOperatorCount() const -> size_t;
  auto getTotalEstimatedCost() const -> double;
  auto getTotalEstimatedMemory() const -> size_t;
  auto getMaxParallelismDegree() const -> size_t;
  auto getEstimatedLatency() const -> std::chrono::milliseconds;

  // Plan validation
  auto validate() const -> bool;
  auto getValidationErrors() const -> std::vector<std::string>;

  // Plan optimization metadata
  auto setOptimizationApplied(const std::string& optimization) -> void;
  auto getAppliedOptimizations() const -> const std::vector<std::string>&;
  auto setCostEstimate(double cost) -> void;
  auto setMemoryEstimate(size_t memory_mb) -> void;
  auto setLatencyEstimate(std::chrono::milliseconds latency) -> void;

  // Plan execution metadata
  auto setProperty(const std::string& key, const std::string& value) -> void;
  auto getProperty(const std::string& key) const -> std::string;
  auto hasProperty(const std::string& key) const -> bool;
  auto removeProperty(const std::string& key) -> void;

  // Plan statistics
  auto getCreationTime() const -> std::chrono::system_clock::time_point;
  auto getLastModificationTime() const -> std::chrono::system_clock::time_point;
  auto getOptimizationCount() const -> size_t;

  // Plan serialization
  auto serialize() const -> std::string;
  static auto deserialize(const std::string& data)
      -> std::unique_ptr<ExecutionPlan>;

  // Plan comparison
  auto isEquivalent(const ExecutionPlan& other) const -> bool;
  auto compare(const ExecutionPlan& other) const
      -> int;  // -1, 0, 1 for less, equal, greater

private:
  // Plan identification
  std::string plan_id_;

  // Plan structure
  std::vector<std::unique_ptr<PlanNode>> operators_;
  std::unordered_map<std::string, PlanNode*> operator_index_;

  // Plan estimates
  double total_cost_{0.0};
  size_t total_memory_mb_{0};
  std::chrono::milliseconds estimated_latency_{0};

  // Plan metadata
  std::vector<std::string> applied_optimizations_;
  std::unordered_map<std::string, std::string> properties_;

  // Plan timing
  std::chrono::system_clock::time_point creation_time_;
  std::chrono::system_clock::time_point last_modification_;

  // Internal helpers
  auto updateOperatorIndex() -> void;
  auto recalculateEstimates() -> void;
  auto findDependencies(const PlanNode& node) const
      -> std::vector<const PlanNode*>;
  auto detectCycles() const -> bool;
  auto validateOperatorChain() const -> bool;
  auto updateLastModification() -> void;
};

}  // namespace sage_flow