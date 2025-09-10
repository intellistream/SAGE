#include "../../include/message/retrieval_context.hpp"

#include <memory>

namespace sage_flow {

// Constructor implementation
RetrievalContext::RetrievalContext(std::string source, float similarity_score)
    : source_(std::move(source)), similarity_score_(similarity_score) {}

RetrievalContext::RetrievalContext(const RetrievalContext& other)
   : source_(other.source_), similarity_score_(other.similarity_score_), metadata_(other.metadata_) {}

auto RetrievalContext::operator=(const RetrievalContext& other) -> RetrievalContext& {
 if (this != &other) {
   source_ = other.source_;
   similarity_score_ = other.similarity_score_;
   metadata_ = other.metadata_;
 }
 return *this;
}

// Accessors
auto RetrievalContext::getSource() const -> const std::string& {
  return source_;
}

auto RetrievalContext::getSimilarityScore() const -> float {
  return similarity_score_;
}

auto RetrievalContext::getMetadata() const
    -> const std::unordered_map<std::string, std::string>& {
  return metadata_;
}

// Modifiers
auto RetrievalContext::setMetadata(std::string key, std::string value) -> void {
  metadata_[std::move(key)] = std::move(value);
}

auto RetrievalContext::clone() const -> std::unique_ptr<RetrievalContext> {
  return std::make_unique<RetrievalContext>(*this);
}

}  // namespace sage_flow
