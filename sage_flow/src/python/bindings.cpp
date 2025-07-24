#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

#include "message/multimodal_message.h"
#include "index/index_types.h"
#include "index/index.h"
#include "index/index_operators.h"
#include "environment/sage_flow_environment.h"
#include "memory/memory_pool.h"

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
    
    // ===============================
    // Index System Bindings
    // ===============================
    
    // IndexType enum
    py::enum_<sage_flow::IndexType>(m, "IndexType")
        .value("NONE", sage_flow::IndexType::kNone)
        .value("BRUTE_FORCE", sage_flow::IndexType::kBruteForce)
        .value("HNSW", sage_flow::IndexType::kHnsw)
        .value("IVF", sage_flow::IndexType::kIvf)
        .value("ADA_IVF", sage_flow::IndexType::kAdaIvf)
        .value("VECTRA_FLOW", sage_flow::IndexType::kVectraFlow)
        .value("VAMANA", sage_flow::IndexType::kVamana)
        .value("FRESH_VAMANA", sage_flow::IndexType::kFreshVamana)
        .value("DYNA_GRAPH", sage_flow::IndexType::kDynaGraph)
        .value("SP_FRESH", sage_flow::IndexType::kSpFresh)
        .value("KNN", sage_flow::IndexType::kKnn);
    
    // SearchResult class
    py::class_<sage_flow::SearchResult>(m, "SearchResult")
        .def(py::init<>(), "Default constructor")
        .def(py::init<uint64_t, float>(), "Constructor with ID and distance")
        .def(py::init<uint64_t, float, float>(),
             "Constructor with ID, distance, and similarity score")
        .def_readwrite("id_", &sage_flow::SearchResult::id_, "Vector ID")
        .def_readwrite("distance_", &sage_flow::SearchResult::distance_, "Distance value")
        .def_readwrite("similarity_score_", &sage_flow::SearchResult::similarity_score_, 
                      "Similarity score")
        .def("__repr__", [](const sage_flow::SearchResult& r) {
            return "SearchResult(id=" + std::to_string(r.id_) + 
                   ", distance=" + std::to_string(r.distance_) + 
                   ", similarity=" + std::to_string(r.similarity_score_) + ")";
        });
    
    // IndexConfig class
    py::class_<sage_flow::IndexConfig>(m, "IndexConfig")
        .def(py::init<>(), "Default constructor")
        .def_readwrite("type_", &sage_flow::IndexConfig::type_, "Index type")
        .def_readwrite("hnsw_m_", &sage_flow::IndexConfig::hnsw_m_, "HNSW M parameter")
        .def_readwrite("hnsw_ef_construction_", &sage_flow::IndexConfig::hnsw_ef_construction_, 
                      "HNSW ef_construction parameter")
        .def_readwrite("hnsw_ef_search_", &sage_flow::IndexConfig::hnsw_ef_search_, 
                      "HNSW ef_search parameter")
        .def_readwrite("ivf_nlist_", &sage_flow::IndexConfig::ivf_nlist_, "IVF nlist parameter")
        .def_readwrite("ivf_nprobe_", &sage_flow::IndexConfig::ivf_nprobe_, "IVF nprobe parameter");
    
    // TODO(developer): Add Index base class binding when all implementations are ready
    // Currently disabled due to undefined symbol issues with abstract base class
    
    // Index base class (abstract)
    py::class_<sage_flow::Index>(m, "Index")
        .def("initialize", &sage_flow::Index::Initialize, "Initialize the index with config")
        .def("add_vector", &sage_flow::Index::AddVector, "Add a vector to the index")
        .def("remove_vector", &sage_flow::Index::RemoveVector, "Remove a vector from the index")
        .def("search", &sage_flow::Index::Search, "Search for similar vectors")
        .def("build", &sage_flow::Index::Build, "Build/rebuild the index")
        .def("clear", &sage_flow::Index::Clear, "Clear all vectors from the index")
        .def("size", &sage_flow::Index::Size, "Get the number of vectors in the index")
        .def("save_index", &sage_flow::Index::SaveIndex, "Save index to file")
        .def("load_index", &sage_flow::Index::LoadIndex, "Load index from file")
        .def("get_type", &sage_flow::Index::GetType, "Get the index type");
    
    // Index factory functions
    m.def("create_index", &sage_flow::CreateIndex, 
          "Create an index of specified type", 
          py::return_value_policy::take_ownership);
    
    // ===============================
    // Memory System Bindings
    // ===============================
    
    // MemoryPool base class (abstract) - use shared_ptr holder
    py::class_<sage_flow::MemoryPool, std::shared_ptr<sage_flow::MemoryPool>>(m, "MemoryPool")
        .def("get_allocated_size", &sage_flow::MemoryPool::get_allocated_size,
             "Get total allocated memory size")
        .def("reset", &sage_flow::MemoryPool::reset,
             "Reset/clear all allocations");
    
    // SimpleMemoryPool concrete implementation - use shared_ptr holder
    auto simple_memory_pool = py::class_<sage_flow::SimpleMemoryPool, sage_flow::MemoryPool,
                                        std::shared_ptr<sage_flow::SimpleMemoryPool>>(m, "SimpleMemoryPool");
    (void)simple_memory_pool; // Mark as used to avoid compiler warning
    
    // Memory pool factory function - return shared_ptr
    m.def("create_default_memory_pool", &sage_flow::CreateDefaultMemoryPool,
          "Create a default memory pool instance");
    
    // ===============================
    // Environment System Bindings
    // ===============================
    
    // EnvironmentConfig class
    py::class_<sage_flow::EnvironmentConfig>(m, "EnvironmentConfig")
        .def(py::init<>(), "Default constructor")
        .def(py::init<std::string>(), "Constructor with job name")
        .def_readwrite("job_name_", &sage_flow::EnvironmentConfig::job_name_, "Job name")
        .def_readwrite("memory_config_", &sage_flow::EnvironmentConfig::memory_config_, 
                      "Memory configuration")
        .def_readwrite("properties_", &sage_flow::EnvironmentConfig::properties_, 
                      "Environment properties");
    
    // SageFlowEnvironment class
    py::class_<sage_flow::SageFlowEnvironment>(m, "SageFlowEnvironment")
        .def(py::init<const std::string&>(), "Constructor with job name")
        .def(py::init<sage_flow::EnvironmentConfig>(), "Constructor with config")
        .def("set_memory", &sage_flow::SageFlowEnvironment::set_memory, 
             "Set memory configuration")
        .def("set_property", &sage_flow::SageFlowEnvironment::set_property, 
             "Set environment property")
        .def("get_property", &sage_flow::SageFlowEnvironment::get_property, 
             "Get environment property")
        .def("get_job_name", &sage_flow::SageFlowEnvironment::get_job_name, 
             "Get job name", py::return_value_policy::reference_internal)
        .def("submit", &sage_flow::SageFlowEnvironment::submit, 
             "Submit job for execution")
        .def("close", &sage_flow::SageFlowEnvironment::close, 
             "Close environment and cleanup")
        .def("run_streaming", &sage_flow::SageFlowEnvironment::run_streaming, 
             "Run in streaming mode")
        .def("run_batch", &sage_flow::SageFlowEnvironment::run_batch, 
             "Run in batch mode");
    
    // TODO(developer): Add specific index implementations when they're ready
    // - HNSW, IVF, Vamana, DynaGraph, AdaIVF, FreshVamana, SPFresh, VectraFlow
}
