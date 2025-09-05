#pragma once

#include <cstdint>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

namespace sage_flow {

class ExecutionPlan;
class PlanNode;

/**
 * @brief Index type enumeration
 */
enum class IndexType : uint8_t {
  kBTree,       // B-Tree index for range queries
  kHash,        // Hash index for equality queries
  kBitmap,      // Bitmap index for low cardinality
  kHNSW,        // HNSW for vector similarity
  kIVF,         // IVF for vector search
  kBruteForce,  // Brute force for small datasets
  kCustom       // Custom index implementation
};

/**
 * @brief Index usage statistics
 */
struct IndexUsageStats {
  uint64_t total_queries{0};
  uint64_t index_hits{0};
  uint64_t index_misses{0};
  double average_query_time_ms{0.0};
  double selectivity{1.0};
  size_t memory_usage_mb{0};
};

/**
 * @brief Index metadata and configuration
 */
struct IndexMetadata {
  std::string index_id;
  std::string table_name;
  std::string column_name;
  IndexType index_type;
  size_t estimated_size_mb{0};
  double creation_cost{0.0};
  double maintenance_cost{0.0};
  bool is_clustered{false};
  bool is_unique{false};
  std::unordered_map<std::string, std::string> properties;

  IndexMetadata(std::string id, std::string table, std::string column,
                IndexType type)
      : index_id(std::move(id)),
        table_name(std::move(table)),
        column_name(std::move(column)),
        index_type(type) {}
};

/**
 * @brief Index recommendation with cost analysis
 */
struct IndexRecommendation {
  IndexMetadata metadata;
  double benefit_score{0.0};
  double creation_cost{0.0};
  double maintenance_cost{0.0};
  double storage_cost{0.0};
  std::vector<std::string> affected_queries;
  std::string recommendation_reason;

  explicit IndexRecommendation(IndexMetadata meta)
      : metadata(std::move(meta)) {}
};

/**
 * @brief Index selector for candyFlow integration
 *
 * Implements intelligent index selection and recommendation for SAGE flow
 * operations. This is a key component of the candyFlow streaming system,
 * providing:
 * - Automatic index selection for query optimization
 * - Index usage analysis and recommendations
 * - Cost-based index evaluation
 * - Dynamic index creation and maintenance
 *
 * Based on candyFlow's IndexSelector design with SAGE integration.
 */
class IndexSelector {
public:
  /**
   * @brief Construct an index selector
   */
  explicit IndexSelector();

  // Prevent copying
  IndexSelector(const IndexSelector&) = delete;
  auto operator=(const IndexSelector&) -> IndexSelector& = delete;

  // Allow moving
  IndexSelector(IndexSelector&&) = default;
  auto operator=(IndexSelector&&) -> IndexSelector& = default;

  /**
   * @brief Select optimal indexes for an execution plan
   * @param plan Execution plan to optimize
   * @return Vector of recommended indexes
   */
  auto selectIndexesForPlan(const ExecutionPlan& plan)
      -> std::vector<IndexRecommendation>;

  /**
   * @brief Select optimal index for a specific operator
   * @param node Plan node containing the operator
   * @param query_patterns Expected query patterns
   * @return Best index recommendation
   */
  auto selectIndexForOperator(const PlanNode& node,
                              const std::vector<std::string>& query_patterns)
      -> std::unique_ptr<IndexRecommendation>;

  /**
   * @brief Analyze index usage and provide recommendations
   * @param plan Execution plan to analyze
   * @return Analysis results and recommendations
   */
  auto analyzeIndexUsage(const ExecutionPlan& plan)
      -> std::vector<IndexRecommendation>;

  // Index metadata management
  auto registerIndex(const IndexMetadata& metadata) -> void;
  auto unregisterIndex(const std::string& index_id) -> void;
  auto getIndexMetadata(const std::string& index_id) const
      -> const IndexMetadata*;
  auto getAllIndexes() const -> std::vector<const IndexMetadata*>;

  // Index statistics tracking
  auto recordIndexUsage(const std::string& index_id,
                        const IndexUsageStats& stats) -> void;
  auto getIndexUsageStats(const std::string& index_id) const
      -> const IndexUsageStats*;
  auto updateIndexStats(const std::string& index_id, uint64_t queries,
                        double avg_time, double selectivity) -> void;

  // Configuration
  auto setMaxIndexesPerTable(size_t max_indexes) -> void;
  auto setIndexCreationThreshold(double threshold) -> void;
  auto setIndexMaintenanceCostWeight(double weight) -> void;
  auto enableAutomaticIndexCreation(bool enable) -> void;

  // Performance monitoring
  auto getIndexEfficiency() const -> double;
  auto getRecommendationAccuracy() const -> double;
  auto getTotalIndexes() const -> size_t;
  auto getActiveIndexes() const -> size_t;

private:
  // Index registry
  std::unordered_map<std::string, IndexMetadata> registered_indexes_;
  std::unordered_map<std::string, IndexUsageStats> index_stats_;

  // Configuration parameters
  size_t max_indexes_per_table_;
  double index_creation_threshold_;
  double maintenance_cost_weight_;
  bool automatic_creation_enabled_;

  // Performance tracking
  mutable uint64_t recommendation_count_;
  mutable double total_accuracy_;

  // Internal analysis methods
  auto analyzeFilterOperator(const PlanNode& node)
      -> std::vector<IndexRecommendation>;
  auto analyzeJoinOperator(const PlanNode& node)
      -> std::vector<IndexRecommendation>;
  auto analyzeAggregateOperator(const PlanNode& node)
      -> std::vector<IndexRecommendation>;
  auto analyzeWindowOperator(const PlanNode& node)
      -> std::vector<IndexRecommendation>;
  auto analyzeSortOperator(const PlanNode& node)
      -> std::vector<IndexRecommendation>;

  // Index type selection
  auto selectIndexType(const std::string& column_type,
                       const std::vector<std::string>& query_patterns)
      -> IndexType;
  auto estimateIndexBenefit(const IndexMetadata& metadata,
                            const PlanNode& node) -> double;
  auto estimateIndexCost(const IndexMetadata& metadata) -> double;

  // Utility methods
  auto generateIndexId(const std::string& table,
                       const std::string& column) -> std::string;
  auto isIndexApplicable(const IndexMetadata& metadata,
                         const PlanNode& node) -> bool;
  auto calculateIndexSelectivity(const IndexMetadata& metadata) -> double;
  auto mergeRecommendations(std::vector<IndexRecommendation> recommendations)
      -> std::vector<IndexRecommendation>;

  // Cost analysis
  auto calculateCreationCost(IndexType type, size_t data_size) -> double;
  auto calculateMaintenanceCost(IndexType type,
                                double update_frequency) -> double;
  auto calculateStorageCost(IndexType type, size_t estimated_size) -> double;
  auto calculateBenefitScore(const IndexMetadata& metadata,
                             const std::vector<std::string>& queries) -> double;

  // Default configurations
  auto initializeDefaultConfiguration() -> void;
  auto getDefaultIndexType(const std::string& operator_type) -> IndexType;
};

}  // namespace sage_flow