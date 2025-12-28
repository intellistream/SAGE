//
// Created by Isshin on 2024/1/8.
//

#ifndef CANDY_PQINDEX_H
#define CANDY_PQINDEX_H
#include <CANDY/PQIndex/Clustering.h>
#include <faiss/Index.h>
#include <Utils/IntelliTensorOP.hpp>
#include <Utils/ConfigMap.hpp>
#include <CANDY/AbstractIndex.h>
#include <faiss/utils/Heap.h>

namespace CANDY {

/**
 * @class ProductQuantizer CANDY/PQIndex.h
 * @brief class for basic product quantization operations on input of tensors
 */
class ProductQuantizer {
 public:
  /// total dim;
  int64_t d_;
  /// number of subquantizers
  int64_t M_;
  /// number of bits per quantization index
  int64_t nbits_;

  /// dimensionality of each subvector
  int64_t subvecDims_;
  /// number of centroids of each subquantizer
  int64_t subK_;

  int64_t code_size_;

  enum train_type_t {
    Train_default,
    Train_shared
  };

  train_type_t train_type_ = Train_default;

  faiss::Index *assign_index_;

  /// (M, subK_, subvecDims_)
  torch::Tensor centroids_;
  /**
   * @brief Set centroids from trained clustering
   * @param cls Clustering
   */
  void setCentroidsFrom(Clustering cls) const;
  /**
   * @brief Set centroids[M] for the Mth subquantizer from trained clustering
   * @param cls Clustering
   * @param M subquantizer identifier
   */
  void setCentroidsFrom(Clustering cls, int64_t M) const;
  /**
   * train PQ with given tensor
   * @param n number of inputs
   * @param t input vectors as tensor
   */
  void train(int64_t n, torch::Tensor t);
  /**
   * @brief
   * @param x vectors to be searched
   * @param nx number of input vectors
   * @param codes codes to be consulted during search
   * @param ncodes number of codes
   * @param res result heap
   * @param init_finalize_heap whether at the end of searching each vector to reorder the heap
   */
  void search(const torch::Tensor x,
              int64_t nx,
              const uint8_t *codes,
              const int64_t ncodes,
              faiss::float_maxheap_array_t *res,
              bool init_finalize_heap);
  /**
   * @brief add vectors to current PQ Index, which would append codes and drift the centroids according to input
   * @param nx number of input vectors
   * @param x input vectors to be added
   */
  void add(int64_t nx, const torch::Tensor x);
  /**
   * @brief compute a single vector to codes
   * @param x vectors to be encoded
   * @param codes destination codes
   */
  void compute_code(const float *x, uint8_t *code) const;
  /**
   * @brief compute vectors to codes
   * @param x input vectors
   * @param codes store computation results from x, pointer target is a torch::Tensor size of (nx, code_size_);
   * @param nx number of input vectors
   * @param start pointers denoting where it starts
   */
  void compute_codes(const float *x, uint8_t *codes, int64_t n) const;
  /**
   * @brief decode from codes
   * @param code codes to be decoded
   * @param x destination vectors
   */
  void decode(const torch::Tensor code, torch::Tensor *x) const;

  /**
   * @brief Compute the distance between single x vector and M*subK centroids
   * @param x
   * @param dis_table
   * @return distance table tensor size of M*subK
   */
  void compute_distance_table(const torch::Tensor x, torch::Tensor *dis_table, int64_t nx) const;
  /**
   * @brief Compute the distance between nx vectors and M*subK centroids
   * @param x tensor of nx * d
   * @param dis_table output table sizeof nx*M*subK
   * @param nx number of vectors
   */
  void compute_distance_tables(const torch::Tensor x, torch::Tensor *dis_table, int64_t nx) const;

