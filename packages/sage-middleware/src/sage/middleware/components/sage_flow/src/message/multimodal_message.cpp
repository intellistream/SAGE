#include "../../include/message/multimodal_message.hpp"

#include <algorithm>
#include <chrono>
#include <stdexcept>

namespace sage_flow {

// Constructor implementations
MultiModalMessage::MultiModalMessage(uint64_t uid)
    : uid_(uid), timestamp_(getCurrentTimestamp()) {}

MultiModalMessage::MultiModalMessage(uint64_t uid, ContentType content_type,
                                     ContentVariant content)
    : uid_(uid),
      timestamp_(getCurrentTimestamp()),
      content_type_(content_type),
      content_(std::move(content)) {
  validateContent();
}

MultiModalMessage::MultiModalMessage(const std::string& sage_uid,
                                     ContentType content_type,
                                     ContentVariant content)
    : sage_uid_(sage_uid),
      timestamp_(getCurrentTimestamp()),
      content_type_(content_type),
      content_(std::move(content)) {
  // Convert sage_uid to uid using hash
  uid_ = std::hash<std::string>{}(sage_uid);
  validateContent();
}

// Move constructor
MultiModalMessage::MultiModalMessage(MultiModalMessage&& other) noexcept
    : uid_(other.uid_),
      sage_uid_(std::move(other.sage_uid_)),
      timestamp_(other.timestamp_),
      content_type_(other.content_type_),
      content_(std::move(other.content_)),
      embedding_(std::move(other.embedding_)),
      metadata_(std::move(other.metadata_)),
      retrieval_contexts_(std::move(other.retrieval_contexts_)),
      processing_trace_(std::move(other.processing_trace_)),
      quality_score_(other.quality_score_),
      source_(std::move(other.source_)),
      tags_(std::move(other.tags_)),
      custom_fields_(std::move(other.custom_fields_)),
      processed_(other.processed_),
      processed_timestamp_(other.processed_timestamp_) {}

// Move assignment operator
auto MultiModalMessage::operator=(MultiModalMessage&& other) noexcept
    -> MultiModalMessage& {
  if (this != &other) {
    uid_ = other.uid_;
    sage_uid_ = std::move(other.sage_uid_);
    timestamp_ = other.timestamp_;
    content_type_ = other.content_type_;
    content_ = std::move(other.content_);
    embedding_ = std::move(other.embedding_);
    metadata_ = std::move(other.metadata_);
    retrieval_contexts_ = std::move(other.retrieval_contexts_);
    processing_trace_ = std::move(other.processing_trace_);
    quality_score_ = other.quality_score_;
    source_ = std::move(other.source_);
    tags_ = std::move(other.tags_);
    custom_fields_ = std::move(other.custom_fields_);
    processed_ = other.processed_;
    processed_timestamp_ = other.processed_timestamp_;
  }
  return *this;
}

// Core accessors
auto MultiModalMessage::getUid() const -> uint64_t { return uid_; }

auto MultiModalMessage::getSageUid() const -> const std::string& {
  return sage_uid_;
}

auto MultiModalMessage::getTimestamp() const -> int64_t { return timestamp_; }

auto MultiModalMessage::getContentType() const -> ContentType {
  return content_type_;
}

auto MultiModalMessage::getContent() const -> const ContentVariant& {
  return content_;
}

auto MultiModalMessage::getEmbedding() const
    -> const std::optional<VectorData>& {
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

// SAGE compatible accessors
auto MultiModalMessage::getSource() const -> const std::string& {
  return source_;
}

auto MultiModalMessage::getTags() const -> const TagList& { return tags_; }

auto MultiModalMessage::getCustomFields() const -> const CustomFieldMap& {
  return custom_fields_;
}

auto MultiModalMessage::isProcessed() const -> bool { return processed_; }

auto MultiModalMessage::getProcessedTimestamp() const
    -> std::optional<int64_t> {
  return processed_timestamp_;
}

// Core mutators
auto MultiModalMessage::setContent(ContentVariant content) -> void {
  content_ = std::move(content);
  validateContent();
}

auto MultiModalMessage::setContentType(ContentType content_type) -> void {
  content_type_ = content_type;
}

auto MultiModalMessage::setEmbedding(VectorData&& embedding) -> void {
  embedding_ = std::move(embedding);
}

auto MultiModalMessage::setMetadata(std::string key,
                                    std::string value) -> void {
  metadata_[std::move(key)] = std::move(value);
}

auto MultiModalMessage::addProcessingStep(std::string step) -> void {
  processing_trace_.push_back(std::move(step));
}

auto MultiModalMessage::setQualityScore(float score) -> void {
  quality_score_ = score;
}

// SAGE compatible mutators
auto MultiModalMessage::setSource(const std::string& source) -> void {
  source_ = source;
}

auto MultiModalMessage::addTag(const std::string& tag) -> void {
  if (std::find(tags_.begin(), tags_.end(), tag) == tags_.end()) {
    tags_.push_back(tag);
  }
}

auto MultiModalMessage::removeTag(const std::string& tag) -> void {
  tags_.erase(std::remove(tags_.begin(), tags_.end(), tag), tags_.end());
}

auto MultiModalMessage::hasTag(const std::string& tag) const -> bool {
  return std::find(tags_.begin(), tags_.end(), tag) != tags_.end();
}

auto MultiModalMessage::setCustomField(const std::string& key,
                                       const std::string& value) -> void {
  custom_fields_[key] = value;
}

auto MultiModalMessage::getCustomField(const std::string& key,
                                       const std::string& default_value) const
    -> std::string {
  auto it = custom_fields_.find(key);
  return (it != custom_fields_.end()) ? it->second : default_value;
}

auto MultiModalMessage::removeCustomField(const std::string& key) -> void {
  custom_fields_.erase(key);
}

auto MultiModalMessage::setProcessed(bool processed) -> void {
  processed_ = processed;
  if (processed) {
    updateProcessedTimestamp();
  }
}

// Utility methods
auto MultiModalMessage::hasEmbedding() const -> bool {
  return embedding_.has_value();
}

auto MultiModalMessage::isTextContent() const -> bool {
  return content_type_ == ContentType::kText &&
         std::holds_alternative<std::string>(content_);
}

auto MultiModalMessage::isBinaryContent() const -> bool {
  return std::holds_alternative<std::vector<uint8_t>>(content_);
}

auto MultiModalMessage::getContentAsString() const -> std::string {
  if (std::holds_alternative<std::string>(content_)) {
    return std::get<std::string>(content_);
  }
  return std::string();  // Return empty string for non-text content
}

auto MultiModalMessage::getContentAsBinary() const
    -> const std::vector<uint8_t>& {
  if (std::holds_alternative<std::vector<uint8_t>>(content_)) {
    return std::get<std::vector<uint8_t>>(content_);
  }
  static const std::vector<uint8_t> empty_vector;
  return empty_vector;
}

// Retrieval context management
auto MultiModalMessage::addRetrievalContext(
    std::unique_ptr<RetrievalContext> context) -> void {
  retrieval_contexts_.push_back(std::move(context));
}

auto MultiModalMessage::getRetrievalContexts() const
    -> const RetrievalContextList& {
  return retrieval_contexts_;
}

// Serialization support (simplified implementations)
auto MultiModalMessage::serialize() const -> std::vector<uint8_t> {
  // Simplified serialization - in practice, you'd use Protocol Buffers or
  // similar
  std::vector<uint8_t> data;
  // Implementation would serialize all member variables
  return data;
}

auto MultiModalMessage::deserialize(const std::vector<uint8_t>& data)
    -> std::unique_ptr<MultiModalMessage> {
  // Simplified deserialization
  return std::make_unique<MultiModalMessage>(0);
}

auto MultiModalMessage::serializeToProtobuf() const -> std::vector<uint8_t> {
  // Placeholder for Protocol Buffers serialization
  return serialize();
}

auto MultiModalMessage::deserializeFromProtobuf(
    const std::vector<uint8_t>& data) -> std::unique_ptr<MultiModalMessage> {
  return deserialize(data);
}

auto MultiModalMessage::serializeToJson() const -> std::string {
  // Placeholder for JSON serialization
  return "{}";
}

auto MultiModalMessage::deserializeFromJson(const std::string& json)
    -> std::unique_ptr<MultiModalMessage> {
  return std::make_unique<MultiModalMessage>(0);
}

// SAGE compatibility methods
auto MultiModalMessage::clone() const -> std::unique_ptr<MultiModalMessage> {
  auto cloned =
      std::make_unique<MultiModalMessage>(uid_, content_type_, content_);
  cloned->sage_uid_ = sage_uid_;
  cloned->timestamp_ = timestamp_;
  cloned->embedding_ = embedding_;
  cloned->metadata_ = metadata_;
  cloned->processing_trace_ = processing_trace_;
  cloned->quality_score_ = quality_score_;
  cloned->source_ = source_;
  cloned->tags_ = tags_;
  cloned->custom_fields_ = custom_fields_;
  cloned->processed_ = processed_;
  cloned->processed_timestamp_ = processed_timestamp_;

  // Clone retrieval contexts (simplified - just copy pointers for now)
  for (const auto& context : retrieval_contexts_) {
    if (context) {
      // For now, we'll create a new context with the same data
      auto new_context = std::make_unique<RetrievalContext>(
          context->getSource(), context->getSimilarityScore());
      // Copy metadata
      for (const auto& [key, value] : context->getMetadata()) {
        new_context->setMetadata(key, value);
      }
      cloned->retrieval_contexts_.push_back(std::move(new_context));
    }
  }

  return cloned;
}

// SageMessage conversion methods removed to avoid compilation issues

// Private helper methods
auto MultiModalMessage::getCurrentTimestamp() const -> int64_t {
  return std::chrono::duration_cast<std::chrono::milliseconds>(
             std::chrono::system_clock::now().time_since_epoch())
      .count();
}

auto MultiModalMessage::validateContent() const -> bool {
  // Basic validation - ensure content type matches content variant
  switch (content_type_) {
    case ContentType::kText:
      return std::holds_alternative<std::string>(content_);
    case ContentType::kImage:
    case ContentType::kAudio:
    case ContentType::kVideo:
    case ContentType::kBinary:
      return std::holds_alternative<std::vector<uint8_t>>(content_);
    default:
      return true;  // Allow other types for now
  }
}

auto MultiModalMessage::generateSageUid() const -> std::string {
  return std::to_string(uid_);
}

auto MultiModalMessage::updateProcessedTimestamp() -> void {
  processed_timestamp_ = getCurrentTimestamp();
}

}  // namespace sage_flow
