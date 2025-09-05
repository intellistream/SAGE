#pragma once

/**
 * @file index_operators.h
 * @brief Convenience header that includes all index-related classes
 *
 * This file has been refactored to follow the "one class per file" principle.
 * All classes have been moved to separate header files for better
 * maintainability.
 *
 * Reference: flow_old/include/index/index.h
 */

// Core index types and configuration
#include "index_types.hpp"

// Base index interface
#include "index.hpp"

// Concrete index implementations
#include "brute_force_index.hpp"
#include "hnsw.hpp"
// #include "ivf_index.hpp"  // Placeholder for future IVF index implementation
// #include "vectra_flow_index.hpp"  // Placeholder for future VectraFlow index
// implementation

// Index operators
#include "index_operator.hpp"
#include "knn_operator.hpp"

namespace sage_flow {

/**
 * @brief Factory function to create index based on type
 * @param type Index type to create
 * @param memory_pool Memory pool for allocation
 * @return Unique pointer to created index
 */
auto CreateIndex(IndexType type, std::shared_ptr<MemoryPool> memory_pool)
    -> std::unique_ptr<Index>;

/**
 * @brief Factory function to create KNN operator
 * @param memory_pool Memory pool for allocation
 * @return Unique pointer to KNN operator
 */
auto CreateKnnOperator(std::shared_ptr<MemoryPool> memory_pool)
    -> std::unique_ptr<KnnOperator>;

}  // namespace sage_flow
