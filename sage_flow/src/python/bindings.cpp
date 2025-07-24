#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

#include "message/multimodal_message.h"

namespace py = pybind11;

PYBIND11_MODULE(sage_flow_py, m) {
    m.doc() = "SAGE Flow C++ Python bindings for high-performance data processing";
    
    // ContentType enum
    py::enum_<sage_flow::ContentType>(m, "ContentType")
        .value("TEXT", sage_flow::ContentType::kText)
        .value("IMAGE", sage_flow::ContentType::kImage)
        .value("AUDIO", sage_flow::ContentType::kAudio)
        .value("VIDEO", sage_flow::ContentType::kVideo)
        .value("BINARY", sage_flow::ContentType::kBinary);
    
    // VectorData class
    py::class_<sage_flow::VectorData>(m, "VectorData")
        .def(py::init<std::vector<float>, size_t>(), 
             "Constructor with vector data and dimension")
        .def("get_data", &sage_flow::VectorData::getData, 
             "Get the vector data", py::return_value_policy::reference_internal)
        .def("get_dimension", &sage_flow::VectorData::getDimension,
             "Get the vector dimension")
        .def("size", &sage_flow::VectorData::size,
             "Get the vector size")
        .def("dot_product", &sage_flow::VectorData::dotProduct,
             "Compute dot product with another vector")
        .def("cosine_similarity", &sage_flow::VectorData::cosineSimilarity,
             "Compute cosine similarity with another vector")
        .def("euclidean_distance", &sage_flow::VectorData::euclideanDistance,
             "Compute Euclidean distance with another vector");
    
    // RetrievalContext class
    py::class_<sage_flow::RetrievalContext>(m, "RetrievalContext")
        .def(py::init<std::string, float>(),
             "Constructor with source and similarity score")
        .def("get_source", &sage_flow::RetrievalContext::getSource,
             "Get the retrieval source", py::return_value_policy::reference_internal)
        .def("get_similarity_score", &sage_flow::RetrievalContext::getSimilarityScore,
             "Get the similarity score")
        .def("get_metadata", &sage_flow::RetrievalContext::getMetadata,
             "Get the metadata dictionary", py::return_value_policy::reference_internal)
        .def("set_metadata", &sage_flow::RetrievalContext::setMetadata,
             "Set metadata key-value pair");
    
    // MultiModalMessage class
    py::class_<sage_flow::MultiModalMessage>(m, "MultiModalMessage")
        .def(py::init<uint64_t>(), "Constructor with UID")
        .def(py::init<uint64_t, sage_flow::ContentType, sage_flow::MultiModalMessage::ContentVariant>(),
             "Constructor with UID, content type, and content")
        .def("get_uid", &sage_flow::MultiModalMessage::getUid,
             "Get the unique identifier")
        .def("get_timestamp", &sage_flow::MultiModalMessage::getTimestamp,
             "Get the timestamp")
        .def("get_content_type", &sage_flow::MultiModalMessage::getContentType,
             "Get the content type")
        .def("get_content", &sage_flow::MultiModalMessage::getContent,
             "Get the content", py::return_value_policy::reference_internal)
        .def("get_embedding", &sage_flow::MultiModalMessage::getEmbedding,
             "Get the embedding", py::return_value_policy::reference_internal)
        .def("get_metadata", &sage_flow::MultiModalMessage::getMetadata,
             "Get the metadata", py::return_value_policy::reference_internal)
        .def("get_processing_trace", &sage_flow::MultiModalMessage::getProcessingTrace,
             "Get the processing trace", py::return_value_policy::reference_internal)
        .def("get_quality_score", &sage_flow::MultiModalMessage::getQualityScore,
             "Get the quality score")
        .def("set_content", &sage_flow::MultiModalMessage::setContent,
             "Set the content")
        .def("set_content_type", &sage_flow::MultiModalMessage::setContentType,
             "Set the content type")
        .def("set_embedding", [](sage_flow::MultiModalMessage& msg, const sage_flow::VectorData& data) {
            sage_flow::VectorData copy = data;  // Make a copy
            msg.setEmbedding(std::move(copy));  // Move the copy
        }, "Set the embedding")
        .def("set_metadata", &sage_flow::MultiModalMessage::setMetadata,
             "Set metadata key-value pair")
        .def("add_processing_step", &sage_flow::MultiModalMessage::addProcessingStep,
             "Add a processing step to the trace")
        .def("set_quality_score", &sage_flow::MultiModalMessage::setQualityScore,
             "Set the quality score")
        .def("has_embedding", &sage_flow::MultiModalMessage::hasEmbedding,
             "Check if message has embedding")
        .def("is_text_content", &sage_flow::MultiModalMessage::isTextContent,
             "Check if content is text")
        .def("is_binary_content", &sage_flow::MultiModalMessage::isBinaryContent,
             "Check if content is binary")
        .def("get_content_as_string", &sage_flow::MultiModalMessage::getContentAsString,
             "Get content as string")
        .def("get_content_as_binary", &sage_flow::MultiModalMessage::getContentAsBinary,
             "Get content as binary", py::return_value_policy::reference_internal);
    
    // Utility functions
    m.def("create_text_message", &sage_flow::CreateTextMessage,
          "Create a text message", py::return_value_policy::take_ownership);
    m.def("create_binary_message", &sage_flow::CreateBinaryMessage,
          "Create a binary message", py::return_value_policy::take_ownership);
}
