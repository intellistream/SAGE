#pragma once

#include <functional>

#include "base_function.hpp"

namespace sage_flow {

/**
 * @brief Map function type definition
 *
 * Based on candyFlow's MapFunc pattern, adapted for MultiModalMessage
 */
using MapFunc = std::function<void(std::unique_ptr<MultiModalMessage>&)>;

/**
 * @brief Map Function class
 *
 * Performs one-to-one transformations on messages.
 * Based on candyFlow's MapFunction design.
 */
class MapFunction final : public BaseFunction {
public:
  explicit MapFunction(std::string name);
  MapFunction(std::string name, MapFunc map_func);

  ~MapFunction() override = default;

  /**
   * @brief Execute the map function on input messages
   * @param response Input response containing messages to transform
   * @return Response with transformed messages
   */
  using BaseFunction::execute;  // Bring base class overloads into scope
  auto execute(FunctionResponse& response) -> FunctionResponse override;

  /**
   * @brief Set the map function
   * @param map_func Function to apply to each message
   */
  void setMapFunc(MapFunc map_func);

private:
  MapFunc map_func_;
};

}  // namespace sage_flow
