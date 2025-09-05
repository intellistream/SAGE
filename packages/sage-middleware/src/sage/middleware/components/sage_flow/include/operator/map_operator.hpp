#pragma once

#include <memory>
#include <string>

#include "base_operator.hpp"
#include "../function/map_function.hpp"

namespace sage_flow {

class MultiModalMessage;
class Response;

/**
 * @brief Map operator for one-to-one transformations
 *
 * Applies a transformation function to each input message and produces
 * exactly one output message. Uses composition pattern with MapFunction.
 */
class MapOperator final : public BaseOperator {
public:
  explicit MapOperator(std::string name);

  /**
   * @brief Constructor with MapFunction
   * @param name Operator name
   * @param map_function MapFunction instance to handle processing logic
   */
  MapOperator(std::string name, std::unique_ptr<MapFunction> map_function);

  // Prevent copying
  MapOperator(const MapOperator&) = delete;
  auto operator=(const MapOperator&) -> MapOperator& = delete;

  // Allow moving
  MapOperator(MapOperator&&) = default;
  auto operator=(MapOperator&&) -> MapOperator& = default;

  auto process(Response& input_record, int slot) -> bool override;

  /**
   * @brief Set the map function
   * @param map_function MapFunction instance to handle processing logic
   */
  void setMapFunction(std::unique_ptr<MapFunction> map_function);

  /**
   * @brief Get the map function
   * @return Reference to the contained MapFunction
   */
  auto getMapFunction() -> MapFunction&;

private:
  std::unique_ptr<MapFunction> map_function_;
};

}  // namespace sage_flow
