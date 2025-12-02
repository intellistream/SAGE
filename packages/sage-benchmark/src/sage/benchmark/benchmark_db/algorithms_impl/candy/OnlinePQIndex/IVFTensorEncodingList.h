/*! \file IVFTensorEncodingList.h*/
//
// Created by tony on 11/01/24.
//

#ifndef CANDY_INCLUDE_CANDY_ONLINEPQINDEX_IVFTENSORLIST_H_
#define CANDY_INCLUDE_CANDY_ONLINEPQINDEX_IVFTENSORLIST_H_
#include <Utils/IntelliTensorOP.hpp>
#include <vector>
#include <list>
#include <mutex>
namespace CANDY {
/**
 * @ingroup  CANDY_lib_bottom_sub The support classes for index approaches
 * @{
 */
/**
  * @class IVFListCell CANDY/OnlinePQIndex/IVFTensorEncodingList.h
  * @brief a cell of row tensor pointers which have the same code
  */
class IVFListCell {
 protected:
  int64_t tensors = 0;
  std::list<INTELLI::TensorPtr> tl;
  std::mutex m_mut;
  std::vector<uint8_t> encode;
 public:
  IVFListCell() {}
  ~IVFListCell() {}
  int64_t size() {
    return tensors;
  }
  /**
  * @brief lock this cell
  */
  void lock() {
    while (!m_mut.try_lock());
  }
  /**
   * @brief unlock this cell
   */
  void unlock() {
    m_mut.unlock();
  }
  void setEncode(std::vector<uint8_t> _encode) {
    encode = _encode;
  }
  std::vector<uint8_t> getEncode() {
    return encode;
  }
  /**
   * @brief insert a tensor
   * @param t the tensor
   */
  void insertTensor(torch::Tensor &t);
  /**
  * @brief insert a tensor pointer
  * @param tp the tensor pointer
  */
  void insertTensorPtr(INTELLI::TensorPtr tp);
  /**
  * @brief delete a tensor
   * @note will check the equal condition by torch::equal
  * @param t the tensor
   * @returen bool whether the tensor is really deleted
  */
  bool deleteTensor(torch::Tensor &t);
  /**
  * @brief delete a tensor pointer
  * @note will check the equal condition by pointer ==
 * @param tp the tensor pointer
   * @returen bool whether the tensor is realy deleted
 */
  bool deleteTensorPtr(INTELLI::TensorPtr tp);
  /**
  * @brief get all of the tensors in list
 * @return a 2-D tensor contain all, torch::zeros({1,1}) if got nothing
 */
  torch::Tensor getAllTensors();

};
/**
 * @ingroup  CANDY_lib_bottom_sub
 * @typedef IVFListCellPtr
 * @brief The class to describe a shared pointer to @ref IVFListCell
 */
typedef std::shared_ptr<CANDY::IVFListCell> IVFListCellPtr;
/**
 * @ingroup  CANDY_lib_bottom_sub
 * @def newIVFListCell
 * @brief (Macro) To creat a new @ref newIVFListCell under shared pointer.
 */
#define  newIVFListCell make_shared<CANDY::IVFListCell>
/**
  * @class IVFListBucket CANDY/OnlinePQIndex/IVFTensorEncodingList.h
  * @brief a bucket of multiple @ref IVFListCell
  */
class IVFListBucket {
 protected:
  int64_t tensors = 0;
  std::list<IVFListCellPtr> cellPtrs;
  std::mutex m_mut;
 public:
  IVFListBucket() {}
  ~IVFListBucket() {}
  int64_t size() {
    return tensors;
  }
  /**
   * @brief lock this bucket
   */
  void lock() {
    while (!m_mut.try_lock());
  }
  /**
   * @brief unlock this bucket
   */
  void unlock() {
    m_mut.unlock();
  }
  /**
  * @brief insert a tensor with its encode
  * @param t the tensor
  * @param encode the corresponding encode
   * @param isConcurrent whether this process is concurrently executed
  */
  void insertTensorWithEncode(torch::Tensor &t, std::vector<uint8_t> &encode, bool isConcurrent = false);
  /**
  * @brief delete a tensor with its encode
  * @param t the tensor
  * @param encode the corresponding encode
   * @param isConcurrent whether this process is concurrently executed
   * @return bool whether the tensor is really deleted
  */
  bool deleteTensorWithEncode(torch::Tensor &t, std::vector<uint8_t> &encode, bool isConcurrent = false);
  /**
  * @brief delete a tensor
   * @note will check the equal condition by torch::equal
  * @param t the tensor
   * @param isConcurrent whether this process is concurrently executed
   * * @return bool whether the tensor is really deleted
  */
  bool deleteTensor(torch::Tensor &t, bool isConcurrent = false);
  /**
  * @brief get all of the tensors in list
 * @return a 2-D tensor contain all, torch::zeros({1,1}) if got nothing
 */
  torch::Tensor getAllTensors();
  /**
* @brief get all of the tensors in list with a specific encode
   * @param _encode the specified encode
* @return a 2-D tensor contain all, torch::zeros({1,1}) if got nothing
*/
  torch::Tensor getAllTensorsWithEncode(std::vector<uint8_t> &_encode);
  /**
* @brief get teh size in list with a specific encode
   * @param _encode the specified encode
* @return the size under _encode
*/
  int64_t sizeWithEncode(std::vector<uint8_t> &_encode);
  /**
* @brief get a minimum number of tensors under sorted hamming distance
 * @param _encode the specified encode
 * @param minNumber the minimum of desired tensors
 * @param _vecDim the dimension of database vectors
* @return a 2-D tensor or result, torch::zeros({1,1}) if got nothing
*/
  torch::Tensor getMinimumTensorsUnderHamming(std::vector<uint8_t> &_encode, int64_t minNumber, int64_t _vecDim);
};
/**
 * @ingroup  CANDY_lib_bottom_sub
 * @typedef IVFListBucketPtr
 * @brief The class to describe a shared pointer to @ref IVFListBucket
 */
typedef std::shared_ptr<CANDY::IVFListBucket> IVFListBucketPtr;
/**
 * @ingroup  CANDY_lib_bottom_sub
 * @def newIVFListBucket
 * @brief (Macro) To creat a new @ref IVFListBucket under shared pointer.
 */
#define  newIVFListBucket make_shared<CANDY::IVFListBucket>
/**
 * @class IVFTensorEncodingList CANDY/OnlinePQIndex/IVFTensorEncodingList.h
 * @brief The inverted file (IVF) list to organize tensor and its encodings
 */

class IVFTensorEncodingList {
 protected:
  std::vector<CANDY::IVFListBucketPtr> bucketPtrs;
  size_t encodeLen = 0;
  static uint8_t getLeftIdxU8(uint8_t idx, uint8_t leftOffset, bool *reachedLeftMost) {
    if (idx < leftOffset) {
      *reachedLeftMost = true;
      return 0;
    }
    return idx - leftOffset;
  }
  static uint8_t getRightIdxU8(uint8_t idx, uint8_t rightOffset, bool *reachedRightMost) {
    uint16_t tempRu = idx;
    tempRu += rightOffset;
    if (tempRu > 255) {
      *reachedRightMost = true;
      return 255;
    }
    return idx + rightOffset;
  }
 public:
  IVFTensorEncodingList() {
  }
  /**
   * @brief init this IVFList
   * @param bkts the number of buckets
   * @param _encodeLen the length of tensors' encoding
   */
  void init(size_t bkts, size_t _encodeLen);
  ~IVFTensorEncodingList() {}
  /**
 * @brief insert a tensor with its encode
 * @param t the tensor
 * @param encode the corresponding encode
   * @param bktIdx the index number of bucket
  * @param isConcurrent whether this process is concurrently executed
 */
  void insertTensorWithEncode(torch::Tensor &t,
                              std::vector<uint8_t> &encode,
                              uint64_t bktIdx,
                              bool isConcurrent = false);
  /**
  * @brief delete a tensor with its encode
  * @param t the tensor
  * @param encode the corresponding encode
   * @param bktIdx the index number of bucket
   * @param isConcurrent whether this process is concurrently executed
   * @return bool whether the tensor is really deleted
  */
  bool deleteTensorWithEncode(torch::Tensor &t,
                              std::vector<uint8_t> &encode,
                              uint64_t bktIdx,
                              bool isConcurrent = false);
  /**
   * @brief get minimum number of tensors that are candidate to query t
   * * @param t the tensor
  * @param encode the corresponding encode
   * @param bktIdx the index number of bucket
   * @param isConcurrent whether this process is concurrently executed
   * @return a 2-D tensor contain all, torch::zeros({minimumNum,D}) if got nothing
   */
  torch::Tensor getMinimumNumOfTensors(torch::Tensor &t,
                                       std::vector<uint8_t> &encode,
                                       uint64_t bktIdx,
                                       int64_t minimumNum);
  bool isConcurrent = false;
  /**
   * @brief get minimum number of tensors that are candidate to query t, using hamming distance
   * * @param t the tensor
   * @param encode the corresponding encode
   * @param bktIdx the index number of bucket
   * @param isConcurrent whether this process is concurrently executed
   * @return a 2-D tensor contain all, torch::zeros({minimumNum,D}) if got nothing
   */
  torch::Tensor getMinimumNumOfTensorsHamming(torch::Tensor &t,
                                              std::vector<uint8_t> &encode,
                                              uint64_t bktIdx,
                                              int64_t minimumNum);

