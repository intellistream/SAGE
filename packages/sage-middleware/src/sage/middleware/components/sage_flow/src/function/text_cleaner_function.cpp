#include "function/text_cleaner_function.hpp"

#include <algorithm>
#include <cctype>
#include <iostream>

#include "message/multimodal_message.hpp"

namespace sage_flow {

auto TextCleanerFunction::execute(FunctionResponse& response)
    -> FunctionResponse {
  FunctionResponse output_response;

  for (auto& message : response.getMessages()) {
    if (!message) {
      continue;
    }

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
      // Clean the text
      std::string cleaned_text = cleanText(text_content);

      // Create new message with cleaned content
      auto cleaned_message = std::make_unique<MultiModalMessage>(
          message->getUid(), ContentType::kText, cleaned_text);

      // Copy original metadata
      for (const auto& [key, value] : message->getMetadata()) {
        cleaned_message->setMetadata(key, value);
      }

      // Add processing step
      cleaned_message->addProcessingStep("TextCleaner");

      output_response.addMessage(std::move(cleaned_message));

    } catch (const std::exception& e) {
      std::cerr << "Error cleaning text: " << e.what() << std::endl;
      // Add original message on error
      output_response.addMessage(std::move(message));
    }
  }

  return output_response;
}

auto TextCleanerFunction::execute(FunctionResponse& left,
                                  FunctionResponse& right) -> FunctionResponse {
  // For text cleaning, we only process the left input
  return execute(left);
}

void TextCleanerFunction::setConfig(const std::string& config) {
  config_ = config;
}

auto TextCleanerFunction::getConfig() const -> const std::string& {
  return config_;
}

void TextCleanerFunction::setCleaningOptions(bool remove_whitespace,
                                             bool remove_punctuation,
                                             bool to_lowercase) {
  remove_whitespace_ = remove_whitespace;
  remove_punctuation_ = remove_punctuation;
  to_lowercase_ = to_lowercase;
}

auto TextCleanerFunction::cleanText(const std::string& text) const
    -> std::string {
  std::string result = text;

  // Remove extra whitespace if enabled
  if (remove_whitespace_) {
    // Replace multiple whitespace with single space
    size_t pos = 0;
    while ((pos = result.find("  ", pos)) != std::string::npos) {
      result.replace(pos, 2, " ");
    }

    // Remove leading/trailing whitespace
    result.erase(result.begin(), std::find_if(result.begin(), result.end(),
                                              [](unsigned char ch) {
                                                return std::isspace(ch) == 0;
                                              }));
    result.erase(
        std::find_if(result.rbegin(), result.rend(),
                     [](unsigned char ch) { return std::isspace(ch) == 0; })
            .base(),
        result.end());
  }

  // Convert to lowercase if enabled
  if (to_lowercase_) {
    std::transform(result.begin(), result.end(), result.begin(),
                   [](unsigned char c) { return std::tolower(c); });
  }

  // Remove punctuation if enabled
  if (remove_punctuation_) {
    result.erase(
        std::remove_if(result.begin(), result.end(),
                       [](unsigned char c) { return std::ispunct(c); }),
        result.end());
  }

  return result;
}

}  // namespace sage_flow
