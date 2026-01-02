/*! \file BlockPartitionRunner.h*/
//
// Created by tony on 24/05/23.
//

#ifndef INTELLISTREAM_INCLUDE_PARALLELIZATION_BLOCKPARTITIONRUNNER_H_
#define INTELLISTREAM_INCLUDE_PARALLELIZATION_BLOCKPARTITIONRUNNER_H_

#include <Utils/AbstractC20Thread.hpp>
#include <Utils/ConfigMap.hpp>
#include <torch/torch.h>
#include <torch/script.h>
#include <memory>
#include <vector>
#include <CPPAlgos/CPPAlgoTable.h>

namespace LibAMM {

#define  newTensor make_shared<torch::Tensor>
typedef std::shared_ptr<torch::Tensor> TensorPtr;
/**
 * @ingroup LibAMM_PARALLELIZATION
 * @{
 * @defgroup PARTITION_RUNNER The partition-based parallelization
 */
/**
 * @class BlockPartitionWorker Parallelization/BlockPartitionRunner.h
 * @ingroup PARTITION_RUNNER
 * @brief The basic partition worker
 */
class BlockPartitionWorker : public INTELLI::AbstractC20Thread {
 protected:
  virtual void inlineMain();

  LibAMM::CPPAlgoTable cppAlgoTable;
  struct timeval tstart, tend;
  uint64_t useCPP = 0;
  uint64_t osScheduling = 0;
  LibAMM::AbstractCPPAlgoPtr cppAlgoPtr = nullptr;
  /**
   * @brief Input matrix A
   */
  TensorPtr matA = nullptr;  // Input matrix A
  /**
    * @brief Input matrix B
    */
  TensorPtr matB = nullptr;  // Input matrix B
  /**
  * @brief OUTput matrix C
  */
  TensorPtr matC = nullptr;  // Output matrix C

  INTELLI::ConfigMapPtr cfg;
  torch::jit::script::Module module;
  uint64_t sketchDimension = 0;
  int coreBind;
  INTELLI::ConfigMapPtr pefResult; // to save pef results

public:
  torch::Tensor irC, subA;
  uint64_t startRow = 0;  // Start row index for the assigned range
  uint64_t endRow = 0;  // End row index (exclusive) for the assigned range

  BlockPartitionWorker() {

  }

  /**
  * @brief set the config map
  * @param _cfg
  */
  void setConfig(INTELLI::ConfigMapPtr _cfg);

  /**
   * @brief set the pointer to A,B,C matrix
   */
  void setABC(TensorPtr A, TensorPtr B, TensorPtr C);

  /**
   * @brief set work parmeters
   * @param aStart The start row in A
   * @param aEnd The end row in A
   * @param mycore the core to be binded
   */
  void setWorkParameters(uint64_t aStart, uint64_t aEnd, int mycore);

  void setCoreBInd(int cno) {
    coreBind = cno;
  }

  ~BlockPartitionWorker() {

  }

  uint64_t getElapsedTime();

  INTELLI::ConfigMapPtr getPefResult();

  /**
  * @brief to export the algorithm breakdown
    * @note only valid for c++ algo
  * @return the key-value table breakdown in ConfigMapPtr;
  */
  virtual INTELLI::ConfigMapPtr getBreakDown();
};
/**
* @ingroup PARTITION_RUNNER
* @def newBlockPartitionWorker
* @brief (Macro) To creat a new @ref BlockPartitionWorker under shared pointer.
*/
#define  newBlockPartitionWorker std::make_shared<LibAMM::BlockPartitionWorker>
typedef std::shared_ptr<LibAMM::BlockPartitionWorker> BlockPartitionWorkerPtr;

/**
 * @class BlockPartitionRunner Parallelization/BlockPartitionRunner.h
 * @ingroup PARTITION_RUNNER
 * @brief The top entity to control all workers, see also @ref BlockPartitionWorker. This one works under a
 * simple row partition parallelization
 * @note parameters
 * - threads, U64, the number of worker threads, default 2
 * - osScheduling, U64, whether use default os scheduling instead of my own core bind, default 0
 * - firstCoreBind, U64, which core will the first thread be bound to, default 0
 * @note default behaviors
 * - create
 * - call @ref setConfig
 * - call @ref runAMM and return result
 * - call @ref getElapsedTime
 * - call @ref getMetrics
 */
class BlockPartitionRunner {

  protected:
    INTELLI::ConfigMapPtr cfg;
    uint64_t threads = 0;
    /**
     * @brief Input matrix A
     */
    TensorPtr matA = nullptr;  // Input matrix A
    /**
      * @brief Input matrix B
      */
    TensorPtr matB = nullptr;  // Input matrix B
    /**
    * @brief OUTput matrix C
    */
    TensorPtr matC = nullptr;  // Output matrix C
    std::vector<BlockPartitionWorkerPtr> workers;
    /**
     * @brief special bind of first core, if need
     */
    uint64_t firstCoreBind = 0;

    INTELLI::ConfigMapPtr metrics = newConfigMap();

  public:
    BlockPartitionRunner() {}

  ~BlockPartitionRunner() {}

  /**
   * @brief set the config map
   * @param _cfg
   */
  void setConfig(INTELLI::ConfigMapPtr _cfg);

  /**
   * @brief create the A,B,C matrix and pass it to all workers
   *  @param A The A matrix
    * @param B The B matrix
    * @warnning call after @ref setConfig
   */
  void createABC(torch::Tensor A, torch::Tensor B);

  /**
* @brief run a parallel forward of A,B, and return C
* @return C=matA*matB
*  @warnning call after @ref createABC
*/
  torch::Tensor parallelForward();

  /**
  * @brief conducte the multithread AMM and return
  * @param A The A matrix
  * @param B The B matrix
  * @return The AMM(A,B)
  * @warnning call after @ref setConfig
  */
  torch::Tensor runAMM(torch::Tensor A, torch::Tensor B);

  /**
   * @brief get the elapsed time of multithread running
   * @return the elapsed time
   * @note Exclude the overhead of cleaning thread states such as loaded module
   */
  uint64_t getElapsedTime();

  /**
   * @brief append the running information of each thread to the result csv
   * @param ru The result csv to be appended
   */
  void appendThreadInfo(INTELLI::ConfigMapPtr ru);

  /**
   * @brief calculate metrics including the pef result for all threads used in the runner, and elapsed time, throughput..
   */
  void calculateMetrics();

  /**
   * @brief get metrics
   * @return metrics ConfigMapPtr
   */
  INTELLI::ConfigMapPtr getMetrics();

  /**
  * @brief to export the algorithm breakdown
    * @note only valid for c++ algo
  * @return the key-value table breakdown in ConfigMapPtr;
  */
  virtual INTELLI::ConfigMapPtr getBreakDown();
    };

} // LibAMM
/**
 * @}
 */
#endif //INTELLISTREAM_INCLUDE_PARALLELIZATION_BLOCKPARTITIONRUNNER_H_