  ProductQuantizer() = default;
  ProductQuantizer(int64_t d, int64_t M, int64_t nbits) {
    d_ = d;
    M_ = M;
    nbits_ = nbits;
    subvecDims_ = d / M;
    code_size_ = (nbits * M + 7) / 8;
    subK_ = 1 << nbits;
    centroids_ = torch::zeros({M, subK_, subvecDims_});
  };
};

/**
 * @class PQEncoder CANDY/PQIndex.h
 * @brief class for encoding input vectors to codes, standing for approximated assignment of centroids
 */
class PQEncoder {
 public:
  uint8_t *code_;
  /// number of bits per subquantizer index
  int64_t nbits_;
  uint8_t offset_;
  uint8_t reg_;

  inline PQEncoder(uint8_t *code, int64_t nbits, uint8_t offset)
      : code_(code), nbits_(nbits), offset_(offset), reg_(0) {
    assert(nbits <= 64);
    if (offset_ > 0) {
      reg_ = (*code_ & ((1 << offset_) - 1));
    }
  };
  /**
   * @brief encode assignment x to code
   * @param x centroids assignment of a vector for its part of sub-vector
   */
  inline void encode(uint64_t x) {
    reg_ = reg_ | (uint8_t) (x << offset_);
    x = x >> (8 - offset_);
    if (offset_ + nbits_ >= 8) {
      *code_++ = reg_;

      for (int i = 0; i < (nbits_ - (8 - offset_)) / 8; i++) {
        *code_++ = (uint8_t) x;
        x = x >> 8;
      }

      offset_ += nbits_;
      offset_ &= 7;
      reg_ = (uint8_t) x;
    } else {
      offset_ += nbits_;
    }

  }

  inline ~PQEncoder() {
    if (offset_ > 0) {
      *code_ = reg_;
    }
  };

};

/**
 * @class PQDecoder CANDY/PQIndex.h
 * @brief class for decoding from codes, approximated assignment of centroids, to centroids indices
 */
class PQDecoder {
 public:
  const uint8_t *code_;
  uint8_t offset_;
  const int64_t nbits_;
  const uint64_t mask_;
  uint8_t reg_;
  inline PQDecoder(const uint8_t *code, int64_t nbits)
      : code_(code), offset_(0), nbits_(nbits), mask_((1ull << nbits) - 1), reg_(0) {
    assert(nbits <= 64);
  };
  /**
   * @brief decode from codes to the actual index of a centroid in sub-vector
   * @return the centroid assignment
   */
  inline uint64_t decode() {
    if (offset_ == 0) {
      reg_ = *code_;
    }
    uint64_t c = (reg_ >> offset_);

    if (offset_ + nbits_ >= 8) {
      uint64_t e = 8 - offset_;
      ++code_;
      for (int i = 0; i < (nbits_ - (8 - offset_)) / 8; ++i) {
        c = c | ((uint64_t) (*code_++) << e);
        e += 8;
      }

      offset_ += nbits_;
      offset_ = offset_ & 7;
      if (offset_ > 0) {
        reg_ = *code_;
        c = c | ((uint64_t) reg_ << e);
      }
    } else {
      offset_ += nbits_;
    }
    return c & mask_;
  };
};

/**
 * @class PQIndex CANDY/PQIndex.h
 * @ingroup  CANDY_lib_bottom
 * @brief class for indexing vectors using product quantizations, this is a raw implementation without hierachical
 * @todo delete and revise a tensor may not be feasible for PQIndex
 *  - @ref deleteTensor
 *  - @ref reviseTensor
 * @todo encode and decode may be verbose for both code tensor and code pointers
 *  - @ref searchTensor
 *  - @ref insertTensor
 * @note config parameters
 * - vecDim, the dimension of vectors, default 768, I64
 * - subQuantizers, the number of sub quantizers, default 8, I64
 * - nBits, the number of bits in each sub quantizer, default 8, I64

 */
class PQIndex : public AbstractIndex {
 protected:
  ProductQuantizer pq_;
  /// encoded dataset npoints_ * pq_.code_size_
  std::vector<uint8_t> codes_;
  torch::Tensor codes_tensor_;
  int64_t npoints_ = 0;
  int64_t vecDim_ = 0;
  bool is_trained = false;
  int64_t frozenLevel = 0;
  /**
   * @brief add a batch of vectors into PQIndex which would serve as the base to modify
   * @param nx number of input x vectors
   * @param x input vectors as tensors
   */
  void add(int64_t nx, torch::Tensor x);

