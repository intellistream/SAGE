/**
 * Copyright (c) Facebook, Inc. and its affiliates.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

// -*- c++ -*-

#pragma once

#include <queue>
#include <unordered_set>
#include <vector>
#include <faiss/impl/HNSW.h>
#include <omp.h>
#include <faiss/Index.h>
#include <faiss/impl/FaissAssert.h>
#include <faiss/impl/platform_macros.h>
#include <faiss/utils/Heap.h>
#include <faiss/utils/random.h>
#include <fstream>
#include <iostream>

namespace faiss {

/** Implementation of the Hierarchical Navigable Small World
 * datastructure.
 *
 * Efficient and robust approximate nearest neighbor search using
 * Hierarchical Navigable Small World graphs
 *
 *  Yu. A. Malkov, D. A. Yashunin, arXiv 2017
 *
 * This implementation is heavily influenced by the NMSlib
 * implementation by Yury Malkov and Leonid Boystov
 * (https://github.com/searchivarius/nmslib)
 *
 * The Vanama object stores only the neighbor link structure, see
 * IndexVanama.h for the full index object.
 */


struct Vanama_breakdown_stats {
    size_t steps_greedy =
            0; // number of vertices traversing in greedy search in add
    size_t steps_iterating_add =
            0; // number of vertices visited in add_neighbors
    size_t steps_iterating_search =
            0; // number of vertices visited in searching from candidates

    size_t time_greedy_insert = 0;
    size_t time_searching_neighbors_to_add = 0;
    size_t time_add_links = 0;

    size_t time_greedy_search = 0;
    size_t time_search_from_candidates = 0;
    size_t time_dc = 0;
    size_t time_dc_linking = 0;
    size_t step_linking =0;
    size_t step_before_shrinking=0;
    Vanama_breakdown_stats() = default;
    //std::string filename="hnswbd.csv";
    void reset() {
        steps_greedy = 0;
        steps_iterating_add = 0;
        steps_iterating_search = 0;
        time_greedy_insert = 0;
        time_searching_neighbors_to_add = 0;
        time_add_links = 0;
        time_greedy_search = 0;
        time_search_from_candidates = 0;
	time_dc = 0;
	time_dc_linking = 0;
	step_before_shrinking = 0;
	step_linking = 0;
    }


    void print() {
        std::cout << steps_greedy << ","; //0
        std::cout << steps_iterating_add << ",";
        std::cout << steps_iterating_search << ","; //0

        std::cout << time_greedy_insert << ",";
        std::cout << time_searching_neighbors_to_add << ",";
        std::cout << time_add_links << ",";

        std::cout << time_greedy_search << ","; //0
        std::cout << time_search_from_candidates << ","; //0
	std::cout<<time_dc<<",";
	std::cout<<time_dc_linking<<",";
	std::cout<<step_before_shrinking<<",";
	std::cout<<step_linking<<"\n";


    std::ofstream outputFile;
    outputFile.open("vanamabd.csv", std::ios_base::app);

    if(!outputFile.is_open()){
        std::cerr<<"Failed to open file."<<std::endl;
        std::cerr<<"Error:"<<std::strerror(errno)<<std::endl;
        return;
    }
        outputFile << steps_greedy << ",";
        outputFile << steps_iterating_add << ",";
        outputFile<< steps_iterating_search << ",";

        outputFile<< time_greedy_insert << ",";
        outputFile<< time_searching_neighbors_to_add << ",";
        outputFile<< time_add_links << ",";

        outputFile<< time_greedy_search << ",";
        outputFile<< time_search_from_candidates << ",";
        outputFile<<time_dc<<",";
        outputFile<<time_dc_linking<<",";
        outputFile<<step_before_shrinking<<",";
        outputFile<<step_linking<<"\n";

    outputFile.close();
    }
};
struct Vanama {
    /// internal storage of vectors (32 bits: this is expensive)
    using storage_idx_t = int32_t;

    typedef std::pair<float, storage_idx_t> Node;


    /** Heap structure that allows fast
     */
    struct MinimaxHeap {
        int n;
        int k;
        int nvalid;

        std::vector<storage_idx_t> ids;
        std::vector<float> dis;
        typedef faiss::CMax<float, storage_idx_t> HC;

        explicit MinimaxHeap(int n) : n(n), k(0), nvalid(0), ids(n), dis(n) {}

        void push(storage_idx_t i, float v);

