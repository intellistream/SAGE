//
// Created by Isshin on 2024/1/8.
//

#include <PQIndex.h>
#include <faiss/IndexFlat.h>
#include <faiss/utils/distances.h>
#include <iostream>
void CANDY::ProductQuantizer::setCentroidsFrom(Clustering cls) const {
  for (int64_t m = 0; m < M_; m++) {
    centroids_[m] = cls.getCentroids();
  }
}
void CANDY::ProductQuantizer::setCentroidsFrom(Clustering cls, int64_t m) const {
  centroids_[m] = cls.getCentroids();

}

// faiss::pq_estimators_from_tables has optimizations for cases of M values. This is the generic version
void pq_estimators_from_tables(
    const CANDY::ProductQuantizer &pq,
    int64_t nbits,
    const torch::Tensor dis_tables,
    const uint8_t *codes,
    const int64_t ncodes,
    int64_t k,
    float *heap_dis,
    int64_t *heap_ids
);

// Single-threaded version of pq-knn-search.
void pq_knn_search_with_tables_single_threaded(
    const CANDY::ProductQuantizer &pq,
    int64_t nbits,
    torch::Tensor dis_tables,
    const uint8_t *codes,
    const int64_t ncodes,
    faiss::float_maxheap_array_t *res,
    bool init_finalize_heap
);

void CANDY::ProductQuantizer::search(const torch::Tensor x,
                                     int64_t nx,
                                     const uint8_t *codes,
                                     const int64_t ncodes,
                                     faiss::float_maxheap_array_t *res,
                                     bool init_finalize_heap) {
  auto dis_tables = HUGE_VALF * torch::ones({nx, subK_, M_});
  compute_distance_tables(x, &dis_tables, nx);
  pq_knn_search_with_tables_single_threaded(*this, nbits_, dis_tables, codes, ncodes, res, init_finalize_heap);

}

void CANDY::ProductQuantizer::train(int64_t n, torch::Tensor x) {
  if (train_type_ != Train_shared) {
    torch::Tensor x_slice = torch::zeros({n, subvecDims_});

    // Process M subquantizers one by one
    for (int64_t m = 0; m < M_; m++) {
      std::cout << "m = " << m << std::endl;
      x_slice = x.slice(1, m * subvecDims_, (m + 1) * subvecDims_);

      Clustering cls(subvecDims_, subK_);
      auto index = new faiss::IndexFlatL2(subvecDims_);

      cls.train(n, x_slice, index, nullptr);
      setCentroidsFrom(cls, m);
    }
  } else {
    // Process all columns together
    Clustering cls(subvecDims_, subK_);
    auto index = new faiss::IndexFlatL2(subvecDims_);

    cls.train(n * M_, x, index, nullptr);
    setCentroidsFrom(cls);
  }
}

void compute_L2sqr(const torch::Tensor x, const torch::Tensor y);

void CANDY::ProductQuantizer::compute_code(const float *x, uint8_t *code) const {
  std::vector<float> distances(subK_);
  PQEncoder encoder(code, nbits_, 0);

  for (int64_t m = 0; m < M_; m++) {
    const float *xsub = x + m * subvecDims_;
    uint64_t idxm = 0;
    idxm = faiss::fvec_L2sqr_ny_nearest(distances.data(),
                                        xsub,
                                        centroids_.slice(0, m, m + 1).contiguous().data_ptr<float>(),
                                        subvecDims_,
                                        subK_);
    encoder.encode(idxm);
  }
}

int pq_compute_codes_block_size = 256 * 1024;
void CANDY::ProductQuantizer::compute_codes(const float *x, uint8_t *codes, int64_t n) const {
  int64_t bs = pq_compute_codes_block_size;
  if (n > bs) {
    for (int64_t head = 0; head < n; head += bs) {
      int64_t tail = head + bs < n ? head + bs : n;
      compute_codes(x + d_ * head, codes + code_size_ * head, tail - head);
    }
    return;
  }

  if (true) {
    for (int64_t i = 0; i < n; i++) {
      compute_code(x + i * d_, codes + i * code_size_);
    }
  } else {

  }

}

void CANDY::ProductQuantizer::decode(const torch::Tensor code, torch::Tensor *x) const {}

// Compute the distance between x(1*d) and y(K*d), return tensor(1*K）
void compute_L2sqr(const torch::Tensor x, const torch::Tensor y, torch::Tensor *dis_table, int64_t nx, int64_t m) {
  int64_t K = y.size(0);
  for (int64_t k = 0; k < K; k++) {
    (*dis_table).slice(0, nx, nx + 1).slice(1, k, k + 1).slice(2, m, m + 1) = (x - y[k]).pow(2).sum(0).sqrt();
  }
}

