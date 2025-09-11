#pragma once

#include <cstdint>
#include <string>
#include <vector>
#include <optional>
#include "data_stream/response.hpp"

namespace sage_flow {

enum class FunctionType : std::uint8_t {
  none,
  source,
  map,
  filter,
  sink,
};

template <typename InType, typename OutType>
class BaseFunction {
public:
  explicit BaseFunction(std::string name, FunctionType type);
  virtual ~BaseFunction() = default;

  // Getters and setters
  auto getName() const -> const std::string&;
  auto getType() const -> FunctionType;
  void setName(const std::string& name);
  void setType(FunctionType type);

  // Main execution methods - using references for Function (no memory management)
  virtual std::optional<OutType> execute(const InType& input) = 0;
  virtual void execute_batch(const std::vector<InType>& inputs, std::vector<OutType>& outputs) = 0;

protected:
private:
  std::string name_;
  FunctionType type_ = FunctionType::none;
};

}  // namespace sage_flow
