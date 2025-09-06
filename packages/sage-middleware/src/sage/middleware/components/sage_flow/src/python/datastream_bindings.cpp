/**
 * @file datastream_bindings.cpp
 * @brief Python bindings for SAGE Flow DataStream API
 *
 * This file provides Python bindings for the actual SAGE Flow DataStream API,
 * enabling seamless integration with sage_examples and sage_core Python code.
 *
 * Binds original MultiModalMessage and DataStream classes directly.
 */

#include <pybind11/functional.h>
#include <pybind11/operators.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <functional>
#include <iostream>
#include <memory>
#include <string>

// Include SAGE Flow core headers
#include "data_stream/data_stream.hpp"
#include "engine/execution_graph.hpp"
#include "engine/stream_engine.hpp"
#include "environment/sage_flow_environment.hpp"
#include "message/content_type.hpp"
#include "message/multimodal_message.hpp"
#include "message/vector_data.hpp"
#include "operator/base_operator.hpp"
#include "operator/operator_types.hpp"

// Forward declarations for binding functions
void BindTerminalSinkOperator(pybind11::module& m);
void BindFileSinkOperator(pybind11::module& m);
void BindVectorStoreSinkOperator(pybind11::module& m);

namespace py = pybind11;

PYBIND11_MODULE(sage_flow_datastream, m) {
  m.doc() = "SAGE Flow DataStream API - Python bindings for original classes";

  // Bind ContentType enum
  py::enum_<sage_flow::ContentType>(m, "ContentType")
      .value("TEXT", sage_flow::ContentType::kText)
      .value("BINARY", sage_flow::ContentType::kBinary)
      .value("IMAGE", sage_flow::ContentType::kImage)
      .value("AUDIO", sage_flow::ContentType::kAudio)
      .value("VIDEO", sage_flow::ContentType::kVideo)
      .value("EMBEDDING", sage_flow::ContentType::kEmbedding)
      .value("METADATA", sage_flow::ContentType::kMetadata);

  // Bind VectorData
  py::enum_<sage_flow::VectorData::DataType>(m, "VectorDataType")
      .value("FLOAT32", sage_flow::VectorData::DataType::kFloat32)
      .value("FLOAT16", sage_flow::VectorData::DataType::kFloat16)
      .value("BFLOAT16", sage_flow::VectorData::DataType::kBFloat16)
      .value("INT8", sage_flow::VectorData::DataType::kInt8)
      .value("UINT8", sage_flow::VectorData::DataType::kUint8);

  py::class_<sage_flow::VectorData>(m, "VectorData")
      .def(py::init<std::vector<float>, size_t>(),
           "Create VectorData from float vector")
      .def(py::init<std::vector<std::uint8_t>, size_t,
                    sage_flow::VectorData::DataType>(),
           "Create VectorData from quantized data")
      .def("get_data", &sage_flow::VectorData::getData, "Get float data",
           py::return_value_policy::reference_internal)
      .def("get_raw_data", &sage_flow::VectorData::getRawData, "Get raw data",
           py::return_value_policy::reference_internal)
      .def("get_dimension", &sage_flow::VectorData::getDimension,
           "Get vector dimension")
      .def("get_data_type", &sage_flow::VectorData::getDataType,
           "Get data type")
      .def("size", &sage_flow::VectorData::size, "Get data size")
      .def("dot_product", &sage_flow::VectorData::dotProduct,
           "Calculate dot product with another vector")
      .def("cosine_similarity", &sage_flow::VectorData::cosineSimilarity,
           "Calculate cosine similarity with another vector")
      .def("euclidean_distance", &sage_flow::VectorData::euclideanDistance,
           "Calculate Euclidean distance to another vector")
      .def("manhattan_distance", &sage_flow::VectorData::manhattanDistance,
           "Calculate Manhattan distance to another vector")
      .def("to_float32", &sage_flow::VectorData::toFloat32,
           "Convert to float32 vector")
      .def("is_quantized", &sage_flow::VectorData::isQuantized,
           "Check if data is quantized");

  // Bind MultiModalMessage - the original class with Python-friendly interface
  py::class_<sage_flow::MultiModalMessage>(m, "MultiModalMessage")
      .def(py::init<uint64_t>(), "Create MultiModalMessage with UID")
      .def(py::init<uint64_t, sage_flow::ContentType,
                    sage_flow::MultiModalMessage::ContentVariant>(),
           "Create MultiModalMessage with content")

      // Accessors
      .def("get_uid", &sage_flow::MultiModalMessage::getUid,
           "Get the unique ID of the message")
      .def("get_timestamp", &sage_flow::MultiModalMessage::getTimestamp,
           "Get the timestamp of the message")
      .def("get_content_type", &sage_flow::MultiModalMessage::getContentType,
           "Get the content type")
      .def("get_content", &sage_flow::MultiModalMessage::getContent,
           "Get the content (variant of string or binary data)")
      .def("get_metadata", &sage_flow::MultiModalMessage::getMetadata,
           "Get metadata map")
      .def("get_processing_trace",
           &sage_flow::MultiModalMessage::getProcessingTrace,
           "Get processing trace")
      .def("get_quality_score", &sage_flow::MultiModalMessage::getQualityScore,
           "Get quality score if available")

      // Mutators
      .def("set_content", &sage_flow::MultiModalMessage::setContent,
           "Set the content")
      .def("set_content_type", &sage_flow::MultiModalMessage::setContentType,
           "Set the content type")
      .def("set_metadata", &sage_flow::MultiModalMessage::setMetadata,
           "Set metadata key-value pair")
      .def("add_processing_step",
           &sage_flow::MultiModalMessage::addProcessingStep,
           "Add processing step to trace")
      .def("set_quality_score", &sage_flow::MultiModalMessage::setQualityScore,
           "Set quality score")

      // Utility methods
      .def("has_embedding", &sage_flow::MultiModalMessage::hasEmbedding,
           "Check if message has embedding")
      .def("is_text_content", &sage_flow::MultiModalMessage::isTextContent,
           "Check if content is text")
      .def("is_binary_content", &sage_flow::MultiModalMessage::isBinaryContent,
           "Check if content is binary")
      .def("get_content_as_string",
           &sage_flow::MultiModalMessage::getContentAsString,
           "Get content as string (for text content)")
      .def("get_content_as_binary",
           &sage_flow::MultiModalMessage::getContentAsBinary,
           "Get content as binary data")

      // Python-friendly representation
      .def("__repr__", [](const sage_flow::MultiModalMessage& msg) {
        return "MultiModalMessage(uid=" + std::to_string(msg.getUid()) +
               ", content_type=" +
               std::to_string(static_cast<int>(msg.getContentType())) + ")";
      });

  // Bind DataStream - using lambdas to handle move semantics properly
  py::class_<sage_flow::DataStream>(m, "DataStream")
       // Add constructor binding to fix segmentation fault
       .def(py::init<std::shared_ptr<sage_flow::StreamEngine>,
                     std::shared_ptr<sage_flow::ExecutionGraph>,
                     sage_flow::ExecutionGraph::OperatorId>(),
            "Create DataStream with engine, graph and last operator ID",
            py::arg("engine"), py::arg("graph"),
            py::arg("last_operator_id") =
                static_cast<sage_flow::ExecutionGraph::OperatorId>(-1))

       // Core DataStream operations - simplified for pybind11 compatibility
       .def("execute", &sage_flow::DataStream::execute,
            "Execute the stream pipeline")
       .def("stop", &sage_flow::DataStream::stop, "Stop stream execution")
       .def("get_operator_count", &sage_flow::DataStream::getOperatorCount,
            "Get number of operators in the stream")
       .def("is_executing", &sage_flow::DataStream::isExecuting,
            "Check if stream is executing")

       // Execution control
       .def("execute_async", &sage_flow::DataStream::executeAsync,
            "Execute the stream pipeline asynchronously")
       .def("stop", &sage_flow::DataStream::stop, "Stop stream execution")

       // Pipeline information
       .def("get_operator_count", &sage_flow::DataStream::getOperatorCount,
            "Get number of operators in the stream")
       .def("is_executing", &sage_flow::DataStream::isExecuting,
            "Check if stream is executing")
       .def("get_last_operator_id", &sage_flow::DataStream::getLastOperatorId,
            "Get last operator ID")
       .def("set_last_operator_id", &sage_flow::DataStream::setLastOperatorId,
            "Set last operator ID")

       // Python-friendly methods
       .def("collect", &sage_flow::DataStream::collect,
            "Collect all results into a list",
            py::return_value_policy::move)
       .def("take", &sage_flow::DataStream::take,
            "Take first N messages from stream",
            py::arg("n"))
       .def("count", &sage_flow::DataStream::count,
            "Count total messages in stream")
       .def("empty", &sage_flow::DataStream::empty,
            "Check if stream is empty")

       // Stream processing operations with lambda support
       .def("map",
            [](sage_flow::DataStream& self, py::function func) -> sage_flow::DataStream& {
              // Convert Python function to C++ lambda with proper message handling
              auto cpp_func = [func](std::unique_ptr<sage_flow::MultiModalMessage> msg) -> std::unique_ptr<sage_flow::MultiModalMessage> {
                if (!msg) return nullptr;

                py::gil_scoped_acquire acquire;
                try {
                  // Convert C++ message to Python dict for easier manipulation
                  py::dict py_msg;
                  py_msg["uid"] = msg->getUid();
                  py_msg["content_type"] = static_cast<int>(msg->getContentType());

                  // Convert content based on type
                  if (msg->getContentType() == sage_flow::ContentType::kText) {
                    py_msg["content"] = msg->getContentAsString();
                  } else {
                    // For binary content, convert to bytes
                    auto binary_data = msg->getContentAsBinary();
                    py_msg["content"] = py::bytes(std::string(binary_data.begin(), binary_data.end()));
                  }

                  // Add metadata
                  py_msg["metadata"] = msg->getMetadata();

                  // Call Python function
                  py::object result = func(py_msg);

                  // Convert result back to C++ message
                  if (py::isinstance<py::dict>(result)) {
                    py::dict result_dict = result.cast<py::dict>();

                    uint64_t uid = result_dict["uid"].cast<uint64_t>();
                    auto content_type = static_cast<sage_flow::ContentType>(result_dict["content_type"].cast<int>());

                    std::string content_str;
                    if (result_dict.contains("content")) {
                      if (py::isinstance<py::str>(result_dict["content"])) {
                        content_str = result_dict["content"].cast<std::string>();
                      } else if (py::isinstance<py::bytes>(result_dict["content"])) {
                        content_str = result_dict["content"].cast<std::string>();
                      }
                    }

                    auto new_msg = std::make_unique<sage_flow::MultiModalMessage>(
                        uid, content_type,
                        sage_flow::MultiModalMessage::ContentVariant(content_str)
                    );

                    // Copy metadata if present
                    if (result_dict.contains("metadata")) {
                      py::dict metadata = result_dict["metadata"].cast<py::dict>();
                      for (auto item : metadata) {
                        std::string key = item.first.cast<std::string>();
                        std::string value = item.second.cast<std::string>();
                        new_msg->setMetadata(key, value);
                      }
                    }

                    return new_msg;
                  } else {
                    // If Python function doesn't return dict, return original message
                    return std::move(msg);
                  }
                } catch (const py::error_already_set& e) {
                  // Log error and return original message
                  std::cerr << "Python map function error: " << e.what() << std::endl;
                  return std::move(msg);
                }
              };
              return self.map(cpp_func);
            },
            py::arg("func"),
            "Apply map transformation with Python function",
            py::return_value_policy::reference_internal)

       .def("filter",
            [](sage_flow::DataStream& self, py::function predicate) -> sage_flow::DataStream& {
              // Convert Python function to C++ lambda
              auto cpp_predicate = [predicate](const sage_flow::MultiModalMessage& msg) -> bool {
                py::gil_scoped_acquire acquire;
                try {
                  // Convert C++ message to Python object
                  py::object py_msg = py::cast(&msg, py::return_value_policy::reference);
                  // Call Python function
                  py::object result = predicate(py_msg);
                  return result.cast<bool>();
                } catch (const py::error_already_set& e) {
                  throw std::runtime_error("Python filter function error: " + std::string(e.what()));
                }
              };
              return self.filter(cpp_predicate);
            },
            py::arg("predicate"),
            "Apply filter transformation with Python function",
            py::return_value_policy::reference_internal)

       .def("sink",
            [](sage_flow::DataStream& self, py::function sink_func) {
              // Convert Python function to C++ lambda
              auto cpp_sink = [sink_func](const sage_flow::MultiModalMessage& msg) {
                py::gil_scoped_acquire acquire;
                try {
                  // Convert C++ message to Python object
                  py::object py_msg = py::cast(&msg, py::return_value_policy::reference);
                  // Call Python function
                  sink_func(py_msg);
                } catch (const py::error_already_set& e) {
                  throw std::runtime_error("Python sink function error: " + std::string(e.what()));
                }
              };
              self.sink(cpp_sink);
            },
            py::arg("sink_func"),
            "Apply sink operation with Python function");

  // Bind SageFlowEnvironment - the factory for DataStreams
  py::class_<sage_flow::SageFlowEnvironment>(m, "Environment")
      .def(py::init<std::string>(), "Create environment with job name")
      .def(py::init<sage_flow::EnvironmentConfig>(),
           "Create environment with config")
      .def("set_memory", &sage_flow::SageFlowEnvironment::set_memory,
           "Set memory configuration")
      .def("set_property", &sage_flow::SageFlowEnvironment::set_property,
           "Set environment property")
      .def("get_property", &sage_flow::SageFlowEnvironment::get_property,
           "Get environment property")
      .def("get_job_name", &sage_flow::SageFlowEnvironment::get_job_name,
           "Get job name", py::return_value_policy::reference_internal)
      .def(
          "create_datastream",
          [](sage_flow::SageFlowEnvironment& self) {
            return self.create_datastream();
          },
          "Create a new DataStream")
      .def("submit", &sage_flow::SageFlowEnvironment::submit,
           "Submit job for execution")
      .def("close", &sage_flow::SageFlowEnvironment::close,
           "Close environment and cleanup")

      // Python-friendly methods
      .def("get_config", &sage_flow::SageFlowEnvironment::get_config,
           "Get environment configuration")
      .def("is_ready", &sage_flow::SageFlowEnvironment::is_ready,
           "Check if environment is ready")
      .def("get_status", &sage_flow::SageFlowEnvironment::get_status,
           "Get environment status information");

  // Bind EnvironmentConfig
  py::class_<sage_flow::EnvironmentConfig>(m, "EnvironmentConfig")
      .def(py::init<>(), "Create default environment config")
      .def(py::init<std::string>(), "Create environment config with job name")
      .def_readwrite("job_name", &sage_flow::EnvironmentConfig::job_name_)
      .def_readwrite("memory_config",
                     &sage_flow::EnvironmentConfig::memory_config_)
      .def_readwrite("properties", &sage_flow::EnvironmentConfig::properties_);

  // Utility functions for creating messages
  m.def(
      "create_text_message",
      [](uint64_t uid, const std::string& text) {
        return std::make_unique<sage_flow::MultiModalMessage>(
            uid, sage_flow::ContentType::kText,
            sage_flow::MultiModalMessage::ContentVariant(text));
      },
      "Create a text message");

  m.def(
      "create_binary_message",
      [](uint64_t uid, const std::vector<uint8_t>& data) {
        return std::make_unique<sage_flow::MultiModalMessage>(
            uid, sage_flow::ContentType::kBinary,
            sage_flow::MultiModalMessage::ContentVariant(data));
      },
      "Create a binary message");

  // Standalone from_list function for Python API compatibility
  m.def("from_list",
        [](py::list data) {
          // Convert Python list of dicts to C++ vector of maps
          std::vector<std::unordered_map<std::string, std::variant<std::string, int64_t, double, bool>>> cpp_data;

          for (auto item : data) {
            if (!py::isinstance<py::dict>(item)) {
              throw std::runtime_error("All items in the list must be dictionaries");
            }

            py::dict py_dict = item.cast<py::dict>();
            std::unordered_map<std::string, std::variant<std::string, int64_t, double, bool>> cpp_dict;

            for (auto pair : py_dict) {
              std::string key = pair.first.cast<std::string>();

              // Convert Python values to C++ variants
              if (py::isinstance<py::str>(pair.second)) {
                cpp_dict[key] = pair.second.cast<std::string>();
              } else if (py::isinstance<py::int_>(pair.second)) {
                cpp_dict[key] = static_cast<int64_t>(pair.second.cast<long>());
              } else if (py::isinstance<py::float_>(pair.second)) {
                cpp_dict[key] = pair.second.cast<double>();
              } else if (py::isinstance<py::bool_>(pair.second)) {
                cpp_dict[key] = pair.second.cast<bool>();
              } else {
                throw std::runtime_error("Unsupported value type for key '" + key + "'");
              }
            }

            cpp_data.push_back(std::move(cpp_dict));
          }

          // Call the C++ method
          return sage_flow::DataStream::from_list(cpp_data, nullptr);
        },
        "Create DataStream from a list of data",
        py::arg("data"));


  // Bind base Operator class
  py::enum_<sage_flow::OperatorType>(m, "OperatorType")
      .value("SOURCE", sage_flow::OperatorType::kSource)
      .value("MAP", sage_flow::OperatorType::kMap)
      .value("FILTER", sage_flow::OperatorType::kFilter)
      .value("SINK", sage_flow::OperatorType::kSink);

  py::class_<sage_flow::BaseOperator>(m, "Operator")
      .def("get_type", &sage_flow::BaseOperator::getType,
           "Get the operator type")
      .def("get_name", &sage_flow::BaseOperator::getName,
           "Get the operator name")
      .def("set_name", &sage_flow::BaseOperator::setName,
           "Set the operator name")
      .def("get_processed_count", &sage_flow::BaseOperator::getProcessedCount,
           "Get number of processed records")
      .def("get_output_count", &sage_flow::BaseOperator::getOutputCount,
           "Get number of output records")
      .def("reset_counters", &sage_flow::BaseOperator::resetCounters,
           "Reset performance counters");

  // Bind Sink operators
  BindTerminalSinkOperator(m);
  BindFileSinkOperator(m);
  BindVectorStoreSinkOperator(m);
}
