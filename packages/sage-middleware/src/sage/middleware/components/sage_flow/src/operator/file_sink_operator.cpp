#include "operator/file_sink_operator.hpp"

#include <ctime>
#include <iostream>
#include <stdexcept>
#include <optional>

#include "operator/operator_types.hpp"

namespace sage_flow {

FileSinkOperator::FileSinkOperator(std::string file_path, FileSinkConfig config)
    : BaseOperator<MultiModalMessage, bool>(OperatorType::kSink, "FileSink"),
      file_path_(std::move(file_path)),
      config_(std::move(config)) {}

auto FileSinkOperator::process(const std::vector<std::shared_ptr<MultiModalMessage>>& input_record) -> std::optional<Response<bool>> {
  incrementProcessedCount();

  if (!output_file_.is_open()) {
    return std::make_optional(Response<bool>(std::vector<std::shared_ptr<bool>>{std::make_shared<bool>(false)}));
  }

  bool all_success = true;
  for (const auto& message : input_record) {
    if (message) {
      if (!writeMessage(*message)) {
        all_success = false;
      }
      message_count_++;

      // Flush periodically based on batch size
      if (config_.batch_size_ > 0 &&
          message_count_ % config_.batch_size_ == 0) {
        output_file_.flush();
      }
    }
  }

  incrementOutputCount();
  auto result = std::make_shared<bool>(all_success);
  std::vector<std::shared_ptr<bool>> results{result};
  return std::make_optional(Response<bool>(std::move(results)));
}

auto FileSinkOperator::open() -> void {
  std::ios_base::openmode mode = std::ios::out;

  if (config_.append_mode_) {
    mode |= std::ios::app;
  }

  output_file_.open(file_path_, mode);
  if (!output_file_.is_open()) {
    throw std::runtime_error("Failed to open file for writing: " + file_path_);
  }

  // Write header if specified
  if (!config_.header_.empty()) {
    output_file_ << config_.header_ << '\n';
  }
}

auto FileSinkOperator::close() -> void {
  if (output_file_.is_open()) {
    output_file_.flush();
    output_file_.close();
  }
}

auto FileSinkOperator::writeMessage(const MultiModalMessage& message) -> bool {
  bool success = true;
  switch (config_.format_) {
    case FileFormat::TEXT:
      success = writeAsText(message);
      break;
    case FileFormat::JSON:
      success = writeAsJson(message);
      break;
    case FileFormat::CSV:
      success = writeAsCsv(message);
      break;
    default:
      success = false;
  }
  return success;
}

auto FileSinkOperator::writeAsText(const MultiModalMessage& message) -> bool {
  if (message.isTextContent()) {
    output_file_ << message.getContentAsString() << '\n';
    return output_file_.good();
  }
  return false;
}

auto FileSinkOperator::writeAsJson(const MultiModalMessage& message) -> bool {
  output_file_ << "{\n";
  output_file_ << "  \"uid\": " << message.getUid() << ",\n";
  output_file_ << "  \"type\": " << static_cast<int>(message.getContentType())
               << ",\n";
  output_file_ << "  \"timestamp\": " << message.getTimestamp() << ",\n";

  if (message.isTextContent()) {
    output_file_ << R"(  "content": ")"
                 << escapeJsonString(message.getContentAsString()) << "\",\n";
  } else if (message.isBinaryContent()) {
    const auto& binary_data = message.getContentAsBinary();
    output_file_ << "  \"binary_size\": " << binary_data.size() << ",\n";
  }

  output_file_ << "  \"processed_at\": " << std::time(nullptr) << "\n";
  output_file_ << "},\n";
  return output_file_.good();
}

auto FileSinkOperator::writeAsCsv(const MultiModalMessage& message) -> bool {
  output_file_ << message.getUid() << ",";
  output_file_ << static_cast<int>(message.getContentType()) << ",";
  output_file_ << message.getTimestamp() << ",";

  if (message.isTextContent()) {
    output_file_ << "\"" << escapeCsvString(message.getContentAsString())
                 << "\"";
  } else {
    output_file_ << "\"[BINARY_DATA]\"";
  }

  output_file_ << "\n";
  return output_file_.good();
}

auto FileSinkOperator::escapeJsonString(const std::string& str) -> std::string {
  std::string escaped;
  escaped.reserve(str.length() * 2);

  for (char c : str) {
    switch (c) {
      case '"':
        escaped += "\\\"";
        break;
      case '\\':
        escaped += "\\\\";
        break;
      case '\b':
        escaped += "\\b";
        break;
      case '\f':
        escaped += "\\f";
        break;
      case '\n':
        escaped += "\\n";
        break;
      case '\r':
        escaped += "\\r";
        break;
      case '\t':
        escaped += "\\t";
        break;
      default:
        if (c < 0x20) {
          escaped += "\\u00";
          escaped += "0123456789abcdef"[c >> 4];
          escaped += "0123456789abcdef"[c & 0xf];
        } else {
          escaped += c;
        }
        break;
    }
  }

  return escaped;
}

auto FileSinkOperator::escapeCsvString(const std::string& str) -> std::string {
  std::string escaped;
  escaped.reserve(str.length() * 2);

  for (char c : str) {
    if (c == '"') {
      escaped += "\"\"";  // Escape quotes by doubling them
    } else {
      escaped += c;
    }
  }

  return escaped;
}

// Factory function implementation
auto CreateFileSink(const std::string& file_path, FileFormat format,
                    bool append_mode) -> std::unique_ptr<FileSinkOperator> {
  FileSinkConfig config;
  config.format_ = format;
  config.append_mode_ = append_mode;
  config.batch_size_ = 100;  // Default batch size

  return std::make_unique<FileSinkOperator>(file_path, config);
}

}  // namespace sage_flow
