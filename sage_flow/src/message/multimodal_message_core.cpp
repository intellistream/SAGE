#include "message/multimodal_message_core.h"

#include "message/retrieval_context.h"
#include <chrono>
#include <stdexcept>
#include <utility>

namespace sage_flow {

MultiModalMessage::MultiModalMessage(uint64_t uid)
    : uid_(uid), timestamp_(getCurrentTimestamp()) {}

MultiModalMessage::MultiModalMessage(uint64_t uid, ContentType content_type, ContentVariant content)
    : uid_(uid), timestamp_(getCurrentTimestamp()), content_type_(content_type), content_(std::move(content)) {}

MultiModalMessage::MultiModalMessage(MultiModalMessage&& other) noexcept
    : uid_(other.uid_),
      timestamp_(other.timestamp_),
      content_type_(other.content_type_),
      content_(std::move(other.content_)),
      embedding_(std::move(other.embedding_)),
      metadata_(std::move(other.metadata_)),
      retrieval_contexts_(std::move(other.retrieval_contexts_)),
      processing_trace_(std::move(other.processing_trace_)),
      quality_score_(other.quality_score_) {}

auto MultiModalMessage::operator=(MultiModalMessage&& other) noexcept -> MultiModalMessage& {
  if (this != &other) {
    uid_ = other.uid_;
    timestamp_ = other.timestamp_;
    content_type_ = other.content_type_;
    content_ = std::move(other.content_);
    embedding_ = std::move(other.embedding_);
    metadata_ = std::move(other.metadata_);
    retrieval_contexts_ = std::move(other.retrieval_contexts_);
    processing_trace_ = std::move(other.processing_trace_);
    quality_score_ = other.quality_score_;
  }
  return *this;
}

auto MultiModalMessage::getUid() const -> uint64_t {
  return uid_;
}

auto MultiModalMessage::getTimestamp() const -> int64_t {
  return timestamp_;
}

auto MultiModalMessage::getContentType() const -> ContentType {
  return content_type_;
}

auto MultiModalMessage::getContent() const -> const ContentVariant& {
  return content_;
}

auto MultiModalMessage::getEmbedding() const -> const std::optional<VectorData>& {
  return embedding_;
}

auto MultiModalMessage::getMetadata() const -> const MetadataMap& {
  return metadata_;
}

auto MultiModalMessage::getProcessingTrace() const -> const ProcessingTrace& {
  return processing_trace_;
}

auto MultiModalMessage::getQualityScore() const -> std::optional<float> {
  return quality_score_;
}

auto MultiModalMessage::setContent(ContentVariant content) -> void {
  content_ = std::move(content);
}

auto MultiModalMessage::setContentType(ContentType content_type) -> void {
  content_type_ = content_type;
}

auto MultiModalMessage::setEmbedding(VectorData&& embedding) -> void {
  embedding_ = std::move(embedding);
}

auto MultiModalMessage::setMetadata(std::string key, std::string value) -> void {
  metadata_[std::move(key)] = std::move(value);
}

auto MultiModalMessage::addProcessingStep(std::string step) -> void {
  processing_trace_.push_back(std::move(step));
}

auto MultiModalMessage::setQualityScore(float score) -> void {
  quality_score_ = score;
}

auto MultiModalMessage::addRetrievalContext(std::unique_ptr<RetrievalContext> context) -> void {
  if (context) {
    retrieval_contexts_.push_back(std::move(context));
  }
}

auto MultiModalMessage::getRetrievalContexts() const -> const RetrievalContextList& {
  return retrieval_contexts_;
}

auto MultiModalMessage::hasEmbedding() const -> bool {
  return embedding_.has_value();
}

auto MultiModalMessage::isTextContent() const -> bool {
  return std::holds_alternative<std::string>(content_);
}

auto MultiModalMessage::isBinaryContent() const -> bool {
  return std::holds_alternative<std::vector<uint8_t>>(content_);
}

auto MultiModalMessage::getContentAsString() const -> std::string {
  if (isTextContent()) {
    return std::get<std::string>(content_);
  }
  throw std::runtime_error("Content is not text type");
}

auto MultiModalMessage::getContentAsBinary() const -> const std::vector<uint8_t>& {
  if (isBinaryContent()) {
    return std::get<std::vector<uint8_t>>(content_);
  }
  throw std::runtime_error("Content is not binary type");
}

auto MultiModalMessage::serialize() const -> std::vector<uint8_t> {
  // Placeholder implementation - would use Protocol Buffers in production
  std::vector<uint8_t> result;
  // TODO(xinyan): Implement proper serialization
  return result;
}

auto MultiModalMessage::deserialize(const std::vector<uint8_t>& data) -> std::unique_ptr<MultiModalMessage> {
  // Placeholder implementation - would use Protocol Buffers in production
  (void)data; // Suppress unused parameter warning
  // TODO(xinyan): Implement proper deserialization
  return std::make_unique<MultiModalMessage>(0);
}

auto MultiModalMessage::getCurrentTimestamp() const -> int64_t {
  return std::chrono::duration_cast<std::chrono::milliseconds>(
      std::chrono::system_clock::now().time_since_epoch()).count();
}

auto MultiModalMessage::validateContent() const -> bool {
  // Basic validation - can be extended
  return !std::holds_alternative<std::string>(content_) || 
         !std::get<std::string>(content_).empty();
}

// Utility functions
auto CreateTextMessage(uint64_t uid, std::string text) -> std::unique_ptr<MultiModalMessage> {
  return std::make_unique<MultiModalMessage>(uid, ContentType::kText, std::move(text));
}

auto CreateBinaryMessage(uint64_t uid, std::vector<uint8_t> data) -> std::unique_ptr<MultiModalMessage> {
  return std::make_unique<MultiModalMessage>(uid, ContentType::kBinary, std::move(data));
}

}  // namespace sage_flow
