/*! \file SingleThreadStamper.h*/
//
// Created by tony on 23/06/23.
//

#ifndef INTELLISTREAM_SINGLETHREADSTREAMER_H
#define INTELLISTREAM_SINGLETHREADSTREAMER_H

#include <Streaming/TimeStamper.h>
#include <CPPAlgos/CPPAlgoTable.h>
#include <Parallelization/BlockPartitionRunner.h>

namespace LibAMM {

/**
 * @ingroup LibAMM_STREAMING
 * @{
 *
 */
/**
  * @class SingleThreadStreamer Streaming/SingleThreadStreamer.h
  * @brief The class to run streaming amm under single thread, let each row of A coming in a streaming manner
  * @ingroup LibAMM_STREAMING
  * @note  Default behavior
  * - create
  * - call @ref setConfig, this will also determine how to generate time stamp and config will be passed to @ref TimeStamper
  * - run streaming amm:
    * - call @ref streamingAmm, if only A matrix will be streamed
    * - call @ref streamingAmm2S, if both A and B will be streamed
  * - call @ref getThroughput, and @ref getLatencyPercentage to get the streaming performance
  * @note configs
  * fullLazy U64, 0 whether or not make everything conducted under lazy mode, will force batchsize to the whole rows of A
  * batchSize, U64,1
  * staticDataSet, U64, 0 , whether or not treat a dataset as static
  */
class SingleThreadStreamer {
 protected:
  INTELLI::ConfigMapPtr cfgGlobal;
  LibAMM::CPPAlgoTable cppAlgoTable;
  uint64_t batchSize = 1;
  LibAMM::AbstractCPPAlgoPtr cppAlgoPtr = nullptr;
  LibAMM::TensorPtr matC = nullptr;
  double throughput = 0.0;
  int coreBind;
  INTELLI::ConfigMapPtr metrics = newConfigMap();
  uint64_t fullLazy = 0;
  uint64_t  staticDataSet=0;
 public:
  SingleThreadStreamer() {}

  ~SingleThreadStreamer() {}

  /**
   * @brief the timestamps to trace the streaming process
   */
  std::vector<LibAMM::AMMTimeStampPtr> myTs;
  /**
  * @brief the additional timestamps to trace the streaming process, if B is also stream
  */
  std::vector<LibAMM::AMMTimeStampPtr> myTsB;

  /**
* @brief Set the GLOBAL config map related to this TimerStamper
* @param cfg The config map
* @return bool whether the config is successfully set
*/
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);
  /**
   * @brief create the time stamps and other datastructures for streaming rn
   * @param A
   * @return
   */
  virtual bool prepareRun(torch::Tensor A, torch::Tensor B);
  /**
* @brief To run a streaming Amm, assuming the rows of A coming in a streaming manner and B is fixed
*  @param A The A matrix
* @param B The B matrix
* @return bool whether the config is successfully set
*/
  virtual torch::Tensor streamingAmm(torch::Tensor A, torch::Tensor B, uint64_t sketchSize = 1);
  /**
* @brief To run a streaming Amm, assuming the rows of A coming in a streaming manner and the cols of B coming in a streaming manner
*  @param A The A matrix
* @param B The B matrix
* @return bool whether the config is successfully set
*/
  virtual torch::Tensor streamingAmm2S(torch::Tensor A, torch::Tensor B, uint64_t sketchSize = 1);

  /**
   * @brief to get the throughput of last streaming process, the unit is rows/second
   * @return the throughput
   */
  double getThroughput() {
    return throughput;
  }

  /**
   * @brief to get the latency within some fraction, such as 0.95
   * @param fraction the 0~1 fraction
   * @return the latency in us
   */
  double getLatencyPercentage(double fraction);

  /**
   * @brief get metrics (including the pef result for all threads used in the runner, and elapsed time, throughput..)
   * @return metrics ConfigMapPtr
   */
  INTELLI::ConfigMapPtr getMetrics(){
    return metrics;
  }

};
/**
 * @}
 */
} // LibAMM

#endif //INTELLISTREAM_SINGLETHREADSTREAMER_H
