//
// Created by rubato on 19/9/24.
//

#include<faiss/IndexMNRU.h>
#include <omp.h>
#include <cassert>
#include <cinttypes>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include <queue>
#include <unordered_set>

#include <sys/stat.h>
#include <sys/types.h>
#include <cstdint>

#include <faiss/Index2Layer.h>
#include <faiss/IndexFlat.h>
#include <faiss/IndexIVFPQ.h>
#include <faiss/impl/AuxIndexStructures.h>
#include <faiss/impl/FaissAssert.h>
#include <faiss/utils/Heap.h>
#include <faiss/utils/distances.h>
#include <faiss/utils/random.h>
#include <faiss/utils/sorting.h>


extern "C"{
int sgemm_(
        const char* transa,
        const char* transb,
        FINTEGER* m,
        FINTEGER* n,
        FINTEGER* k,
        const float* alpha,
        const float* a,
        FINTEGER* lda,
        const float* b,
        FINTEGER* ldb,
        float* beta,
        float* c,
        FINTEGER* ldc);
}
namespace faiss{
    using MinimaxHeap = HNSW::MinimaxHeap;
    using storage_idx_t = HNSW::storage_idx_t;
    using NodeDistFarther = HNSW::NodeDistFarther;

    HNSWStats mnru_stats;


    namespace {

/* Wrap the distance computer into one that negates the
   distances. This makes supporting INNER_PRODUCE search easier */

        struct NegativeDistanceComputer : DistanceComputer {
            /// owned by this
            DistanceComputer* basedis;

            explicit NegativeDistanceComputer(DistanceComputer* basedis)
                    : basedis(basedis) {}

            void set_query(const float* x) override {
                basedis->set_query(x);
            }

            /// compute distance of vector i to current query
            float operator()(idx_t i) override {
                return -(*basedis)(i);
            }

            void distances_batch_4(
                    const idx_t idx0,
                    const idx_t idx1,
                    const idx_t idx2,
                    const idx_t idx3,
                    float& dis0,
                    float& dis1,
                    float& dis2,
                    float& dis3) override {
                basedis->distances_batch_4(
                        idx0, idx1, idx2, idx3, dis0, dis1, dis2, dis3);
                dis0 = -dis0;
                dis1 = -dis1;
                dis2 = -dis2;
                dis3 = -dis3;
            }

            /// compute distance between two stored vectors
            float symmetric_dis(idx_t i, idx_t j) override {
                return -basedis->symmetric_dis(i, j);
            }

            virtual ~NegativeDistanceComputer() {
                delete basedis;
            }
        };

        DistanceComputer* storage_distance_computer(const Index* storage) {
            if (is_similarity_metric(storage->metric_type)) {
                return new NegativeDistanceComputer(storage->get_distance_computer());
            } else {
                return storage->get_distance_computer();
            }
        }

