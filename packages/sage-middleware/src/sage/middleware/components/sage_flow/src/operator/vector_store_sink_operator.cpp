#include "operator/vector_store_sink_operator.hpp"

#include "operator/operator_types.hpp"

namespace sage_flow {

VectorStoreSinkOperator::VectorStoreSinkOperator(VectorStoreConfig config)
    : BaseOperator<MultiModalMessage, bool>(OperatorType::kSink, "VectorStoreSink"),
      config_(std::move(config)) {
  batch_messages_.reserve(config_.batch_size_);
}

auto VectorStoreSinkOperator::process(const Response<MultiModalMessage>& input_record,
                                      int slot) -> bool {
  incrementProcessedCount();

  if (input_record.hasMessages()) {
    const auto messages = input_record.getMessages();
    for (const auto& message : messages) {
      if (message && message->hasEmbedding()) {
        batch_messages_.push_back(message.get());

        // Process batch when it reaches the configured size
        if (batch_messages_.size() >= config_.batch_size_) {
          processBatch();
        }
      }
    }
  }

  incrementOutputCount();
  return true;
}

auto VectorStoreSinkOperator::open() -> void {
  // TODO(developer): Initialize connection to sage_memory vector store
  // This would establish connection to the vector database
}

auto VectorStoreSinkOperator::close() -> void {
  // Process any remaining messages in the batch
  if (!batch_messages_.empty()) {
    processBatch();
  }

  // TODO(developer): Close connection to sage_memory vector store
}

auto VectorStoreSinkOperator::processBatch() -> void {
  if (batch_messages_.empty()) {
    return;
  }

  // TODO(developer): Integrate with sage_memory vector store
  // For now, simulate vector storage processing
  for (const auto* message : batch_messages_) {
    if (message != nullptr && message->hasEmbedding()) {
      auto embedding_opt = message->getEmbedding();
      if (embedding_opt.has_value()) {
        // Simulate vector storage operation
        message_count_++;
      }
    }
  }

  batch_messages_.clear();
}

// Factory function implementation
auto CreateVectorStoreSink(const std::string& collection_name,
                           size_t batch_size, bool update_index)
    -> std::unique_ptr<VectorStoreSinkOperator> {
  VectorStoreConfig config;
  config.collection_name_ = collection_name;
  config.batch_size_ = batch_size;
  config.update_index_ = update_index;

  return std::make_unique<VectorStoreSinkOperator>(config);
}

}  // namespace sage_flow
