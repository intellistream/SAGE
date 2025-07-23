#pragma once

#include <string>
#include <unordered_map>

#include "operator/operator.h"

namespace sage_flow {

/**
 * @brief Document parser function for multi-format document processing
 * 
 * Supports parsing of various document formats including PDF, Word, HTML,
 * and plain text. Extracts textual content and metadata for further processing.
 */
class DocumentParserFunction final : public MapOperator {
 public:
  enum class DocumentFormat : std::uint8_t {
    kAuto,      // Auto-detect format
    kPlainText,
    kHtml,
    kPdf,
    kDocx,
    kMarkdown
  };
  
  struct ParseConfig {
    DocumentFormat format_ = DocumentFormat::kAuto;
    bool extract_metadata_ = true;
    bool preserve_structure_ = false;
    std::string encoding_ = "utf-8";
  };
  
  explicit DocumentParserFunction(ParseConfig config);
  explicit DocumentParserFunction(std::string name, ParseConfig config);
  
  auto map(std::unique_ptr<MultiModalMessage> input)
      -> std::unique_ptr<MultiModalMessage> override;
  
 private:
  ParseConfig config_;
  
  auto parseDocument(const std::string& content, DocumentFormat format) const -> std::string;
  auto detectFormat(const std::string& content) const -> DocumentFormat;
  auto parseHtml(const std::string& html_content) const -> std::string;
  auto parsePlainText(const std::string& text_content) const -> std::string;
  auto extractMetadata(const std::string& content, DocumentFormat format) const 
      -> std::unordered_map<std::string, std::string>;
};

}  // namespace sage_flow