        void hnsw_add_vertices(
                IndexMNRU& index_hnsw,
                size_t n0,
                size_t n,
                const float* x,
                bool verbose,
                bool preset_levels = false) {
            size_t d = index_hnsw.d;
            HNSW& hnsw = index_hnsw.main_index;
            size_t ntotal = n0 + n;
            double t0 = getmillisecs();
            if (verbose) {
                printf("hnsw_add_vertices: adding %zd elements on top of %zd "
                       "(preset_levels=%d)\n",
                       n,
                       n0,
                       int(preset_levels));
            }

            if (n == 0) {
                return;
            }

            int max_level = hnsw.prepare_level_tab(n, preset_levels);

            if (verbose) {
                printf("  max_level = %d\n", max_level);
            }

            std::vector<omp_lock_t> locks(ntotal);
            for (int i = 0; i < ntotal; i++)
                omp_init_lock(&locks[i]);

            // add vectors from highest to lowest level
            std::vector<int> hist;
            std::vector<int> order(n);

            { // make buckets with vectors of the same level

                // build histogram
                for (int i = 0; i < n; i++) {
                    storage_idx_t pt_id = i + n0;
                    int pt_level = hnsw.levels[pt_id] - 1;
                    while (pt_level >= hist.size())
                        hist.push_back(0);
                    hist[pt_level]++;
                }

                // accumulate
                std::vector<int> offsets(hist.size() + 1, 0);
                for (int i = 0; i < hist.size() - 1; i++) {
                    offsets[i + 1] = offsets[i] + hist[i];
                }

                // bucket sort
                for (int i = 0; i < n; i++) {
                    storage_idx_t pt_id = i + n0;
                    int pt_level = hnsw.levels[pt_id] - 1;
                    order[offsets[pt_level]++] = pt_id;
                }
            }

            idx_t check_period = InterruptCallback::get_period_hint(
                    max_level * index_hnsw.d * hnsw.efConstruction);

            { // perform add
                RandomGenerator rng2(789);

                int i1 = n;

                for (int pt_level = hist.size() - 1; pt_level >= 0; pt_level--) {
                    int i0 = i1 - hist[pt_level];

                    if (verbose) {
                        printf("Adding %d elements at level %d\n", i1 - i0, pt_level);
                    }

                    // random permutation to get rid of dataset order bias
                    for (int j = i0; j < i1; j++)
                        std::swap(order[j], order[j + rng2.rand_int(i1 - j)]);

                    bool interrupt = false;

//#pragma omp parallel if (i1 > i0 + 100)
                    {
                        VisitedTable vt(ntotal);

                        std::unique_ptr<DistanceComputer> dis(
                                storage_distance_computer(index_hnsw.storage));
                        int prev_display =
                                verbose && omp_get_thread_num() == 0 ? 0 : -1;
                        size_t counter = 0;

                        // here we should do schedule(dynamic) but this segfaults for
                        // some versions of LLVM. The performance impact should not be
                        // too large when (i1 - i0) / num_threads >> 1
//#pragma omp for schedule(static)
                        for (int i = i0; i < i1; i++) {
                            storage_idx_t pt_id = order[i];
                            dis->set_query(x + (pt_id - n0) * d);

                            // cannot break
                            if (interrupt) {
                                continue;
                            }

                            hnsw.add_with_locks(*dis, pt_level, pt_id, locks, vt);

                            if (prev_display >= 0 && i - i0 > prev_display + 10000) {
                                prev_display = i - i0;
                                printf("  %d / %d\r", i - i0, i1 - i0);
                                fflush(stdout);
                            }
                            if (counter % check_period == 0) {
                                if (InterruptCallback::is_interrupted()) {
                                    interrupt = true;
                                }
                            }
                            counter++;
                        }
                    }
                    if (interrupt) {
                        FAISS_THROW_MSG("computation interrupted");
                    }
                    i1 = i0;
                }
                FAISS_ASSERT(i1 == 0);
            }
            if (verbose) {
                printf("Done in %.3f ms\n", getmillisecs() - t0);
            }

            for (int i = 0; i < ntotal; i++) {
                omp_destroy_lock(&locks[i]);
            }
        }