        float max() const;

        int size() const;

        void clear();

        int pop_min(float* vmin_out = nullptr);

        int count_below(float thresh);
    };

    /// to sort pairs of (id, distance) from nearest to fathest or the reverse
    struct NodeDistCloser {
        float d;
        int id;
        NodeDistCloser(float d, int id) : d(d), id(id) {}
        bool operator<(const NodeDistCloser& obj1) const {
            return d < obj1.d;
        }
    };

    struct NodeDistFarther {
        float d;
        int id;
        NodeDistFarther(float d, int id) : d(d), id(id) {}
        bool operator<(const NodeDistFarther& obj1) const {
            return d > obj1.d;
        }
    };

    /// assignment probability to each layer (sum=1)
    std::vector<double> assign_probas;

    /// number of neighbors stored per layer (cumulative), should not
    /// be changed after first add
    std::vector<int> cum_nneighbor_per_level;

    /// level of each vector (base level = 1), size = ntotal
    std::vector<int> levels;

    /// offsets[i] is the offset in the neighbors array where vector i is stored
    /// size ntotal + 1
    std::vector<size_t> offsets;

    /// neighbors[offsets[i]:offsets[i+1]] is the list of neighbors of vector i
    /// for all levels. this is where all storage goes.
    std::vector<storage_idx_t> neighbors;

    /// entry point in the search structure (one of the points with maximum
    /// level
    storage_idx_t entry_point = -1;

    faiss::RandomGenerator rng;

    /// maximum level
    int max_level = -1;

    /// expansion factor at construction time
    int efConstruction = 40;

    /// expansion factor at search time
    int efSearch = 16;

    int M_ = 32;

    /// during search: do we check whether the next best distance is good
    /// enough?
    bool check_relative_distance = true;

    /// number of entry points in levels > 0.
    int upper_beam = 1;

    /// use bounded queue during exploration
    bool search_bounded_queue = true;

    // methods that initialize the tree sizes

    /// initialize the assign_probas and cum_nneighbor_per_level to
    /// have 2*M links on level 0 and M links on levels > 0
    void set_default_probas(int M, float levelMult);

    /// set nb of neighbors for this level (before adding anything)
    void set_nb_neighbors(int level_no, int n);

    // methods that access the tree sizes

    /// nb of neighbors for this level
    int nb_neighbors(int layer_no) const;

    /// cumumlative nb up to (and excluding) this level
    int cum_nb_neighbors(int layer_no) const;

    /// range of entries in the neighbors table of vertex no at layer_no
    void neighbor_range(idx_t no, int layer_no, size_t* begin, size_t* end)
            const;

    /// only mandatory parameter: nb of neighbors
    explicit Vanama(int M = 32);

    /// pick a random level for a new point
    int random_level();

    /// add n random levels to table (for debugging...)
    void fill_with_random_links(size_t n);

    void add_links_starting_from(
            DistanceComputer& ptdis,
            storage_idx_t pt_id,
            storage_idx_t nearest,
            float d_nearest,
            int level,
            omp_lock_t* locks,
            VisitedTable& vt);

    /** add point pt_id on all levels <= pt_level and build the link
     * structure for them. */
    void add_with_locks(
            DistanceComputer& ptdis,
            int pt_level,
            int pt_id,
            std::vector<omp_lock_t>& locks,
            VisitedTable& vt);

    /// search interface for 1 point, single thread
    HNSWStats search(
            DistanceComputer& qdis,
            int k,
            idx_t* I,
            float* D,
            VisitedTable& vt,
            const SearchParametersHNSW* params = nullptr) const;

    /// search only in level 0 from a given vertex
    void search_level_0(
            DistanceComputer& qdis,
            int k,
            idx_t* idxi,
            float* simi,
            idx_t nprobe,
            const storage_idx_t* nearest_i,
            const float* nearest_d,
            int search_type,
            HNSWStats& search_stats,
            VisitedTable& vt) const;

    void reset();

    void clear_neighbor_tables(int level);
    void print_neighbor_stats(int level) const;

    int prepare_level_tab(size_t n, bool preset_levels = false);

    static void shrink_neighbor_list(
            DistanceComputer& qdis,
            std::priority_queue<NodeDistFarther>& input,
            std::vector<NodeDistFarther>& output,
            int max_size);

    void permute_entries(const idx_t* map);
};



} // namespace faiss