  /**
   * @brief train the PQIndex upon input vectors. Should be called after add()
   * @param nx number of input x vectors
   * @param x input vectors as tensors
   */
  void train(int64_t nx, torch::Tensor x);
 public:
  PQIndex() {}
  ~PQIndex() {

  }

  /**
    * @brief reset this index to inited status
    */
  virtual void reset();
  /**
   * @brief set the index-specific config related to one index
   * @param cfg the config of this class
   * @return bool whether the configuration is successful
   */
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);

  /**
   * @brief insert a tensor. In PQIndex setting it requires to re-train on new data
   * @param t the tensor, accept multiple rows
   * @return bool whether the insertion is successful
   */
  virtual bool insertTensor(torch::Tensor &t);
  /**
  * @brief load the initial tensors of a data base, use this BEFORE @ref insertTensor
  * @note This is majorly an offline function, and is different from @ref insertTensor for this one:
  * - Will firstly try to build clusters from scratch using t
  * @param t the tensor, some index need to be single row
  * @return bool whether the loading is successful
  */
  virtual bool loadInitialTensor(torch::Tensor &t);
  /**
   * @brief delete a tensor. In PQIndex setting it requires to re-train on new data
   * @param t the tensor, recommend single row
   * @param k the number of nearest neighbors
   * @return bool whether the deleting is successful
   */
  virtual bool deleteTensor(torch::Tensor &t, int64_t k = 1);

  /**
   * @brief revise a tensor. In PQIndex setting it requires to re-train on new data
   * @param t the tensor to be revised, recommend single row
   * @param w the revised value
   * @return bool whether the revising is successful
   */
  virtual bool reviseTensor(torch::Tensor &t, torch::Tensor &w);
  /**
   * @brief search the k-NN of a query tensor, return their index
   * @param t the tensor, allow multiple rows
   * @param k the returned neighbors
   * @return std::vector<faiss::idx_t> the index, follow faiss's order
   */
  virtual std::vector<faiss::idx_t> searchIndex(torch::Tensor q, int64_t k);
  /**
   * @brief search the k-NN of a query tensor, return the result tensors
   * @param t the tensor, allow multiple rows
   * @param k the returned neighbors
   * @return std::vector<torch::Tensor> the result tensor for each row of query
   */
  virtual std::vector<torch::Tensor> searchTensor(torch::Tensor &q, int64_t k);
  /**
   * @brief return a vector of tensors according to some index
   * @param idx the index, follow faiss's style, allow the KNN index of multiple queries
   * @param k the returned neighbors, i.e., will be the number of rows of each returned tensor
   * @return a vector of tensors, each tensor represent KNN results of one query in idx
   */
  virtual std::vector<torch::Tensor> getTensorByIndex(std::vector<faiss::idx_t> &idx, int64_t k);
  /**
   * @brief return the rawData of tensor
   * @return The raw data stored in tensor
   */
  virtual torch::Tensor rawData();
  /**
  * @brief set the frozen level of online updating internal state
  * @param frozenLv the level of frozen, 0 means freeze any online update in internal state
  * @note the frozen levels
  * - 0 frozen everything
  * - >=1 frozen nothing
  * @return whether the setting is successful
  */
  virtual bool setFrozenLevel(int64_t frozenLv);
};

/**
 * @ingroup  CANDY_lib_bottom
 * @typedef PQIndexPtr
 * @brief The class to describe a shared pointer to @ref  PQIndex

 */
typedef std::shared_ptr<class CANDY::PQIndex> PQIndexPtr;
/**
 * @ingroup  CANDY_lib_bottom
 * @def newPQIndex
 * @brief (Macro) To creat a new @ref  PQIndex shared pointer.
 */
#define newPQIndex std::make_shared<CANDY::PQIndex>
}
#endif //CANDY_PQINDEX_H
