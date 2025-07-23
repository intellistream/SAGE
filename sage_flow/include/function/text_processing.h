#pragma once

#include <regex>
#include <string>
#include <vector>
#include <unordered_map>

#include "operator/operator.h"

namespace sage_flow {

/**
 * @brief Configuration for text cleaning operations
 */
struct TextCleanConfig {
  std::vector<std::string> regex_patterns_;      // Patterns to remove
  bool remove_extra_whitespace_ = true;          // Remove extra spaces
  bool to_lowercase_ = false;                    // Convert to lowercase
  bool remove_punctuation_ = false;              // Remove punctuation
  std::string replacement_text_;                 // Replacement for matched patterns
  
  // Quality assessment parameters
  float min_length_ = 10.0F;                    // Minimum text length
  float max_length_ = 10000.0F;                 // Maximum text length
  float min_quality_score_ = 0.3F;              // Minimum quality threshold
};

/**
 * @brief Text cleaning function for processing textual content
 * 
 * This function implements comprehensive text cleaning and preprocessing
 * capabilities, including regex-based pattern removal, whitespace normalization,
 * and quality assessment. It follows Google C++ Style Guide conventions
 * and integrates with the SAGE flow operator system.
 */
class TextCleanerFunction final : public MapOperator {
 public:
  explicit TextCleanerFunction(TextCleanConfig config);
  explicit TextCleanerFunction(std::string name, TextCleanConfig config);
  
  // Disable copy operations for performance
  TextCleanerFunction(const TextCleanerFunction&) = delete;
  auto operator=(const TextCleanerFunction&) -> TextCleanerFunction& = delete;
  
  // Enable move operations
  TextCleanerFunction(TextCleanerFunction&& other) noexcept;
  auto operator=(TextCleanerFunction&& other) noexcept -> TextCleanerFunction& = default;
  
  // MapOperator interface implementation
  auto map(std::unique_ptr<MultiModalMessage> input) 
      -> std::unique_ptr<MultiModalMessage> override;
  
  // Configuration management
  auto getConfig() const -> const TextCleanConfig&;
  auto updateConfig(const TextCleanConfig& new_config) -> void;
  
 private:
  TextCleanConfig config_;
  std::vector<std::regex> compiled_patterns_;
  
  // Core text processing methods
  auto cleanText(const std::string& input_text) const -> std::string;
  auto removePatterns(const std::string& text) const -> std::string;
  auto normalizeWhitespace(const std::string& text) const -> std::string;
  auto removePunctuation(const std::string& text) const -> std::string;
  auto toLowerCase(const std::string& text) const -> std::string;
  
  // Quality assessment methods
  auto calculateQualityScore(const std::string& text) const -> float;
  auto assessTextLength(const std::string& text) const -> float;
  auto assessTextComplexity(const std::string& text) const -> float;
  auto assessLanguageDetection(const std::string& text) const -> float;
  
  // Utility methods
  auto compilePatterns() -> void;
  auto isValidText(const std::string& text) const -> bool;
};

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

/**
 * @brief Quality assessor function for data quality evaluation
 * 
 * Evaluates the quality of processed data based on various metrics
 * including completeness, consistency, and relevance.
 */
class QualityAssessorFunction final : public MapOperator {
 public:
  struct QualityMetrics {
    float completeness_score_ = 0.0F;
    float consistency_score_ = 0.0F;
    float relevance_score_ = 0.0F;
    float overall_score_ = 0.0F;
  };
  
  struct AssessmentConfig {
    float completeness_weight_ = 0.4F;
    float consistency_weight_ = 0.3F;
    float relevance_weight_ = 0.3F;
    float min_acceptable_score_ = 0.5F;
  };
  
  explicit QualityAssessorFunction(AssessmentConfig config);
  
  auto map(std::unique_ptr<MultiModalMessage> input)
      -> std::unique_ptr<MultiModalMessage> override;
  
  auto assessQuality(const MultiModalMessage& message) const -> QualityMetrics;
  
 private:
  AssessmentConfig config_;
  
  auto assessCompleteness(const MultiModalMessage& message) const -> float;
  auto assessConsistency(const MultiModalMessage& message) const -> float;
  auto assessRelevance(const MultiModalMessage& message) const -> float;
  auto calculateOverallScore(const QualityMetrics& metrics) const -> float;
};

}  // namespace sage_flow
