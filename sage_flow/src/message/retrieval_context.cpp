#include "message/retrieval_context.h"

#include <utility>

namespace sage_flow {

RetrievalContext::RetrievalContext(std::string source, float similarity_score)
    : source_(std::move(source)), similarity_score_(similarity_score) {}

auto RetrievalContext::getSource() const -> const std::string& {
  return source_;
}

auto RetrievalContext::getSimilarityScore() const -> float {
  return similarity_score_;
}

auto RetrievalContext::getMetadata() const -> const std::unordered_map<std::string, std::string>& {
  return metadata_;
}

auto RetrievalContext::setMetadata(std::string key, std::string value) -> void {
  metadata_[std::move(key)] = std::move(value);
}

}  // namespace sage_flow
