#include "sage_db/vector_store.h"
#include <chrono>
#include <fstream>
#include <iostream>
#include <algorithm>
#include <unordered_map>
#include <cmath>

#ifdef FAISS_AVAILABLE
#include <faiss/IndexFlat.h>
#include <faiss/IndexIVFFlat.h>
#include <faiss/IndexIVFPQ.h>
#include <faiss/IndexHNSW.h>
#include <faiss/index_io.h>
#include <faiss/AutoTune.h>
#endif

namespace sage_db {

class VectorStore::Impl {
public:
    explicit Impl(const DatabaseConfig& config) : config_(config) {
#ifdef FAISS_AVAILABLE
        create_index();
#else
        // Fallback implementation without FAISS
        vectors_.reserve(1000);
#endif
    }
    
    ~Impl() = default;
    
    VectorId add_vector(const Vector& vector) {
        std::lock_guard<std::mutex> lock(mutex_);
        
#ifdef FAISS_AVAILABLE
        if (index_ && index_->is_trained) {
            VectorId custom_id = next_id_++;
            index_->add(1, vector.data());
            id_to_vector_[custom_id] = vector;
            faiss_to_custom_id_.push_back(custom_id);  // Map FAISS index to custom ID
            return custom_id;
        } else if (index_ && !index_->is_trained) {
            // Index exists but not trained - store in fallback until training
            VectorId custom_id = next_id_++;
            id_to_vector_[custom_id] = vector;
            vectors_.emplace_back(custom_id, vector);
            return custom_id;
        }
#endif
        // Fallback implementation
        VectorId id = next_id_++;
        vectors_.emplace_back(id, vector);
        return id;
    }
    
    std::vector<VectorId> add_vectors(const std::vector<Vector>& vectors) {
        std::lock_guard<std::mutex> lock(mutex_);
        std::vector<VectorId> ids;
        ids.reserve(vectors.size());
        
#ifdef FAISS_AVAILABLE
        if (index_ && !vectors.empty() && index_->is_trained) {
            // Prepare data for batch insertion
            std::vector<float> data;
            data.reserve(vectors.size() * config_.dimension);
            
        for (const auto& vector : vectors) {
            VectorId id = next_id_++;
            ids.push_back(id);
            id_to_vector_[id] = vector;
            faiss_to_custom_id_.push_back(id);  // Map FAISS index to custom ID
            
            for (float val : vector) {
                data.push_back(val);
            }
        }
            index_->add(vectors.size(), data.data());
            return ids;
        } else if (index_ && !vectors.empty() && !index_->is_trained) {
            // Index exists but not trained - store in fallback until training
            for (const auto& vector : vectors) {
                VectorId id = next_id_++;
                ids.push_back(id);
                id_to_vector_[id] = vector;
                vectors_.emplace_back(id, vector);
            }
            return ids;
        }
#endif
        // Fallback implementation
        for (const auto& vector : vectors) {
            VectorId id = next_id_++;
            ids.push_back(id);
            vectors_.emplace_back(id, vector);
        }
        return ids;
    }
    
    std::vector<QueryResult> search(const Vector& query, const SearchParams& params) const {
        std::lock_guard<std::mutex> lock(mutex_);
        
#ifdef FAISS_AVAILABLE
        if (index_) {
            return search_faiss(query, params);
        }
#endif
        return search_fallback(query, params);
    }
    
    void build_index() {
#ifdef FAISS_AVAILABLE
        std::lock_guard<std::mutex> lock(mutex_);
        if (config_.index_type == IndexType::IVF_FLAT || 
            config_.index_type == IndexType::IVF_PQ) {
            if (!is_trained_ && id_to_vector_.size() >= config_.nlist) {
                train_index_internal();
            }
        }
#endif
    }
    
    void train_index(const std::vector<Vector>& training_data) {
#ifdef FAISS_AVAILABLE
        std::lock_guard<std::mutex> lock(mutex_);
        if (!training_data.empty()) {
            train_index_with_data(training_data);
        }
#endif
    }
    
    bool is_trained() const {
#ifdef FAISS_AVAILABLE
        return !index_ || index_->is_trained;
#else
        return true;
#endif
    }
    
