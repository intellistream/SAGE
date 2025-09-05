#pragma once

#include <cstdint>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include "content_type.hpp"
#include "multimodal_message.hpp"

namespace sage_flow {
namespace integration {

/**
 * @brief SAGE Kernel 消息适配器
 *
 * 提供与 SAGE Kernel Python 消息系统的兼容接口，
 * 实现零拷贝转换和高性能数据交换。
 */
class SagePacketAdapter {
public:
  // SAGE Kernel ContentType 映射
  enum class SageContentType : std::uint8_t {
    kText = 0,
    kImage = 1,
    kAudio = 2,
    kVideo = 3,
    kBinary = 4,
    kStructured = 5
  };

  // SAGE Kernel 兼容的消息元数据
  struct SageMessageMetadata {
    std::string source;
    double timestamp;
    double quality_score;
    std::vector<std::string> tags;
    std::unordered_map<std::string, std::string> custom_fields;

    SageMessageMetadata()
        : source("unknown"), timestamp(0.0), quality_score(1.0) {}
  };

  /**
   * @brief SAGE Kernel 兼容的消息接口
   */
  class SageMessage {
  public:
    explicit SageMessage(std::string uid, SageContentType content_type);
    virtual ~SageMessage() = default;

    // 核心接口
    auto getUid() const -> const std::string&;
    auto getContentType() const -> SageContentType;
    auto getMetadata() -> SageMessageMetadata&;
    auto getMetadata() const -> const SageMessageMetadata&;
    auto isProcessed() const -> bool;
    auto setProcessed(bool processed) -> void;

    // 标签管理
    auto addTag(const std::string& tag) -> void;
    auto hasTag(const std::string& tag) const -> bool;

    // 自定义字段管理
    auto getCustomField(const std::string& key,
                        const std::string& default_value = "") const
        -> std::string;
    auto setCustomField(const std::string& key,
                        const std::string& value) -> void;

    // 抽象接口
    virtual auto getContentAsString() const -> std::string = 0;
    virtual auto getContentAsBinary() const -> std::vector<uint8_t> = 0;
    virtual auto setContent(const std::string& content) -> void = 0;
    virtual auto setContent(const std::vector<uint8_t>& content) -> void = 0;
    virtual auto clone() const -> std::unique_ptr<SageMessage> = 0;

  private:
    std::string uid_;
    SageContentType content_type_;
    SageMessageMetadata metadata_;
    bool processed_ = false;
  };

  /**
   * @brief SAGE 文本消息实现
   */
  class SageTextMessage : public SageMessage {
  public:
    SageTextMessage(std::string uid, std::string content);

    auto getContentAsString() const -> std::string override;
    auto getContentAsBinary() const -> std::vector<uint8_t> override;
    auto setContent(const std::string& content) -> void override;
    auto setContent(const std::vector<uint8_t>& content) -> void override;
    auto clone() const -> std::unique_ptr<SageMessage> override;

  private:
    std::string content_;
  };

  /**
   * @brief SAGE 多媒体消息实现
   */
  class SageMultimediaMessage : public SageMessage {
  public:
    SageMultimediaMessage(std::string uid, SageContentType content_type,
                          std::vector<uint8_t> data);

    auto getContentAsString() const -> std::string override;
    auto getContentAsBinary() const -> std::vector<uint8_t> override;
    auto setContent(const std::string& content) -> void override;
    auto setContent(const std::vector<uint8_t>& content) -> void override;
    auto clone() const -> std::unique_ptr<SageMessage> override;

    // 多媒体特定方法
    auto getFormat() const -> const std::string&;
    auto setFormat(const std::string& format) -> void;
    auto getSize() const -> size_t;

  private:
    std::vector<uint8_t> data_;
    std::string format_;
  };

  // 静态工厂方法
  static auto createTextMessage(const std::string& uid,
                                const std::string& content)
      -> std::unique_ptr<SageMessage>;

  static auto createBinaryMessage(const std::string& uid,
                                  const std::vector<uint8_t>& data)
      -> std::unique_ptr<SageMessage>;

  static auto createImageMessage(const std::string& uid,
                                 const std::vector<uint8_t>& data)
      -> std::unique_ptr<SageMessage>;

  static auto createAudioMessage(const std::string& uid,
                                 const std::vector<uint8_t>& data)
      -> std::unique_ptr<SageMessage>;

  static auto createVideoMessage(const std::string& uid,
                                 const std::vector<uint8_t>& data)
      -> std::unique_ptr<SageMessage>;

  // 类型转换函数
  static auto mapContentType(SageContentType sage_type) -> ContentType;
  static auto mapContentType(ContentType flow_type) -> SageContentType;
};

/**
 * @brief 消息转换工具类
 *
 * 提供 SAGE Kernel 消息与 sage-flow MultiModalMessage 之间的转换
 */
class MessageConverter {
public:
  // SAGE -> sage-flow 转换
  static auto convertToMultiModal(
      const SagePacketAdapter::SageMessage& sage_msg)
      -> std::unique_ptr<MultiModalMessage>;

  // sage-flow -> SAGE 转换
  static auto convertFromMultiModal(const MultiModalMessage& flow_msg)
      -> std::unique_ptr<SagePacketAdapter::SageMessage>;

  // 批量转换（性能优化）
  static auto convertBatchToMultiModal(
      const std::vector<std::unique_ptr<SagePacketAdapter::SageMessage>>&
          sage_msgs) -> std::vector<std::unique_ptr<MultiModalMessage>>;

  static auto convertBatchFromMultiModal(
      const std::vector<std::unique_ptr<MultiModalMessage>>& flow_msgs)
      -> std::vector<std::unique_ptr<SagePacketAdapter::SageMessage>>;

private:
  // 辅助转换方法
  static auto convertMetadata(
      const SagePacketAdapter::SageMessageMetadata& sage_meta,
      MultiModalMessage& flow_msg) -> void;

  static auto convertMetadata(const MultiModalMessage& flow_msg,
                              SagePacketAdapter::SageMessageMetadata& sage_meta)
      -> void;
};

}  // namespace integration
}  // namespace sage_flow