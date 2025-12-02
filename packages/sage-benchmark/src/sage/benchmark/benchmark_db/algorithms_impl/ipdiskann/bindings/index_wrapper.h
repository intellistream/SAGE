#pragma once

#include <memory>
#include <vector>
#include "index.h"
#include "index_factory.h"
#include "abstract_index.h"

class MyIndexWrapper {
public:

    void setup(size_t max_points, size_t dim, uint32_t R = 64, uint32_t L = 100, uint32_t num_threads = 1);

    void build(const float* data, size_t num_points, const std::vector<uint32_t>& tags);

    void query(const float* query, size_t K, std::vector<uint32_t>& result_tags, std::vector<float>& distances);

    void batch_query(const float* queries, size_t num_queries, size_t dim, size_t K,
                    std::vector<std::vector<uint32_t>>& all_result_tags,
                    std::vector<std::vector<float>>& all_distances,
                    int num_threads = 1);

    bool insert_point(const float* point, uint32_t tag);

    std::vector<bool> insert_points_concurrent(const float* data,
                                             const uint32_t* tags,
                                             size_t num_points,
                                             size_t dim,
                                             int32_t thread_count = 1);

    void remove(const std::vector<uint32_t>& tags_to_delete);

private:
    std::unique_ptr<diskann::AbstractIndex> index_;;
    uint32_t L_ = 100;
};