    size_t size() const {
        std::lock_guard<std::mutex> lock(mutex_);
#ifdef FAISS_AVAILABLE
        return index_ ? index_->ntotal : vectors_.size();
#else
        return vectors_.size();
#endif
    }
    
    void save(const std::string& filepath) const {
        std::lock_guard<std::mutex> lock(mutex_);
#ifdef FAISS_AVAILABLE
        if (index_) {
            faiss::write_index(index_.get(), filepath.c_str());
            
            // Also save ID mapping
            std::ofstream id_file(filepath + ".ids", std::ios::binary);
            size_t map_size = id_to_vector_.size();
            id_file.write(reinterpret_cast<const char*>(&map_size), sizeof(map_size));
            for (const auto& pair : id_to_vector_) {
                id_file.write(reinterpret_cast<const char*>(&pair.first), sizeof(pair.first));
                size_t vec_size = pair.second.size();
                id_file.write(reinterpret_cast<const char*>(&vec_size), sizeof(vec_size));
                id_file.write(reinterpret_cast<const char*>(pair.second.data()), 
                             vec_size * sizeof(float));
            }
        }
#else
        // Fallback save implementation
        std::ofstream file(filepath, std::ios::binary);
        size_t vec_count = vectors_.size();
        file.write(reinterpret_cast<const char*>(&vec_count), sizeof(vec_count));
        for (const auto& pair : vectors_) {
            file.write(reinterpret_cast<const char*>(&pair.first), sizeof(pair.first));
            size_t vec_size = pair.second.size();
            file.write(reinterpret_cast<const char*>(&vec_size), sizeof(vec_size));
            file.write(reinterpret_cast<const char*>(pair.second.data()), 
                      vec_size * sizeof(float));
        }
#endif
    }
    
    void load(const std::string& filepath) {
        std::lock_guard<std::mutex> lock(mutex_);
#ifdef FAISS_AVAILABLE
        index_.reset(faiss::read_index(filepath.c_str()));
        
        // Load ID mapping
        std::ifstream id_file(filepath + ".ids", std::ios::binary);
        if (id_file.is_open()) {
            id_to_vector_.clear();
            size_t map_size;
            id_file.read(reinterpret_cast<char*>(&map_size), sizeof(map_size));
            
            for (size_t i = 0; i < map_size; ++i) {
                VectorId id;
                id_file.read(reinterpret_cast<char*>(&id), sizeof(id));
                size_t vec_size;
                id_file.read(reinterpret_cast<char*>(&vec_size), sizeof(vec_size));
                Vector vec(vec_size);
                id_file.read(reinterpret_cast<char*>(vec.data()), vec_size * sizeof(float));
                id_to_vector_[id] = vec;
                next_id_ = std::max(next_id_.load(), id + 1);
            }
        }
#else
        // Fallback load implementation
        std::ifstream file(filepath, std::ios::binary);
        if (file.is_open()) {
            vectors_.clear();
            size_t vec_count;
            file.read(reinterpret_cast<char*>(&vec_count), sizeof(vec_count));
            
            for (size_t i = 0; i < vec_count; ++i) {
                VectorId id;
                file.read(reinterpret_cast<char*>(&id), sizeof(id));
                size_t vec_size;
                file.read(reinterpret_cast<char*>(&vec_size), sizeof(vec_size));
                Vector vec(vec_size);
                file.read(reinterpret_cast<char*>(vec.data()), vec_size * sizeof(float));
                vectors_.emplace_back(id, vec);
                next_id_ = std::max(next_id_.load(), id + 1);
            }
        }
#endif
    }

private:
    DatabaseConfig config_;
    mutable std::mutex mutex_;
    std::atomic<VectorId> next_id_{1};
    
    // Always have vectors_ for fallback support
    std::vector<std::pair<VectorId, Vector>> vectors_;
    
#ifdef FAISS_AVAILABLE
    std::unique_ptr<faiss::Index> index_;
    std::unordered_map<VectorId, Vector> id_to_vector_;
    std::vector<VectorId> faiss_to_custom_id_;  // Map FAISS index to custom ID
    bool is_trained_ = false;
    
