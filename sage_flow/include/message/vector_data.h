#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace sage_flow {

/**
 * @brief Vector data container with type safety and multi-precision support
 */
class VectorData final {
 public:
  enum class DataType : std::uint8_t {
    kFloat32,
    kFloat16,
    kBFloat16,
    kInt8,
    kUint8
  };

  // Constructors for different data types
  explicit VectorData(std::vector<float> data, size_t dimension);
  explicit VectorData(const float* data, size_t dimension);
  explicit VectorData(std::vector<std::uint8_t> data, size_t dimension, DataType dtype);
  
  // Copy constructor and assignment (needed for Python bindings)
  VectorData(const VectorData& other);
  auto operator=(const VectorData& other) -> VectorData&;
  
  // Move constructor and assignment
  VectorData(VectorData&& other) noexcept;
  auto operator=(VectorData&& other) noexcept -> VectorData&;
  
  // Accessors
  auto getData() const -> const std::vector<float>&;
  auto getRawData() const -> const std::vector<std::uint8_t>&;
  auto getDimension() const -> size_t;
  auto getDataType() const -> DataType;
  auto size() const -> size_t;
  
  // Vector operations with similarity metrics
  auto dotProduct(const VectorData& other) const -> float;
  auto cosineSimilarity(const VectorData& other) const -> float;
  auto euclideanDistance(const VectorData& other) const -> float;
  auto manhattanDistance(const VectorData& other) const -> float;
  
  // Type conversion utilities
  auto toFloat32() const -> std::vector<float>;
  auto isQuantized() const -> bool;
  auto isSparse() const -> bool;
  
  // Numpy-like interface compatibility (for pybind11)
  auto getNumpyShape() const -> std::vector<size_t>;
  auto getNumpyDtype() const -> std::string;
  
 private:
  std::vector<float> data_;
  std::vector<std::uint8_t> raw_data_;
  size_t dimension_;
  DataType data_type_;
  
  // Helper functions
  static auto getDataTypeSize(DataType dtype) -> size_t;
  static auto convertToFloat32(const std::vector<std::uint8_t>& raw_data, DataType dtype) -> std::vector<float>;
};

}  // namespace sage_flow
