#pragma once

#include <memory>
#include <string>
#include <unordered_map>

namespace sage_flow {

/**
 * @brief Retrieval context for RAG operations
 */
class RetrievalContext final {
public:
  explicit RetrievalContext(std::string source, float similarity_score);

// Allow copying
RetrievalContext(const RetrievalContext& other);
auto operator=(const RetrievalContext& other) -> RetrievalContext&;

// Allow moving
RetrievalContext(RetrievalContext&&) = default;
auto operator=(RetrievalContext&&) -> RetrievalContext& = default;

auto clone() const -> std::unique_ptr<RetrievalContext>;

auto getSource() const -> const std::string&;
auto getSimilarityScore() const -> float;
auto getMetadata() const
    -> const std::unordered_map<std::string, std::string>&;
auto setMetadata(std::string key, std::string value) -> void;

private:
  std::string source_;
  float similarity_score_;
  std::unordered_map<std::string, std::string> metadata_;
};

}  // namespace sage_flow
