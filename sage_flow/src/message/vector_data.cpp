#include "message/vector_data.h"

#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>
#include <utility>

namespace sage_flow {

VectorData::VectorData(std::vector<float> data, size_t dimension)
    : data_(std::move(data)), dimension_(dimension), data_type_(DataType::kFloat32) {
  if (data_.size() != dimension_) {
    throw std::invalid_argument("Data size does not match specified dimension");
  }
}

VectorData::VectorData(const float* data, size_t dimension)
    : data_(data, data + dimension), dimension_(dimension), data_type_(DataType::kFloat32) {
  if (data == nullptr) {
    throw std::invalid_argument("Data pointer cannot be null");
  }
}

VectorData::VectorData(std::vector<std::uint8_t> data, size_t dimension, DataType dtype)
    : raw_data_(std::move(data)), dimension_(dimension), data_type_(dtype) {
  if (raw_data_.size() != dimension_ * getDataTypeSize(dtype)) {
    throw std::invalid_argument("Raw data size does not match dimension and data type");
  }
  data_ = convertToFloat32(raw_data_, dtype);
}

VectorData::VectorData(const VectorData& other) = default;

auto VectorData::operator=(const VectorData& other) -> VectorData& {
  if (this != &other) {
    data_ = other.data_;
    raw_data_ = other.raw_data_;
    dimension_ = other.dimension_;
    data_type_ = other.data_type_;
  }
  return *this;
}

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

auto VectorData::getData() const -> const std::vector<float>& {
  return data_;
}

auto VectorData::getRawData() const -> const std::vector<std::uint8_t>& {
  return raw_data_;
}

auto VectorData::getDimension() const -> size_t {
  return dimension_;
}

auto VectorData::getDataType() const -> DataType {
  return data_type_;
}

auto VectorData::size() const -> size_t {
  return data_.size();
}

auto VectorData::dotProduct(const VectorData& other) const -> float {
  if (dimension_ != other.dimension_) {
    throw std::invalid_argument("Vector dimensions must match for dot product");
  }
  
  return std::inner_product(data_.begin(), data_.end(), other.data_.begin(), 0.0F);
}

auto VectorData::cosineSimilarity(const VectorData& other) const -> float {
  if (dimension_ != other.dimension_) {
    throw std::invalid_argument("Vector dimensions must match for cosine similarity");
  }
  
  float dot_prod = dotProduct(other);
  
  float norm_this = std::sqrt(std::inner_product(data_.begin(), data_.end(), data_.begin(), 0.0F));
  float norm_other = std::sqrt(std::inner_product(other.data_.begin(), other.data_.end(), 
                                                 other.data_.begin(), 0.0F));
  
  if (norm_this == 0.0F || norm_other == 0.0F) {
    return 0.0F;
  }
  
  return dot_prod / (norm_this * norm_other);
}

auto VectorData::euclideanDistance(const VectorData& other) const -> float {
  if (dimension_ != other.dimension_) {
    throw std::invalid_argument("Vector dimensions must match for Euclidean distance");
  }
  
  float distance = 0.0F;
  for (size_t i = 0; i < dimension_; ++i) {
    float diff = data_[i] - other.data_[i];
    distance += diff * diff;
  }
  
  return std::sqrt(distance);
}

auto VectorData::manhattanDistance(const VectorData& other) const -> float {
  if (dimension_ != other.dimension_) {
    throw std::invalid_argument("Vector dimensions must match for Manhattan distance");
  }
  
  float distance = 0.0F;
  for (size_t i = 0; i < dimension_; ++i) {
    distance += std::abs(data_[i] - other.data_[i]);
  }
  
  return distance;
}

auto VectorData::toFloat32() const -> std::vector<float> {
  return data_;
}

auto VectorData::isQuantized() const -> bool {
  return data_type_ != DataType::kFloat32;
}

auto VectorData::isSparse() const -> bool {
  // Simple heuristic: consider sparse if more than 50% are zeros
  auto zero_count = static_cast<size_t>(std::count(data_.begin(), data_.end(), 0.0F));
  return (static_cast<float>(zero_count) / static_cast<float>(data_.size())) > 0.5F;
}

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
  }
  return "float32";
}

auto VectorData::getDataTypeSize(DataType dtype) -> size_t {
  switch (dtype) {
    case DataType::kFloat32:
      return sizeof(float);
    case DataType::kFloat16:
    case DataType::kBFloat16:
      return 2;
    case DataType::kInt8:
    case DataType::kUint8:
      return 1;
  }
  return sizeof(float);
}

auto VectorData::convertToFloat32(const std::vector<std::uint8_t>& raw_data, DataType dtype) -> std::vector<float> {
  std::vector<float> result;
  
  switch (dtype) {
    case DataType::kFloat32: {
      const auto* float_data = reinterpret_cast<const float*>(raw_data.data());
      result.assign(float_data, float_data + raw_data.size() / sizeof(float));
      break;
    }
    case DataType::kInt8: {
      const auto* int8_data = reinterpret_cast<const int8_t*>(raw_data.data());
      result.reserve(raw_data.size());
      for (size_t i = 0; i < raw_data.size(); ++i) {
        result.push_back(static_cast<float>(int8_data[i]));
      }
      break;
    }
    case DataType::kUint8: {
      result.reserve(raw_data.size());
      for (std::uint8_t byte : raw_data) {
        result.push_back(static_cast<float>(byte));
      }
      break;
    }
    case DataType::kFloat16:
    case DataType::kBFloat16:
      // Simplified conversion - would need proper half-precision conversion in production
      result.reserve(raw_data.size() / 2);
      for (size_t i = 0; i < raw_data.size(); i += 2) {
        // Placeholder conversion - real implementation would decode IEEE 754 half precision
        result.push_back(static_cast<float>(raw_data[i]) / 255.0F);
      }
      break;
  }
  
  return result;
}

}  // namespace sage_flow
