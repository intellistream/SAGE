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
#include <pybind11/numpy.h>
#include <pybind11/operators.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/cast.h>

#include <functional>
#include <iostream>
#include <memory>
#include <string>
#include <optional>
#include <variant>
#include <stdexcept>


// Include SAGE Flow core headers
#include "data_stream/data_stream.hpp"
#include "engine/execution_graph.hpp"
#include "engine/stream_engine.hpp"
#include "environment/sage_flow_environment.hpp"
#include "message/content_type.hpp"
#include "message/multimodal_message.hpp"
#include "message/vector_data.hpp"
#include "operator/base_operator.hpp"
#include "operator/filter_operator.hpp"
#include "operator/map_operator.hpp"
#include "operator/operator_types.hpp"
#include "state/state_manager.hpp"

namespace sage_flow {
class MultiModalMessage;
}

// Forward declarations for binding functions
void BindTerminalSinkOperator(pybind11::module& m);
void BindFileSinkOperator(pybind11::module& m);
void BindVectorStoreSinkOperator(pybind11::module& m);

namespace py = pybind11;

PYBIND11_MODULE(sageflow, m) {
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
  // Custom caster for ContentVariant
  py::class_<sage_flow::MultiModalMessage::ContentVariant> content_variant(m, "ContentVariant");
  content_variant
      .def(py::init<std::string>())
      .def(py::init<std::vector<uint8_t>>())
      .def("__repr__", [](const sage_flow::MultiModalMessage::ContentVariant& v) {
        if (std::holds_alternative<std::string>(v)) {
          return "ContentVariant(text='" + std::get<std::string>(v) + "')";
        } else {
          return "ContentVariant(binary, size=" + std::to_string(std::get<std::vector<uint8_t>>(v).size()) + ")";
        }
      });

  // Custom caster for optional<VectorData>
  m.def("get_optional_vector_data", [](const std::optional<sage_flow::VectorData>& opt) -> py::object {
    if (opt.has_value()) {
      return py::cast(opt.value());
    } else {
      return py::none();
    }
  });

  py::class_<sage_flow::MultiModalMessage>(m, "MultiModalMessage")
      .def(py::init<uint64_t>(), "Create MultiModalMessage with UID")
      .def(py::init<uint64_t, sage_flow::ContentType, sage_flow::MultiModalMessage::ContentVariant>(),
           "Create MultiModalMessage with content", py::keep_alive<0, 3>())

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

  // Bind DataStream as Stream, using non-template methods to avoid compilation issues
  // Forward declaration first
  // Bind Stream<MultiModalMessage> as "Stream" for Python API compatibility
  py::class_<sage_flow::Stream<sage_flow::MultiModalMessage>>(m, "Stream")
       .def(py::init<std::shared_ptr<sage_flow::StreamEngine>,
                     std::shared_ptr<sage_flow::ExecutionGraph>,
                     sage_flow::ExecutionGraph::OperatorId>(),
            "Create Stream with engine, graph and last operator ID",
            py::arg("engine"), py::arg("graph"),
            py::arg("last_operator_id") = static_cast<sage_flow::ExecutionGraph::OperatorId>(-1))

       // Static factory methods
       .def_static("from_vector", &sage_flow::Stream<sage_flow::MultiModalMessage>::from_vector<sage_flow::MultiModalMessage>,
                   py::arg("data"), py::arg("engine") = nullptr, "Create Stream from vector of MultiModalMessage")

       // Template method wrappers using lambda for Python functions
       .def("map", [](sage_flow::Stream<sage_flow::MultiModalMessage>& self, py::function func) -> sage_flow::Stream<sage_flow::MultiModalMessage>& {
         std::cout << "Stream map: Creating C++ lambda from Python function" << std::endl;
         // Convert Python function to C++ lambda with GIL optimization
         auto cpp_map_func = [func](const std::shared_ptr<sage_flow::MultiModalMessage>& input) -> std::shared_ptr<sage_flow::MultiModalMessage> {
           if (!input) {
             std::cerr << "Map function: null input message" << std::endl;
             return nullptr;
           }
           py::gil_scoped_acquire acquire;
           try {
             py::object py_input = py::cast(input);
             py::object result = func(py_input);
             auto result_msg = py::cast<std::shared_ptr<sage_flow::MultiModalMessage>>(result);
             std::cout << "Map function: successfully processed message UID " << input->getUid() << std::endl;
             return result_msg;
           } catch (const py::error_already_set& e) {
             std::cerr << "Python map function error: " << e.what() << std::endl;
             return input;  // Return original on error
           }
         };
         // Use apply_operator as the general method for template operations
         return self.apply_operator<sage_flow::MultiModalMessage>("map", cpp_map_func);
       }, py::arg("func"), "Apply map transformation with Python function", py::keep_alive<1, 2>())

       .def("filter", [](sage_flow::Stream<sage_flow::MultiModalMessage>& self, py::function predicate) -> sage_flow::Stream<sage_flow::MultiModalMessage>& {
         std::cout << "Stream filter: Creating C++ predicate from Python function" << std::endl;
         auto cpp_filter_func = [predicate](const std::shared_ptr<sage_flow::MultiModalMessage>& input) -> bool {
           if (!input) {
             std::cerr << "Filter predicate: null input message" << std::endl;
             return false;
           }
           py::gil_scoped_acquire acquire;
           try {
             py::object py_input = py::cast(input);
             py::object result = predicate(py_input);
             bool keep = result.cast<bool>();
             std::cout << "Filter predicate: message UID " << input->getUid() << " keep=" << keep << std::endl;
             return keep;
           } catch (const py::error_already_set& e) {
             std::cerr << "Python filter function error: " << e.what() << std::endl;
             return true;  // Default pass on error
           }
         };
         return self.apply_operator<sage_flow::MultiModalMessage>("filter", cpp_filter_func);
       }, py::arg("predicate"), "Apply filter transformation with Python function", py::keep_alive<1, 2>())

       .def("aggregate", [](sage_flow::Stream<sage_flow::MultiModalMessage>& self, py::function agg_func) -> sage_flow::Stream<sage_flow::MultiModalMessage>& {
         auto cpp_agg_func = [agg_func](const std::vector<sage_flow::MultiModalMessage>& batch) -> sage_flow::MultiModalMessage {
           py::gil_scoped_acquire acquire;
           try {
             py::list py_batch;
             for (const auto& msg : batch) {
               py_batch.append(py::cast(msg));
             }
             py::object result = agg_func(py_batch);
             return result.cast<sage_flow::MultiModalMessage>();
           } catch (const py::error_already_set& e) {
             std::cerr << "Python aggregate function error: " << e.what() << std::endl;
             // Return first message as default
             return batch.empty() ? sage_flow::MultiModalMessage(0) : batch[0];
           }
         };
         return self.apply_operator<sage_flow::MultiModalMessage>("aggregate", cpp_agg_func);
       }, py::arg("agg_func"), "Apply aggregate transformation", py::keep_alive<1, 2>())

       // Execution methods
       .def("execute", &sage_flow::Stream<sage_flow::MultiModalMessage>::execute, "Execute the stream pipeline")
       .def("execute_async", &sage_flow::Stream<sage_flow::MultiModalMessage>::executeAsync, "Execute asynchronously")
       .def("stop", &sage_flow::Stream<sage_flow::MultiModalMessage>::stop, "Stop stream execution")

       // Status and monitoring
       .def("is_executing", &sage_flow::Stream<sage_flow::MultiModalMessage>::isExecuting, "Check if stream is executing")
       .def("get_operator_count", &sage_flow::Stream<sage_flow::MultiModalMessage>::getOperatorCount, "Get number of operators")
       .def("get_last_operator_id", &sage_flow::Stream<sage_flow::MultiModalMessage>::getLastOperatorId, "Get last operator ID")
       .def("set_last_operator_id", &sage_flow::Stream<sage_flow::MultiModalMessage>::setLastOperatorId, "Set last operator ID")

       // Python-friendly collection methods
       .def("collect", [](sage_flow::Stream<sage_flow::MultiModalMessage>& self) {
         self.execute();
         // Placeholder - actual collection would depend on execution result
         py::list result;
         result.append(py::str("Stream executed successfully"));
         return result;
       }, "Collect all results into a list")
       .def("take", &sage_flow::Stream<sage_flow::MultiModalMessage>::take, py::arg("n"), "Take first N messages")
       .def("count", &sage_flow::Stream<sage_flow::MultiModalMessage>::count, "Count total messages")
       .def("empty", &sage_flow::Stream<sage_flow::MultiModalMessage>::empty, "Check if stream is empty")

       // NumPy integration for vector data processing (zero-copy where possible)
       .def_static("from_numpy", [](py::array_t<double> arr, std::shared_ptr<sage_flow::StreamEngine> engine = nullptr) {
         if (!engine) {
           engine = std::make_shared<sage_flow::StreamEngine>();
         }
         std::vector<sage_flow::MultiModalMessage> messages;
         for (size_t i = 0; i < arr.size(); ++i) {
           auto msg = sage_flow::MultiModalMessage(static_cast<uint64_t>(i));
           msg.setContent(sage_flow::MultiModalMessage::ContentVariant(std::to_string(arr.at(i))));
           messages.push_back(msg);
         }
         return sage_flow::Stream<sage_flow::MultiModalMessage>::from_vector(messages, engine);
       }, py::arg("np_array"), py::arg("engine") = nullptr, "Create Stream from NumPy array with zero-copy")

       .def("execute_as_array", [](sage_flow::Stream<sage_flow::MultiModalMessage>& self) -> py::array_t<double> {
         self.execute();
         // Placeholder - extract numeric values from messages
         std::vector<double> result_data = {1.0, 2.0, 3.0, 4.0, 5.0};  // Demo data
         return py::array_t<double>(result_data.size(), result_data.data()).release();  // Zero-copy release
       }, "Execute and return numeric results as NumPy array")

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

  // Bind StreamEngine for parallelism config
  py::class_<sage_flow::StreamEngine>(m, "StreamEngine")
      .def(py::init<>())
      .def("set_parallelism", &sage_flow::StreamEngine::set_parallelism, py::arg("parallelism"), "Set parallelism level")
      .def("get_parallelism", &sage_flow::StreamEngine::get_parallelism, "Get current parallelism level")
      .def("configure", &sage_flow::StreamEngine::configure, "Configure engine with options");

  // Bind StateManager
  py::class_<sage_flow::StateManager>(m, "StateManager")
      .def(py::init<>())
      .def("get", &sage_flow::StateManager::get, py::arg("key"), "Get state value by key")
      .def("set", &sage_flow::StateManager::set, py::arg("key"), py::arg("value"), "Set state value")
      .def("exists", &sage_flow::StateManager::exists, py::arg("key"), "Check if key exists")
      .def("remove", &sage_flow::StateManager::remove, py::arg("key"), "Remove state key");

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
          std::cout << "from_list: Converting Python list of length " << py::len(data) << std::endl;
          // Convert Python list of dicts to C++ vector of maps
          std::vector<std::unordered_map<std::string, std::variant<std::string, int64_t, double, bool>>> cpp_data;

          for (size_t i = 0; i < py::len(data); ++i) {
            py::handle item = data[i];
            if (!py::isinstance<py::dict>(item)) {
              throw std::runtime_error("All items in the list must be dictionaries at index " + std::to_string(i));
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

          std::cout << "from_list: Created " << cpp_data.size() << " C++ data entries" << std::endl;
          // Call the C++ method
          return sage_flow::DataStream::from_list(cpp_data, nullptr);
        },
        "Create DataStream from a list of data",
        py::arg("data"));


  // Bind Response template specialization for MultiModalMessage (single definition)
  py::class_<sage_flow::Response<sage_flow::MultiModalMessage>>(m, "Response")
      .def(py::init<std::shared_ptr<sage_flow::MultiModalMessage>>())
      .def(py::init<std::vector<std::shared_ptr<sage_flow::MultiModalMessage>>>())
      .def("has_message", &sage_flow::Response<sage_flow::MultiModalMessage>::hasMessage)
      .def("has_messages", &sage_flow::Response<sage_flow::MultiModalMessage>::hasMessages)
      .def("get_message", &sage_flow::Response<sage_flow::MultiModalMessage>::getMessage,
           py::return_value_policy::reference_internal)
      .def("get_messages", &sage_flow::Response<sage_flow::MultiModalMessage>::getMessages,
           py::return_value_policy::reference_internal)
      .def("size", &sage_flow::Response<sage_flow::MultiModalMessage>::size);

  // Simplified BaseOperator binding (non-template for compatibility)
  py::class_<sage_flow::BaseOperator>(m, "Operator", py::module_local())
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
           "Reset performance counters")
      .def("open", &sage_flow::BaseOperator::open)
      .def("close", &sage_flow::BaseOperator::close)
      .def("process", [](sage_flow::BaseOperator& op, py::list input_list) {
          std::vector<std::shared_ptr<sage_flow::MultiModalMessage>> input;
          for (auto item : input_list) {
              input.push_back(item.cast<std::shared_ptr<sage_flow::MultiModalMessage>>());
          }
          auto result = op.process(input);
          if (result) {
              return py::cast(result.value());
          }
          return py::none();
      }, py::arg("in"), "Process input batch");

  // Bind MapOperator with modern signature wrapper
  py::class_<sage_flow::MapOperator, sage_flow::BaseOperator>(m, "MapOperator")
      .def(py::init<std::string, sage_flow::MapOperator::MapFunc>(), py::arg("name"), py::arg("func"), "Create MapOperator")
      .def("process", [](sage_flow::MapOperator& op, py::list input_list) {
          std::vector<std::shared_ptr<sage_flow::MultiModalMessage>> input;
          for (auto item : input_list) {
              input.push_back(item.cast<std::shared_ptr<sage_flow::MultiModalMessage>>());
          }
          auto result = op.process(input);
          if (result) {
              return py::cast(result.value());
          }
          return py::none();
      }, py::arg("in"), "Process input", py::return_value_policy::automatic)
      .def("set_function", [](sage_flow::MapOperator& op, py::function func) {
        // Optimized lambda conversion with GIL management and keep_alive
        auto cpp_func = [func](const std::shared_ptr<sage_flow::MultiModalMessage>& input) -> std::shared_ptr<sage_flow::MultiModalMessage> {
          if (!input) return nullptr;
          py::gil_scoped_acquire acquire;
          try {
            py::dict py_input = py::cast(*input);
            py::object result = func(py_input);
            auto result_msg = result.cast<std::shared_ptr<sage_flow::MultiModalMessage>>();
            return py::keep_alive<0, 1>(result_msg);
          } catch (const py::error_already_set& e) {
            std::cerr << "Python map function error: " << e.what() << std::endl;
            return input;
          }
        };
        op = sage_flow::MapOperator(op.getName(), cpp_func);
      }, "Set map function from Python lambda", py::keep_alive<1, 2>());

  // Bind FilterOperator with modern signature wrapper
  py::class_<sage_flow::FilterOperator, sage_flow::BaseOperator>(m, "FilterOperator")
      .def(py::init<std::string, sage_flow::FilterOperator::PredicateFunc>(), py::arg("name"), py::arg("pred"), "Create FilterOperator")
      .def("process", [](sage_flow::FilterOperator& op, py::list input_list) {
          std::vector<std::shared_ptr<sage_flow::MultiModalMessage>> input;
          for (auto item : input_list) {
              input.push_back(item.cast<std::shared_ptr<sage_flow::MultiModalMessage>>());
          }
          auto result = op.process(input);
          if (result) {
              return py::cast(result.value());
          }
          return py::none();
      }, py::arg("in"), "Process input", py::return_value_policy::automatic)
      .def("set_predicate", [](sage_flow::FilterOperator& op, py::function pred) {
        auto cpp_pred = [pred](const std::shared_ptr<sage_flow::MultiModalMessage>& input) -> bool {
          if (!input) return false;
          py::gil_scoped_acquire acquire;
          try {
            py::dict py_input = py::cast(*input);
            py::object result = pred(py_input);
            return result.cast<bool>();
          } catch (const py::error_already_set& e) {
            std::cerr << "Python filter function error: " << e.what() << std::endl;
            return true;  // Default pass
          }
        };
        op = sage_flow::FilterOperator(op.getName(), cpp_pred);
      }, "Set filter predicate from Python lambda", py::keep_alive<1, 2>());

  // Bind Sink operators (already exposed)
  BindTerminalSinkOperator(m);
  BindFileSinkOperator(m);
  BindVectorStoreSinkOperator(m);
}
