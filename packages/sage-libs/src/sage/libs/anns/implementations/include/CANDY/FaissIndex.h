/*! \file FaissIndex.h*/
//
// Created by Isshin on 2024/1/30.
//

#ifndef CANDY_FAISSINDEX_H
#define CANDY_FAISSINDEX_H
#include <CANDY/AbstractIndex.h>
#include <faiss/Index.h>
#include <faiss/IndexIVFPQ.h>

namespace CANDY {

/**
 * @ingroup  CANDY_lib_bottom The main body and interfaces of library function
 * @{
 */
/**
 * @class FaissIndex CANDY/FaissIndex.h
 * @brief The class of converting faiss index api into rania index style
 * @note currently single thread
 * @todo more explanation on IVFPQ, NNDecent, LSH, NSG
 * @note config parameters
 * - vecDim, the dimension of vectors, default 768, I64
 * - faissIndexTag, the internal tag of loading faiss index approaches,String can be either one of the following
    * - flat (default), using faiss::IndexFlat
    * - HNSW, using faiss::IndexHNSWFlat, additional config as follows
        * - maxConnection, I64, default 32, the max number of neighbor connections in hnsw
    * - PQ, using faiss::IndexPQ, additional config as follows
        * - encodeLen, the encoding length in bytes, I64, default 1
        * - encodeLenBits, the encoding length in bits, I64, default encodeLen*8 (will overwrite encodeLen if manually set)
        * - subQuantizers, the number of subquantizers used, I64, default 8
    * - IVFPQ, using faiss::IndexIVFPQ, additional config as follows
        * - encodeLen, the encoding length in bytes, I64, default 1
        * - encodeLenBits, the encoding length in bits, I64, default encodeLen*8 (will overwrite encodeLen if manually set)
        * - subQuantizers, the number of subquantizers used, I64, default 8
        * - lists, the number of lists used, I64, default 1000
    * - LSH, using faiss::IndexLSH, additional config as follows
        * - encodeLen, the encoding length in bytes, I64, default 1
        * - encodeLenBits, the encoding length in bits, I64, default encodeLen*8 (will overwrite encodeLen if manually set)
    * - NNDescent, using faiss::IndexNNDescentFlat, still some missing functions like @ref insertTensor
    * - NSG, using faiss::IndexNSGFlat, still some missing functions like @ref insertTensor
 */
class FaissIndex : public AbstractIndex {
 protected:
  typedef std::string index_type_t;
  typedef std::string metric_type_t;
  bool isFaissTrained = false;
  faiss::Index *index = nullptr;
  index_type_t index_type;
  metric_type_t metricType;
  int64_t vecDim;
  torch::Tensor dbTensor;
  int64_t lastNNZ;
  int64_t expandStep;
 public:

  FaissIndex() = default;

  /**
   * @brief set the index-specific config related to one index
   * @param cfg the config of this class
   * @return bool whether the configuration is successful
   */
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);
  /**
  * @brief load the initial tensors of a data base, use this BEFORE @ref insertTensor
  * @note This is majorly an offline function, and may be different from @ref insertTensor for some indexes
  * @param t the tensor, some index need to be single row
  * @return bool whether the loading is successful
  */
  virtual bool loadInitialTensor(torch::Tensor &t);
  /**
   * @brief insert a tensor
   * @param t the tensor, accept multiple rows
   * @return bool whether the insertion is successful
   */
  virtual bool insertTensor(torch::Tensor &t);
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
     * @brief search the k-NN of a query tensor, return their index
     * @param t the tensor, allow multiple rows
     * @param k the returned neighbors
     * @return std::vector<faiss::idx_t> the index, follow faiss's order
     */
    virtual std::vector<faiss::idx_t> searchIndexParam(torch::Tensor q, int64_t k, int64_t param);
};

/**
 * @ingroup  CANDY_lib_bottom
 * @typedef FaissIndexPtr
 * @brief The class to describe a shared pointer to @ref  FaissIndexPtr

 */
typedef std::shared_ptr<class CANDY::FaissIndex> FaissIndexPtr;
/**
 * @ingroup  CANDY_lib_bottom
 * @def newFaissIndex
 * @brief (Macro) To creat a new @ref  FaissIndex shared pointer.
 */
#define newFaissIndex std::make_shared<CANDY::FaissIndex>
}
/**
 * @}
 */
#endif //CANDY_FAISSINDEX_H
