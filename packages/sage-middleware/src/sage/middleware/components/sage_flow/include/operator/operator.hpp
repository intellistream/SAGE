#pragma once

/**
 * @file operator.h
 * @brief Convenience header that includes all operator-related classes
 *
 * This file has been refactored to follow the "one class per file" principle.
 * All classes have been moved to separate header files for better
 * maintainability.
 *
 * Provides the complete operator framework for SAGE flow processing pipeline.
 */

// Core operator types and enums
#include "operator_types.hpp"

// Response container
#include "response.hpp"

// Base operator class
#include "base_operator.hpp"

// Specific operator implementations
#include "aggregate_operator.hpp"
#include "base_operator.hpp"
#include "filter_operator.hpp"
#include "join_operator.hpp"
#include "map_operator.hpp"
#include "sink_operator.hpp"
#include "source_operator.hpp"  // NOLINT
#include "topk_operator.hpp"
#include "window_operator.hpp"

namespace sage_flow {

/**
 * @brief Factory function to create operators based on type
 * @param type Operator type to create
 * @param name Name for the operator
 * @return Unique pointer to created operator
 */
auto CreateOperator(OperatorType type,
                    const std::string& name) -> std::unique_ptr<BaseOperator>;

/**
 * @brief Factory function to create TopK operator
 * @param name Name for the operator
 * @param k Number of top elements to maintain
 * @return Unique pointer to TopK operator
 */
auto CreateTopKOperator(const std::string& name,
                        size_t k) -> std::unique_ptr<TopKOperator>;

/**
 * @brief Factory function to create Window operator
 * @param name Name for the operator
 * @param window_type Type of window (tumbling, sliding, session)
 * @return Unique pointer to Window operator
 */
auto CreateWindowOperator(const std::string& name,
                          WindowOperator::WindowType window_type)
    -> std::unique_ptr<WindowOperator>;

}  // namespace sage_flow
