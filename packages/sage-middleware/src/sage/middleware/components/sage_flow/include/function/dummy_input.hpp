#pragma once

namespace sage_flow {

/**
 * @brief Dummy input type for source functions
 *
 * Source functions don't require input, so we use this empty struct
 * as the InType parameter for BaseFunction<void, OutType>
 */
struct DummyInput {};

}  // namespace sage_flow