#include "../../include/message/sage_packet_adapter.hpp"

#include <algorithm>
#include <chrono>
#include <functional>
#include <stdexcept>
#include <string>
#include <vector>

namespace sage_flow {
namespace integration {

// =============================================================================
// SageMessage 实现
// =============================================================================

SagePacketAdapter::SageMessage::SageMessage(std::string uid,
                                            SageContentType content_type)
    : uid_(std::move(uid)), content_type_(content_type) {
  metadata_.timestamp = std::chrono::duration_cast<std::chrono::milliseconds>(
                            std::chrono::system_clock::now().time_since_epoch())
                            .count() /
                        1000.0;
}

auto SagePacketAdapter::SageMessage::getUid() const -> const std::string& {
  return uid_;
}

auto SagePacketAdapter::SageMessage::getContentType() const -> SageContentType {
  return content_type_;
}

auto SagePacketAdapter::SageMessage::getMetadata() -> SageMessageMetadata& {
  return metadata_;
}

auto SagePacketAdapter::SageMessage::getMetadata() const
    -> const SageMessageMetadata& {
  return metadata_;
}

auto SagePacketAdapter::SageMessage::isProcessed() const -> bool {
  return processed_;
}

auto SagePacketAdapter::SageMessage::setProcessed(bool processed) -> void {
  processed_ = processed;
}

auto SagePacketAdapter::SageMessage::addTag(const std::string& tag) -> void {
  if (std::find(metadata_.tags.begin(), metadata_.tags.end(), tag) ==
      metadata_.tags.end()) {
    metadata_.tags.push_back(tag);
  }
}

auto SagePacketAdapter::SageMessage::hasTag(const std::string& tag) const
    -> bool {
  return std::find(metadata_.tags.begin(), metadata_.tags.end(), tag) !=
         metadata_.tags.end();
}

auto SagePacketAdapter::SageMessage::getCustomField(
    const std::string& key,
    const std::string& default_value) const -> std::string {
  auto it = metadata_.custom_fields.find(key);
  return (it != metadata_.custom_fields.end()) ? it->second : default_value;
}

auto SagePacketAdapter::SageMessage::setCustomField(
    const std::string& key, const std::string& value) -> void {
  metadata_.custom_fields[key] = value;
}

// =============================================================================
// SageTextMessage 实现
// =============================================================================

SagePacketAdapter::SageTextMessage::SageTextMessage(std::string uid,
                                                    std::string content)
    : SageMessage(std::move(uid), SageContentType::kText),
      content_(std::move(content)) {}

auto SagePacketAdapter::SageTextMessage::getContentAsString() const
    -> std::string {
  return content_;
}

auto SagePacketAdapter::SageTextMessage::getContentAsBinary() const
    -> std::vector<uint8_t> {
  return std::vector<uint8_t>(content_.begin(), content_.end());
}

auto SagePacketAdapter::SageTextMessage::setContent(const std::string& content)
    -> void {
  content_ = content;
}

auto SagePacketAdapter::SageTextMessage::setContent(
    const std::vector<uint8_t>& content) -> void {
  content_ = std::string(content.begin(), content.end());
}

auto SagePacketAdapter::SageTextMessage::clone() const
    -> std::unique_ptr<SageMessage> {
  auto cloned = std::make_unique<SageTextMessage>(getUid(), content_);
  cloned->getMetadata() = getMetadata();
  cloned->setProcessed(isProcessed());
  return cloned;
}

// =============================================================================
// SageMultimediaMessage 实现
// =============================================================================

SagePacketAdapter::SageMultimediaMessage::SageMultimediaMessage(
    std::string uid, SageContentType content_type, std::vector<uint8_t> data)
    : SageMessage(std::move(uid), content_type), data_(std::move(data)) {
  if (content_type == SageContentType::kText ||
      content_type == SageContentType::kStructured) {
    throw std::invalid_argument(
        "SageMultimediaMessage cannot be used for text or structured content");
  }
}

auto SagePacketAdapter::SageMultimediaMessage::getContentAsString() const
    -> std::string {
  // 对于多媒体消息，返回 base64 编码或者错误信息
  return std::string(data_.begin(), data_.end());
}

auto SagePacketAdapter::SageMultimediaMessage::getContentAsBinary() const
    -> std::vector<uint8_t> {
  return data_;
}

auto SagePacketAdapter::SageMultimediaMessage::setContent(
    const std::string& content) -> void {
  data_ = std::vector<uint8_t>(content.begin(), content.end());
}

auto SagePacketAdapter::SageMultimediaMessage::setContent(
    const std::vector<uint8_t>& content) -> void {
  data_ = content;
}

auto SagePacketAdapter::SageMultimediaMessage::clone() const
    -> std::unique_ptr<SageMessage> {
  auto cloned = std::make_unique<SageMultimediaMessage>(
      getUid(), getContentType(), data_);
  cloned->getMetadata() = getMetadata();
  cloned->setProcessed(isProcessed());
  cloned->setFormat(getFormat());
  return cloned;
}

auto SagePacketAdapter::SageMultimediaMessage::getFormat() const
    -> const std::string& {
  return format_;
}

auto SagePacketAdapter::SageMultimediaMessage::setFormat(
    const std::string& format) -> void {
  format_ = format;
}

auto SagePacketAdapter::SageMultimediaMessage::getSize() const -> size_t {
  return data_.size();
}

// =============================================================================
// SagePacketAdapter 静态工厂方法
// =============================================================================

auto SagePacketAdapter::createTextMessage(const std::string& uid,
                                          const std::string& content)
    -> std::unique_ptr<SageMessage> {
  return std::make_unique<SageTextMessage>(uid, content);
}

auto SagePacketAdapter::createBinaryMessage(const std::string& uid,
                                            const std::vector<uint8_t>& data)
    -> std::unique_ptr<SageMessage> {
  return std::make_unique<SageMultimediaMessage>(uid, SageContentType::kBinary,
                                                 data);
}

auto SagePacketAdapter::createImageMessage(const std::string& uid,
                                           const std::vector<uint8_t>& data)
    -> std::unique_ptr<SageMessage> {
  return std::make_unique<SageMultimediaMessage>(uid, SageContentType::kImage,
                                                 data);
}

auto SagePacketAdapter::createAudioMessage(const std::string& uid,
                                           const std::vector<uint8_t>& data)
    -> std::unique_ptr<SageMessage> {
  return std::make_unique<SageMultimediaMessage>(uid, SageContentType::kAudio,
                                                 data);
}

auto SagePacketAdapter::createVideoMessage(const std::string& uid,
                                           const std::vector<uint8_t>& data)
    -> std::unique_ptr<SageMessage> {
  return std::make_unique<SageMultimediaMessage>(uid, SageContentType::kVideo,
                                                 data);
}

// =============================================================================
// 类型转换函数
// =============================================================================

auto SagePacketAdapter::mapContentType(SageContentType sage_type)
    -> ContentType {
  switch (sage_type) {
    case SageContentType::kText:
      return ContentType::kText;
    case SageContentType::kImage:
      return ContentType::kImage;
    case SageContentType::kAudio:
      return ContentType::kAudio;
    case SageContentType::kVideo:
      return ContentType::kVideo;
    case SageContentType::kBinary:
      return ContentType::kBinary;
    case SageContentType::kStructured:
      return ContentType::kMetadata;
    default:
      return ContentType::kText;
  }
}

auto SagePacketAdapter::mapContentType(ContentType flow_type)
    -> SageContentType {
  switch (flow_type) {
    case ContentType::kText:
      return SageContentType::kText;
    case ContentType::kImage:
      return SageContentType::kImage;
    case ContentType::kAudio:
      return SageContentType::kAudio;
    case ContentType::kVideo:
      return SageContentType::kVideo;
    case ContentType::kBinary:
      return SageContentType::kBinary;
    case ContentType::kEmbedding:
      return SageContentType::kBinary;  // 嵌入向量作为二进制数据
    case ContentType::kMetadata:
      return SageContentType::kStructured;
    default:
      return SageContentType::kText;
  }
}

// =============================================================================
// MessageConverter 实现
// =============================================================================

auto MessageConverter::convertToMultiModal(
    const SagePacketAdapter::SageMessage& sage_msg)
    -> std::unique_ptr<MultiModalMessage> {
  // 转换 UID (SAGE 使用 string，sage-flow 使用 uint64_t)
  uint64_t uid = std::hash<std::string>{}(sage_msg.getUid());

  // 转换内容类型
  auto content_type =
      SagePacketAdapter::mapContentType(sage_msg.getContentType());

  // 创建 MultiModalMessage
  std::unique_ptr<MultiModalMessage> flow_msg;

  if (sage_msg.getContentType() == SagePacketAdapter::SageContentType::kText) {
    flow_msg = std::make_unique<MultiModalMessage>(
        uid, content_type, sage_msg.getContentAsString());
  } else {
    flow_msg = std::make_unique<MultiModalMessage>(
        uid, content_type, sage_msg.getContentAsBinary());
  }

  // 转换元数据
  convertMetadata(sage_msg.getMetadata(), *flow_msg);

  return flow_msg;
}

auto MessageConverter::convertFromMultiModal(const MultiModalMessage& flow_msg)
    -> std::unique_ptr<SagePacketAdapter::SageMessage> {
  // 转换 UID
  std::string uid = std::to_string(flow_msg.getUid());

  // 转换内容类型
  auto sage_content_type =
      SagePacketAdapter::mapContentType(flow_msg.getContentType());

  // 创建 SageMessage
  std::unique_ptr<SagePacketAdapter::SageMessage> sage_msg;

  if (flow_msg.isTextContent()) {
    sage_msg = SagePacketAdapter::createTextMessage(
        uid, flow_msg.getContentAsString());
  } else {
    auto binary_data = flow_msg.getContentAsBinary();
    switch (sage_content_type) {
      case SagePacketAdapter::SageContentType::kImage:
        sage_msg = SagePacketAdapter::createImageMessage(uid, binary_data);
        break;
      case SagePacketAdapter::SageContentType::kAudio:
        sage_msg = SagePacketAdapter::createAudioMessage(uid, binary_data);
        break;
      case SagePacketAdapter::SageContentType::kVideo:
        sage_msg = SagePacketAdapter::createVideoMessage(uid, binary_data);
        break;
      default:
        sage_msg = SagePacketAdapter::createBinaryMessage(uid, binary_data);
        break;
    }
  }

  // 转换元数据
  SagePacketAdapter::SageMessageMetadata sage_meta;
  convertMetadata(flow_msg, sage_meta);
  sage_msg->getMetadata() = sage_meta;

  return sage_msg;
}

auto MessageConverter::convertBatchToMultiModal(
    const std::vector<std::unique_ptr<SagePacketAdapter::SageMessage>>&
        sage_msgs) -> std::vector<std::unique_ptr<MultiModalMessage>> {
  std::vector<std::unique_ptr<MultiModalMessage>> flow_msgs;
  flow_msgs.reserve(sage_msgs.size());

  for (const auto& sage_msg : sage_msgs) {
    if (sage_msg) {
      flow_msgs.push_back(convertToMultiModal(*sage_msg));
    }
  }

  return flow_msgs;
}

auto MessageConverter::convertBatchFromMultiModal(
    const std::vector<std::unique_ptr<MultiModalMessage>>& flow_msgs)
    -> std::vector<std::unique_ptr<SagePacketAdapter::SageMessage>> {
  std::vector<std::unique_ptr<SagePacketAdapter::SageMessage>> sage_msgs;
  sage_msgs.reserve(flow_msgs.size());

  for (const auto& flow_msg : flow_msgs) {
    if (flow_msg) {
      sage_msgs.push_back(convertFromMultiModal(*flow_msg));
    }
  }

  return sage_msgs;
}

auto MessageConverter::convertMetadata(
    const SagePacketAdapter::SageMessageMetadata& sage_meta,
    MultiModalMessage& flow_msg) -> void {
  // 设置质量分数
  if (sage_meta.quality_score > 0.0) {
    flow_msg.setQualityScore(static_cast<float>(sage_meta.quality_score));
  }

  // 设置元数据字段
  flow_msg.setMetadata("source", sage_meta.source);
  flow_msg.setMetadata("timestamp", std::to_string(sage_meta.timestamp));

  // 设置标签
  for (const auto& tag : sage_meta.tags) {
    flow_msg.addProcessingStep("tag:" + tag);
  }

  // 设置自定义字段
  for (const auto& [key, value] : sage_meta.custom_fields) {
    flow_msg.setMetadata(key, value);
  }
}

auto MessageConverter::convertMetadata(
    const MultiModalMessage& flow_msg,
    SagePacketAdapter::SageMessageMetadata& sage_meta) -> void {
  // 转换质量分数
  if (auto score = flow_msg.getQualityScore(); score.has_value()) {
    sage_meta.quality_score = static_cast<double>(score.value());
  }

  // 转换时间戳
  sage_meta.timestamp = static_cast<double>(flow_msg.getTimestamp()) / 1000.0;

  // 转换元数据
  const auto& metadata = flow_msg.getMetadata();
  for (const auto& [key, value] : metadata) {
    if (key == "source") {
      sage_meta.source = value;
    } else {
      sage_meta.custom_fields[key] = value;
    }
  }

  // 从处理跟踪中提取标签
  const auto& trace = flow_msg.getProcessingTrace();
  for (const auto& step : trace) {
    if (step.size() >= 4 && step.substr(0, 4) == "tag:") {
      sage_meta.tags.push_back(step.substr(4));  // 移除 "tag:" 前缀
    }
  }
}

}  // namespace integration
}  // namespace sage_flow