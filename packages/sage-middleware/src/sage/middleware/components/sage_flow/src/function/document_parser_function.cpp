#include "function/document_parser_function.hpp"

#include <algorithm>
#include <cctype>
#include <iostream>

#include "message/multimodal_message.hpp"

namespace sage_flow {

auto DocumentParserFunction::execute(FunctionResponse& response)
    -> FunctionResponse {
  FunctionResponse output_response;

  for (auto& message : response.getMessages()) {
    if (!message) {
      continue;
    }

    // Get text content from message
    std::string content;
    if (message->isTextContent()) {
      content = message->getContentAsString();
    } else {
      // Skip non-text content for now
      output_response.addMessage(std::move(message));
      continue;
    }

    if (content.empty()) {
      output_response.addMessage(std::move(message));
      continue;
    }

    try {
      // Simple text processing - normalize whitespace
      std::string processed_content = content;

      // Replace multiple whitespace with single space
      size_t pos = 0;
      while ((pos = processed_content.find("  ", pos)) != std::string::npos) {
        processed_content.replace(pos, 2, " ");
      }

      // Remove leading/trailing whitespace
      processed_content.erase(
          processed_content.begin(),
          std::find_if(processed_content.begin(), processed_content.end(),
                       [](unsigned char ch) { return std::isspace(ch) == 0; }));
      processed_content.erase(
          std::find_if(processed_content.rbegin(), processed_content.rend(),
                       [](unsigned char ch) { return std::isspace(ch) == 0; })
              .base(),
          processed_content.end());

      // Create new message with processed content
      auto processed_message = std::make_unique<MultiModalMessage>(
          message->getUid(), ContentType::kText, processed_content);

      // Copy original metadata
      for (const auto& [key, value] : message->getMetadata()) {
        processed_message->setMetadata(key, value);
      }

      // Add processing step
      processed_message->addProcessingStep("DocumentParser");

      output_response.addMessage(std::move(processed_message));

    } catch (const std::exception& e) {
      std::cerr << "Error parsing document: " << e.what() << std::endl;
      // Add original message on error
      output_response.addMessage(std::move(message));
    }
  }

  return output_response;
}

auto DocumentParserFunction::execute(
    FunctionResponse& left, FunctionResponse& right) -> FunctionResponse {
  // For document parsing, we only process the left input
  return execute(left);
}

void DocumentParserFunction::setConfig(const std::string& config) {
  config_ = config;
}

auto DocumentParserFunction::getConfig() const -> const std::string& {
  return config_;
}

}  // namespace sage_flow
