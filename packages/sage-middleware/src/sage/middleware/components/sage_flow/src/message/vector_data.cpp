#include "../../include/message/vector_data.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace sage_flow {

// Constructor implementations
VectorData::VectorData(std::vector<float> data, size_t dimension)
    : data_(std::move(data)),
      dimension_(dimension),
      data_type_(DataType::kFloat32) {
  if (data_.size() != dimension_) {
    throw std::invalid_argument("Data size must match dimension");
  }
}

VectorData::VectorData(const float* data, size_t dimension)
    : data_(data, data + dimension),
      dimension_(dimension),
      data_type_(DataType::kFloat32) {}

VectorData::VectorData(std::vector<std::uint8_t> data, size_t dimension,
                       DataType dtype)
    : raw_data_(std::move(data)), dimension_(dimension), data_type_(dtype) {
  if (dtype == DataType::kFloat32) {
    data_ = convertToFloat32(raw_data_, dtype);
  }
}

// Copy constructor and assignment
VectorData::VectorData(const VectorData& other)
    : data_(other.data_),
      raw_data_(other.raw_data_),
      dimension_(other.dimension_),
      data_type_(other.data_type_) {}

auto VectorData::operator=(const VectorData& other) -> VectorData& {
  if (this != &other) {
    data_ = other.data_;
    raw_data_ = other.raw_data_;
    dimension_ = other.dimension_;
    data_type_ = other.data_type_;
  }
  return *this;
}

// Move constructor and assignment
VectorData::VectorData(VectorData&& other) noexcept
    : data_(std::move(other.data_)),
      raw_data_(std::move(other.raw_data_)),
      dimension_(other.dimension_),
      data_type_(other.data_type_) {}

auto VectorData::operator=(VectorData&& other) noexcept -> VectorData& {
  if (this != &other) {
    data_ = std::move(other.data_);
    raw_data_ = std::move(other.raw_data_);
    dimension_ = other.dimension_;
    data_type_ = other.data_type_;
  }
  return *this;
}

// Accessors
auto VectorData::getData() const -> const std::vector<float>& { return data_; }

auto VectorData::getRawData() const -> const std::vector<std::uint8_t>& {
  return raw_data_;
}

auto VectorData::getDimension() const -> size_t { return dimension_; }

auto VectorData::getDataType() const -> DataType { return data_type_; }

auto VectorData::size() const -> size_t { return dimension_; }

// Vector operations
auto VectorData::dotProduct(const VectorData& other) const -> float {
  if (dimension_ != other.dimension_) {
    throw std::invalid_argument("Vector dimensions must match for dot product");
  }

  float result = 0.0f;
  for (size_t i = 0; i < dimension_; ++i) {
    result += data_[i] * other.data_[i];
  }
  return result;
}

auto VectorData::cosineSimilarity(const VectorData& other) const -> float {
  float dot_product = dotProduct(other);
  float norm1 = 0.0f;
  float norm2 = 0.0f;

  for (float val : data_) {
    norm1 += val * val;
  }
  for (float val : other.data_) {
    norm2 += val * val;
  }

  norm1 = std::sqrt(norm1);
  norm2 = std::sqrt(norm2);

  if (norm1 == 0.0f || norm2 == 0.0f) {
    return 0.0f;
  }

  return dot_product / (norm1 * norm2);
}

auto VectorData::euclideanDistance(const VectorData& other) const -> float {
  if (dimension_ != other.dimension_) {
    throw std::invalid_argument("Vector dimensions must match");
  }

  float sum = 0.0f;
  for (size_t i = 0; i < dimension_; ++i) {
    float diff = data_[i] - other.data_[i];
    sum += diff * diff;
  }
  return std::sqrt(sum);
}

auto VectorData::manhattanDistance(const VectorData& other) const -> float {
  if (dimension_ != other.dimension_) {
    throw std::invalid_argument("Vector dimensions must match");
  }

  float sum = 0.0f;
  for (size_t i = 0; i < dimension_; ++i) {
    sum += std::abs(data_[i] - other.data_[i]);
  }
  return sum;
}

// Type conversion utilities
auto VectorData::toFloat32() const -> std::vector<float> {
  if (data_type_ == DataType::kFloat32) {
    return data_;
  }
  return convertToFloat32(raw_data_, data_type_);
}

auto VectorData::isQuantized() const -> bool {
  return data_type_ != DataType::kFloat32;
}

auto VectorData::isSparse() const -> bool {
  // Simplified - assume dense for now
  return false;
}

// Numpy-like interface compatibility
auto VectorData::getNumpyShape() const -> std::vector<size_t> {
  return {dimension_};
}

auto VectorData::getNumpyDtype() const -> std::string {
  switch (data_type_) {
    case DataType::kFloat32:
      return "float32";
    case DataType::kFloat16:
      return "float16";
    case DataType::kBFloat16:
      return "bfloat16";
    case DataType::kInt8:
      return "int8";
    case DataType::kUint8:
      return "uint8";
    default:
      return "unknown";
  }
}

// Helper functions
auto VectorData::getDataTypeSize(DataType dtype) -> size_t {
  switch (dtype) {
    case DataType::kFloat32:
      return 4;
    case DataType::kFloat16:
      return 2;
    case DataType::kBFloat16:
      return 2;
    case DataType::kInt8:
      return 1;
    case DataType::kUint8:
      return 1;
    default:
      return 4;
  }
}

auto VectorData::convertToFloat32(const std::vector<std::uint8_t>& raw_data,
                                  DataType dtype) -> std::vector<float> {
  // Simplified conversion - just return zeros for now
  size_t element_size = getDataTypeSize(dtype);
  size_t num_elements = raw_data.size() / element_size;
  return std::vector<float>(num_elements, 0.0f);
}

}  // namespace sage_flow
