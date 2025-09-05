#pragma once

/**
 * @file multimodal_message.h
 * @brief Convenience header that includes all multimodal message related
 * classes
 *
 * This file has been refactored to follow the "one class per file" principle.
 * All classes have been moved to separate header files for better
 * maintainability.
 *
 * Original file contained multiple classes and has been split into:
 * - content_type.h: ContentType enum
 * - vector_data.h: VectorData class for vector operations
 * - retrieval_context.h: RetrievalContext class for RAG operations
 * - multimodal_message.hpp: MultiModalMessage main class
 */

// Core content type definitions
#include "content_type.hpp"

// Vector data handling
#include "vector_data.hpp"

// Retrieval context for RAG operations
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <unordered_map>
#include <variant>
#include <vector>

#include "content_type.hpp"
#include "retrieval_context.hpp"
#include "vector_data.hpp"

namespace sage_flow {

/**
 * @brief Multi-modal message container for SAGE flow processing
 *
 * This class represents the core data structure for processing various types
 * of content (text, image, audio, etc.) through the SAGE flow pipeline.
 * It maintains compatibility with sage_core Packet protocol and provides
 * efficient data handling for C++ runtime performance.
 */
class MultiModalMessage final {
public:
  using ContentVariant = std::variant<std::string, std::vector<uint8_t>>;
  using MetadataMap = std::unordered_map<std::string, std::string>;
  using ProcessingTrace = std::vector<std::string>;
  using RetrievalContextList = std::vector<std::unique_ptr<RetrievalContext>>;
  using TagList = std::vector<std::string>;
  using CustomFieldMap = std::unordered_map<std::string, std::string>;

  // Constructors
  explicit MultiModalMessage(uint64_t uid);
  MultiModalMessage(uint64_t uid, ContentType content_type,
                    ContentVariant content);

  // SAGE 兼容构造函数
  MultiModalMessage(const std::string& sage_uid, ContentType content_type,
                    ContentVariant content);

  // Prevent copying
  MultiModalMessage(const MultiModalMessage&) = delete;
  auto operator=(const MultiModalMessage&) -> MultiModalMessage& = delete;

  // Move semantics
  MultiModalMessage(MultiModalMessage&& other) noexcept;
  auto operator=(MultiModalMessage&& other) noexcept -> MultiModalMessage&;

  // Core accessors
  auto getUid() const -> uint64_t;
  auto getSageUid() const -> const std::string&;  // SAGE 兼容的字符串 UID
  auto getTimestamp() const -> int64_t;
  auto getContentType() const -> ContentType;
  auto getContent() const -> const ContentVariant&;
  auto getEmbedding() const -> const std::optional<VectorData>&;
  auto getMetadata() const -> const MetadataMap&;
  auto getProcessingTrace() const -> const ProcessingTrace&;
  auto getQualityScore() const -> std::optional<float>;

  // SAGE 兼容访问器
  auto getSource() const -> const std::string&;
  auto getTags() const -> const TagList&;
  auto getCustomFields() const -> const CustomFieldMap&;
  auto isProcessed() const -> bool;
  auto getProcessedTimestamp() const -> std::optional<int64_t>;

  // Core mutators
  auto setContent(ContentVariant content) -> void;
  auto setContentType(ContentType content_type) -> void;
  auto setEmbedding(VectorData&& embedding) -> void;
  auto setMetadata(std::string key, std::string value) -> void;
  auto addProcessingStep(std::string step) -> void;
  auto setQualityScore(float score) -> void;

  // SAGE 兼容修改器
  auto setSource(const std::string& source) -> void;
  auto addTag(const std::string& tag) -> void;
  auto removeTag(const std::string& tag) -> void;
  auto hasTag(const std::string& tag) const -> bool;
  auto setCustomField(const std::string& key, const std::string& value) -> void;
  auto getCustomField(const std::string& key, const std::string& default_value =
                                                  "") const -> std::string;
  auto removeCustomField(const std::string& key) -> void;
  auto setProcessed(bool processed) -> void;

  // Retrieval context management
  auto addRetrievalContext(std::unique_ptr<RetrievalContext> context) -> void;
  auto getRetrievalContexts() const -> const RetrievalContextList&;

  // Utility methods
  auto hasEmbedding() const -> bool;
  auto isTextContent() const -> bool;
  auto isBinaryContent() const -> bool;
  auto getContentAsString() const -> std::string;
  auto getContentAsBinary() const -> const std::vector<uint8_t>&;

  // Serialization support (for Protocol Buffers integration)
  auto serialize() const -> std::vector<uint8_t>;
  static auto deserialize(const std::vector<uint8_t>& data)
      -> std::unique_ptr<MultiModalMessage>;

  // SAGE 兼容性方法
  auto clone() const -> std::unique_ptr<MultiModalMessage>;
  // Note: SageMessage conversion methods removed to avoid compilation issues

  // 高级序列化支持
  auto serializeToProtobuf() const -> std::vector<uint8_t>;
  static auto deserializeFromProtobuf(const std::vector<uint8_t>& data)
      -> std::unique_ptr<MultiModalMessage>;
  auto serializeToJson() const -> std::string;
  static auto deserializeFromJson(const std::string& json)
      -> std::unique_ptr<MultiModalMessage>;

private:
  // Core data members (following Google C++ Style Guide naming)
  uint64_t uid_;
  std::string sage_uid_;  // SAGE 兼容的字符串 UID
  int64_t timestamp_;
  ContentType content_type_ = ContentType::kText;
  ContentVariant content_;
  std::optional<VectorData> embedding_;
  MetadataMap metadata_;
  RetrievalContextList retrieval_contexts_;
  ProcessingTrace processing_trace_;
  std::optional<float> quality_score_;

  // SAGE 兼容性字段
  std::string source_ = "unknown";
  TagList tags_;
  CustomFieldMap custom_fields_;
  bool processed_ = false;
  std::optional<int64_t> processed_timestamp_;

  // Helper methods
  auto getCurrentTimestamp() const -> int64_t;
  auto validateContent() const -> bool;
  auto generateSageUid() const -> std::string;
  auto updateProcessedTimestamp() -> void;
};

}  // namespace sage_flow
