#pragma once

#include <cstdint>

namespace sage_flow {

/**
 * @brief Function type enumeration
 *
 * Based on candyFlow's FunctionType design, adapted for SAGE Flow
 */
enum class FunctionType : std::uint8_t {
  None,
  Source,
  Map,
  Filter,
  Sink,
  Join,
  Aggregate,
  Window,
  TopK,
  ITopK,  // Inverted TopK
  FlatMap,
  KeyBy
};

}  // namespace sage_flow