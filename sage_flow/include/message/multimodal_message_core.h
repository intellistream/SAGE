#pragma once

#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <unordered_map>
#include <variant>
#include <vector>

#include "content_type.h"
#include "vector_data.h"
#include "retrieval_context.h"

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
  
  // Constructors
  explicit MultiModalMessage(uint64_t uid);
  MultiModalMessage(uint64_t uid, ContentType content_type, ContentVariant content);

  // Prevent copying
  MultiModalMessage(const MultiModalMessage&) = delete;
  auto operator=(const MultiModalMessage&) -> MultiModalMessage& = delete;
  
  // Move semantics
  MultiModalMessage(MultiModalMessage&& other) noexcept;
  auto operator=(MultiModalMessage&& other) noexcept -> MultiModalMessage&;
  
  // Accessors
  auto getUid() const -> uint64_t;
  auto getTimestamp() const -> int64_t;
  auto getContentType() const -> ContentType;
  auto getContent() const -> const ContentVariant&;
  auto getEmbedding() const -> const std::optional<VectorData>&;
  auto getMetadata() const -> const MetadataMap&;
  auto getProcessingTrace() const -> const ProcessingTrace&;
  auto getQualityScore() const -> std::optional<float>;
  
  // Mutators
  auto setContent(ContentVariant content) -> void;
  auto setContentType(ContentType content_type) -> void;
  auto setEmbedding(VectorData&& embedding) -> void;
  auto setMetadata(std::string key, std::string value) -> void;
  auto addProcessingStep(std::string step) -> void;
  auto setQualityScore(float score) -> void;
  
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
  static auto deserialize(const std::vector<uint8_t>& data) -> std::unique_ptr<MultiModalMessage>;
  
 private:
  // Core data members (following Google C++ Style Guide naming)
  uint64_t uid_;
  int64_t timestamp_;
  ContentType content_type_ = ContentType::kText;
  ContentVariant content_;
  std::optional<VectorData> embedding_;
  MetadataMap metadata_;
  RetrievalContextList retrieval_contexts_;
  ProcessingTrace processing_trace_;
  std::optional<float> quality_score_;
  
  // Helper methods
  auto getCurrentTimestamp() const -> int64_t;
  auto validateContent() const -> bool;
};

// Utility functions
auto CreateTextMessage(uint64_t uid, std::string text) -> std::unique_ptr<MultiModalMessage>;
auto CreateBinaryMessage(uint64_t uid, std::vector<uint8_t> data) -> std::unique_ptr<MultiModalMessage>;

}  // namespace sage_flow
