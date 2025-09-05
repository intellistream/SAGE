#include "function/text_embedding_function.hpp"

#include <algorithm>
#include <cmath>
#include <iostream>
#include <random>
#include <sstream>

namespace sage_flow {

auto TextEmbeddingFunction::execute(FunctionResponse& response)
    -> FunctionResponse {
  FunctionResponse output_response;

  // Process each message in the response
  for (auto& message : response.getMessages()) {
    if (!message) continue;

    // Extract text content from message
    std::string text_content;
    if (message->isTextContent()) {
      text_content = message->getContentAsString();
    } else {
      // Skip non-text content
      output_response.addMessage(std::move(message));
      continue;
    }

    if (text_content.empty()) {
      output_response.addMessage(std::move(message));
      continue;
    }

    try {
      // Generate mock embedding
      std::vector<float> embedding = generateEmbedding(text_content);

      // Create new message with embedding data
      auto output_message = std::make_unique<MultiModalMessage>(
          message->getUid(), ContentType::kText, text_content);

      // Store embedding as metadata (simplified implementation)
      std::ostringstream embedding_str;
      for (size_t i = 0; i < embedding.size(); ++i) {
        if (i > 0) embedding_str << ",";
        embedding_str << embedding[i];
      }
      output_message->setMetadata("embedding", embedding_str.str());
      output_message->setMetadata("embedding_dim", std::to_string(dimensions_));
      output_message->setMetadata("model", model_name_);

      // Copy original metadata
      for (const auto& [key, value] : message->getMetadata()) {
        output_message->setMetadata(key, value);
      }

      // Add processing step
      output_message->addProcessingStep("TextEmbedding");

      output_response.addMessage(std::move(output_message));

    } catch (const std::exception& e) {
      std::cerr << "Error generating embedding: " << e.what() << std::endl;
      // Add original message on error
      output_response.addMessage(std::move(message));
    }
  }

  return output_response;
}

auto TextEmbeddingFunction::execute(
    FunctionResponse& left, FunctionResponse& right) -> FunctionResponse {
  // For text embedding, we only process the left input
  return execute(left);
}

void TextEmbeddingFunction::setConfig(const std::string& config) {
  config_ = config;
}

auto TextEmbeddingFunction::getConfig() const -> const std::string& {
  return config_;
}

void TextEmbeddingFunction::setModel(const std::string& model_name) {
  model_name_ = model_name;
}

auto TextEmbeddingFunction::getModel() const -> const std::string& {
  return model_name_;
}

void TextEmbeddingFunction::setDimensions(size_t dimensions) {
  dimensions_ = dimensions;
}

auto TextEmbeddingFunction::getDimensions() const -> size_t {
  return dimensions_;
}

auto TextEmbeddingFunction::generateEmbedding(const std::string& text) const
    -> std::vector<float> {
  // Mock embedding generation using simple hash-based approach
  std::vector<float> embedding(dimensions_);

  // Use text hash to seed random number generator
  std::hash<std::string> hasher;
  size_t hash = hasher(text);
  std::mt19937 gen(hash);
  std::normal_distribution<float> dist(0.0f, 1.0f);

  for (size_t i = 0; i < dimensions_; ++i) {
    embedding[i] = dist(gen);
  }

  // Simple L2 normalization
  float norm = 0.0f;
  for (float val : embedding) {
    norm += val * val;
  }
  norm = std::sqrt(norm);

  if (norm > 1e-8f) {
    for (auto& val : embedding) {
      val /= norm;
    }
  }

  return embedding;
}

}  // namespace sage_flow
