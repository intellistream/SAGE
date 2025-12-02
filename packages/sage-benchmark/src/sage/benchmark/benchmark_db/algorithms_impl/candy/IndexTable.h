/*! \file IndexTable.h*/
//
// Created by tony on 25/05/23.
//

#ifndef CANDY_INCLUDE_CANDY_INDEXTABLE_H_
#define CANDY_INCLUDE_CANDY_INDEXTABLE_H_

#include <map>
#include <AbstractIndex.h>

namespace CANDY {
/**
 * ingroup  CANDY_lib
 * @{
 */
/**
* @class IndexTable  CANDY/IndexTable.h
* @brief The table to index index algos
* @ingroup  CANDY_lib The TOP interfaces of library function
 * @note  Default behavior
* - create
* - (optional) call @ref addIndex for new algo
* - find a loader by @ref getIndex using its tag
* @note default tags (String)
 * - flat @ref FlatIndex
 * - parallelPartition @ref ParallelPartitionIndex
 * - onlinePQ @ref OnlinePQIndex
 * - onlineIVFLSH @ref OnlineIVFLSHIndex
 * - HNSWNaive @ref HNSWNaiveIndex
 * - faiss @ref FaissIndex
 * - congestionDrop @ref CongestionDropIndex
 * - bufferedCongestionDrop @ref BufferedCongestionDropIndex
 * - flatAMMIP @ref FlatAMMIPIndex
*/
class IndexTable {
 protected:
  std::map<std::string, CANDY::AbstractIndexPtr> indexMap;
 public:
  IndexTable();

  ~IndexTable() {}

  /**
   * @brief To register a new ALGO
   * @param anew The new algo
   * @param tag THe name tag
   */
  void addIndex(CANDY::AbstractIndexPtr anew, std::string tag) {
    indexMap[tag] = anew;
  }

  /**
   * @brief find a dataloader in the table according to its name
   * @param name The nameTag of loader
   * @return The AbstractIndexPtr, nullptr if not found
   */
  CANDY::AbstractIndexPtr getIndex(std::string name) {
    if (indexMap.count(name)) {
      return indexMap[name];
    }
    return nullptr;
  }
};
/**
 * @}
 */
} // CANDY

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_IndexTable_H_
