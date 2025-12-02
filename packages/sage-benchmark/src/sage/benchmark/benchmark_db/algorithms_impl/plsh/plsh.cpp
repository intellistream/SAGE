#include "plsh.hpp"

#include <algorithm>
#include <cmath>
#include <random>
#include <stdexcept>
#if defined(__AVX2__)
#include <immintrin.h>
#endif

PLSHIndex::PLSHIndex(size_t dimensions, int k, int m, unsigned int num_threads,
                     double delta_merge_ratio, size_t min_delta_merge)
    : D_(dimensions),
      k_(k),
      m_(m),
      L_(m > 1 ? m * (m - 1) / 2 : 0),
      num_threads_(num_threads),
      delta_size_(0),
      delta_merge_ratio_(delta_merge_ratio),
      min_delta_merge_(min_delta_merge) {
    if (D_ == 0) {
        throw std::invalid_argument(
            "Vector dimensions must be greater than 0.");
    }
    if (k_ <= 0 || k_ % 2 != 0) {
        throw std::invalid_argument("k must be a positive even integer.");
    }
    if (m_ < 2) {
        throw std::invalid_argument("m must be 2 or greater to form pairs.");
    }
    if (num_threads_ == 0) {
        throw std::invalid_argument("Number of threads must be at least 1.");
    }
    if (delta_merge_ratio_ < 0.0) {
        throw std::invalid_argument("delta_merge_ratio must be non-negative.");
    }
    if (min_delta_merge_ == 0) {
        min_delta_merge_ = 1;
    }

    const size_t total_hyperplanes = m_ * (k_ / 2);
    random_hyperplanes_.resize(total_hyperplanes);

    std::random_device rd;
    std::mt19937 gen(rd());
    std::normal_distribution<float> dist(0.0f, 1.0f);

    for (size_t i = 0; i < total_hyperplanes; ++i) {
        random_hyperplanes_[i].resize(D_);
        float norm_sq = 0.0f;

        for (size_t j = 0; j < D_; ++j) {
            float val = dist(gen);
            random_hyperplanes_[i][j] = val;
            norm_sq += val * val;
        }

        float norm = std::sqrt(norm_sq);
        if (norm > 0) {
            for (size_t j = 0; j < D_; ++j) {
                random_hyperplanes_[i][j] /= norm;
            }
        }
    }

    static_tables_offsets_.resize(L_);
    static_tables_data_.resize(L_);
    delta_tables_.resize(L_);
}

namespace {
#if defined(__AVX2__)
inline float sparse_dot_hyperplane_avx(const SparseVector& vec,
                                       const float* hyperplane,
                                       size_t dimension) {
    const size_t n = vec.indices.size();
    const uint32_t* idx_ptr = vec.indices.data();
    const float* val_ptr = vec.values.data();

    __m256 acc = _mm256_setzero_ps();
    size_t i = 0;
    constexpr int scale = sizeof(float);

    for (; i + 8 <= n; i += 8) {
        __m256i index_vec =
            _mm256_loadu_si256(reinterpret_cast<const __m256i*>(idx_ptr + i));
        __m256 gathered = _mm256_i32gather_ps(hyperplane, index_vec, scale);
        __m256 values = _mm256_loadu_ps(val_ptr + i);
#if defined(__FMA__)
        acc = _mm256_fmadd_ps(values, gathered, acc);
#else
        acc = _mm256_add_ps(acc, _mm256_mul_ps(values, gathered));
#endif
    }

    float partial[8];
    _mm256_storeu_ps(partial, acc);
    float result = partial[0] + partial[1] + partial[2] + partial[3] +
                   partial[4] + partial[5] + partial[6] + partial[7];

    for (; i < n; ++i) {
        uint32_t feature_idx = idx_ptr[i];
        if (feature_idx < dimension) {
            result += val_ptr[i] * hyperplane[feature_idx];
        }
    }
    return result;
}
#endif

inline float sparse_dot_hyperplane(const SparseVector& vec,
                                   const float* hyperplane, size_t dimension) {
#if defined(__AVX2__)
    return sparse_dot_hyperplane_avx(vec, hyperplane, dimension);
#else
    float dot_product = 0.0f;
    for (size_t k = 0; k < vec.indices.size(); ++k) {
        uint32_t feature_idx = vec.indices[k];
        if (feature_idx < dimension) {
            dot_product += vec.values[k] * hyperplane[feature_idx];
        }
    }
    return dot_product;
#endif
}
}  // namespace

