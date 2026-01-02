/*! \file SMPPCACPPAlgo.h*/
//
// Created by yuhao on 6/6/23.
//

#ifndef INTELLISTREAM_INCLUDE_CPPALGOS_SMPPCACppAlgo_H_
#define INTELLISTREAM_INCLUDE_CPPALGOS_SMPPCACppAlgo_H_

#include <CPPAlgos/AbstractCPPAlgo.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_CppAlgos The algorithms written in c++
 * @{
 */
/**
 * @class SMPPCACPPAlgo CPPAlgos/SMPPCACPPAlgo.h
 * @brief sketch scaled JL class of c++ algos
 *
 */
class SMPPCACPPAlgo : public LibAMM::AbstractCPPAlgo {
 public:
  SMPPCACPPAlgo() {

  }

  ~SMPPCACPPAlgo() {

  }

  /**
   * @brief the virtual function provided for outside callers, rewrite in children classes
   * @param A the A matrix
   * @param B the B matrix
   * @param sketchSize the size of sketch
   * @return the output c matrix
   */
  virtual torch::Tensor amm(torch::Tensor A, torch::Tensor B, uint64_t sketchSize);

};

/**
 * @ingroup LibAMM_CppAlgos
 * @typedef AbstractMatrixCppAlgoPtr
 * @brief The class to describe a shared pointer to @ref SMPPCACppAlgo

 */
typedef std::shared_ptr<class LibAMM::SMPPCACPPAlgo> SMPPCACPPAlgoPtr;
/**
 * @ingroup LibAMM_CppAlgos
 * @def newSMPPCACppAlgo
 * @brief (Macro) To creat a new @ref  SMPPCACppAlgounder shared pointer.
 */
#define newSMPPCACPPAlgo std::make_shared<LibAMM::SMPPCACPPAlgo>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_SMPPCACppAlgo_H_
