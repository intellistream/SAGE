#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <cstdint>
#include <stdexcept>
#include <memory> // For std::shared_ptr if needed
#include <ctime>  // For potential timestamp generation, though we'll use index here

// Assuming sageFlow headers are accessible via include path
#include "common/data_types.h" // For DataType enum

using namespace candy;

// Function to read vectors from an fvecs file (remains the same)
int read_fvecs(const std::string& filename, std::vector<float>& data, int expected_dim = -1) {
    std::ifstream input(filename, std::ios::binary);
    if (!input.is_open()) {
        throw std::runtime_error("Cannot open file: " + filename);
    }

    int dimension = 0;
    int vector_count = 0;
    std::vector<float> vector_buffer; // Temporary buffer for one vector

    while (true) {
        // Read dimension for the current vector
        int current_dim = 0;
        input.read(reinterpret_cast<char*>(&current_dim), sizeof(int));

        if (input.eof()) {
            break; // End of file reached cleanly
        }
        if (input.fail()) {
             throw std::runtime_error("Error reading dimension from file: " + filename);
        }

        if (vector_count == 0) {
            dimension = current_dim; // Set dimension from the first vector
            if (expected_dim != -1 && dimension != expected_dim) {
                 throw std::runtime_error("Unexpected dimension in file " + filename +
                                          ". Expected " + std::to_string(expected_dim) +
                                          ", got " + std::to_string(dimension));
            }
            if (dimension <= 0) {
                 throw std::runtime_error("Invalid dimension read from file: " + std::to_string(dimension));
            }
            vector_buffer.resize(dimension); // Resize buffer once
        } else if (current_dim != dimension) {
            // Check consistency
            throw std::runtime_error("Inconsistent dimension found in file " + filename +
                                      ". Expected " + std::to_string(dimension) +
                                      ", found " + std::to_string(current_dim) +
                                      " at vector index " + std::to_string(vector_count));
        }

        // Read vector data
        input.read(reinterpret_cast<char*>(vector_buffer.data()), dimension * sizeof(float));
        if (input.fail()) {
             throw std::runtime_error("Error reading vector data from file: " + filename +
                                      " at vector index " + std::to_string(vector_count));
        }

        // Append vector data to the main data buffer
        data.insert(data.end(), vector_buffer.begin(), vector_buffer.end());
        vector_count++;
    }

    input.close();

    if (vector_count == 0 && dimension == 0) {
        std::cerr << "Warning: Input file " << filename << " might be empty or invalid." << std::endl;
    } else {
         std::cout << "Read " << vector_count << " vectors of dimension " << dimension << " from " << filename << std::endl;
    }

    return dimension; // Return the dimension found
}

// Function to write data to vector_records.bin format, matching generate_vector_records.cpp
void write_vector_records_compatible(const std::string& output_filename,
                                     const std::vector<float>& data,
                                     int dimension,
                                     DataType data_type = DataType::Float32) {

    if (dimension <= 0 || data.empty() || data.size() % dimension != 0) {
        throw std::invalid_argument("Invalid data or dimension for writing vector records.");
    }
    if (data_type != DataType::Float32) {
        // This simple writer currently only supports Float32 from fvecs
        throw std::invalid_argument("This writer currently only supports DataType::Float32.");
    }

    std::ofstream output(output_filename, std::ios::binary | std::ios::trunc);
    if (!output.is_open()) {
        throw std::runtime_error("Cannot open output file: " + output_filename);
    }

    size_t num_vectors_size_t = data.size() / dimension;
    // if (num_vectors_size_t > std::numeric_limits<int32_t>::max()) {
    //      throw std::runtime_error("Too many vectors to fit in int32_t count.");
    // }
    int32_t num_vectors = static_cast<int32_t>(num_vectors_size_t); // Cast for header

    size_t vector_byte_size = static_cast<size_t>(dimension) * sizeof(float);
    int32_t dim32 = static_cast<int32_t>(dimension); // Cast dimension to int32_t
    int32_t type32 = static_cast<int32_t>(data_type); // Cast enum to int32_t

    std::cout << "Writing " << num_vectors << " records to " << output_filename
              << " (compatible format)..." << std::endl;

    // --- Write Header: Number of records ---
    output.write(reinterpret_cast<const char*>(&num_vectors), sizeof(int32_t));
    if (output.fail()) {
        throw std::runtime_error("Error writing record count header to file: " + output_filename);
    }

    // --- Write Records ---
    for (int32_t i = 0; i < num_vectors; ++i) {
        uint64_t uid = static_cast<uint64_t>(i + 1); // Assign simple UIDs starting from 1
        int64_t timestamp = static_cast<int64_t>(i); // Use index as placeholder timestamp
        const float* vector_start = data.data() + static_cast<size_t>(i) * dimension;

        // Write fields in the order matching VectorRecord::Serialize (hypothesized)
        // 1. uid (uint64_t)
        output.write(reinterpret_cast<const char*>(&uid), sizeof(uint64_t));
        // 2. timestamp (int64_t)
        output.write(reinterpret_cast<const char*>(&timestamp), sizeof(int64_t));
        // 3. dimension (int32_t)
        output.write(reinterpret_cast<const char*>(&dim32), sizeof(int32_t));
        // 4. data type (int32_t representation of the enum)
        output.write(reinterpret_cast<const char*>(&type32), sizeof(int32_t));
        // 5. raw vector data
        output.write(reinterpret_cast<const char*>(vector_start), vector_byte_size);

        if (output.fail()) {
            throw std::runtime_error("Error writing record " + std::to_string(uid) + " to file: " + output_filename);
        }
    }

    output.close();
    std::cout << "Successfully wrote " << num_vectors << " records to " << output_filename << std::endl;
}


int main(int argc, char* argv[]) {
    // Use command line arguments again for flexibility
    // if (argc != 3) {
    //     std::cerr << "Usage: " << argv[0] << " <input_fvecs_file> <output_vector_records_bin_file>" << std::endl;
    //     return 1;
    // }

    std::string input_filename = "data/siftsmall/siftsmall_query.fvecs"; // ;
    std::string output_filename = "data/siftsmall_bin/siftsmall_query.bin"; // ;
    int expected_dimension = 128; // SIFT dimension

    try {
        std::vector<float> all_vector_data;
        int dimension = read_fvecs(input_filename, all_vector_data, expected_dimension);

        if (dimension > 0 && !all_vector_data.empty()) {
            // Call the updated writing function
            write_vector_records_compatible(output_filename, all_vector_data, dimension, DataType::Float32);
        } else {
             std::cerr << "No valid data read from input file. Output file not created." << std::endl;
             return 1;
        }

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}