float PLSHIndex::l2_distance(const SparseVector& v1, const SparseVector& v2) {
    size_t i = 0;
    size_t j = 0;
    float sum_sq = 0.0f;

    while (i < v1.indices.size() && j < v2.indices.size()) {
        uint32_t idx1 = v1.indices[i];
        uint32_t idx2 = v2.indices[j];
        if (idx1 == idx2) {
            float diff = v1.values[i] - v2.values[j];
            sum_sq += diff * diff;
            ++i;
            ++j;
        } else if (idx1 < idx2) {
            float val = v1.values[i];
            sum_sq += val * val;
            ++i;
        } else {
            float val = v2.values[j];
            sum_sq += val * val;
            ++j;
        }
    }

    while (i < v1.indices.size()) {
        float val = v1.values[i++];
        sum_sq += val * val;
    }
    while (j < v2.indices.size()) {
        float val = v2.values[j++];
        sum_sq += val * val;
    }

    return std::sqrt(sum_sq);
}

void PLSHIndex::build(const std::vector<SparseVector>& data_points) {
    std::unique_lock<std::shared_mutex> lock(index_mutex_);

    data_storage_.clear();
    static_tables_offsets_.clear();
    static_tables_data_.clear();
    delta_tables_.clear();
    delta_size_.store(0, std::memory_order_relaxed);

    static_tables_offsets_.resize(L_);
    static_tables_data_.resize(L_);
    delta_tables_.resize(L_);

    const size_t n_points = data_points.size();
    if (n_points == 0) {
        return;
    }
    data_storage_ = data_points;

    std::vector<std::vector<uint16_t>> base_hashes =
        _compute_base_hashes(data_storage_);
    _build_static_tables_parallel(base_hashes);
}

std::vector<std::vector<uint16_t>> PLSHIndex::_compute_base_hashes(
    const std::vector<SparseVector>& points) const {
    const size_t n_points = points.size();
    const int k_half = k_ / 2;

    std::vector<std::vector<uint16_t>> hashes(n_points,
                                              std::vector<uint16_t>(m_, 0));
    std::vector<std::thread> threads;
    size_t chunk_size = (n_points + num_threads_ - 1) / num_threads_;

    for (unsigned int t = 0; t < num_threads_; ++t) {
        threads.emplace_back([=, &points, &hashes] {
            size_t start = t * chunk_size;
            size_t end = std::min(start + chunk_size, n_points);

            for (size_t i = start; i < end; ++i) {
                for (int j = 0; j < m_; ++j) {
                    uint16_t current_hash = 0;
                    for (int bit = 0; bit < k_half; ++bit) {
                        size_t hyperplane_idx = j * k_half + bit;
                        const float* hyperplane =
                            random_hyperplanes_[hyperplane_idx].data();
                        float dot_product =
                            sparse_dot_hyperplane(points[i], hyperplane, D_);

                        if (dot_product >= 0) {
                            current_hash |= (1 << bit);
                        }
                    }
                    hashes[i][j] = current_hash;
                }
            }
        });
    }

    for (auto& th : threads) {
        th.join();
    }

    return hashes;
}

void PLSHIndex::_build_static_tables_parallel(
    const std::vector<std::vector<uint16_t>>& base_hashes) {
    const size_t n_points = data_storage_.size();
    if (n_points == 0) return;

    std::vector<std::vector<uint32_t>> level1_partitions(
        m_, std::vector<uint32_t>(n_points));

    _partition_level1_parallel(level1_partitions, base_hashes);
    _partition_level2_parallel(level1_partitions, base_hashes);
}