    void create_index() {
        faiss::MetricType metric = (config_.metric == DistanceMetric::L2) ? 
            faiss::METRIC_L2 : faiss::METRIC_INNER_PRODUCT;
        
        switch (config_.index_type) {
            case IndexType::FLAT:
                index_ = std::make_unique<faiss::IndexFlat>(config_.dimension, metric);
                break;
            case IndexType::IVF_FLAT:
                {
                    auto quantizer = std::make_unique<faiss::IndexFlat>(config_.dimension, metric);
                    index_ = std::make_unique<faiss::IndexIVFFlat>(
                        quantizer.release(), config_.dimension, config_.nlist, metric);
                }
                break;
            case IndexType::IVF_PQ:
                {
                    auto quantizer = std::make_unique<faiss::IndexFlat>(config_.dimension, metric);
                    index_ = std::make_unique<faiss::IndexIVFPQ>(
                        quantizer.release(), config_.dimension, config_.nlist, 
                        config_.m, config_.nbits, metric);
                }
                break;
            case IndexType::AUTO:
            default:
                // Start with flat index, can be upgraded later
                index_ = std::make_unique<faiss::IndexFlat>(config_.dimension, metric);
                break;
        }
    }
    
    std::vector<QueryResult> search_faiss(const Vector& query, const SearchParams& params) const {
        if (!index_) return {};
        
        std::vector<long> indices(params.k);
        std::vector<float> distances(params.k);
        
        // Set search parameters for IVF indices
        faiss::IndexIVF* ivf_index = dynamic_cast<faiss::IndexIVF*>(index_.get());
        if (ivf_index) {
            ivf_index->nprobe = params.nprobe;
        }
        
        index_->search(1, query.data(), params.k, distances.data(), indices.data());
        
        std::vector<QueryResult> results;
        results.reserve(params.k);
        
        for (size_t i = 0; i < params.k && indices[i] >= 0; ++i) {
            size_t faiss_index = static_cast<size_t>(indices[i]);
            if (faiss_index < faiss_to_custom_id_.size()) {
                VectorId id = faiss_to_custom_id_[faiss_index];
                Score score = distances[i];
                
                // Convert distance to similarity if needed
                if (config_.metric == DistanceMetric::INNER_PRODUCT) {
                    score = -score; // Higher is better for inner product
                }
                
                results.emplace_back(id, score);
            }
        }
        
        return results;
    }
    
    void train_index_internal() {
        if (is_trained_ || id_to_vector_.empty()) return;
        
        std::vector<float> training_data;
        training_data.reserve(id_to_vector_.size() * config_.dimension);
        
        for (const auto& pair : id_to_vector_) {
            for (float val : pair.second) {
                training_data.push_back(val);
            }
        }
        
        index_->train(id_to_vector_.size(), training_data.data());
        is_trained_ = true;
        
        // After training, transfer vectors from fallback storage to FAISS index
        transfer_vectors_to_faiss();
    }
    
    void train_index_with_data(const std::vector<Vector>& training_data) {
        if (is_trained_ || training_data.empty()) return;
        
        std::vector<float> data;
        data.reserve(training_data.size() * config_.dimension);
        
        for (const auto& vec : training_data) {
            for (float val : vec) {
                data.push_back(val);
            }
        }
        
        index_->train(training_data.size(), data.data());
        is_trained_ = true;
        
        // After training, transfer vectors from fallback storage to FAISS index
        transfer_vectors_to_faiss();
    }
    
    void transfer_vectors_to_faiss() {
        if (!index_ || !is_trained_ || vectors_.empty()) return;
        
        // Prepare batch data for FAISS
        std::vector<float> data;
        data.reserve(vectors_.size() * config_.dimension);
        
        for (const auto& pair : vectors_) {
            const Vector& vec = pair.second;
            for (float val : vec) {
                data.push_back(val);
            }
            // Update the mapping
            faiss_to_custom_id_.push_back(pair.first);
        }
        
        // Add all vectors to FAISS at once
        if (!data.empty()) {
            index_->add(vectors_.size(), data.data());
        }
        
        // Clear the fallback storage since vectors are now in FAISS
        vectors_.clear();
    }
#endif
    
