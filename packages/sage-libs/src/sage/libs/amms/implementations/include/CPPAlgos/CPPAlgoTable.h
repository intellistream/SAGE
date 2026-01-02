/*! \file CPPAlgoTable.h*/
//
// Created by tony on 25/05/23.
//

#ifndef INTELLISTREAM_INCLUDE_CPPALGOS_CPPALGOTABLE_H_
#define INTELLISTREAM_INCLUDE_CPPALGOS_CPPALGOTABLE_H_

#include <map>
#include <CPPAlgos/AbstractCPPAlgo.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_CppAlgos The algorithms writtrn in c++
 * @{
 */
/**
* @class CPPAlgoTable CPPAlgos/CPPAlgoTable.h
* @brief The table to index cpp algos
 * @note  Default behavior
* - create
* - (optional) call @ref registerNewCppAlgo for new algo
* - find a loader by @ref findCppAlgo using its tag
 * @note default tags
 * - mm @ref AbstractCPPAlgo (default matmul)
 * - crs @ref CRSCPPAlgo (the column-row-sampling, crs)
*/
class CPPAlgoTable {
 protected:
  std::map<std::string, LibAMM::AbstractCPPAlgoPtr> algoMap;
 public:
  CPPAlgoTable();

  ~CPPAlgoTable() {}

  /**
   * @brief To register a new ALGO
   * @param anew The new algo
   * @param tag THe name tag
   */
  void registerNewCppAlgo(LibAMM::AbstractCPPAlgoPtr anew, std::string tag) {
    algoMap[tag] = anew;
  }

  /**
   * @brief find a dataloader in the table according to its name
   * @param name The nameTag of loader
   * @return The AbstractCppAlgoPtr, nullptr if not found
   */
  LibAMM::AbstractCPPAlgoPtr findCppAlgo(std::string name) {
    if (algoMap.count(name)) {
      return algoMap[name];
    }
    return nullptr;
  }
};
/**
 * @}
 */
} // LibAMM

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_CPPALGOTABLE_H_
