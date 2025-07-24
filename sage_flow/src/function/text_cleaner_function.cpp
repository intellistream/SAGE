#include "function/text_cleaner_function.h"
#include "message/multimodal_message.h"

#include <algorithm>
#include <cctype>
#include <utility>

namespace sage_flow {

// TextCleanerFunction implementation
TextCleanerFunction::TextCleanerFunction(TextCleanConfig config)
    : MapOperator("TextCleaner"), config_(std::move(config)) {
  compilePatterns();
}

TextCleanerFunction::TextCleanerFunction(std::string name, TextCleanConfig config)
    : MapOperator(std::move(name)), config_(std::move(config)) {
  compilePatterns();
}

TextCleanerFunction::TextCleanerFunction(TextCleanerFunction&& other) noexcept
    : MapOperator(std::move(other)),
      config_(std::move(other.config_)),
      compiled_patterns_(std::move(other.compiled_patterns_)) {}

auto TextCleanerFunction::operator=(TextCleanerFunction&& other) noexcept -> TextCleanerFunction& {
  if (this != &other) {
    MapOperator::operator=(std::move(other));
    config_ = std::move(other.config_);
    compiled_patterns_ = std::move(other.compiled_patterns_);
  }
  return *this;
}

auto TextCleanerFunction::map(std::unique_ptr<MultiModalMessage> input) 
    -> std::unique_ptr<MultiModalMessage> {
  if (!input || !input->isTextContent()) {
    return input;  // Pass through non-text content unchanged
  }
  
  // Add processing step to trace
  input->addProcessingStep("TextCleaner");
  
  // Get original text content
  const std::string original_text = input->getContentAsString();
  
  // Apply text cleaning operations
  const std::string cleaned_text = cleanText(original_text);
  
  // Validate cleaned text
  if (!isValidText(cleaned_text)) {
    // Set low quality score for invalid text
    input->setQualityScore(0.0F);
    return input;
  }
  
  // Calculate quality score
  const float quality_score = calculateQualityScore(cleaned_text);
  
  // Update message with cleaned content and quality score
  input->setContent(cleaned_text);
  input->setQualityScore(quality_score);
  
  // Add metadata about cleaning operation
  input->setMetadata("cleaned_length", std::to_string(cleaned_text.length()));
  input->setMetadata("original_length", std::to_string(original_text.length()));
  input->setMetadata("quality_score", std::to_string(quality_score));
  
  return input;
}

auto TextCleanerFunction::getConfig() const -> const TextCleanConfig& {
  return config_;
}

auto TextCleanerFunction::updateConfig(const TextCleanConfig& new_config) -> void {
  config_ = new_config;
  compilePatterns();
}

// Private methods implementation
auto TextCleanerFunction::cleanText(const std::string& input_text) const -> std::string {
  std::string result = input_text;
  
  // Apply cleaning operations in sequence
  result = removePatterns(result);
  
  if (config_.remove_punctuation_) {
    result = removePunctuation(result);
  }
  
  if (config_.to_lowercase_) {
    result = toLowerCase(result);
  }
  
  if (config_.remove_extra_whitespace_) {
    result = normalizeWhitespace(result);
  }
  
  return result;
}

auto TextCleanerFunction::removePatterns(const std::string& text) const -> std::string {
  std::string result = text;
  
  for (const auto& pattern : compiled_patterns_) {
    result = std::regex_replace(result, pattern, config_.replacement_text_);
  }
  
  return result;
}

auto TextCleanerFunction::normalizeWhitespace(const std::string& text) const -> std::string {
  std::string result = text;
  
  // Replace multiple whitespace characters with single space
  result = std::regex_replace(result, std::regex(R"(\\s+)"), " ");
  
  // Trim leading and trailing whitespace
  result.erase(result.begin(), std::find_if(result.begin(), result.end(), [](unsigned char ch) {
    return std::isspace(ch) == 0;
  }));
  result.erase(std::find_if(result.rbegin(), result.rend(), [](unsigned char ch) {
    return std::isspace(ch) == 0;
  }).base(), result.end());
  
  return result;
}

auto TextCleanerFunction::removePunctuation(const std::string& text) const -> std::string {
  std::string result;
  result.reserve(text.length());
  
  for (char c : text) {
    if (std::ispunct(static_cast<unsigned char>(c)) == 0) {
      result += c;
    }
  }
  
  return result;
}

auto TextCleanerFunction::toLowerCase(const std::string& text) const -> std::string {
  std::string result = text;
  std::transform(result.begin(), result.end(), result.begin(), [](unsigned char c) {
    return std::tolower(c);
  });
  return result;
}

auto TextCleanerFunction::calculateQualityScore(const std::string& text) const -> float {
  const float length_score = assessTextLength(text);
  const float complexity_score = assessTextComplexity(text);
  const float language_score = assessLanguageDetection(text);
  
  // Weighted average of quality metrics
  return (length_score * 0.4F + complexity_score * 0.4F + language_score * 0.2F);
}

auto TextCleanerFunction::assessTextLength(const std::string& text) const -> float {
  const auto length = static_cast<float>(text.length());
  
  if (length < config_.min_length_) {
    return 0.0F;
  }
  if (length > config_.max_length_) {
    return 0.5F;  // Penalty for overly long text
  }
  
  // Optimal length range scoring
  const float optimal_min = config_.min_length_ * 2.0F;
  const float optimal_max = config_.max_length_ * 0.8F;
  
  if (length >= optimal_min && length <= optimal_max) {
    return 1.0F;
  }
  
  // Linear scaling for sub-optimal lengths
  if (length < optimal_min) {
    return (length - config_.min_length_) / (optimal_min - config_.min_length_);
  }
  
  return 1.0F - (length - optimal_max) / (config_.max_length_ - optimal_max) * 0.5F;
}

auto TextCleanerFunction::assessTextComplexity(const std::string& text) const -> float {
  if (text.empty()) {
    return 0.0F;
  }
  
  // Simple complexity metrics
  const auto word_count = static_cast<size_t>(std::count(text.begin(), text.end(), ' ') + 1);
  const size_t char_count = text.length();
  
  if (word_count == 0) {
    return 0.0F;
  }
  
  const float avg_word_length = static_cast<float>(char_count) / static_cast<float>(word_count);
  
  // Score based on average word length (optimal range: 4-8 characters)
  if (avg_word_length >= 4.0F && avg_word_length <= 8.0F) {
    return 1.0F;
  }
  if (avg_word_length < 2.0F || avg_word_length > 15.0F) {
    return 0.2F;
  }
  
  return 0.7F;  // Moderate complexity
}

auto TextCleanerFunction::assessLanguageDetection(const std::string& text) const -> float {
  // Simplified language detection based on character distribution
  if (text.empty()) {
    return 0.0F;
  }
  
  size_t letter_count = 0;
  size_t digit_count = 0;
  size_t special_count = 0;
  
  for (char c : text) {
    if (std::isalpha(static_cast<unsigned char>(c)) != 0) {
      ++letter_count;
    } else if (std::isdigit(static_cast<unsigned char>(c)) != 0) {
      ++digit_count;
    } else if (std::isspace(static_cast<unsigned char>(c)) == 0) {
      ++special_count;
    }
  }
  
  const size_t total_chars = letter_count + digit_count + special_count;
  if (total_chars == 0) {
    return 0.0F;
  }
  
  const float letter_ratio = static_cast<float>(letter_count) / static_cast<float>(total_chars);
  
  // Good text should be mostly letters
  if (letter_ratio >= 0.7F) {
    return 1.0F;
  }
  if (letter_ratio >= 0.5F) {
    return 0.8F;
  }
  if (letter_ratio >= 0.3F) {
    return 0.5F;
  }
  
  return 0.2F;
}

auto TextCleanerFunction::compilePatterns() -> void {
  compiled_patterns_.clear();
  compiled_patterns_.reserve(config_.regex_patterns_.size());
  
  for (const auto& pattern_str : config_.regex_patterns_) {
    try {
      compiled_patterns_.emplace_back(pattern_str);
    } catch (const std::regex_error& e) {
      // Log error but continue with other patterns
      // TODO(xinyan): Add proper logging integration
      static_cast<void>(e);  // Suppress unused variable warning
    }
  }
}

auto TextCleanerFunction::isValidText(const std::string& text) const -> bool {
  const auto length = static_cast<float>(text.length());
  return length >= config_.min_length_ && length <= config_.max_length_;
}

}  // namespace sage_flow