void PLSHIndex::_partition_level1_parallel(
    std::vector<std::vector<uint32_t>>& partitioned_indices,
    const std::vector<std::vector<uint16_t>>& base_hashes) {
    const size_t n_points = data_storage_.size();
    if (n_points == 0) return;

    const int num_partitions_l1 = 1 << (k_ / 2);
    std::vector<std::thread> threads_l1;
    for (int i = 0; i < m_; ++i) {
        threads_l1.emplace_back([this, i, n_points, num_partitions_l1,
                                 &partitioned_indices, &base_hashes] {
            std::vector<uint32_t>& output_indices = partitioned_indices[i];

            std::vector<std::vector<uint32_t>> local_histograms(
                num_threads_, std::vector<uint32_t>(num_partitions_l1, 0));
            size_t chunk_size = (n_points + num_threads_ - 1) / num_threads_;

            std::vector<std::thread> hist_threads;
            for (unsigned int t = 0; t < num_threads_; ++t) {
                hist_threads.emplace_back([this, t, i, chunk_size, n_points,
                                           &local_histograms, &base_hashes] {
                    size_t start = t * chunk_size;
                    size_t end = std::min(start + chunk_size, n_points);
                    for (size_t p = start; p < end; ++p) {
                        uint16_t bucket = base_hashes[p][i];
                        local_histograms[t][bucket]++;
                    }
                });
            }
            for (auto& th : hist_threads) th.join();

            std::vector<uint32_t> global_offsets(num_partitions_l1, 0);
            for (unsigned int t = 0; t < num_threads_; ++t) {
                for (int part = 0; part < num_partitions_l1; ++part) {
                    uint32_t count = local_histograms[t][part];
                    local_histograms[t][part] = global_offsets[part];
                    global_offsets[part] += count;
                }
            }

            std::vector<std::thread> scatter_threads;
            for (unsigned int t = 0; t < num_threads_; ++t) {
                scatter_threads.emplace_back([this, t, i, chunk_size, n_points,
                                              &local_histograms, &base_hashes,
                                              &output_indices] {
                    size_t start = t * chunk_size;
                    size_t end = std::min(start + chunk_size, n_points);
                    for (size_t p = start; p < end; ++p) {
                        uint16_t hash_val = base_hashes[p][i];
                        output_indices[local_histograms[t][hash_val]++] = p;
                    }
                });
            }
            for (auto& th : scatter_threads) th.join();
        });
    }
    for (auto& th : threads_l1) th.join();
}

void PLSHIndex::_partition_level2_parallel(
    const std::vector<std::vector<uint32_t>>& level1_partitions,
    const std::vector<std::vector<uint16_t>>& base_hashes) {
    const size_t n_points = data_storage_.size();
    if (n_points == 0) return;

    const int num_partitions_l2 = 1 << k_;
    int table_idx = 0;
    for (int i = 0; i < m_; ++i) {
        for (int j = i + 1; j < m_; ++j) {
            static_tables_data_[table_idx].resize(n_points);
            static_tables_offsets_[table_idx].resize(num_partitions_l2 + 1, 0);
            const std::vector<uint32_t>& input_indices = level1_partitions[i];
            std::vector<uint16_t> reordered_l2_hashes(n_points);
            for (size_t p = 0; p < n_points; ++p) {
                reordered_l2_hashes[p] = base_hashes[input_indices[p]][j];
            }

            auto& offsets = static_tables_offsets_[table_idx];
            for (size_t p = 0; p < n_points; ++p) {
                uint16_t l1_hash = base_hashes[input_indices[p]][i];
                uint16_t l2_hash = reordered_l2_hashes[p];
                uint32_t combined_hash =
                    (static_cast<uint32_t>(l1_hash) << (k_ / 2)) | l2_hash;
                offsets[combined_hash + 1]++;
            }

            for (int part = 0; part < num_partitions_l2; ++part) {
                offsets[part + 1] += offsets[part];
            }

            auto& data_output = static_tables_data_[table_idx];
            std::vector<uint32_t> current_offsets = offsets;
            for (size_t p = 0; p < n_points; ++p) {
                uint16_t l1_hash = base_hashes[input_indices[p]][i];
                uint16_t l2_hash = reordered_l2_hashes[p];
                uint32_t combined_hash =
                    (static_cast<uint32_t>(l1_hash) << (k_ / 2)) | l2_hash;
                data_output[current_offsets[combined_hash]++] =
                    input_indices[p];
            }

            table_idx++;
        }
    }
}

void PLSHIndex::insert(const SparseVector& data_point) {
    std::vector<SparseVector> single_batch;
    single_batch.reserve(1);
    single_batch.push_back(data_point);
    insert_batch(single_batch);
}

