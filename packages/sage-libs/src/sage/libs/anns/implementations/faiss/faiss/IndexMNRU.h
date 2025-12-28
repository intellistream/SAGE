//
// Created by rubato on 19/9/24.
//

#pragma once

#include<vector>
#include<faiss/IndexFlat.h>
#include <faiss/IndexPQ.h>
#include <faiss/IndexScalarQuantizer.h>
#include<faiss/impl/HNSW.h>
#include<faiss/utils/utils.h>


namespace faiss{

    struct IndexMNRU;


    struct IndexMNRU: Index{
        typedef HNSW::storage_idx_t storage_idx_t;

        HNSW main_index;
        HNSW backup_index;
        bool own_fields = false;
        Index* storage=nullptr;
        int64_t backup_tau = 10000;


        explicit IndexMNRU(int d = 0, int M = 32, MetricType metric = METRIC_L2);
        explicit IndexMNRU(Index* storage, int M = 32);

        ~IndexMNRU() override;

        void add(idx_t n, const float* x) override;

        /// Trains the storage if needed
        void train(idx_t n, const float* x) override;

        /// entry point for search
        void search(
                idx_t n,
                const float* x,
                idx_t k,
                float* distances,
                idx_t* labels,
                const SearchParameters* params = nullptr) const override;

        void reconstruct(idx_t key, float* recons) const override;

        void reset() override;


    };

    struct IndexMNRUFlat : IndexMNRU{
        IndexMNRUFlat();
        IndexMNRUFlat(int d, int M, MetricType metric = METRIC_L2);
    };
}
