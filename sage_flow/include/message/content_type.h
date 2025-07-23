#pragma once

#include <cstdint>

namespace sage_flow {

/**
 * @brief Content types supported in MultiModalMessage
 */
enum class ContentType : std::uint8_t {
  kText,
  kBinary,
  kImage,
  kAudio,
  kVideo,
  kEmbedding,
  kMetadata
};

}  // namespace sage_flow