    // Fallback search implementation (brute force)
    std::vector<QueryResult> search_fallback(const Vector& query, const SearchParams& params) const {
        std::vector<std::pair<float, VectorId>> scored_results;
        
#ifdef FAISS_AVAILABLE
        for (const auto& pair : id_to_vector_) {
            float distance = compute_distance(query, pair.second);
            scored_results.emplace_back(distance, pair.first);
        }
#else
        for (const auto& pair : vectors_) {
            float distance = compute_distance(query, pair.second);
            scored_results.emplace_back(distance, pair.first);
        }
#endif
        
        // Sort by distance (ascending for L2, descending for inner product)
        bool ascending = (config_.metric == DistanceMetric::L2);
        std::sort(scored_results.begin(), scored_results.end(),
                 [ascending](const auto& a, const auto& b) {
                     return ascending ? a.first < b.first : a.first > b.first;
                 });
        
        std::vector<QueryResult> results;
        size_t k = std::min(static_cast<size_t>(params.k), scored_results.size());
        results.reserve(k);
        
        for (size_t i = 0; i < k; ++i) {
            results.emplace_back(scored_results[i].second, scored_results[i].first);
        }
        
        return results;
    }
    
    float compute_distance(const Vector& a, const Vector& b) const {
        if (a.size() != b.size()) {
            throw SageDBException("Vector dimensions do not match");
        }
        
        float distance = 0.0f;
        
        switch (config_.metric) {
            case DistanceMetric::L2:
                for (size_t i = 0; i < a.size(); ++i) {
                    float diff = a[i] - b[i];
                    distance += diff * diff;
                }
                return std::sqrt(distance);
                
            case DistanceMetric::INNER_PRODUCT:
                for (size_t i = 0; i < a.size(); ++i) {
                    distance += a[i] * b[i];
                }
                return distance;
                
            case DistanceMetric::COSINE:
                {
                    float dot = 0.0f, norm_a = 0.0f, norm_b = 0.0f;
                    for (size_t i = 0; i < a.size(); ++i) {
                        dot += a[i] * b[i];
                        norm_a += a[i] * a[i];
                        norm_b += b[i] * b[i];
                    }
                    return 1.0f - (dot / (std::sqrt(norm_a) * std::sqrt(norm_b)));
                }
        }
        return 0.0f;
    }
};

// VectorStore implementation
VectorStore::VectorStore(const DatabaseConfig& config) 
    : impl_(std::make_unique<Impl>(config)), config_(config), next_id_(1) {
    if (config_.dimension == 0) {
        throw SageDBException("Vector dimension must be greater than 0");
    }
}

VectorStore::~VectorStore() = default;

VectorId VectorStore::add_vector(const Vector& vector) {
    validate_vector(vector);
    return impl_->add_vector(vector);
}

std::vector<VectorId> VectorStore::add_vectors(const std::vector<Vector>& vectors) {
    for (const auto& vector : vectors) {
        validate_vector(vector);
    }
    return impl_->add_vectors(vectors);
}

std::vector<QueryResult> VectorStore::search(const Vector& query, const SearchParams& params) const {
    validate_vector(query);
    ensure_trained();
    return impl_->search(query, params);
}

void VectorStore::build_index() {
    impl_->build_index();
}

void VectorStore::train_index(const std::vector<Vector>& training_data) {
    impl_->train_index(training_data);
}

bool VectorStore::is_trained() const {
    return impl_->is_trained();
}

size_t VectorStore::size() const {
    return impl_->size();
}

Dimension VectorStore::dimension() const {
    return config_.dimension;
}

IndexType VectorStore::index_type() const {
    return config_.index_type;
}

void VectorStore::save(const std::string& filepath) const {
    impl_->save(filepath);
}

void VectorStore::load(const std::string& filepath) {
    impl_->load(filepath);
}

void VectorStore::validate_vector(const Vector& vector) const {
    if (vector.size() != config_.dimension) {
        throw SageDBException("Vector dimension mismatch: expected " + 
                             std::to_string(config_.dimension) + 
                             ", got " + std::to_string(vector.size()));
    }
}

void VectorStore::ensure_trained() const {
    if (!is_trained()) {
        throw SageDBException("Index is not trained. Call train_index() first.");
    }
}

} // namespace sage_db
