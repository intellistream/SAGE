//
// Created by tony on 24/07/24.
//
#include <FlatGPUIndex/DiskMemBuffer.h>
#include <c10/util/Logging.h>
namespace CANDY {
void PlainMemBufferTU::init(int64_t vecDim,
                                int64_t bufferSize,
                                int64_t _tensorBegin,
                                int64_t _u64Begin,
                                int64_t _dmaSize) {
  //diskInfo.
  diskInfo.vecDim = vecDim;
  bsize = bufferSize;
  tensorBegin = _tensorBegin;
  u64Begin = _u64Begin;
  dmaSize = _dmaSize;
  if (bufferSize > 0) {
    cacheT.buffer = torch::zeros({bufferSize, vecDim});
    cacheT.beginPos = 0;
    cacheT.endPos = bufferSize-1;
    cacheU.buffer = std::vector<uint64_t>(bufferSize, 0);
    cacheU.beginPos = 0;
    cacheU.endPos = bufferSize-1;
    //std::cout<<cacheT.buffer;
    isDirtyT = false;
    isDirtyU = false;
  }

}
int64_t PlainMemBufferTU::getMemoryWriteCntTotal() {
  return memoryWriteCntTotal;
}
int64_t PlainMemBufferTU::getMemoryWriteCntMiss() {
  return memoryWriteCntMiss;
}
int64_t PlainMemBufferTU::getMemoryReadCntTotal() {
  return memoryReadCntTotal;
}
int64_t PlainMemBufferTU::getMemoryReadCntMiss() {
  return memoryReadCntMiss;
}
void PlainMemBufferTU::clearStatistics() {
  memoryWriteCntTotal = 0;
  memoryWriteCntMiss = 0;
  memoryReadCntTotal = 0;
  memoryReadCntMiss = 0;
}

int64_t PlainMemBufferTU::size() {
  return diskInfo.vecCnt;
}
torch::Tensor PlainMemBufferTU::getTensor(int64_t startPos, int64_t endPos) {
  if (bsize <= 0 || endPos - startPos <= bsize) {
    return getTensorInline(startPos, endPos);
  }
  auto ru = torch::zeros({endPos - startPos, (int64_t) (diskInfo.vecDim)});
  int64_t total_vectors = endPos - startPos;
  for (int64_t i = 0; i < total_vectors; i += bsize) {
    int64_t endI = std::min(i + bsize, total_vectors);
    ru.slice(0, i, endI) = getTensor(startPos + i, startPos + endI);
  }
  return ru;
}
bool PlainMemBufferTU::reviseTensor(int64_t startPos, torch::Tensor &t) {
  if (bsize <= 0 || t.size(0) <= bsize) {
    return reviseTensorInline(startPos, t);
  }
  int64_t total_vectors = t.size(0);
  for (int64_t i = 0; i < total_vectors; i += bsize) {
    int64_t endI = std::min(i + bsize, total_vectors);
    auto iSlice = t.slice(0, i, endI);
    reviseTensorInline(startPos + i, iSlice);
    // ru.slice(0,i,endI) = getTensor(startPos+i,startPos+endI);
  }
  return true;
}
torch::Tensor PlainMemBufferTU::getTensorInline(int64_t startPos, int64_t endPos) {

  //int64_t remainSizeRu;
  int64_t diskOffset;
  /**
   * @brief no buffer, direct disk read
   */
  auto inMemTensor = cacheT.buffer.contiguous();
  memoryReadCntTotal++;
  /**
  * @brief totally inside memory
  */
  torch::Tensor ru = inMemTensor.slice(0, startPos - cacheT.beginPos, endPos - cacheT.beginPos);
  return ru;

}
std::vector<uint64_t> PlainMemBufferTU::getU64(int64_t startPos, int64_t endPos) {
  auto &inMemBuffer = cacheU.buffer;
  //int64_t remainSizeRu;
  int64_t bufferBegin = u64Begin;
  // Totally inside memory

  std::vector<uint64_t> ru(inMemBuffer.begin() + (startPos - cacheU.beginPos),
                             inMemBuffer.begin() + (endPos - cacheU.beginPos));

    return ru;
}
bool PlainMemBufferTU::reviseTensorInline(int64_t startPos, torch::Tensor &t) {
  int64_t endPos = startPos + t.size(0);
  //int64_t remainSizeRu;

  isDirtyT = true;
  memoryWriteCntTotal++;

  /**
 * @brief totally inside memory
 */
  if (startPos >= cacheT.beginPos && endPos <= cacheT.endPos) {
    cacheT.buffer.slice(0, startPos - cacheT.beginPos, endPos - cacheT.beginPos) = t;
    return true;
  }
  else{
    LOG(ERROR) << "Out of memory buffer";
    return  false;
  }

}
bool PlainMemBufferTU::reviseU64(int64_t startPos, std::vector<uint64_t> &data) {
  int64_t endPos = startPos + data.size();
  int64_t remainSizeRu;
  int64_t diskOffset;
  isDirtyU = true;
  int64_t bufferBegin = u64Begin;
  // Totally inside memory
  if (startPos >= cacheU.beginPos && endPos <= cacheU.endPos) {
    std::copy(data.begin(), data.end(), cacheU.buffer.begin() + (startPos - cacheU.beginPos));
    return true;
  }
  return false;
}
bool PlainMemBufferTU::appendTensor(torch::Tensor &t) {
  int64_t startPos = diskInfo.vecCnt;
  // int64_t diskOffset;
  reviseTensor(startPos, t);
  // diskOffset = tensorBegin;
  diskInfo.vecCnt += t.size(0);
  return true;
}
bool PlainMemBufferTU::appendU64(std::vector<uint64_t> &data) {
  int64_t startPos = diskInfo.vecCnt;
  reviseU64(startPos, data);
  diskInfo.u64Cnt += data.size();
  return true;
}

bool PlainMemBufferTU::deleteTensor(int64_t startPos, int64_t endPos) {
  int64_t delSize = endPos - startPos;
  auto inMemTensor = getTensor(diskInfo.vecCnt - delSize,diskInfo.vecCnt);
  reviseTensor(startPos, inMemTensor);
  diskInfo.vecCnt -= delSize;
  return true;
}
bool PlainMemBufferTU::deleteU64(int64_t startPos, int64_t endPos) {
  int64_t delSize = endPos - startPos;
  std::vector<uint64_t> inMemBuffer(delSize, 0);
  int64_t diskOffset;
  int64_t bufferBegin = u64Begin;
  // Read the tail valid data
  diskOffset = (diskInfo.u64Cnt - delSize) * sizeof(uint64_t) + 512 + bufferBegin;
  //ssdPtr->read(reinterpret_cast<void *>(inMemBuffer.data()), delSize * sizeof(uint64_t), diskOffset, ssdQpair);
  reviseU64(startPos, inMemBuffer);
  diskInfo.vecCnt -= delSize;
  return true;
}

void PlainMemBufferTU::clear() {
  //ssdPtr->write(&diskInfo, sizeof(DiskHeader), tensorBegin, ssdQpair);
  //spdk_nvme_ctrlr_free_io_qpair(ssdQpair);
}
}