void CANDY::ProductQuantizer::compute_distance_table(const torch::Tensor x,
                                                     torch::Tensor *dis_table,
                                                     int64_t nx) const {
  /*
   * x 1*d
   * x.slice 1*subvecDims_
   * centroids_[m] subK_, subvecDim_;
   * dis_table[m] 1,subK_
   * input dis_table M*subK_
   */
  for (int64_t m = 0; m < M_; m++) {
    compute_L2sqr(x.slice(0, m * subvecDims_, (m + 1) * subvecDims_), centroids_[m], dis_table, nx, m);
  }
}

void CANDY::ProductQuantizer::compute_distance_tables(const torch::Tensor x,
                                                      torch::Tensor *dis_table,
                                                      int64_t nx) const {
  for (int64_t i = 0; i < nx; i++) {

    compute_distance_table(x[i], dis_table, i);
  }
}

void pq_estimators_from_tables(
    const CANDY::ProductQuantizer &pq,
    int64_t nbits,
    const torch::Tensor dis_tables,
    const uint8_t *codes,
    int64_t ncodes,
    int64_t k,
    float *heap_dis,
    int64_t *heap_ids
) {
  const int64_t M = pq.M_;
  const int64_t subK = pq.subK_;
  for (int64_t j = 0; j < ncodes; j++) {
    CANDY::PQDecoder decoder(codes + j * pq.code_size_, nbits);
    float dis = 0;
    // in faiss's float* version, here it acquires dis_table_page[c] then append the pointer by subK;
    // dis_table_page size : M*subK, append by subK is move to next line  within this page
    auto dis_tables_data = dis_tables.contiguous().data_ptr<float>();

    for (int64_t m = 0; m < M; m++) {
      uint64_t c = decoder.decode();
      dis += dis_tables_data[c];
      dis_tables_data += subK;
    }
    if (faiss::CMax<float, int64_t>::cmp(heap_dis[0], dis)) {
      faiss::heap_replace_top<faiss::CMax<float, int64_t>>(k, heap_dis, heap_ids, dis, j);
    }
  }
}

// Single-threaded version of pq-knn-search.
void pq_knn_search_with_tables_single_threaded(
    const CANDY::ProductQuantizer &pq,
    int64_t nbits,
    const torch::Tensor dis_tables,
    const uint8_t *codes,
    const int64_t ncodes,
    faiss::float_maxheap_array_t *res,
    bool init_finalize_heap
) {
  auto k = res->k;
  auto nx = res->nh;
  for (int64_t i = 0; i < (int64_t) nx; i++) {
    int64_t *heap_ids = res->ids + i * k;
    float *heap_dis = res->val + i * k;
    auto dis_table_page = dis_tables[i];
    if (init_finalize_heap) {
      faiss::heap_heapify<faiss::CMax<float, int64_t>>(k, heap_dis, heap_ids);
    }
    pq_estimators_from_tables(
        pq,
        nbits,
        dis_table_page,
        codes,
        ncodes,
        k,
        heap_dis,
        heap_ids
    );
    if (init_finalize_heap) {
      faiss::heap_reorder<faiss::CMax<float, int64_t>>(k, heap_dis, heap_ids);
    }
  }
}
void CANDY::PQIndex::add(int64_t nx, torch::Tensor x) {
  if (nx == 0) {
    return;
  }
  codes_.resize((npoints_ + nx) * pq_.code_size_);
  auto x_data = x.contiguous().data_ptr<float>();
  pq_.compute_codes(x_data, codes_.data() + (npoints_ * pq_.code_size_), nx);
  //copy uint8_t* codes to codes_tensor_
  torch::Tensor new_code = torch::zeros({1, pq_.code_size_});
  for (int64_t i = 0; i < nx; i++) {
    for (int64_t j = 0; j < pq_.code_size_; j++) {
      new_code.slice(1, j, j + 1) = codes_[pq_.code_size_ * (i + npoints_) + j];
    }
    INTELLI::IntelliTensorOP::appendRows(&codes_tensor_, &new_code);
  }
  npoints_ += nx;

}

void CANDY::PQIndex::train(int64_t nx, torch::Tensor x) {
  pq_.train(nx, x);
}

