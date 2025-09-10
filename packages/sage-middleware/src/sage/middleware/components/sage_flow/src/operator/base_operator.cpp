#include "../../include/operator/base_operator.hpp"

#include "../../include/operator/operator_types.hpp"
#include "../../include/message/multimodal_message.hpp"
#include "../../include/operator/response.hpp"

namespace sage_flow {

// Template implementations
template <typename InputType, typename OutputType>
BaseOperator<InputType, OutputType>::BaseOperator(OperatorType type) : type_(type) {}

template <typename InputType, typename OutputType>
BaseOperator<InputType, OutputType>::BaseOperator(OperatorType type, std::string name)
    : type_(type), name_(std::move(name)) {}

template <typename InputType, typename OutputType>
auto BaseOperator<InputType, OutputType>::open() -> void {
  // Default implementation - do nothing
}

template <typename InputType, typename OutputType>
auto BaseOperator<InputType, OutputType>::process(const InputType& input, Response<OutputType>& output) -> void {
  // Default implementation for Function integration - pass through
  output.addMessage(std::make_shared<OutputType>(input));
}

template <typename InputType, typename OutputType>
auto BaseOperator<InputType, OutputType>::close() -> void {
  // Default implementation - do nothing
}

template <typename InputType, typename OutputType>
auto BaseOperator<InputType, OutputType>::emit(int output_id, Response<OutputType>& output_record) const -> void {
  if (emit_callback_) {
    emit_callback_(output_id, output_record);
  }
}

template <typename InputType, typename OutputType>
auto BaseOperator<InputType, OutputType>::getType() const -> OperatorType { 
  return type_; 
}

template <typename InputType, typename OutputType>
auto BaseOperator<InputType, OutputType>::getName() const -> const std::string& { 
  return name_; 
}

template <typename InputType, typename OutputType>
auto BaseOperator<InputType, OutputType>::setName(std::string name) -> void {
  name_ = std::move(name);
}

template <typename InputType, typename OutputType>
auto BaseOperator<InputType, OutputType>::getProcessedCount() const -> uint64_t {
  return processed_count_;
}

template <typename InputType, typename OutputType>
auto BaseOperator<InputType, OutputType>::getOutputCount() const -> uint64_t { 
  return output_count_; 
}

template <typename InputType, typename OutputType>
auto BaseOperator<InputType, OutputType>::resetCounters() -> void {
  processed_count_ = 0;
  output_count_ = 0;
}

template <typename InputType, typename OutputType>
auto BaseOperator<InputType, OutputType>::incrementProcessedCount() -> void { 
  ++processed_count_; 
}

template <typename InputType, typename OutputType>
auto BaseOperator<InputType, OutputType>::incrementOutputCount() -> void { 
  ++output_count_; 
}

template <typename InputType, typename OutputType>
auto BaseOperator<InputType, OutputType>::setEmitCallback(EmitCallback callback) -> void {
  emit_callback_ = std::move(callback);
}

template <typename InputType, typename OutputType>
auto BaseOperator<InputType, OutputType>::getEmitCallback() const -> const EmitCallback& {
  return emit_callback_;
}

template <typename InputType, typename OutputType>
auto BaseOperator<InputType, OutputType>::createEmptyResponse() -> std::optional<Response<OutputType>> {
  return std::make_optional(Response<OutputType>());
}

}  // namespace sage_flow
