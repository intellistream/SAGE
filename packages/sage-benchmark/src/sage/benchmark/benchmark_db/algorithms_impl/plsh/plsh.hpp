#ifndef PLSH_HPP
#define PLSH_HPP

#include <vector>
#include <cstdint>
#include <mutex>
#include <shared_mutex>
#include <thread>
#include <atomic>

struct SparseVector {
    std::vector<uint32_t> indices;
    std::vector<float> values;
};

struct Result {
    uint32_t id;
    float distance;
};

class PLSHIndex {
public:
    PLSHIndex(size_t dimensions, int k, int m,
              unsigned int num_threads = std::thread::hardware_concurrency(),
              double delta_merge_ratio = 0.1,
              size_t min_delta_merge = 1024);

    void build(const std::vector<SparseVector>& data_points);

    void insert(const SparseVector& data_point);
    void insert_batch(const std::vector<SparseVector>& data_points);

    std::vector<Result> query_radius(const SparseVector& query_point, float radius) const;

    std::vector<Result> query_topk(const SparseVector& query_point,size_t topk) const;

    std::vector<std::vector<Result>> query_batch(
        const std::vector<SparseVector>& query_points, float radius) const;

    void merge_delta_to_static();

private:
    const size_t D_;
    const int k_;
    const int m_;
    const int L_;
    const unsigned int num_threads_;

    std::vector<SparseVector> data_storage_;
    std::vector<std::vector<float>> random_hyperplanes_;

    std::vector<std::vector<uint32_t>> static_tables_offsets_;
    std::vector<std::vector<uint32_t>> static_tables_data_;

    std::vector<std::vector<std::vector<uint32_t>>> delta_tables_;
    std::atomic<size_t> delta_size_;
    double delta_merge_ratio_;
    size_t min_delta_merge_;

    mutable std::shared_mutex index_mutex_;
    std::mutex delta_insert_mutex_;

    std::vector<std::vector<uint16_t>> _compute_base_hashes(const std::vector<SparseVector>& points) const;

    void _build_static_tables_parallel(const std::vector<std::vector<uint16_t>>& base_hashes);

    void _partition_level1_parallel(
        std::vector<std::vector<uint32_t>>& partitioned_indices,
        const std::vector<std::vector<uint16_t>>& base_hashes);

    void _partition_level2_parallel(
        const std::vector<std::vector<uint32_t>>& level1_partitions,
        const std::vector<std::vector<uint16_t>>& base_hashes);

    std::vector<uint32_t> _get_candidates(const SparseVector& query_point) const;

    static float l2_distance(const SparseVector& v1, const SparseVector& v2);

    std::vector<Result> _filter_candidates(
        const SparseVector& query_point,
        const std::vector<uint32_t>& candidates,
        float radius) const;

    std::vector<Result> _query_locked(const SparseVector& query_point, float radius) const;

    void _maybe_trigger_merge(size_t total_points_snapshot);
};

#endif // PLSH_HPP
