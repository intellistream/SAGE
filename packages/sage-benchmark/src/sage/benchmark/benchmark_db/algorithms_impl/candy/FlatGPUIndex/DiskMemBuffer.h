/*! \file DiskMemBuffer.h*/
//
// Created by tony on 24/07/24.
//

#ifndef CANDY_INCLUDE_CANDY_FLATSSDGPUINDEX_DISKMEMBUFFER_H_
#define CANDY_INCLUDE_CANDY_FLATSSDGPUINDEX_DISKMEMBUFFER_H_
#include <stdint.h>
#include <memory>
#include <torch/torch.h>
#include <vector>
#include <atomic>
namespace CANDY {
/**
 *  @defgroup  CANDY_lib_bottom_sub The support classes for index approaches
 * @{
 */
/**
 * @class DiskHeader CANDY/FlatSSDGPUIndex/DiskMemBuffer.h
 * @brief The class to store necessary information on disk, typically at first sector
 */
class DiskHeader {
 public:
  uint64_t version = 0;
  uint64_t vecDim = 0;
  uint64_t vecCnt = 0;
  uint64_t u64Cnt = 0;
  uint64_t aknnType = 0;
  DiskHeader() {}
  ~DiskHeader() {}
};
/**
 * @class TensorCacheLine CANDY/FlatSSDGPUIndex/DiskMemBuffer.h
 * @brief The virtual cache line to buffer data, storage of tensor
 */
class TensorVCacheLine {
 public:
  int64_t beginPos = 0;
  int64_t endPos = 0;
  int64_t temperature = 0;
  torch::Tensor buffer;
  TensorVCacheLine() {}
  ~TensorVCacheLine() {}
};
/**
 * @class U64VCacheLine CANDY/FlatSSDGPUIndex/DiskMemBuffer.h
 * @brief The virtual cache line to buffer data, storage of uint64_t
 */
class U64VCacheLine {
 public:
  int64_t beginPos = 0;
  int64_t endPos = 0;
  int64_t temperature = 0;
  std::vector<uint64_t> buffer;
  U64VCacheLine() {}
  ~U64VCacheLine() {}
};
/**
 * @class PlainDiskMemBufferOfTensor CANDY/FlatSSDGPUIndex/DiskMemBuffer.h
 * @brief a straight forward plain storage of tensor and u64, will firstly use in-memory data, and switch into disk, full flush between memory and disk
 * @note NOt yet done the really disk part
 * @note will use half of namespace for tensor, another for U64
 */
class PlainMemBufferTU {
 protected:
  DiskHeader diskInfo;
  TensorVCacheLine cacheT;
  U64VCacheLine cacheU;
  int64_t tensorBegin = 0, u64Begin = 0;
  int64_t bsize = 0;
  int64_t dmaSize = 1024000;
  int64_t memoryReadCntTotal = 0, memoryReadCntMiss = 0;
  int64_t memoryWriteCntTotal = 0, memoryWriteCntMiss = 0;
  std::atomic_bool isDirtyT = false;
  std::atomic_bool isDirtyU = false;
  /**
   * @brief inline helper to get the tensor at specified position
   * @param startPos the start position
   * @param endPos the end position
   * @return the tensor, [n*vecDim]
   */
  torch::Tensor getTensorInline(int64_t startPos, int64_t endPos);
  /**
   * @brief inline helper to revise the tensor at specified position
   * @param startPos the start position
   * @param t the tensor, [n*vecDim]
   * @return whether it is successful
   */
  bool reviseTensorInline(int64_t startPos, torch::Tensor &t);
 public:
 // struct spdk_nvme_qpair *diskQpair;
  PlainMemBufferTU() {}
  ~PlainMemBufferTU() {}
  //SPDKSSD *ssdPtr = nullptr;
  /**
   * @brief get the total count of times in terms of memory read
   * @return the count of times
   */
  int64_t getMemoryReadCntTotal(void);
  /**
  * @brief get the miss count of times in terms of memory read
  * @return the count of times
  */
  int64_t getMemoryReadCntMiss(void);
  /**
  * @brief get the total count of times in terms of memory write
  * @return the count of times
  */
  int64_t getMemoryWriteCntTotal(void);
  /**
  * @brief get the miss count of times in terms of memory write
  * @return the count of times
  */
  int64_t getMemoryWriteCntMiss(void);
  /**
   * @brief init everything
   * @param vecDim The dimension of vectors
   * @param bufferSize the size for both tensor cache (in rows) and  U64 cache (in sizeof(uint64_t))
   * @param _tensorBegin the begin offset of tensor storage in disk
   * @param _u64Begin the begin offset of u64 storage in disk
   * @param _dmaSize the max size of dma buffer, I64, default 1024000
   */
  void init(int64_t vecDim,
            int64_t bufferSize,
            int64_t _tensorBegin,
            int64_t _u64Begin,
            int64_t _dmaSize = 1024000);
  /**
   * @brief to return the size of ingested vectors
   * @return the number of rows.
   */
  int64_t size();
  /**
  * @brief clear the occupied resource
  */
  void clear();
  /**
  * @brief clear the statistics
  */
  void clearStatistics();
  /**
   * @brief to get the tensor at specified position
   * @param startPos the start position
   * @param endPos the end position
   * @return the tensor, [n*vecDim]
   */
  torch::Tensor getTensor(int64_t startPos, int64_t endPos);
  /**
 * @brief to get the tensor at specified position
 * @param startPos the start position
 * @param endPos the end position
 * @return the tensor, [n*vecDim]
 */
  std::vector<uint64_t> getU64(int64_t startPos, int64_t endPos);
  /**
   * @brief to revise the tensor at specified position
   * @param startPos the start position
   * @param t the tensor, [n*vecDim]
   * @return whether it is successful
   */
  bool reviseTensor(int64_t startPos, torch::Tensor &t);
  /**
   * @brief to revise the tensor at specified position
   * @param startPos the start position
   * @param u the u64 vector, [n]
   * @return whether it is successful
   */
  bool reviseU64(int64_t startPos, std::vector<uint64_t> &u);
  /**
 * @brief to append the tensor to the end of storage region
 * @param t the tensor, [n*vecDim]
 * @return whether it is successful
 */
  bool appendTensor(torch::Tensor &t);
  /**
 * @brief to append the tensor to the end of storage region
 * @param u the u64 vector, [n]
 * @return whether it is successful
 */
  bool appendU64(std::vector<uint64_t> &u);
  /**
   * @brief to delete the tensor at specified position
   * @param startPos the start position
   * @param endPos the end position
   * @return whether it is successful
   */
  bool deleteTensor(int64_t startPos, int64_t endPos);
  /**
   * @brief to delete a U64 at specified position
   * @param startPos the start position
   * @param endPos the end position
   * @return whether it is successful
   */
  bool deleteU64(int64_t startPos, int64_t endPos);

};
}
/**
 * @}
 */
#endif //CANDY_INCLUDE_CANDY_FLATSSDGPUINDEX_DISKMEMBUFFER_H_
