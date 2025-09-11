#include "message/multimodal_message.hpp"

namespace sage_flow {

MultiModalMessage::MultiModalMessage() = default;

MultiModalMessage::~MultiModalMessage() = default;

std::unique_ptr<MultiModalMessage> MultiModalMessage::clone() const {
  return std::make_unique<MultiModalMessage>(*this);
}

std::string MultiModalMessage::getContent() const {
  return content_;
}

void MultiModalMessage::setContent(const std::string& content) {
  content_ = content;
}

std::string MultiModalMessage::getType() const {
  return type_;
}

void MultiModalMessage::setType(const std::string& type) {
  type_ = type;
}

}  // namespace sage_flow
