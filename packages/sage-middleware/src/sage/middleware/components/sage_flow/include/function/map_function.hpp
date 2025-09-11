#pragma once

#include <functional>

#include "base_function.hpp"
#include "data_stream/response.hpp"

namespace sage_flow {

template <typename InType, typename OutType>
class MapFunction final : public BaseFunction<InType, OutType> {
public:
  using MapFunc = std::function<OutType(const InType&)>;
  
  explicit MapFunction(std::string name);
  MapFunction(std::string name, MapFunc map_func);

  virtual ~MapFunction() = default;

  /**
   * @brief Execute the map function on input
   * @param input Input to transform
   * @return Transformed output or nullopt if no transformation
   */
  std::optional<OutType> execute(const InType& input) override;
  void execute_batch(const std::vector<InType>& inputs, std::vector<OutType>& outputs) override;

  /**
   * @brief Set the map function
   * @param map_func Function to apply to each message (no memory management)
   */
  void setMapFunc(MapFunc map_func);

private:
  MapFunc map_func_;
};

}  // namespace sage_flow
