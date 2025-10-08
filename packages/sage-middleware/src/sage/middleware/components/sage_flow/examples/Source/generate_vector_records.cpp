#include <fstream>
#include <iostream>
#include <random>
#include <string>
#include <vector>

#include "common/data_types.h"
static int cnt = 0;

// Helper function to generate a random vector
auto GenerateRandomVectorData(std::mt19937& gen, int dim, candy::DataType data_type) -> candy::VectorData {
  candy::VectorData vector_data(dim, data_type);
  float begin = 0;
  float end = 1.0F;
  // Create distributions based on data type
  std::uniform_int_distribution<int> int_dist(-100, 100);
  std::uniform_real_distribution<float> float_dist(begin, end);
  std::uniform_real_distribution<double> double_dist(-100.0, 100.0);

  // Fill the vector with random data based on its type
  int element_size = candy::DATA_TYPE_SIZE[data_type];
  for (int i = 0; i < dim; ++i) {
    switch (data_type) {
      case candy::Int8: {
        auto value = static_cast<int8_t>(int_dist(gen) % 128);
        std::memcpy(vector_data.data_.get() + i * element_size, &value, element_size);
        break;
      }
      case candy::Int16: {
        auto value = static_cast<int16_t>(int_dist(gen));
        std::memcpy(vector_data.data_.get() + i * element_size, &value, element_size);
        break;
      }
      case candy::Int32: {
        int32_t value = int_dist(gen);
        std::memcpy(vector_data.data_.get() + i * element_size, &value, element_size);
        break;
      }
      case candy::Int64: {
        auto value = static_cast<int64_t>(int_dist(gen));
        std::memcpy(vector_data.data_.get() + i * element_size, &value, element_size);
        break;
      }
      case candy::Float32: {
        float value = float_dist(gen);
        std::memcpy(vector_data.data_.get() + i * element_size, &value, element_size);
        break;
      }
      case candy::Float64: {
        double value = double_dist(gen);
        std::memcpy(vector_data.data_.get() + i * element_size, &value, element_size);
        break;
      }
      default:
        break;
    }
  }

  return vector_data;
}

auto main(int argc, char* argv[]) -> int {
  // Set the output file path
  const int num_records = 100000;
  int32_t dim = 25;
  std::string output_path = "vector_records_" + std::to_string(dim) + "_" + std::to_string(num_records) + ".bin";
  if (argc > 1) {
    output_path = argv[1];
  }

  // Open output file
  std::ofstream output_file(output_path, std::ios::binary);
  if (!output_file.is_open()) {
    std::cerr << "Failed to open output file: " << output_path << std::endl;
    return 1;
  }

  // Set up random number generator
  std::random_device rd;
  std::mt19937 gen(rd());

  // Distributions for various fields
  std::uniform_int_distribution<uint64_t> uid_dist(1, 1000000);
  std::uniform_int_distribution<int> dim_dist(2, 1024);  // Dimensions between 2 and 1024
  std::uniform_int_distribution<int> type_dist(1, 6);    // Data types from Int8 to Float64

  // Current timestamp as starting point
  auto base_timestamp = static_cast<int64_t>(time(nullptr));

  // Generate and write 1000 vector records

  std::cout << "Generating " << num_records << " vector records..." << std::endl;

  // Write number of records as header
  int32_t record_count = num_records;
  output_file.write(reinterpret_cast<char*>(&record_count), sizeof(int32_t));
  candy::DataType type = candy::Float32;
  for (int i = 0; i < num_records; ++i) {
    // Generate random values for the vector record
    uint64_t uid = i;
    int64_t timestamp = base_timestamp + i;  // Sequential timestamps

    // Generate random vector data
    candy::VectorData vector_data = GenerateRandomVectorData(gen, dim, type);

    // Create vector record

    // Serialize and write to file
    if (candy::VectorRecord record(uid, timestamp, std::move(vector_data)); !record.Serialize(output_file)) {
      std::cerr << "Failed to serialize record " << i << '\n';
      output_file.close();
      return 1;
    }

    // Progress output
    if (i % 100 == 0) {
      std::cout << "Generated " << i << " records..." << '\n';
    }
  }

  output_file.close();
  std::cout << "Successfully generated " << num_records << " vector records to " << output_path << '\n';

  return 0;
}
