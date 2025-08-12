#pragma once

#include "vector_store.h"
#include "metadata_store.h"
#include "query_engine.h"

namespace sage_db {

class SageDB {
public:
    explicit SageDB(const DatabaseConfig& config);
    ~SageDB() = default;

    // Vector operations
    VectorId add(const Vector& vector, const Metadata& metadata = {});
    std::vector<VectorId> add_batch(const std::vector<Vector>& vectors,
                                   const std::vector<Metadata>& metadata = {});
    
    bool remove(VectorId id);
    bool update(VectorId id, const Vector& vector, const Metadata& metadata = {});
    
    // Search operations
    std::vector<QueryResult> search(const Vector& query, 
                                   uint32_t k = 10, 
                                   bool include_metadata = true) const;
    
    std::vector<QueryResult> search(const Vector& query, const SearchParams& params) const;
    
    std::vector<QueryResult> filtered_search(
        const Vector& query,
        const SearchParams& params,
        const std::function<bool(const Metadata&)>& filter) const;
    
    // Batch operations
    std::vector<std::vector<QueryResult>> batch_search(
        const std::vector<Vector>& queries, const SearchParams& params) const;
    
    // Index management
    void build_index();
    void train_index(const std::vector<Vector>& training_data = {});
    bool is_trained() const;
    
    // Metadata operations
    bool set_metadata(VectorId id, const Metadata& metadata);
    bool get_metadata(VectorId id, Metadata& metadata) const;
    std::vector<VectorId> find_by_metadata(const std::string& key, 
                                          const MetadataValue& value) const;
    
    // Persistence
    void save(const std::string& filepath) const;
    void load(const std::string& filepath);
    
    // Statistics
    size_t size() const;
    Dimension dimension() const;
    IndexType index_type() const;
    const DatabaseConfig& config() const;
    
    // Advanced features
    QueryEngine& query_engine() { return *query_engine_; }
    const QueryEngine& query_engine() const { return *query_engine_; }
    
    VectorStore& vector_store() { return *vector_store_; }
    const VectorStore& vector_store() const { return *vector_store_; }
    
    MetadataStore& metadata_store() { return *metadata_store_; }
    const MetadataStore& metadata_store() const { return *metadata_store_; }

private:
    DatabaseConfig config_;
    std::shared_ptr<VectorStore> vector_store_;
    std::shared_ptr<MetadataStore> metadata_store_;
    std::shared_ptr<QueryEngine> query_engine_;
    
    // Helper methods
    void validate_dimension(const Vector& vector) const;
    void ensure_consistent_metadata(const std::vector<Vector>& vectors,
                                   const std::vector<Metadata>& metadata) const;
};

// Factory functions
std::unique_ptr<SageDB> create_database(Dimension dimension,
                                       IndexType index_type = IndexType::AUTO,
                                       DistanceMetric metric = DistanceMetric::L2);

std::unique_ptr<SageDB> create_database(const DatabaseConfig& config);

// Utility functions
std::string index_type_to_string(IndexType type);
IndexType string_to_index_type(const std::string& str);

std::string distance_metric_to_string(DistanceMetric metric);
DistanceMetric string_to_distance_metric(const std::string& str);

} // namespace sage_db
