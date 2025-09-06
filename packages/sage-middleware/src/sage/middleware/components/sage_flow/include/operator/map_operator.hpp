#pragma once

#include <functional>
#include <memory>
#include <string>
#include <vector>
#include <optional>

#include "base_operator.hpp"
#include "operator/response.hpp"
#include "message/multimodal_message.hpp"

namespace sage_flow {

class MapOperator : public BaseOperator<MultiModalMessage, MultiModalMessage> {
public:
  using MapFunc = std::function<std::shared_ptr<MultiModalMessage>(const std::shared_ptr<MultiModalMessage>&)>;

  explicit MapOperator(std::string name, MapFunc f);
  MapOperator(std::string name, MapFunc f, std::string description);

  // Prevent copying
  MapOperator(const MapOperator&) = delete;
  auto operator=(const MapOperator&) -> MapOperator& = delete;

  // Allow moving
  MapOperator(MapOperator&&) = default;
  auto operator=(MapOperator&&) -> MapOperator& = default;

  auto process(const std::vector<std::shared_ptr<MultiModalMessage>>& input) -> std::optional<Response<MultiModalMessage>> override;

private:
  MapFunc map_func_;
};

}  // namespace sage_flow
