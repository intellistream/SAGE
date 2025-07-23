#pragma once

#include <cstdint>

namespace sage_flow {

/**
 * @brief Operator types in SAGE flow processing pipeline
 */
enum class OperatorType : std::uint8_t {
  kNone,
  kSource,
  kMap,
  kFilter, 
  kJoin,
  kAggregate,
  kSink,
  kTopK,
  kWindow,
  kITopK,
  kOutput
};

}  // namespace sage_flow
