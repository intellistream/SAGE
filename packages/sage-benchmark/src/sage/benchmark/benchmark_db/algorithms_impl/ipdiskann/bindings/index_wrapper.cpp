#include "index_wrapper.h"
#include "index_factory.h"

void MyIndexWrapper::setup(size_t max_points, size_t dim, uint32_t R, uint32_t L, uint32_t num_threads) {
    L_ = L;

    auto write_params = diskann::IndexWriteParametersBuilder(L, R)
                            .with_num_threads(num_threads)
                            .with_max_occlusion_size(500)
                            .with_alpha(1.2f)
                            .build();

    auto search_params = diskann::IndexSearchParams(L, num_threads);

    auto config = diskann::IndexConfigBuilder()
                      .with_metric(diskann::Metric::L2)
                      .with_dimension(dim)
                      .with_max_points(max_points)
                      .is_dynamic_index(true)
                      .is_enable_tags(true)
                      .is_use_opq(false)
                      .with_num_pq_chunks(0)
                      .is_pq_dist_build(false)
                      .with_tag_type("uint32")
                      .with_label_type("uint32")
                      .with_data_type("float")
                      .with_index_write_params(write_params)
                      .with_index_search_params(search_params)
                      .with_data_load_store_strategy(diskann::DataStoreStrategy::MEMORY)
                      .with_graph_load_store_strategy(diskann::GraphStoreStrategy::MEMORY)
                      .build();

    diskann::IndexFactory factory(config);
    index_ = factory.create_instance();
}

void MyIndexWrapper::build(const float* data, size_t num_points, const std::vector<uint32_t>& tags) {
//    if (!index_) throw std::runtime_error("Index not initialized. Call setup() first.");
    index_->build(data, num_points, tags);
}

void MyIndexWrapper::query(const float* query, size_t K, std::vector<uint32_t>& result_tags, std::vector<float>& distances) {
    result_tags.resize(K);
    distances.resize(K);
    std::vector<float*> res_vectors;
    index_->search_with_tags(query, K, L_, result_tags.data(), distances.data(),
                                                   res_vectors, false, "");
}

void MyIndexWrapper::batch_query(const float* queries, size_t num_queries, size_t dim, size_t K,
                    std::vector<std::vector<uint32_t>>& all_result_tags,
                    std::vector<std::vector<float>>& all_distances,
                    int num_threads) {

    all_result_tags.resize(num_queries);
    all_distances.resize(num_queries);

    for (size_t i = 0; i < num_queries; ++i) {
        all_result_tags[i].resize(K);
        all_distances[i].resize(K);
    }

    size_t num_failed = 0;

#pragma omp parallel for num_threads(num_threads) schedule(dynamic) reduction(+:num_failed)
    for (int64_t i = 0; i < static_cast<int64_t>(num_queries); ++i) {
        try {
            const float* query_ptr = queries + i * dim;
            std::vector<float*> res_vectors;

            int search_result = index_->search_with_tags(
                query_ptr, K, L_,
                all_result_tags[i].data(),
                all_distances[i].data(),
                res_vectors, false, ""
            );

            if (search_result != 0) {
                num_failed++;
            }
        } catch (const std::exception& e) {
            num_failed++;
            std::cerr << "Query " << i << " failed: " << e.what() << std::endl;
        }
    }

    if (num_failed > 0) {
        std::cout << num_failed << " of " << num_queries << " queries failed" << std::endl;
    }
}

bool MyIndexWrapper::insert_point(const float* point, uint32_t tag) {
    int res = index_->insert_point(point, tag);
    return res == 0;
}

std::vector<bool> MyIndexWrapper::insert_points_concurrent(const float* data,
                                             const uint32_t* tags,
                                             size_t num_points,
                                             size_t dim,
                                             int32_t thread_count) {
    if (!index_) throw std::runtime_error("Index not initialized");

    if (thread_count <= 0) {
        thread_count = omp_get_max_threads();
    }

    std::vector<bool> results(num_points, false);

#pragma omp parallel for num_threads(thread_count) schedule(dynamic)
    for (int64_t j = 0; j < (int64_t)num_points; j++) {
        try {
            const float* point_data = &data[j * dim];
            uint32_t tag = tags[j];

            int res = index_->insert_point(point_data, tag);
            results[j] = (res == 0);

            if (res != 0) {
                #pragma omp critical
                {
                    std::cerr << "Failed to insert point at index " << j
                    << " with tag " << tag << std::endl;
                }
            }
        } catch (const std::exception& e) {
            #pragma omp critical
            {
                std::cerr << "Exception inserting point " << j << ": " << e.what() << std::endl;
            }
            results[j] = false;
        } catch (...) {
            #pragma omp critical
            {
                std::cerr << "Unknown exception inserting point " << j << std::endl;
            }
            results[j] = false;
        }
    }

    return results;
    }

void MyIndexWrapper::remove(const std::vector<uint32_t>& tags_to_delete) {
    std::vector<uint32_t> failed;
    index_->inplace_delete(tags_to_delete, failed);
    if (!failed.empty()) {
        // std::cerr << "Warning: Failed to delete " << failed.size() << " tags.\n";
    }
}
