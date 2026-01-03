/*! \file RIPCPPAlgo.h*/
//
// Created by tony on 25/05/23.
//

#ifndef INTELLISTREAM_INCLUDE_CPPALGOS_RIPCppAlgo_H_
#define INTELLISTREAM_INCLUDE_CPPALGOS_RIPCppAlgo_H_

#include <CPPAlgos/AbstractCPPAlgo.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_CppAlgos The algorithms written in c++
 * @{
 */
/**
 * @class RIPCPPAlgo CPPAlgos/RIPCPPAlgo.h
 * @brief New and improved Johnson-Lindenstrauss embeddings via the Restricted Isometry Property
 *
 */
class RIPCPPAlgo : public LibAMM::AbstractCPPAlgo {
 public:
  RIPCPPAlgo() {

  }

  ~RIPCPPAlgo() {

  }

  /**
   * @brief the virtual function provided for outside callers, rewrite in children classes
   * @param A the A matrix
   * @param B the B matrix
   * @param sketchSize the size of sketc or sampling
   * @return the output c matrix
   */
  virtual torch::Tensor amm(torch::Tensor A, torch::Tensor B, uint64_t sketchSize);

};

/**
 * @ingroup LibAMM_CppAlgos
 * @typedef AbstractMatrixCppAlgoPtr
 * @brief The class to describe a shared pointer to @ref RIPCppAlgo

 */
typedef std::shared_ptr<class LibAMM::RIPCPPAlgo> RIPCPPAlgoPtr;
/**
 * @ingroup LibAMM_CppAlgos
 * @def newRIPCppAlgo
 * @brief (Macro) To creat a new @ref  RIPCppAlgounder shared pointer.
 */
#define newRIPCPPAlgo std::make_shared<LibAMM::RIPCPPAlgo>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_RIPCppAlgo_H_
