#pragma once

#include <cstdint>
#include <fstream>
#include <memory>
#include <string>

#include "message/multimodal_message.hpp"
#include "operator/base_operator.hpp"
#include "operator/response.hpp"

namespace sage_flow {

// File output format options
enum class FileFormat : std::uint8_t {
  TEXT,  // Plain text output
  JSON,  // JSON formatted output
  CSV    // CSV formatted output
};

// Configuration for file sink operator
struct FileSinkConfig {
  FileFormat format_{FileFormat::TEXT};
  bool append_mode_{false};
  size_t batch_size_{100};
  std::string header_;
};

/**
 * @brief File sink operator for writing messages to files
 *
 * This operator writes incoming messages to a file in various formats.
 * It supports text, JSON, and CSV output formats with configurable
 * batch processing and append modes.
 */
class FileSinkOperator final : public BaseOperator<MultiModalMessage, bool> {
public:
  explicit FileSinkOperator(std::string file_path, FileSinkConfig config);

  // Rule of Five
  ~FileSinkOperator() override = default;
  FileSinkOperator(const FileSinkOperator&) = delete;
  auto operator=(const FileSinkOperator&) -> FileSinkOperator& = delete;
  FileSinkOperator(FileSinkOperator&&) noexcept = default;
  auto operator=(FileSinkOperator&&) noexcept -> FileSinkOperator& = default;

  // Operator interface
  auto process(const std::vector<std::shared_ptr<MultiModalMessage>>& input_record) -> std::optional<Response<bool>> override;
  auto open() -> void override;
  auto close() -> void override;

  // Getter for message count
  auto getMessageCount() const -> size_t { return message_count_; }

private:
  auto writeMessage(const MultiModalMessage& message) -> bool;
  auto writeAsText(const MultiModalMessage& message) -> bool;
  auto writeAsJson(const MultiModalMessage& message) -> bool;
  auto writeAsCsv(const MultiModalMessage& message) -> bool;

  static auto escapeJsonString(const std::string& str) -> std::string;
  static auto escapeCsvString(const std::string& str) -> std::string;

  std::string file_path_;
  FileSinkConfig config_;
  std::ofstream output_file_;
  size_t message_count_{0};
};

// Factory function
auto CreateFileSink(
    const std::string& file_path, FileFormat format = FileFormat::TEXT,
    bool append_mode = false) -> std::unique_ptr<FileSinkOperator>;

}  // namespace sage_flow