        void backup_add_vertices(
                IndexMNRU& index_hnsw,
                size_t n0,//always be ZERO!
                size_t n,
                const float* x,
                bool verbose,
                bool preset_levels = false) {
            size_t d = index_hnsw.d;
            HNSW& hnsw = index_hnsw.backup_index;
            n0 = 0;
            hnsw.reset();
            size_t ntotal = n0 + n;
            double t0 = getmillisecs();
            if (verbose) {
                printf("hnsw_add_vertices: adding %zd elements on top of %zd "
                       "(preset_levels=%d)\n",
                       n,
                       n0,
                       int(preset_levels));
            }

            if (n == 0) {
                return;
            }

            int max_level = hnsw.prepare_level_tab(n, preset_levels);

            if (verbose) {
                printf("  max_level = %d\n", max_level);
            }

            std::vector<omp_lock_t> locks(ntotal);
            for (int i = 0; i < ntotal; i++)
                omp_init_lock(&locks[i]);

            // add vectors from highest to lowest level
            std::vector<int> hist;
            std::vector<int> order(n);

            { // make buckets with vectors of the same level

                // build histogram
                for (int i = 0; i < n; i++) {
                    storage_idx_t pt_id = i + n0;
                    int pt_level = hnsw.levels[pt_id] - 1;
                    while (pt_level >= hist.size())
                        hist.push_back(0);
                    hist[pt_level]++;
                }

                // accumulate
                std::vector<int> offsets(hist.size() + 1, 0);
                for (int i = 0; i < hist.size() - 1; i++) {
                    offsets[i + 1] = offsets[i] + hist[i];
                }

                // bucket sort
                for (int i = 0; i < n; i++) {
                    storage_idx_t pt_id = i + n0;
                    int pt_level = hnsw.levels[pt_id] - 1;
                    order[offsets[pt_level]++] = pt_id;
                }
            }

            idx_t check_period = InterruptCallback::get_period_hint(
                    max_level * index_hnsw.d * hnsw.efConstruction);

            { // perform add
                RandomGenerator rng2(789);

                int i1 = n;

                for (int pt_level = hist.size() - 1; pt_level >= 0; pt_level--) {
                    int i0 = i1 - hist[pt_level];

                    if (verbose) {
                        printf("Adding %d elements at level %d\n", i1 - i0, pt_level);
                    }

                    // random permutation to get rid of dataset order bias
                    for (int j = i0; j < i1; j++)
                        std::swap(order[j], order[j + rng2.rand_int(i1 - j)]);

                    bool interrupt = false;

//#pragma omp parallel if (i1 > i0 + 100)
                    {
                        VisitedTable vt(ntotal);

                        std::unique_ptr<DistanceComputer> dis(
                                storage_distance_computer(index_hnsw.storage));
                        int prev_display =
                                verbose && omp_get_thread_num() == 0 ? 0 : -1;
                        size_t counter = 0;

                        // here we should do schedule(dynamic) but this segfaults for
                        // some versions of LLVM. The performance impact should not be
                        // too large when (i1 - i0) / num_threads >> 1
//#pragma omp for schedule(static)
                        for (int i = i0; i < i1; i++) {
                            storage_idx_t pt_id = order[i];
                            dis->set_query(x + (pt_id - n0) * d);

                            // cannot break
                            if (interrupt) {
                                continue;
                            }

                            hnsw.add_with_locks(*dis, pt_level, pt_id, locks, vt);

                            if (prev_display >= 0 && i - i0 > prev_display + 10000) {
                                prev_display = i - i0;
                                printf("  %d / %d\r", i - i0, i1 - i0);
                                fflush(stdout);
                            }
                            if (counter % check_period == 0) {
                                if (InterruptCallback::is_interrupted()) {
                                    interrupt = true;
                                }
                            }
                            counter++;
                        }
                    }
                    if (interrupt) {
                        FAISS_THROW_MSG("computation interrupted");
                    }
                    i1 = i0;
                }
                FAISS_ASSERT(i1 == 0);
            }
            if (verbose) {
                printf("Done in %.3f ms\n", getmillisecs() - t0);
            }

            for (int i = 0; i < ntotal; i++) {
                omp_destroy_lock(&locks[i]);
            }
        }

    } // namespace


    IndexMNRU::IndexMNRU(int d, int M, faiss::MetricType metric) :Index(d,metric){}
    IndexMNRU::IndexMNRU(faiss::Index *storage, int M) :Index(storage->d, storage->metric_type), main_index(M),
                                                        backup_index(M), storage(storage){}
    IndexMNRU::~IndexMNRU(){
        if(own_fields){
            delete storage;
        }
    }


    void IndexMNRU::search(
            idx_t n,
            const float* x,
            idx_t k,
            float* distances,
            idx_t* labels,
            const SearchParameters* params_in) const {
        FAISS_THROW_IF_NOT(k > 0);
        FAISS_THROW_IF_NOT_MSG(
                storage,
                "Please use IndexMNRUFlat (or variants) instead of IndexMNRU directly");
        const SearchParametersHNSW* params = nullptr;

        int efSearch = main_index.efSearch;
        if (params_in) {
            params = dynamic_cast<const SearchParametersHNSW*>(params_in);
            FAISS_THROW_IF_NOT_MSG(params, "params type invalid");
            efSearch = params->efSearch;
        }
        size_t n1 = 0, n2 = 0, n3 = 0, ndis = 0, nreorder = 0;

        idx_t check_period =
                InterruptCallback::get_period_hint(main_index.max_level * d * efSearch);

        for (idx_t i0 = 0; i0 < n; i0 += check_period) {
            idx_t i1 = std::min(i0 + check_period, n);

//#pragma omp parallel
            {
                VisitedTable vt(ntotal);

                std::unique_ptr<DistanceComputer> dis(
                        storage_distance_computer(storage));

//#pragma omp for reduction(+ : n1, n2, n3, ndis, nreorder) schedule(guided)
                for (idx_t i = i0; i < i1; i++) {
                    idx_t* idxi = labels + i * k;
                    float* simi = distances + i * k;
                    dis->set_query(x + i * d);

                    std::vector<idx_t> backup_results(k);
                    std::vector<float> backup_distances(k);

                    maxheap_heapify(k, simi, idxi);

                    maxheap_heapify(k, backup_distances.data(), backup_results.data());

                    // dual index search
                    HNSWStats stats = main_index.search(*dis, k, idxi, simi, vt, params);
                    backup_index.search(*dis, k, backup_results.data(), backup_distances.data(), vt, params);
                    // merge results
                    for(size_t i=0; i<backup_distances.size();i++){
                        float dis = backup_distances[i];
                        auto idx = backup_results[i];
                        if(dis<simi[0]) {
                            faiss::maxheap_replace_top(k, simi, idxi, dis, idx);
                        }
                    }


                    n1 += stats.n1;
                    n2 += stats.n2;
                    n3 += stats.n3;
                    ndis += stats.ndis;
                    nreorder += stats.nreorder;
                    maxheap_reorder(k, simi, idxi);

                }
            }
            InterruptCallback::check();
        }

        if (is_similarity_metric(metric_type)) {
            // we need to revert the negated distances
            for (size_t i = 0; i < k * n; i++) {
                distances[i] = -distances[i];
            }
        }

        mnru_stats.combine({n1, n2, n3, ndis, nreorder});
    }

