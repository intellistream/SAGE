#include "sage_db/query_engine.h"
#include <chrono>
#include <algorithm>
#include <set>

namespace sage_db {

QueryEngine::QueryEngine(std::shared_ptr<VectorStore> vector_store,
                        std::shared_ptr<MetadataStore> metadata_store)
    : vector_store_(vector_store), metadata_store_(metadata_store) {
    if (!vector_store_ || !metadata_store_) {
        throw SageDBException("Vector store and metadata store cannot be null");
    }
}

std::vector<QueryResult> QueryEngine::search(const Vector& query, const SearchParams& params) const {
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // Get vector search results
    auto vector_results = vector_store_->search(query, params);
    
    auto mid_time = std::chrono::high_resolution_clock::now();
    
    // Add metadata if requested
    if (params.include_metadata) {
        for (auto& result : vector_results) {
            metadata_store_->get_metadata(result.id, result.metadata);
        }
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    
    // Update statistics
    SearchStats stats;
    stats.total_candidates = vector_results.size();
    stats.filtered_candidates = vector_results.size();
    stats.final_results = vector_results.size();
    stats.search_time_ms = std::chrono::duration<double, std::milli>(mid_time - start_time).count();
    stats.filter_time_ms = std::chrono::duration<double, std::milli>(end_time - mid_time).count();
    stats.total_time_ms = std::chrono::duration<double, std::milli>(end_time - start_time).count();
    update_stats(stats);
    
    return vector_results;
}

std::vector<QueryResult> QueryEngine::filtered_search(
    const Vector& query, 
    const SearchParams& params,
    const std::function<bool(const Metadata&)>& filter) const {
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // Get more candidates for filtering
    SearchParams expanded_params = params;
    expanded_params.k = std::min(params.k * 10, 1000u); // Get 10x more candidates
    
    auto vector_results = vector_store_->search(query, expanded_params);
    
    auto mid_time = std::chrono::high_resolution_clock::now();
    
    // Apply metadata filter
    auto filtered_results = apply_metadata_filter(vector_results, filter);
    
    // Limit to requested k
    if (filtered_results.size() > params.k) {
        filtered_results.resize(params.k);
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    
    // Update statistics
    SearchStats stats;
    stats.total_candidates = vector_results.size();
    stats.filtered_candidates = filtered_results.size();
    stats.final_results = filtered_results.size();
    stats.search_time_ms = std::chrono::duration<double, std::milli>(mid_time - start_time).count();
    stats.filter_time_ms = std::chrono::duration<double, std::milli>(end_time - mid_time).count();
    stats.total_time_ms = std::chrono::duration<double, std::milli>(end_time - start_time).count();
    update_stats(stats);
    
    return filtered_results;
}

std::vector<QueryResult> QueryEngine::search_with_metadata(
    const Vector& query,
    const SearchParams& params,
    const std::string& metadata_key,
    const MetadataValue& metadata_value) const {
    
    auto filter = [&metadata_key, &metadata_value](const Metadata& metadata) {
        auto it = metadata.find(metadata_key);
        return it != metadata.end() && it->second == metadata_value;
    };
    
    return filtered_search(query, params, filter);
}

std::vector<std::vector<QueryResult>> QueryEngine::batch_search(
    const std::vector<Vector>& queries, const SearchParams& params) const {
    
    std::vector<std::vector<QueryResult>> results;
    results.reserve(queries.size());
    
    for (const auto& query : queries) {
        results.push_back(search(query, params));
    }
    
    return results;
}

std::vector<std::vector<QueryResult>> QueryEngine::batch_filtered_search(
    const std::vector<Vector>& queries,
    const SearchParams& params,
    const std::function<bool(const Metadata&)>& filter) const {
    
    std::vector<std::vector<QueryResult>> results;
    results.reserve(queries.size());
    
    for (const auto& query : queries) {
        results.push_back(filtered_search(query, params, filter));
    }
    
    return results;
}

std::vector<QueryResult> QueryEngine::hybrid_search(
    const Vector& query,
    const SearchParams& params,
    const std::string& text_query,
    float vector_weight,
    float text_weight) const {
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // Get vector search results
    SearchParams expanded_params = params;
    expanded_params.k = params.k * 2; // Get more candidates for hybrid scoring
    auto vector_results = vector_store_->search(query, expanded_params);
    
    auto mid_time = std::chrono::high_resolution_clock::now();
    
    // If no text query, return vector results
    if (text_query.empty()) {
        if (vector_results.size() > params.k) {
            vector_results.resize(params.k);
        }
        return vector_results;
    }
    
    // Simple text search in metadata (could be enhanced with proper text search)
    std::vector<VectorId> text_results;
    for (const auto& result : vector_results) {
        Metadata metadata;
        if (metadata_store_->get_metadata(result.id, metadata)) {
            for (const auto& pair : metadata) {
                if (pair.second.find(text_query) != std::string::npos) {
                    text_results.push_back(result.id);
                    break;
                }
            }
        }
    }
    
    // Merge and rerank results
    auto hybrid_results = merge_and_rerank(vector_results, text_results, 
                                          vector_weight, text_weight);
    
    // Limit to requested k
    if (hybrid_results.size() > params.k) {
        hybrid_results.resize(params.k);
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    
    // Update statistics
    SearchStats stats;
    stats.total_candidates = vector_results.size();
    stats.filtered_candidates = hybrid_results.size();
    stats.final_results = hybrid_results.size();
    stats.search_time_ms = std::chrono::duration<double, std::milli>(mid_time - start_time).count();
    stats.filter_time_ms = std::chrono::duration<double, std::milli>(end_time - mid_time).count();
    stats.total_time_ms = std::chrono::duration<double, std::milli>(end_time - start_time).count();
    update_stats(stats);
    
    return hybrid_results;
}

std::vector<QueryResult> QueryEngine::range_search(
    const Vector& query,
    float radius,
    const SearchParams& params) const {
    
    // For range search, we need to get all results within radius
    SearchParams range_params = params;
    range_params.radius = radius;
    range_params.k = 10000; // Large number to get all candidates
    
    auto results = vector_store_->search(query, range_params);
    
    // Filter by radius (distance-dependent)
    std::vector<QueryResult> filtered_results;
    for (const auto& result : results) {
        if (result.score <= radius) { // Assuming L2 distance
            filtered_results.push_back(result);
        }
    }
    
    // Add metadata if requested
    if (params.include_metadata) {
        for (auto& result : filtered_results) {
            metadata_store_->get_metadata(result.id, result.metadata);
        }
    }
    
    return filtered_results;
}

std::vector<QueryResult> QueryEngine::search_with_rerank(
    const Vector& query,
    const SearchParams& params,
    const std::function<float(const Vector&, const Metadata&)>& rerank_fn,
    uint32_t rerank_k) const {
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // Get more candidates for reranking
    SearchParams rerank_params = params;
    rerank_params.k = rerank_k;
    
    auto candidates = vector_store_->search(query, rerank_params);
    
    auto mid_time = std::chrono::high_resolution_clock::now();
    
    // Apply reranking function
    for (auto& candidate : candidates) {
        Metadata metadata;
        metadata_store_->get_metadata(candidate.id, metadata);
        candidate.metadata = metadata;
        
        // Apply reranking function to adjust score
        float rerank_score = rerank_fn(query, metadata);
        candidate.score = candidate.score * 0.7f + rerank_score * 0.3f; // Weighted combination
    }
    
    // Sort by new scores
    std::sort(candidates.begin(), candidates.end(),
             [](const QueryResult& a, const QueryResult& b) {
                 return a.score < b.score; // Assuming lower is better
             });
    
    // Limit to requested k
    if (candidates.size() > params.k) {
        candidates.resize(params.k);
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    
    // Update statistics
    SearchStats stats;
    stats.total_candidates = rerank_k;
    stats.filtered_candidates = candidates.size();
    stats.final_results = candidates.size();
    stats.search_time_ms = std::chrono::duration<double, std::milli>(mid_time - start_time).count();
    stats.filter_time_ms = std::chrono::duration<double, std::milli>(end_time - mid_time).count();
    stats.total_time_ms = std::chrono::duration<double, std::milli>(end_time - start_time).count();
    update_stats(stats);
    
    return candidates;
}

std::vector<QueryResult> QueryEngine::apply_metadata_filter(
    const std::vector<QueryResult>& results,
    const std::function<bool(const Metadata&)>& filter) const {
    
    std::vector<QueryResult> filtered_results;
    filtered_results.reserve(results.size());
    
    for (const auto& result : results) {
        Metadata metadata;
        if (metadata_store_->get_metadata(result.id, metadata)) {
            if (filter(metadata)) {
                QueryResult filtered_result = result;
                filtered_result.metadata = metadata;
                filtered_results.push_back(filtered_result);
            }
        }
    }
    
    return filtered_results;
}

std::vector<QueryResult> QueryEngine::merge_and_rerank(
    const std::vector<QueryResult>& vector_results,
    const std::vector<VectorId>& text_results,
    float vector_weight,
    float text_weight) const {
    
    std::map<VectorId, QueryResult> merged_results;
    
    // Add vector results with vector weight
    for (const auto& result : vector_results) {
        QueryResult weighted_result = result;
        weighted_result.score *= vector_weight;
        merged_results[result.id] = weighted_result;
    }
    
    // Boost scores for text matches
    std::set<VectorId> text_set(text_results.begin(), text_results.end());
    for (auto& pair : merged_results) {
        if (text_set.count(pair.first)) {
            // Boost score for text matches (lower score is better)
            pair.second.score *= (1.0f - text_weight);
        }
    }
    
    // Convert back to vector and sort
    std::vector<QueryResult> final_results;
    final_results.reserve(merged_results.size());
    
    for (const auto& pair : merged_results) {
        final_results.push_back(pair.second);
    }
    
    std::sort(final_results.begin(), final_results.end(),
             [](const QueryResult& a, const QueryResult& b) {
                 return a.score < b.score;
             });
    
    return final_results;
}

void QueryEngine::update_stats(const SearchStats& stats) const {
    last_stats_ = stats;
}

} // namespace sage_db
