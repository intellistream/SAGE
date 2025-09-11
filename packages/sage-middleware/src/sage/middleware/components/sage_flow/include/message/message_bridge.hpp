#pragma once

#include <memory>
#include "message/multimodal_message.hpp"


namespace sage_flow {

class MessageBridge {
public:
  MessageBridge() = default;
  virtual ~MessageBridge() = default;
  
  virtual void init() = 0;
  virtual void close() = 0;
  virtual void send_message(std::unique_ptr<sage_flow::MultiModalMessage> message) = 0;
  virtual std::unique_ptr<sage_flow::MultiModalMessage> receive_message() = 0;
};

}  // namespace sage_flow