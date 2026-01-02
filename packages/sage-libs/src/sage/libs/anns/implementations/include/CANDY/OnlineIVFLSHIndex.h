/*! \file OnlineIVFLSHIndex*/
//
// Created by tony on 04/01/24.
//

#ifndef CANDY_INCLUDE_CANDY_ONLINEIVFLSHINDEX_H_
#define CANDY_INCLUDE_CANDY_ONLINEIVFLSHINDEX_H_

#include <Utils/AbstractC20Thread.hpp>
#include <Utils/ConfigMap.hpp>
#include <memory>
#include <vector>
#include <Utils/IntelliTensorOP.hpp>
#include <faiss/IndexFlat.h>
#include <CANDY/AbstractIndex.h>
#include <CANDY/OnlinePQIndex/IVFTensorEncodingList.h>
#include <faiss/VectorTransform.h>
namespace CANDY {

/**
 * @ingroup  CANDY_lib_bottom The main body and interfaces of library function
 * @{
 */
/**
 * @class OnlineIVFLSHIndex CANDY/OnlineIVFLSHIndex.h
 * @brief A LSH indexing, using 2-tier IVF List to manage buckets. The base tier is hamming encoding, implemented under list,
 * the top tier is sampled summarization of hamming encoding, implemented under vector (faster access, harder to change, but less representative).
 * The LSH function is the vanilla random projection (gaussian or random matrix).
 * @note currently single thread
 * @note using hamming LSH function defined in faiss
 * @note config parameters
 * - vecDim, the dimension of vectors, default 768, I64
 * - candidateTimes, the times of k to determine minimum candidates, default 1 ,I64
 * - numberOfBuckets, the number of first titer buckets, default 1, I64, suggest 2^n
 * - encodeLen, the length of LSH encoding, in bytes, default 1, I64
 * - metricType, the type of AKNN metric, default L2, String
 * - lshMatrixType, the type of lsh matrix, default gaussian, String
    * - gaussian means a N(0,1) LSH matrix
    * - random means a random matrix where each value ranges from -0.5~0.5
 * - useCRS, whether or not use column row sampling in projecting the vector, 0 (No), I64
    * - further trade off of accuracy v.s. efficiency
 * - CRSDim, the dimension which are not pruned by crs, 1/10 of vecDim, I64
 * - redoCRSIndices, whether or not re-generate the indices of CRS, 0 (No), I64
 */
class OnlineIVFLSHIndex : public AbstractIndex {
 protected:
  INTELLI::ConfigMapPtr myCfg = nullptr;
  int64_t vecDim = 0;
  int64_t numberOfBuckets = 1;
  int64_t encodeLen = 1;
  int64_t candidateTimes = 1;
  int64_t useCRS = 0;
  int64_t CRSDim = 1;
  int64_t bucketsLog2 = 0;
  int64_t redoCRSIndices = 0;
  std::string lshMatrixType = "gaussian";
  double maskReference = 0.5;
  IVFTensorEncodingList IVFList;
  std::vector<uint8_t> encodeSingleRow(torch::Tensor &tensor, uint64_t *bucket);
  torch::Tensor rotationMatrix, crsIndices;
  virtual torch::Tensor randomProjection(torch::Tensor &a);
  /**
   * @brief the inline function of deleting  rows
   * @param t the tensor, multiple rows
   * @return bool whether the deleting is successful
   */
  bool deleteRowsInline(torch::Tensor &t);
  /**
   * @brief to generate the sampling indices of crs
   */
  void genCrsIndices(void);
 public:
  OnlineIVFLSHIndex() {

  }

  ~OnlineIVFLSHIndex() {

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
   * @brief insert a tensor
   * @param t the tensor, accept multiple rows
   * @return bool whether the insertion is successful
   */
  virtual bool insertTensor(torch::Tensor &t);

  /**
   * @brief delete a tensor
   * @param t the tensor, recommend single row
   * @param k the number of nearest neighbors
   * @return bool whether the deleting is successful
   */
  virtual bool deleteTensor(torch::Tensor &t, int64_t k = 1);

  /**
   * @brief revise a tensor
   * @param t the tensor to be revised, recommend single row
   * @param w the revised value
   * @return bool whether the revising is successful
   */
  virtual bool reviseTensor(torch::Tensor &t, torch::Tensor &w);

  /**
   * @brief search the k-NN of a query tensor, return the result tensors
   * @param t the tensor, allow multiple rows
   * @param k the returned neighbors
   * @return std::vector<torch::Tensor> the result tensor for each row of query
   */
  virtual std::vector<torch::Tensor> searchTensor(torch::Tensor &q, int64_t k);

  static void fvecs2bitvecs(const float *x, uint8_t *b, size_t d, size_t n, float ref);
  static void fvec2bitvec(const float *x, uint8_t *b, size_t d, float ref);
  /**
   * @brief thw column row sampling to compute approximate matrix multiplication
   * @param A the left side matrix
   * @param B the right side matrix
   * @param idx the indices of sampling
   * @param _crsDim the dimension of preserved dimensions
   */
  static torch::Tensor crsAmm(torch::Tensor &A, torch::Tensor &B, torch::Tensor &indices);
};

/**
 * @ingroup  CANDY_lib_bottom
 * @typedef OnlineIVFLSHIndexPtr
 * @brief The class to describe a shared pointer to @ref  OnlineIVFLSHIndex

 */
typedef std::shared_ptr<class CANDY::OnlineIVFLSHIndex> OnlineIVFLSHIndexPtr;
/**
 * @ingroup  CANDY_lib_bottom
 * @def newOnlineIVFLSHIndex
 * @brief (Macro) To creat a new @ref  OnlineIVFLSHIndex shared pointer.
 */
#define newOnlineIVFLSHIndex std::make_shared<CANDY::OnlineIVFLSHIndex>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_ABSTRACTCPPALGO_H_