void PLSHIndex::insert_batch(const std::vector<SparseVector>& data_points) {
    if (data_points.empty()) {
        return;
    }

    const size_t batch_size = data_points.size();
    const int k_half = k_ / 2;

    std::vector<std::vector<uint16_t>> batched_hashes(
        batch_size, std::vector<uint16_t>(m_));

    size_t chunk_size = (batch_size + num_threads_ - 1) / num_threads_;
    std::vector<std::thread> workers;
    workers.reserve(num_threads_);
    for (unsigned int t = 0; t < num_threads_; ++t) {
        size_t start = t * chunk_size;
        if (start >= batch_size) break;
        size_t end = std::min(start + chunk_size, batch_size);
        workers.emplace_back(
            [this, start, end, &data_points, &batched_hashes, k_half] {
                for (size_t idx = start; idx < end; ++idx) {
                    const SparseVector& point = data_points[idx];
                    for (int i = 0; i < m_; ++i) {
                        uint16_t current_hash = 0;
                        for (int bit = 0; bit < k_half; ++bit) {
                            size_t hyperplane_idx = i * k_half + bit;
                            const float* hyperplane =
                                random_hyperplanes_[hyperplane_idx].data();
                            float dot_product =
                                sparse_dot_hyperplane(point, hyperplane, D_);
                            if (dot_product >= 0) {
                                current_hash |= (1 << bit);
                            }
                        }
                        batched_hashes[idx][i] = current_hash;
                    }
                }
            });
    }
    for (auto& worker : workers) {
        worker.join();
    }

    uint32_t base_id = 0;
    size_t total_after_insert = 0;
    {
        std::lock_guard<std::mutex> lock(delta_insert_mutex_);
        base_id = static_cast<uint32_t>(data_storage_.size());
        data_storage_.reserve(base_id + batch_size);
        data_storage_.insert(data_storage_.end(), data_points.begin(),
                             data_points.end());
        total_after_insert = data_storage_.size();

        if (delta_tables_.size() < static_cast<size_t>(L_)) {
            delta_tables_.resize(L_);
        }

        for (int table_idx = 0; table_idx < L_; ++table_idx) {
            if (delta_tables_[table_idx].empty()) {
                delta_tables_[table_idx].resize(1 << k_);
            }
        }

        int table_idx = 0;
        for (int i = 0; i < m_; ++i) {
            for (int j = i + 1; j < m_; ++j) {
                auto& table = delta_tables_[table_idx];
                for (size_t idx = 0; idx < batch_size; ++idx) {
                    uint32_t combined_hash =
                        (static_cast<uint32_t>(batched_hashes[idx][i])
                         << k_half) |
                        batched_hashes[idx][j];
                    table[combined_hash].push_back(base_id +
                                                   static_cast<uint32_t>(idx));
                }
                table_idx++;
            }
        }
    }

    delta_size_.fetch_add(batch_size, std::memory_order_relaxed);
    _maybe_trigger_merge(total_after_insert);
}

void PLSHIndex::_maybe_trigger_merge(size_t total_points_snapshot) {
    if (delta_merge_ratio_ <= 0.0) {
        return;
    }

    const size_t pending_delta = delta_size_.load(std::memory_order_relaxed);
    if (pending_delta == 0) {
        return;
    }

    if (total_points_snapshot == 0) {
        return;
    }

    const size_t ratio_threshold = static_cast<size_t>(
        delta_merge_ratio_ * static_cast<double>(total_points_snapshot));
    const size_t threshold = std::max(min_delta_merge_, ratio_threshold);

    if (pending_delta >= threshold) {
        merge_delta_to_static();
    }
}

std::vector<Result> PLSHIndex::query_radius(const SparseVector& query_point,
                                            float radius) const {
    std::shared_lock<std::shared_mutex> lock(index_mutex_);
    return _query_locked(query_point, radius);
}

std::vector<Result> PLSHIndex::_query_locked(const SparseVector& query_point,
                                             float radius) const {
    std::vector<uint32_t> candidates = _get_candidates(query_point);

    if (candidates.empty()) {
        return {};
    }

    thread_local std::vector<uint32_t> seen_versions;
    thread_local uint32_t seen_epoch = 0;
    thread_local std::vector<uint32_t> unique_candidates_buffer;

    if (++seen_epoch == 0) {
        std::fill(seen_versions.begin(), seen_versions.end(), 0);
        seen_epoch = 1;
    }

    if (seen_versions.size() < data_storage_.size()) {
        seen_versions.resize(data_storage_.size(), 0);
    }

    unique_candidates_buffer.clear();
    unique_candidates_buffer.reserve(candidates.size());

    for (const uint32_t id : candidates) {
        if (seen_versions[id] != seen_epoch) {
            seen_versions[id] = seen_epoch;
            unique_candidates_buffer.push_back(id);
        }
    }

    return _filter_candidates(query_point, unique_candidates_buffer, radius);
}

