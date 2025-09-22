#pragma once

#include "common.h"
#include "vector_store.h"
#include "metadata_store.h"
#include <functional>

namespace sage_db {

class QueryEngine {
public:
    QueryEngine(std::shared_ptr<VectorStore> vector_store,
               std::shared_ptr<MetadataStore> metadata_store);
    ~QueryEngine() = default;

    // Basic search
    std::vector<QueryResult> search(const Vector& query, const SearchParams& params) const;
    
    // Filtered search
    std::vector<QueryResult> filtered_search(
        const Vector& query, 
        const SearchParams& params,
        const std::function<bool(const Metadata&)>& filter) const;
    
    // Search with metadata constraints
    std::vector<QueryResult> search_with_metadata(
        const Vector& query,
        const SearchParams& params,
        const std::string& metadata_key,
        const MetadataValue& metadata_value) const;
    
    // Batch search operations
    std::vector<std::vector<QueryResult>> batch_search(
        const std::vector<Vector>& queries, const SearchParams& params) const;
    
    std::vector<std::vector<QueryResult>> batch_filtered_search(
        const std::vector<Vector>& queries,
        const SearchParams& params,
        const std::function<bool(const Metadata&)>& filter) const;
    
    // Hybrid search (vector + text/metadata)
    std::vector<QueryResult> hybrid_search(
        const Vector& query,
        const SearchParams& params,
        const std::string& text_query = "",
        float vector_weight = 0.7f,
        float text_weight = 0.3f) const;
    
    // Range search
    std::vector<QueryResult> range_search(
        const Vector& query,
        float radius,
        const SearchParams& params = SearchParams()) const;
    
    // Advanced search with re-ranking
    std::vector<QueryResult> search_with_rerank(
        const Vector& query,
        const SearchParams& params,
        const std::function<float(const Vector&, const Metadata&)>& rerank_fn,
        uint32_t rerank_k = 100) const;
    
    // Statistics and analysis
    struct SearchStats {
        size_t total_candidates;
        size_t filtered_candidates;
        size_t final_results;
        double search_time_ms;
        double filter_time_ms;
        double total_time_ms;
    };
    
    SearchStats get_last_search_stats() const { return last_stats_; }
    
private:
    std::shared_ptr<VectorStore> vector_store_;
    std::shared_ptr<MetadataStore> metadata_store_;
    mutable SearchStats last_stats_;
    
    // Helper methods
    std::vector<QueryResult> apply_metadata_filter(
        const std::vector<QueryResult>& results,
        const std::function<bool(const Metadata&)>& filter) const;
    
    std::vector<QueryResult> merge_and_rerank(
        const std::vector<QueryResult>& vector_results,
        const std::vector<VectorId>& text_results,
        float vector_weight,
        float text_weight) const;
    
    void update_stats(const SearchStats& stats) const;
};

} // namespace sage_db
