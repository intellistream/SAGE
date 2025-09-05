#pragma once

#include <memory>
#include <string>
#include <vector>

#include "content_type.hpp"
#include "multimodal_message.hpp"
#include "vector_data.hpp"

namespace sage_flow {

// Factory functions for common message types
inline auto CreateTextMessage(uint64_t uid, std::string text)
    -> std::unique_ptr<MultiModalMessage> {
  return std::make_unique<MultiModalMessage>(uid, ContentType::kText,
                                             std::move(text));
}

inline auto CreateBinaryMessage(uint64_t uid, std::vector<uint8_t> data)
    -> std::unique_ptr<MultiModalMessage> {
  return std::make_unique<MultiModalMessage>(uid, ContentType::kBinary,
                                             std::move(data));
}

/**
 * @brief Create an image message with binary data
 */
inline auto CreateImageMessage(uint64_t uid, std::vector<uint8_t> image_data)
    -> std::unique_ptr<MultiModalMessage> {
  auto message = std::make_unique<MultiModalMessage>(uid, ContentType::kImage,
                                                     std::move(image_data));
  return message;
}

/**
 * @brief Create an audio message with binary data
 */
inline auto CreateAudioMessage(uint64_t uid, std::vector<uint8_t> audio_data)
    -> std::unique_ptr<MultiModalMessage> {
  auto message = std::make_unique<MultiModalMessage>(uid, ContentType::kAudio,
                                                     std::move(audio_data));
  return message;
}

/**
 * @brief Create a video message with binary data
 */
inline auto CreateVideoMessage(uint64_t uid, std::vector<uint8_t> video_data)
    -> std::unique_ptr<MultiModalMessage> {
  auto message = std::make_unique<MultiModalMessage>(uid, ContentType::kVideo,
                                                     std::move(video_data));
  return message;
}

/**
 * @brief Create an embedding message with vector data
 */
inline auto CreateEmbeddingMessage(uint64_t uid, VectorData embedding)
    -> std::unique_ptr<MultiModalMessage> {
  auto message = std::make_unique<MultiModalMessage>(uid);
  message->setContentType(ContentType::kEmbedding);
  message->setEmbedding(std::move(embedding));
  return message;
}

}  // namespace sage_flow