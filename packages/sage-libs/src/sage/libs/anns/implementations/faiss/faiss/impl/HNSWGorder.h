//add by ghr

#pragma once

#include <vector>

#include <faiss/Index.h>

namespace faiss {

struct HNSW;

/**
 * Compute the Gorder permutation for the level-0 graph of an HNSW structure.
 *
 * @param graph  reference graph that exposes neighbor lists via HNSW API
 * @param window sliding window ("w" in the paper); must be >= 0
 * @return vector pinv where pinv[old_id] = new_id
 */
FAISS_API std::vector<idx_t> compute_hnsw_gorder_old_to_new(
        const HNSW& graph,
        int window);

} // namespace faiss
