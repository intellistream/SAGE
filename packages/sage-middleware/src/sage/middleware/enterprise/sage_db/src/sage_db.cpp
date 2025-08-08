#include "sage_db/sage_db.h"
#include <algorithm>
#include <fstream>

namespace sage_db {

SageDB::SageDB(const DatabaseConfig& config) : config_(config) {
    if (config_.dimension == 0) {
        throw SageDBException("Vector dimension must be greater than 0");
    }
    
    // Create components
    vector_store_ = std::make_shared<VectorStore>(config_);
    metadata_store_ = std::make_shared<MetadataStore>();
    query_engine_ = std::make_shared<QueryEngine>(vector_store_, metadata_store_);
}

VectorId SageDB::add(const Vector& vector, const Metadata& metadata) {
    validate_dimension(vector);
    
    VectorId id = vector_store_->add_vector(vector);
    
    if (!metadata.empty()) {
        metadata_store_->set_metadata(id, metadata);
    }
    
    return id;
}

std::vector<VectorId> SageDB::add_batch(const std::vector<Vector>& vectors,
                                       const std::vector<Metadata>& metadata) {
    if (!metadata.empty()) {
        ensure_consistent_metadata(vectors, metadata);
    }
    
    for (const auto& vector : vectors) {
        validate_dimension(vector);
    }
    
    auto ids = vector_store_->add_vectors(vectors);
    
    if (!metadata.empty()) {
        metadata_store_->set_batch_metadata(ids, metadata);
    }
    
    return ids;
}

bool SageDB::remove(VectorId id) {
    // Note: FAISS doesn't support removing vectors efficiently
    // This is a limitation that could be addressed with a custom implementation
    metadata_store_->remove_metadata(id);
    // TODO: Implement vector removal when FAISS supports it or use custom index
    return true;
}

bool SageDB::update(VectorId id, const Vector& vector, const Metadata& metadata) {
    validate_dimension(vector);
    
    // For now, we can only update metadata
    // Vector updates would require rebuilding the index
    if (!metadata.empty()) {
        metadata_store_->set_metadata(id, metadata);
        return true;
    }
    
    return false;
}

std::vector<QueryResult> SageDB::search(const Vector& query, 
                                       uint32_t k, 
                                       bool include_metadata) const {
    SearchParams params;
    params.k = k;
    params.include_metadata = include_metadata;
    return search(query, params);
}

std::vector<QueryResult> SageDB::search(const Vector& query, const SearchParams& params) const {
    validate_dimension(query);
    return query_engine_->search(query, params);
}

std::vector<QueryResult> SageDB::filtered_search(
    const Vector& query,
    const SearchParams& params,
    const std::function<bool(const Metadata&)>& filter) const {
    
    validate_dimension(query);
    return query_engine_->filtered_search(query, params, filter);
}

std::vector<std::vector<QueryResult>> SageDB::batch_search(
    const std::vector<Vector>& queries, const SearchParams& params) const {
    
    for (const auto& query : queries) {
        validate_dimension(query);
    }
    
    return query_engine_->batch_search(queries, params);
}

void SageDB::build_index() {
    vector_store_->build_index();
}

void SageDB::train_index(const std::vector<Vector>& training_data) {
    if (!training_data.empty()) {
        for (const auto& vector : training_data) {
            validate_dimension(vector);
        }
    }
    vector_store_->train_index(training_data);
}

bool SageDB::is_trained() const {
    return vector_store_->is_trained();
}

bool SageDB::set_metadata(VectorId id, const Metadata& metadata) {
    metadata_store_->set_metadata(id, metadata);
    return true;
}

bool SageDB::get_metadata(VectorId id, Metadata& metadata) const {
    return metadata_store_->get_metadata(id, metadata);
}

std::vector<VectorId> SageDB::find_by_metadata(const std::string& key, 
                                               const MetadataValue& value) const {
    return metadata_store_->find_by_metadata(key, value);
}

void SageDB::save(const std::string& filepath) const {
    vector_store_->save(filepath + ".vectors");
    metadata_store_->save(filepath + ".metadata");
    
    // Save configuration
    std::ofstream config_file(filepath + ".config");
    if (config_file.is_open()) {
        config_file << "dimension=" << config_.dimension << "\n";
        config_file << "index_type=" << static_cast<int>(config_.index_type) << "\n";
        config_file << "metric=" << static_cast<int>(config_.metric) << "\n";
        config_file << "nlist=" << config_.nlist << "\n";
        config_file << "m=" << config_.m << "\n";
        config_file << "nbits=" << config_.nbits << "\n";
        config_file << "M=" << config_.M << "\n";
        config_file << "efConstruction=" << config_.efConstruction << "\n";
    }
}

void SageDB::load(const std::string& filepath) {
    // Load configuration
    std::ifstream config_file(filepath + ".config");
    if (config_file.is_open()) {
        std::string line;
        while (std::getline(config_file, line)) {
            size_t pos = line.find('=');
            if (pos != std::string::npos) {
                std::string key = line.substr(0, pos);
                std::string value = line.substr(pos + 1);
                
                if (key == "dimension") {
                    config_.dimension = std::stoul(value);
                } else if (key == "index_type") {
                    config_.index_type = static_cast<IndexType>(std::stoi(value));
                } else if (key == "metric") {
                    config_.metric = static_cast<DistanceMetric>(std::stoi(value));
                } else if (key == "nlist") {
                    config_.nlist = std::stoul(value);
                } else if (key == "m") {
                    config_.m = std::stoul(value);
                } else if (key == "nbits") {
                    config_.nbits = std::stoul(value);
                } else if (key == "M") {
                    config_.M = std::stoul(value);
                } else if (key == "efConstruction") {
                    config_.efConstruction = std::stoul(value);
                }
            }
        }
    }
    
    // Recreate components with loaded configuration
    vector_store_ = std::make_shared<VectorStore>(config_);
    metadata_store_ = std::make_shared<MetadataStore>();
    query_engine_ = std::make_shared<QueryEngine>(vector_store_, metadata_store_);
    
    // Load data
    vector_store_->load(filepath + ".vectors");
    metadata_store_->load(filepath + ".metadata");
}

size_t SageDB::size() const {
    return vector_store_->size();
}

Dimension SageDB::dimension() const {
    return config_.dimension;
}

IndexType SageDB::index_type() const {
    return config_.index_type;
}

const DatabaseConfig& SageDB::config() const {
    return config_;
}

void SageDB::validate_dimension(const Vector& vector) const {
    if (vector.size() != config_.dimension) {
        throw SageDBException("Vector dimension mismatch: expected " + 
                             std::to_string(config_.dimension) + 
                             ", got " + std::to_string(vector.size()));
    }
}

void SageDB::ensure_consistent_metadata(const std::vector<Vector>& vectors,
                                       const std::vector<Metadata>& metadata) const {
    if (vectors.size() != metadata.size()) {
        throw SageDBException("Vectors and metadata must have the same size");
    }
}

// Factory functions
std::unique_ptr<SageDB> create_database(Dimension dimension,
                                       IndexType index_type,
                                       DistanceMetric metric) {
    DatabaseConfig config(dimension);
    config.index_type = index_type;
    config.metric = metric;
    return std::make_unique<SageDB>(config);
}

std::unique_ptr<SageDB> create_database(const DatabaseConfig& config) {
    return std::make_unique<SageDB>(config);
}

// Utility functions
std::string index_type_to_string(IndexType type) {
    switch (type) {
        case IndexType::FLAT: return "FLAT";
        case IndexType::IVF_FLAT: return "IVF_FLAT";
        case IndexType::IVF_PQ: return "IVF_PQ";
        case IndexType::HNSW: return "HNSW";
        case IndexType::AUTO: return "AUTO";
        default: return "UNKNOWN";
    }
}

IndexType string_to_index_type(const std::string& str) {
    if (str == "FLAT") return IndexType::FLAT;
    if (str == "IVF_FLAT") return IndexType::IVF_FLAT;
    if (str == "IVF_PQ") return IndexType::IVF_PQ;
    if (str == "HNSW") return IndexType::HNSW;
    if (str == "AUTO") return IndexType::AUTO;
    throw SageDBException("Unknown index type: " + str);
}

std::string distance_metric_to_string(DistanceMetric metric) {
    switch (metric) {
        case DistanceMetric::L2: return "L2";
        case DistanceMetric::INNER_PRODUCT: return "INNER_PRODUCT";
        case DistanceMetric::COSINE: return "COSINE";
        default: return "UNKNOWN";
    }
}

DistanceMetric string_to_distance_metric(const std::string& str) {
    if (str == "L2") return DistanceMetric::L2;
    if (str == "INNER_PRODUCT") return DistanceMetric::INNER_PRODUCT;
    if (str == "COSINE") return DistanceMetric::COSINE;
    throw SageDBException("Unknown distance metric: " + str);
}

} // namespace sage_db