    void IndexMNRU::train(idx_t n, const float* x) {
        FAISS_THROW_IF_NOT_MSG(
                storage,
                "Please use IndexMNRUFlat (or variants) instead of IndexMNRU directly");
        // hnsw structure does not require training
        storage->train(n, x);
        is_trained = true;
    }

    void IndexMNRU::add(idx_t n, const float* x) {
        FAISS_THROW_IF_NOT_MSG(
                storage,
                "Please use IndexMNRUFlat (or variants) instead of IndexMNRU directly");
        FAISS_THROW_IF_NOT(is_trained);
        int n0 = ntotal;
        printf("adding %ld vectors\n", n);
        storage->add(n, x);
        ntotal = storage->ntotal;


        hnsw_add_vertices(*this, n0, n, x, verbose, main_index.levels.size() == ntotal);
        printf("adding %ld vectors finishes\n", n);

        if(/*ntotal%backup_tau==0||*/true){
            // perform backup index update
            backup_index.reset();
            float* entry_vector = new float[d];
            reconstruct(main_index.entry_point, entry_vector);

            std::vector<float> distances(ntotal);
            std::vector<idx_t> labels(ntotal);
            VisitedTable vt(ntotal);
            std::unique_ptr<DistanceComputer> dis(
                    storage_distance_computer(storage));
            dis->set_query(entry_vector);
            main_index.search_bounded_queue=false;
            main_index.search(*dis, ntotal, labels.data(), distances.data(),vt);
            main_index.search_bounded_queue=true;
            std::vector<bool> present(ntotal);
            for(size_t i=0; i<ntotal; i++){
                auto idx = labels[i];
//                if(present[idx]==true){
//                    printf("overlapping for %ld!\n", idx);
//                }
                present[idx]=true;
            }
            std::vector<idx_t> unreachables;
            for(size_t i=0; i<ntotal; i++){
                if(!present[i]){
                    unreachables.push_back(i);
                }
            }
            delete[] entry_vector;
            printf("Found %ld unreachable vectors!\n", unreachables.size());
            std::vector<float> unreachable_vectors(d*unreachables.size());
            for(size_t i=0; i<unreachables.size(); i++){
                auto idx = unreachables[i];
                reconstruct(idx, unreachable_vectors.data()+d*i);
            }

            backup_add_vertices(*this, 0, unreachables.size(), unreachable_vectors.data(),verbose, backup_index.levels.size() == ntotal);
        }
    }

    void IndexMNRU::reset() {
        main_index.reset();
        backup_index.reset();
        storage->reset();
        ntotal = 0;
    }

    void IndexMNRU::reconstruct(idx_t key, float* recons) const {
        storage->reconstruct(key, recons);
    }

    IndexMNRUFlat::IndexMNRUFlat() {
        is_trained = true;
    }

    IndexMNRUFlat::IndexMNRUFlat(int d, int M, MetricType metric)
            : IndexMNRU(
            (metric == METRIC_L2) ? new IndexFlatL2(d)
                                  : new IndexFlat(d, metric),
            M) {
        own_fields = true;
        is_trained = true;
    }
}