  /**
  * @brief get minimum number of tensors that are candidate to query t, must inside a bucket
  * * @param t the tensor
 * @param encode the corresponding encode
  * @param bktIdx the index number of bucket
  * @param isConcurrent whether this process is concurrently executed
  * @return a 2-D tensor contain all, torch::zeros({minimumNum,D}) if got nothing
  * @todo improve the efficiency of this function in travsing lists!
  */
  torch::Tensor getMinimumNumOfTensorsInsideBucket(torch::Tensor &t,
                                                   std::vector<uint8_t> &encode,
                                                   uint64_t bktIdx,
                                                   int64_t minimumNum);
  /**
  * @brief get minimum number of tensors that are candidate to query t, must inside a bucket
  * * @param t the tensor
 * @param encode the corresponding encode
  * @param bktIdx the index number of bucket
  * @param isConcurrent whether this process is concurrently executed
  * @return a 2-D tensor contain all, torch::zeros({minimumNum,D}) if got nothing
  * @todo improve the efficiency of this function in travsing lists!
  */
  torch::Tensor getMinimumNumOfTensorsInsideBucketHamming(torch::Tensor &t,
                                                          std::vector<uint8_t> &encode,
                                                          uint64_t bktIdx,
                                                          int64_t minimumNum);
};
}
/**
 * @}
 */
#endif //CANDY_INCLUDE_CANDY_ONLINEPQINDEX_IVFTENSORLIST_H_
