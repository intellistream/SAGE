#pragma once

#include <string>
#include <unordered_map>

namespace sage_flow {

/**
 * @brief Retrieval context for RAG operations
 */
class RetrievalContext final {
 public:
  explicit RetrievalContext(std::string source, float similarity_score);

  // Prevent copying
  RetrievalContext(const RetrievalContext&) = delete;
  auto operator=(const RetrievalContext&) -> RetrievalContext& = delete;

  // Allow moving
  RetrievalContext(RetrievalContext&&) = default;
  auto operator=(RetrievalContext&&) -> RetrievalContext& = default;
  
  auto getSource() const -> const std::string&;
  auto getSimilarityScore() const -> float;
  auto getMetadata() const -> const std::unordered_map<std::string, std::string>&;
  auto setMetadata(std::string key, std::string value) -> void;
  
 private:
  std::string source_;
  float similarity_score_;
  std::unordered_map<std::string, std::string> metadata_;
};

}  // namespace sage_flow
