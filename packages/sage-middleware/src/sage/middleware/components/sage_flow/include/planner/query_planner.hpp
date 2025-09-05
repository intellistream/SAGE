#pragma once

#include <chrono>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include "execution_plan.hpp"

namespace sage_flow {

class Operator;
class CostEstimator;
class IndexSelector;

/**
 * @brief Query planner for candyFlow integration
 *
 * Implements query planning and optimization for SAGE flow pipelines.
 * This is a core component of the candyFlow streaming system, providing:
 * - Query plan generation and optimization
 * - Cost-based optimization strategies
 * - Operator reordering and selection
 * - Index usage optimization
 * - Parallel execution planning
 *
 * Based on candyFlow's QueryPlanner design with SAGE integration.
 */
class QueryPlanner {
public:
  enum class OptimizationLevel : uint8_t {
    kNone,       // No optimization
    kBasic,      // Basic rule-based optimization
    kAdvanced,   // Cost-based optimization
    kAggressive  // Aggressive optimization with experimental features
  };

  enum class PlanningStrategy : uint8_t {
    kGreedy,    // Greedy planning strategy
    kDynamic,   // Dynamic programming approach
    kGenetic,   // Genetic algorithm for complex queries
    kHeuristic  // Heuristic-based planning
  };

  /**
   * @brief Construct a query planner
   * @param optimization_level Level of optimization to apply
   * @param strategy Planning strategy to use
   */
  explicit QueryPlanner(
      OptimizationLevel optimization_level = OptimizationLevel::kAdvanced,
      PlanningStrategy strategy = PlanningStrategy::kDynamic);

  // Prevent copying
  QueryPlanner(const QueryPlanner&) = delete;
  auto operator=(const QueryPlanner&) -> QueryPlanner& = delete;

  // Allow moving
  QueryPlanner(QueryPlanner&&) = default;
  auto operator=(QueryPlanner&&) -> QueryPlanner& = default;

  /**
   * @brief Generate an optimized execution plan
   * @param operators List of operators in the query
   * @param constraints Query constraints and requirements
   * @return Optimized execution plan
   */
  auto generatePlan(const std::vector<std::unique_ptr<Operator>>& operators,
                    const QueryConstraints& constraints)
      -> std::unique_ptr<ExecutionPlan>;

  /**
   * @brief Optimize an existing execution plan
   * @param plan Execution plan to optimize
   * @return Optimized execution plan
   */
  auto optimizePlan(std::unique_ptr<ExecutionPlan> plan)
      -> std::unique_ptr<ExecutionPlan>;

  // Configuration interface
  auto setOptimizationLevel(OptimizationLevel level) -> void;
  auto setPlanningStrategy(PlanningStrategy strategy) -> void;
  auto setCostEstimator(std::unique_ptr<CostEstimator> estimator) -> void;
  auto setIndexSelector(std::unique_ptr<IndexSelector> selector) -> void;
  auto setMaxPlanningTime(std::chrono::milliseconds max_time) -> void;
  auto setParallelismDegree(size_t degree) -> void;

  // Rule management
  auto addOptimizationRule(std::unique_ptr<OptimizationRule> rule) -> void;
  auto removeOptimizationRule(const std::string& rule_name) -> void;
  auto enableRule(const std::string& rule_name, bool enable) -> void;

  // Performance monitoring
  auto getPlanningStatistics() const -> PlanningStatistics;
  auto getLastPlanningTime() const -> std::chrono::milliseconds;
  auto resetStatistics() -> void;

private:
  // Core planning components
  OptimizationLevel optimization_level_;
  PlanningStrategy strategy_;
  std::unique_ptr<CostEstimator> cost_estimator_;
  std::unique_ptr<IndexSelector> index_selector_;

  // Configuration
  std::chrono::milliseconds max_planning_time_;
  size_t parallelism_degree_;

  // Optimization rules
  std::unordered_map<std::string, std::unique_ptr<OptimizationRule>>
      optimization_rules_;
  std::unordered_map<std::string, bool> rule_enabled_;

  // Statistics
  mutable PlanningStatistics statistics_;
  mutable std::chrono::milliseconds last_planning_time_;

  // Internal planning methods
  auto applyBasicOptimizations(std::unique_ptr<ExecutionPlan> plan)
      -> std::unique_ptr<ExecutionPlan>;
  auto applyCostBasedOptimizations(std::unique_ptr<ExecutionPlan> plan)
      -> std::unique_ptr<ExecutionPlan>;
  auto applyAdvancedOptimizations(std::unique_ptr<ExecutionPlan> plan)
      -> std::unique_ptr<ExecutionPlan>;

  // Rule application
  auto applyOptimizationRules(std::unique_ptr<ExecutionPlan> plan)
      -> std::unique_ptr<ExecutionPlan>;
  auto validatePlan(const ExecutionPlan& plan) -> bool;

  // Strategy implementations
  auto planGreedy(const std::vector<std::unique_ptr<Operator>>& operators,
                  const QueryConstraints& constraints)
      -> std::unique_ptr<ExecutionPlan>;
  auto planDynamic(const std::vector<std::unique_ptr<Operator>>& operators,
                   const QueryConstraints& constraints)
      -> std::unique_ptr<ExecutionPlan>;
  auto planGenetic(const std::vector<std::unique_ptr<Operator>>& operators,
                   const QueryConstraints& constraints)
      -> std::unique_ptr<ExecutionPlan>;
  auto planHeuristic(const std::vector<std::unique_ptr<Operator>>& operators,
                     const QueryConstraints& constraints)
      -> std::unique_ptr<ExecutionPlan>;

  // Utility methods
  auto estimatePlanCost(const ExecutionPlan& plan) -> double;
  auto selectOptimalIndexes(const ExecutionPlan& plan) -> void;
  auto optimizeOperatorOrder(ExecutionPlan& plan) -> void;
  auto analyzeParallelismOpportunities(ExecutionPlan& plan) -> void;

  // Default optimization rules
  auto initializeDefaultRules() -> void;
};

}  // namespace sage_flow