#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <thread>
#include <unordered_set>
#include <vector>

#include "plsh.hpp"

using DenseVector = std::vector<float>;

DenseVector create_random_dense_vector(size_t dimensions) {
    DenseVector vec(dimensions);
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_real_distribution<float> val_dist(-1.0f, 1.0f);

    for (size_t i = 0; i < dimensions; ++i) {
        vec[i] = val_dist(gen);
    }
    return vec;
}

SparseVector dense_to_sparse_and_normalize(const DenseVector& dense_vec) {
    SparseVector sparse_vec;
    sparse_vec.indices.reserve(dense_vec.size());
    sparse_vec.values.reserve(dense_vec.size());
    float norm_sq = 0.0f;

    for (uint32_t i = 0; i < dense_vec.size(); ++i) {
        sparse_vec.indices.push_back(i);
        sparse_vec.values.push_back(dense_vec[i]);
        norm_sq += dense_vec[i] * dense_vec[i];
    }

    float norm = std::sqrt(norm_sq);
    if (norm > 0) {
        for (float& val : sparse_vec.values) {
            val /= norm;
        }
    }
    return sparse_vec;
}

float calculate_angular_distance_dense(const DenseVector& v1,
                                       const DenseVector& v2) {
    float dot_product = 0.0f;
    float norm1_sq = 0.0f;
    float norm2_sq = 0.0f;

    for (size_t i = 0; i < v1.size(); ++i) {
        dot_product += v1[i] * v2[i];
        norm1_sq += v1[i] * v1[i];
        norm2_sq += v2[i] * v2[i];
    }

    float norm1 = std::sqrt(norm1_sq);
    float norm2 = std::sqrt(norm2_sq);

    if (norm1 == 0 || norm2 == 0) return M_PI / 2.0f;

    float cosine_similarity = dot_product / (norm1 * norm2);

    cosine_similarity = std::max(-1.0f, std::min(1.0f, cosine_similarity));
    return std::acos(cosine_similarity);
}

std::vector<Result> find_ground_truth_dense(
    const DenseVector& query_point, const std::vector<DenseVector>& all_data,
    float radius, uint32_t query_id_to_exclude) {
    std::vector<Result> ground_truth_results;
    for (uint32_t i = 0; i < all_data.size(); ++i) {
        if (i == query_id_to_exclude) continue;

        float distance =
            calculate_angular_distance_dense(query_point, all_data[i]);
        if (distance <= radius) {
            ground_truth_results.push_back({i, distance});
        }
    }
    return ground_truth_results;
}

