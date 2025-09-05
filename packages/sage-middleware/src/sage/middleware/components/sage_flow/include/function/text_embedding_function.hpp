#pragma once

#include <string>
#include <vector>

#include "base_function.hpp"
#include "function_type.hpp"

namespace sage_flow {

/**
 * @brief Text Embedding Function class
 *
 * Function for generating text embeddings from input text.
 * Supports various embedding models and vectorization techniques.
 */
class TextEmbeddingFunction : public BaseFunction {
public:
  explicit TextEmbeddingFunction(const std::string& name)
      : BaseFunction(name, FunctionType::Map) {}

  ~TextEmbeddingFunction() override = default;

  /**
   * @brief Execute text embedding on input response
   * @param response Input response containing text messages
   * @return Response with text embeddings
   */
  auto execute(FunctionResponse& response) -> FunctionResponse override;

  /**
   * @brief Execute with two inputs (not supported for text embedding)
   * @param left Left input response
   * @param right Right input response
   * @return Processed response
   */
  auto execute(FunctionResponse& left,
               FunctionResponse& right) -> FunctionResponse override;

  /**
   * @brief Set embedding configuration
   * @param config Configuration string for text embedding
   */
  void setConfig(const std::string& config);

  /**
   * @brief Get current embedding configuration
   * @return Configuration string
   */
  auto getConfig() const -> const std::string&;

  /**
   * @brief Set embedding model
   * @param model_name Name of the embedding model to use
   */
  void setModel(const std::string& model_name);

  /**
   * @brief Get current embedding model
   * @return Model name
   */
  auto getModel() const -> const std::string&;

  /**
   * @brief Set embedding dimensions
   * @param dimensions Number of dimensions for embeddings
   */
  void setDimensions(size_t dimensions);

  /**
   * @brief Get embedding dimensions
   * @return Number of dimensions
   */
  auto getDimensions() const -> size_t;

private:
  std::string config_;
  std::string model_name_ = "default";
  size_t dimensions_ = 384;

  /**
   * @brief Generate embedding for text content
   * @param text Input text to embed
   * @return Vector of embedding values
   */
  auto generateEmbedding(const std::string& text) const -> std::vector<float>;
};

}  // namespace sage_flow