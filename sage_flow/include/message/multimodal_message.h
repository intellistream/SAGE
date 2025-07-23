#pragma once

/**
 * @file multimodal_message.h
 * @brief Convenience header that includes all multimodal message related classes
 * 
 * This file has been refactored to follow the "one class per file" principle.
 * All classes have been moved to separate header files for better maintainability.
 * 
 * Original file contained multiple classes and has been split into:
 * - content_type.h: ContentType enum
 * - vector_data.h: VectorData class for vector operations
 * - retrieval_context.h: RetrievalContext class for RAG operations
 * - multimodal_message_core.h: MultiModalMessage main class
 */

// Core content type definitions
#include "content_type.h"

// Vector data handling
#include "vector_data.h"

// Retrieval context for RAG operations
#include "retrieval_context.h"

// Main multimodal message class
#include "multimodal_message_core.h"

namespace sage_flow {

// Re-export key types for backward compatibility
using ContentType = sage_flow::ContentType;
using VectorData = sage_flow::VectorData;
using RetrievalContext = sage_flow::RetrievalContext;
using MultiModalMessage = sage_flow::MultiModalMessage;

// Factory functions for common message types
inline auto CreateTextMessage(uint64_t uid, std::string text) -> std::unique_ptr<MultiModalMessage> {
  return std::make_unique<MultiModalMessage>(uid, ContentType::kText, std::move(text));
}

inline auto CreateBinaryMessage(uint64_t uid, std::vector<uint8_t> data) -> std::unique_ptr<MultiModalMessage> {
  return std::make_unique<MultiModalMessage>(uid, ContentType::kBinary, std::move(data));
}

/**
 * @brief Create an image message with binary data
 */
inline auto CreateImageMessage(uint64_t uid, std::vector<uint8_t> image_data) -> std::unique_ptr<MultiModalMessage> {
  auto message = std::make_unique<MultiModalMessage>(uid, ContentType::kImage, std::move(image_data));
  return message;
}

/**
 * @brief Create an audio message with binary data
 */
inline auto CreateAudioMessage(uint64_t uid, std::vector<uint8_t> audio_data) -> std::unique_ptr<MultiModalMessage> {
  auto message = std::make_unique<MultiModalMessage>(uid, ContentType::kAudio, std::move(audio_data));
  return message;
}

/**
 * @brief Create a video message with binary data
 */
inline auto CreateVideoMessage(uint64_t uid, std::vector<uint8_t> video_data) -> std::unique_ptr<MultiModalMessage> {
  auto message = std::make_unique<MultiModalMessage>(uid, ContentType::kVideo, std::move(video_data));
  return message;
}

/**
 * @brief Create an embedding message with vector data
 */
inline auto CreateEmbeddingMessage(uint64_t uid, VectorData embedding) -> std::unique_ptr<MultiModalMessage> {
  auto message = std::make_unique<MultiModalMessage>(uid);
  message->setContentType(ContentType::kEmbedding);
  message->setEmbedding(std::move(embedding));
  return message;
}

}  // namespace sage_flow
