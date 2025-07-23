#pragma once

/**
 * @file index_operators.h
 * @brief Convenience header that includes all index-related classes
 * 
 * This file has been refactored to follow the "one class per file" principle.
 * All classes have been moved to separate header files for better maintainability.
 * 
 * Reference: flow_old/include/index/index.h
 */

// Core index types and configuration
#include "index_types.h"

// Base index interface
#include "index.h"

// Concrete index implementations
#include "brute_force_index.h"
#include "hnsw_index.h"
// #include "ivf_index.h"  // Placeholder for future IVF index implementation
// #include "vectra_flow_index.h"  // Placeholder for future VectraFlow index implementation

// Index operators
#include "index_operator.h"
#include "knn_operator.h"
#include "itopk_operator.h"

namespace sage_flow {

/**
 * @brief Factory function to create index based on type
 * @param type Index type to create
 * @param memory_pool Memory pool for allocation
 * @return Unique pointer to created index
 */
auto CreateIndex(IndexType type, 
                                  std::shared_ptr<MemoryPool> memory_pool) -> std::unique_ptr<Index>;

/**
 * @brief Factory function to create KNN operator
 * @param memory_pool Memory pool for allocation
 * @return Unique pointer to KNN operator
 */
auto CreateKnnOperator(std::shared_ptr<MemoryPool> memory_pool) -> std::unique_ptr<KnnOperator>;

/**
 * @brief Factory function to create Top-K operator
 * @param memory_pool Memory pool for allocation
 * @return Unique pointer to Top-K operator
 */
auto CreateTopKOperator(std::shared_ptr<MemoryPool> memory_pool) -> std::unique_ptr<ITopKOperator>;

}  // namespace sage_flow