std::vector<std::vector<Result>> PLSHIndex::query_batch(
    const std::vector<SparseVector>& query_points, float radius) const {
    const size_t total_queries = query_points.size();
    std::vector<std::vector<Result>> batch_results(total_queries);
    if (total_queries == 0) {
        return batch_results;
    }

    struct SharedLockGuard {
        std::shared_mutex& mutex;
        explicit SharedLockGuard(std::shared_mutex& m) : mutex(m) {
            mutex.lock_shared();
        }
        ~SharedLockGuard() { mutex.unlock_shared(); }
        SharedLockGuard(const SharedLockGuard&) = delete;
        SharedLockGuard& operator=(const SharedLockGuard&) = delete;
    };

    SharedLockGuard guard(index_mutex_);

    const unsigned int threads_to_use = std::min<unsigned int>(
        num_threads_, static_cast<unsigned int>(total_queries));
    if (threads_to_use <= 1) {
        for (size_t i = 0; i < total_queries; ++i) {
            batch_results[i] = _query_locked(query_points[i], radius);
        }
        return batch_results;
    }

#pragma omp parallel for schedule(dynamic, 8) num_threads(threads_to_use)
    for (int64_t idx = 0; idx < static_cast<int64_t>(total_queries); ++idx) {
        batch_results[idx] = _query_locked(query_points[idx], radius);
    }

    return batch_results;
}

std::vector<Result> PLSHIndex::query_topk(const SparseVector& query_point,
                                          size_t topk) const {
    std::shared_lock<std::shared_mutex> lock(index_mutex_);
    std::vector<uint32_t> candidates = _get_candidates(query_point);

    if (candidates.empty()) {
        return {};
    }

    std::vector<uint32_t> unique_candidates;
    unique_candidates.reserve(candidates.size());
    std::vector<bool> seen(data_storage_.size(), false);
    for (const uint32_t id : candidates) {
        if (!seen[id]) {
            unique_candidates.push_back(id);
            seen[id] = true;
        }
    }

    SparseVector normalized_query = query_point;
    float norm_sq = 0.0f;
    for (float val : normalized_query.values) norm_sq += val * val;
    float norm = std::sqrt(norm_sq);
    if (norm > 0) {
        for (float& val : normalized_query.values) val /= norm;
    }

    std::vector<Result> results;
    results.reserve(unique_candidates.size());
    for (const uint32_t id : unique_candidates) {
        const SparseVector& candidate_vec = data_storage_[id];
        float distance = l2_distance(normalized_query, candidate_vec);
        results.push_back({id, distance});
    }

    if (results.size() > topk) {
        std::nth_element(results.begin(), results.begin() + topk, results.end(),
                         [](const Result& a, const Result& b) {
                             return a.distance < b.distance;
                         });
        results.resize(topk);
        std::sort(results.begin(), results.end(),
                  [](const Result& a, const Result& b) {
                      return a.distance < b.distance;
                  });
    } else {
        std::sort(results.begin(), results.end(),
                  [](const Result& a, const Result& b) {
                      return a.distance < b.distance;
                  });
    }

    return results;
}

std::vector<uint32_t> PLSHIndex::_get_candidates(
    const SparseVector& query_point) const {
    std::vector<uint32_t> candidates;
    const int k_half = k_ / 2;

    std::vector<uint16_t> base_hashes(m_);
    for (int i = 0; i < m_; ++i) {
        uint16_t current_hash = 0;
        for (int bit = 0; bit < k_half; ++bit) {
            size_t hyperplane_idx = i * k_half + bit;
            const float* hyperplane =
                random_hyperplanes_[hyperplane_idx].data();
            float dot_product =
                sparse_dot_hyperplane(query_point, hyperplane, D_);
            if (dot_product >= 0) {
                current_hash |= (1 << bit);
            }
        }
        base_hashes[i] = current_hash;
    }

    int table_idx = 0;
    for (int i = 0; i < m_; ++i) {
        for (int j = i + 1; j < m_; ++j) {
            uint32_t combined_hash =
                (static_cast<uint32_t>(base_hashes[i]) << k_half) |
                base_hashes[j];
            if (table_idx < static_tables_offsets_.size() &&
                !static_tables_offsets_[table_idx].empty()) {
                uint32_t start =
                    static_tables_offsets_[table_idx][combined_hash];
                uint32_t end =
                    static_tables_offsets_[table_idx][combined_hash + 1];
                for (uint32_t p = start; p < end; ++p) {
                    candidates.push_back(static_tables_data_[table_idx][p]);
                }
            }

            if (table_idx < delta_tables_.size() &&
                !delta_tables_[table_idx].empty()) {
                const auto& bucket = delta_tables_[table_idx][combined_hash];
                candidates.insert(candidates.end(), bucket.begin(),
                                  bucket.end());
            }

            table_idx++;
        }
    }

    return candidates;
}

