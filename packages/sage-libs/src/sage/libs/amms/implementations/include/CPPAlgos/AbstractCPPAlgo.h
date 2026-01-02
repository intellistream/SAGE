/*! \file AbstractCPPAlgo.h*/
//
// Created by tony on 25/05/23.
//

#ifndef INTELLISTREAM_INCLUDE_CPPALGOS_ABSTRACTCPPALGO_H_
#define INTELLISTREAM_INCLUDE_CPPALGOS_ABSTRACTCPPALGO_H_

#include <Utils/AbstractC20Thread.hpp>
#include <Utils/ConfigMap.hpp>
#include <torch/torch.h>
#include <torch/script.h>
#include <memory>
#include <vector>

namespace LibAMM {
/**
 * @ingroup LibAMM_CppAlgos The algorithms written in c++
 * @{
 */
/**
 * @class AbstractCPPAlgo CPPAlgos/AbstractCPPAlgo.h
 * @brief The abstract class of c++ algos
 */
class AbstractCPPAlgo {
 protected:
  /**
   * @brief the default time break dowm variables
   * @note By default, we decompose each AMM as
   * - buildA, to translate A matrix
   * - buildB, to translate B matrix
   * - fABTime, to conduct mm or table look-up over the reduced A,B
   * - postProcessTime, if f(A,B) is not the finall result, measure the time spend for post process
   * - useCuda, whether or not use cuda to conduct computation, default 0
   */
  uint64_t buildATime = 0, buildBTime = 0, fABTime = 0, postProcessTime = 0;
  uint64_t useCuda = 0;
 public:
  AbstractCPPAlgo() {

  }

  ~AbstractCPPAlgo() {

  }

  /**
   * @brief set the alo-specfic config related to one algorithm
   */
  virtual void setConfig(INTELLI::ConfigMapPtr cfg);

  /**
   * @brief the virtual function provided for outside callers, rewrite in children classes
   * @param A the A matrix
   * @param B the B matrix
   * @param sketchSize the size of sketc or sampling
   * @return the output c matrix
   */
  virtual torch::Tensor amm(torch::Tensor A, torch::Tensor B, uint64_t sketchSize);

  /**
   * @brief to get the breakdown of this algorithm, returned as a config map
   * @return the key-value table breakdown in ConfigMapPtr;
   */
  virtual INTELLI::ConfigMapPtr getBreakDown();
};

/**
 * @ingroup LibAMM_CppAlgos
 * @typedef AbstractMatrixCppAlgoPtr
 * @brief The class to describe a shared pointer to @ref AbstractCPPAlgo

 */
typedef std::shared_ptr<class LibAMM::AbstractCPPAlgo> AbstractCPPAlgoPtr;
/**
 * @ingroup LibAMM_CppAlgos
 * @def newAbstractCppAlgo
 * @brief (Macro) To creat a new @ref  AbstractCppAlgounder shared pointer.
 */
#define newAbstractCPPAlgo std::make_shared<LibAMM::AbstractCPPAlgo>
}
/**
 * @}
 */

#endif //INTELLISTREAM_INCLUDE_CPPALGOS_ABSTRACTCPPALGO_H_