bool CANDY::PQIndex::setConfig(INTELLI::ConfigMapPtr cfg) {
  assert(cfg);
  int64_t d = cfg->tryI64("vecDim", 768, true);
  int64_t M = cfg->tryI64("subQuantizers", 8, true);
  int64_t nbits = cfg->tryI64("nBits", 8, true);
  vecDim_ = d;
  npoints_ = 0;
  pq_ = ProductQuantizer(d, M, nbits);
  codes_tensor_ = torch::zeros({0, pq_.code_size_});
  return true;
}
// Insert x(1*(M*subVecDims)) into storage of size npoints and update y(M_*subK_*subVecDims_);
void insert_update_centroids(const torch::Tensor *x, torch::Tensor *y, const int64_t npoints) {
  (*y) = (*y + (*x - *y) / npoints);

}

bool CANDY::PQIndex::insertTensor(torch::Tensor &t) {
  auto nx = t.size(0);
  if (!is_trained) {
    train(nx, t);
  }
  add(nx, t);

  for (int n = 0; n < nx; n++) {
    for (int64_t m = 0; m < pq_.M_; m++) {
      auto t_slice = t.slice(0, n, n + 1).slice(1, m * (pq_.subvecDims_), (m + 1) * (pq_.subvecDims_));
      auto centroids_slice = pq_.centroids_.slice(0, m, m + 1);
      if (frozenLevel) {
        insert_update_centroids(&t_slice, &centroids_slice, npoints_);
      }

      pq_.centroids_.slice(0, m, m + 1) = centroids_slice;

    }
  }

  return true;
}

//Delete x from storage of size npoints and update y
void delete_update_centroids(const torch::Tensor *x, torch::Tensor *y, const int64_t npoints) {
  (*y) = (*y - (*x - *y) / npoints);

}
bool CANDY::PQIndex::deleteTensor(torch::Tensor &t, int64_t k) {
  auto nx = t.size(0);
  if (frozenLevel) {
    delete_update_centroids(&t, &(pq_.centroids_), npoints_);
  }
  npoints_ -= nx;

  return false;
}
void CANDY::PQIndex::reset() {
  npoints_ = 0;
  pq_ = ProductQuantizer(pq_.d_, pq_.M_, pq_.nbits_);
}

std::vector<faiss::idx_t> CANDY::PQIndex::searchIndex(torch::Tensor q, int64_t k) {
  return std::vector<faiss::idx_t>(0);
}

std::vector<torch::Tensor> CANDY::PQIndex::getTensorByIndex(std::vector<faiss::idx_t> &idx, int64_t k) {
  return std::vector<torch::Tensor>(0);
}

torch::Tensor CANDY::PQIndex::rawData() {
  return codes_tensor_;
}
bool CANDY::PQIndex::reviseTensor(torch::Tensor &t, torch::Tensor &w) {
  return false;
}
bool CANDY::PQIndex::loadInitialTensor(torch::Tensor &t) {
  train((int64_t) t.size(0), t);
  add((int64_t) t.size(0), t);
  return true;
}
bool CANDY::PQIndex::setFrozenLevel(int64_t frozenLv) {
  frozenLevel = frozenLv;
  return true;
}
std::vector<torch::Tensor> CANDY::PQIndex::searchTensor(torch::Tensor &q, int64_t k) {
  int64_t querySize = q.size(0);
  assert(querySize > 0);
  std::vector<torch::Tensor> results(querySize);
  std::vector<torch::Tensor> result_codes(querySize);
  std::vector<float> res_distances(k * querySize);
  std::vector<faiss::idx_t> res_labels(k * querySize);
  faiss::float_maxheap_array_t
      res = {static_cast<size_t>(querySize), static_cast<size_t>(k), res_labels.data(), res_distances.data()};
  pq_.search(q, querySize, codes_.data(), npoints_, &res, true);
  for (int64_t i = 0; i < querySize; i++) {
    results[i] = torch::zeros({k, vecDim_});
    result_codes[i] = torch::zeros({k, pq_.code_size_});
    for (int64_t j = 0; j < k; j++) {
      int64_t tempIdx = res_labels[i * k + j];

      if (tempIdx >= 0) {
        // verbose, just to check codes
        for (int64_t code_step = 0; code_step < pq_.code_size_; code_step++) {
          result_codes[i][j][code_step] = codes_[tempIdx * pq_.code_size_ + code_step];
        }
        // decode codes_[tempIdx] to centroids idx
        CANDY::PQDecoder decoder(codes_.data() + pq_.code_size_ * tempIdx, pq_.nbits_);
        for (int64_t m = 0; m < pq_.M_; m++) {
          uint64_t c = decoder.decode();
          // assign centroids[m][c] to results[i] per subquantizer
          results[i].slice(0, j, j + 1).slice(1, m * pq_.subvecDims_, (m + 1) * pq_.subvecDims_) =
              pq_.centroids_[m].slice(0, c, c + 1);
        }
      }
    }

  }

  return results;

}
