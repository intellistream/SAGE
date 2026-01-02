/*! \file BlockLRACPPAlgo.h*/
//
// Created by yuhao on 27/05/23.
//

#ifndef INTELLISTREAM_INCLUDE_CPPALGOS_BlockLRACPPAlgo_H_
#define INTELLISTREAM_INCLUDE_CPPALGOS_BlockLRACPPAlgo_H_

#include <CPPAlgos/AbstractCPPAlgo.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_CPPAlgos The algorithms writtrn in c++
 * @{
 */
/**
 * @class BlockLRACPPlgo CPPAlgos/BlockLRACPPAlgo.h
 * @brief The block SVD LRA class of c++ algos
 *
 */
class BlockLRACPPAlgo : public LibAMM::AbstractCPPAlgo {

 protected:
  double ARankRatio = 0.5;
  double BRankRatio = 0.5;

 public:
  BlockLRACPPAlgo() {

  }

  ~BlockLRACPPAlgo() {

  }

  /**
   * @brief set the alo-specfic config related to one algorithm
   * @param ARankRatio LRA rank ratio over A complete SVD rank
   * @param BRankRatio LRA rank ratio over B complete SVD rank
   */
  virtual void setConfig(INTELLI::ConfigMapPtr cfg);

  /**
   * @brief Implementation of paper [IEEE-HPCS 2017] Accelerating Matrix Multiplication in Deep Learning by Using Low-Rank Approximation https://ieeexplore.ieee.org/abstract/document/8035076
   * @param A the A matrix
   * @param B the B matrix
   * @param blockSize the size of block to do SVD
   * @return the output c matrix
   */
  virtual torch::Tensor amm(torch::Tensor A, torch::Tensor B, uint64_t blockSize);

};
/**
 * @ingroup LibAMM_CPPAlgos
 * @typedef AbstractMatrixCPPAlgoPtr
 * @brief The class to describe a shared pointer to @ref BlockLRACPPAlgo

*/
typedef std::shared_ptr<class LibAMM::BlockLRACPPAlgo> BlockLRACPPAlgoPtr;
/**
   * @ingroup LibAMM_CPPAlgos
   * @def newBlockLRACPPAlgo
   * @brief (Macro) To creat a new @ref  BlockLRACPPAlgounder shared pointer.
   */
#define newBlockLRACPPAlgo std::make_shared<LibAMM::BlockLRACPPAlgo>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_BlockLRACPPAlgo_H_