int main() {
    std::cout << "--- PLSH Index Demo Adapted for DENSE Vectors (e.g., "
                 "SIFT-like data) ---"
              << std::endl;
    std::cout << "!!! WARNING: Using a sparse-optimized algorithm for dense "
                 "data. Expect low performance. !!!"
              << std::endl;
    std::cout << "!!! WARNING: Distance metric is Angular, which may not be "
                 "ideal for SIFT. !!!"
              << std::endl;

    const size_t dimensions = 128;
    const int k = 10;
    const int m = 60;
    const unsigned int num_threads = std::thread::hardware_concurrency();

    const int initial_points = 20000;
    const int streaming_points = 80000;
    const int total_points = initial_points + streaming_points;

    std::cout << "\n[CONFIG]" << std::endl;
    std::cout << "  - Vector Type: DENSE" << std::endl;
    std::cout << "  - Dimensions: " << dimensions << ", k: " << k
              << ", m: " << m << std::endl;
    std::cout << "  - Data Size: " << initial_points << " (initial) + "
              << streaming_points << " (streaming) = " << total_points
              << std::endl;

    try {
        std::cout << "\n[PHASE 1: Generating Dense Data]" << std::endl;
        std::vector<DenseVector> all_data(total_points);
        for (int i = 0; i < total_points; ++i) {
            all_data[i] = create_random_dense_vector(dimensions);
        }
        std::cout << "  - Generated " << total_points << " dense vectors."
                  << std::endl;

        PLSHIndex index(dimensions, k, m, num_threads);
        std::cout << "\n[PHASE 2: Initial Index Build]" << std::endl;
        std::vector<SparseVector> initial_data_sparse;
        initial_data_sparse.reserve(initial_points);
        for (int i = 0; i < initial_points; ++i) {
            initial_data_sparse.push_back(
                dense_to_sparse_and_normalize(all_data[i]));
        }
        index.build(initial_data_sparse);
        std::cout << "  - Built initial index with " << initial_points
                  << " points." << std::endl;

        std::cout << "\n[PHASE 3: Streaming Inserts & Periodic Merging]"
                  << std::endl;
        auto streaming_start = std::chrono::high_resolution_clock::now();
        std::vector<SparseVector> streaming_batch;
        streaming_batch.reserve(streaming_points);
        for (int i = 0; i < streaming_points; ++i) {
            streaming_batch.push_back(
                dense_to_sparse_and_normalize(all_data[initial_points + i]));
        }
        index.insert_batch(streaming_batch);

        std::cout << "  -> Performing merge after streaming batch..."
                  << std::endl;
        index.merge_delta_to_static();

        auto streaming_end = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> streaming_duration =
            streaming_end - streaming_start;
        double effective_insert_qps =
            streaming_points > 0 ? streaming_points / streaming_duration.count()
                                 : 0;

        std::cout << "  - All streaming data inserted and merged." << std::endl;
        std::cout << std::fixed << std::setprecision(2);
        std::cout << "  - Total streaming inserts: " << streaming_points
                  << std::endl;
        std::cout << "  - Total streaming time (inserts + merges): "
                  << streaming_duration.count() << " s" << std::endl;
        std::cout << "  - Effective Insert QPS: " << effective_insert_qps
                  << " ops/sec" << std::endl;

        std::cout << "\n[PHASE 4: Query Performance Test]" << std::endl;
        const int num_queries = 200;
        const float radius = 1.2f;

        std::vector<SparseVector> query_batch;
        query_batch.reserve(num_queries);
        for (int i = 0; i < num_queries; ++i) {
            query_batch.push_back(dense_to_sparse_and_normalize(all_data[i]));
        }

        auto query_start = std::chrono::high_resolution_clock::now();
        auto batch_results = index.query_batch(query_batch, radius);
        auto query_end = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> query_duration = query_end - query_start;
        double query_qps = num_queries / query_duration.count();
        double avg_latency_ms = (query_duration.count() * 1000) / num_queries;

        std::cout << std::fixed << std::setprecision(2);
        std::cout << "  - Query QPS:     " << query_qps << " ops/sec"
                  << std::endl;
        std::cout << "  - Avg Latency:   " << avg_latency_ms << " ms/query"
                  << std::endl;

        std::cout << "\n[PHASE 5: Recall Verification]" << std::endl;
        const int query_idx_for_recall = 0;
        const DenseVector& query_point_dense = all_data[query_idx_for_recall];

        SparseVector query_point_sparse =
            dense_to_sparse_and_normalize(query_point_dense);
        std::vector<Result> lsh_results =
            index.query_radius(query_point_sparse, radius);
        std::vector<Result> ground_truth = find_ground_truth_dense(
            query_point_dense, all_data, radius, query_idx_for_recall);

        std::unordered_set<uint32_t> ground_truth_ids;
        for (const auto& res : ground_truth) ground_truth_ids.insert(res.id);

        int true_positives = 0;
        for (const auto& lsh_res : lsh_results) {
            if (ground_truth_ids.count(lsh_res.id)) {
                true_positives++;
            }
        }

        double recall =
            ground_truth.empty()
                ? 1.0
                : static_cast<double>(true_positives) / ground_truth.size();
        std::cout << "  - Ground Truth Neighbors: " << ground_truth.size()
                  << std::endl;
        std::cout << "  - LSH Found Neighbors:    " << lsh_results.size()
                  << std::endl;
        std::cout << "  - Correctly Found:      " << true_positives
                  << std::endl;
        std::cout << "  - Recall:               " << recall * 100.0 << "%"
                  << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "\nAn error occurred: " << e.what() << std::endl;
        return 1;
    }

    std::cout << "\n--- Dense Vector Demo finished ---" << std::endl;
    return 0;
}