std::vector<Result> PLSHIndex::_filter_candidates(
    const SparseVector& query_point, const std::vector<uint32_t>& candidates,
    float radius) const {
    std::vector<Result> results;
    SparseVector normalized_query = query_point;
    float norm_sq = 0.0f;
    for (float val : normalized_query.values) norm_sq += val * val;
    float norm = std::sqrt(norm_sq);
    if (norm > 0) {
        for (float& val : normalized_query.values) val /= norm;
    }

    const float min_cosine = std::cos(radius);
    std::vector<float> dense_query(D_, 0.0f);
    for (size_t i = 0; i < normalized_query.indices.size(); ++i) {
        dense_query[normalized_query.indices[i]] = normalized_query.values[i];
    }

    const unsigned int threads = std::min<unsigned int>(
        num_threads_, static_cast<unsigned int>(candidates.size()));
    if (threads <= 1) {
        for (const uint32_t id : candidates) {
            const SparseVector& candidate_vec = data_storage_[id];
            float dot_product = 0.0f;
            for (size_t i = 0; i < candidate_vec.indices.size(); ++i) {
                dot_product += dense_query[candidate_vec.indices[i]] *
                               candidate_vec.values[i];
            }

            if (dot_product >= min_cosine) {
                float distance =
                    std::acos(std::max(-1.0f, std::min(1.0f, dot_product)));
                results.push_back({id, distance});
            }
        }
        return results;
    }

    std::vector<std::vector<Result>> thread_results(threads);
    std::vector<std::thread> workers;
    workers.reserve(threads);
    size_t chunk_size = (candidates.size() + threads - 1) / threads;

    for (unsigned int t = 0; t < threads; ++t) {
        size_t start = t * chunk_size;
        if (start >= candidates.size()) break;
        size_t end = std::min(start + chunk_size, candidates.size());
        thread_results[t].reserve(end - start);

        workers.emplace_back([this, start, end, &candidates, &dense_query,
                              min_cosine, &thread_results, t] {
            auto& local = thread_results[t];
            for (size_t idx = start; idx < end; ++idx) {
                const uint32_t id = candidates[idx];
                const SparseVector& candidate_vec = data_storage_[id];
                float dot_product = 0.0f;
                for (size_t i = 0; i < candidate_vec.indices.size(); ++i) {
                    dot_product += dense_query[candidate_vec.indices[i]] *
                                   candidate_vec.values[i];
                }
                if (dot_product >= min_cosine) {
                    float distance =
                        std::acos(std::max(-1.0f, std::min(1.0f, dot_product)));
                    local.push_back({id, distance});
                }
            }
        });
    }

    for (auto& worker : workers) {
        if (worker.joinable()) {
            worker.join();
        }
    }

    size_t total_results = 0;
    for (const auto& local : thread_results) {
        total_results += local.size();
    }
    results.reserve(total_results);
    for (auto& local : thread_results) {
        results.insert(results.end(), local.begin(), local.end());
    }

    return results;
}

void PLSHIndex::merge_delta_to_static() {
    std::unique_lock<std::shared_mutex> lock(index_mutex_);

    if (data_storage_.empty()) {
        return;
    }

    static_tables_offsets_.clear();
    static_tables_data_.clear();
    delta_tables_.clear();
    delta_size_.store(0, std::memory_order_relaxed);

    static_tables_offsets_.resize(L_);
    static_tables_data_.resize(L_);
    delta_tables_.resize(L_);

    if (!data_storage_.empty()) {
        std::vector<std::vector<uint16_t>> base_hashes =
            _compute_base_hashes(data_storage_);
        _build_static_tables_parallel(base_hashes);
    }
}
