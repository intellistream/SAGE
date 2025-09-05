#include "function/quality_assessor_function.hpp"

#include <iostream>

#include "message/multimodal_message.hpp"

namespace sage_flow {

auto QualityAssessorFunction::execute(FunctionResponse& response)
    -> FunctionResponse {
  FunctionResponse output_response;

  for (auto& message : response.getMessages()) {
    if (!message) {
      continue;
    }

    try {
      // Assess quality based on content
      double quality_score = 0.0;

      if (message->isTextContent()) {
        const std::string content = message->getContentAsString();
        quality_score = assessTextQuality(content);
      } else if (message->isBinaryContent()) {
        const auto& content = message->getContentAsBinary();
        quality_score = content.empty() ? 0.0 : 1.0;
      } else {
        quality_score = 0.5;  // Default score for other content types
      }

      // Create new message with quality assessment
      auto assessed_message = std::make_unique<MultiModalMessage>(
          message->getUid(), message->getContentType(), message->getContent());

      // Set quality score
      assessed_message->setQualityScore(static_cast<float>(quality_score));

      // Add quality metadata
      assessed_message->setMetadata("quality_score",
                                    std::to_string(quality_score));
      assessed_message->setMetadata("quality_threshold",
                                    std::to_string(threshold_));
      assessed_message->setMetadata(
          "quality_passed", quality_score >= threshold_ ? "true" : "false");

      // Copy original metadata
      for (const auto& [key, value] : message->getMetadata()) {
        assessed_message->setMetadata(key, value);
      }

      // Add processing step
      assessed_message->addProcessingStep("QualityAssessor");

      output_response.addMessage(std::move(assessed_message));

    } catch (const std::exception& e) {
      std::cerr << "Error assessing quality: " << e.what() << std::endl;
      // Add original message on error
      output_response.addMessage(std::move(message));
    }
  }

  return output_response;
}

auto QualityAssessorFunction::execute(
    FunctionResponse& left, FunctionResponse& right) -> FunctionResponse {
  // For quality assessment, we only process the left input
  return execute(left);
}

void QualityAssessorFunction::setConfig(const std::string& config) {
  config_ = config;
}

auto QualityAssessorFunction::getConfig() const -> const std::string& {
  return config_;
}

void QualityAssessorFunction::setThreshold(double threshold) {
  threshold_ = threshold;
}

auto QualityAssessorFunction::getThreshold() const -> double {
  return threshold_;
}

auto QualityAssessorFunction::assessTextQuality(
    const std::string& content) const -> double {
  if (content.empty()) {
    return 0.0;
  }

  // Simple quality assessment based on text characteristics
  double score = 1.0;

  // Penalize very short content
  if (content.length() < 10) {
    score *= 0.5;
  }

  // Penalize content with too many special characters
  size_t special_chars = 0;
  for (char c : content) {
    if (!std::isalnum(c) && !std::isspace(c)) {
      special_chars++;
    }
  }

  double special_ratio = static_cast<double>(special_chars) / content.length();
  if (special_ratio > 0.3) {
    score *= 0.7;
  }

  return score;
}

auto QualityAssessorFunction::assessStructuredQuality(
    const std::vector<std::string>& data) const -> double {
  if (data.empty()) {
    return 0.0;
  }

  // Simple quality assessment for structured data
  double score = 1.0;

  // Penalize empty fields
  size_t empty_count = 0;
  for (const auto& field : data) {
    if (field.empty()) {
      empty_count++;
    }
  }

  double empty_ratio = static_cast<double>(empty_count) / data.size();
  score *= (1.0 - empty_ratio * 0.5);

  return score;
}

}  // namespace sage_flow
