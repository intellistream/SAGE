#pragma once

#include <functional>
#include <memory>
#include <string>
#include <vector>
#include <optional>

#include "base_operator.hpp"
#include "data_stream/response.hpp"

namespace sage_flow {

template <typename InputType, typename OutputType>
class MapOperator : public BaseOperator<InputType, OutputType> {
public:
  using MapFunc = std::function<std::shared_ptr<OutputType>(const std::shared_ptr<InputType>&)>;

  explicit MapOperator(std::string name, MapFunc f);
  MapOperator(std::string name, MapFunc f, std::string description);

  // Prevent copying
  MapOperator(const MapOperator&) = delete;
  auto operator=(const MapOperator&) -> MapOperator& = delete;

  // Allow moving
  MapOperator(MapOperator&&) = default;
  auto operator=(MapOperator&&) -> MapOperator& = default;

  auto process(const std::vector<std::unique_ptr<InputType>>& input) -> std::optional<Response<OutputType>> override;

private:
  MapFunc map_func_;
};

}  // namespace sage_flow
