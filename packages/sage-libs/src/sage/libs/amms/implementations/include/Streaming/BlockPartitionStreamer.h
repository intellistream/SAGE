//
// Created by haolan on 27/6/23.
//

#ifndef INTELLISTREAM_BLOCKPARTITIONSTREAMER_H
#define INTELLISTREAM_BLOCKPARTITIONSTREAMER_H
#include <Streaming/TimeStamper.h>
#include <CPPAlgos/CPPAlgoTable.h>
#include <Parallelization/BlockPartitionRunner.h>
#include <Utils/BS_thread_pool.hpp>

namespace LibAMM {

/**
 * @ingroup LibAMM_STREAMING
 * @{
 *
 */
/**
  * @class BlockPartitionStreamer Streaming/BlockPartitionStreamer.h
  * @brief The class to run streaming amm under block partition scheme, let rows of A coming in a streaming manner, all of which are partitioned with BlockPartitionRunner
  * @ingroup LibAMM_STREAMING
  * @note  Default behavior
  * - create
  * - call @ref setConfig, this will also determine how to generate time stamp and config will be passed to @ref TimeStamper
  * - run streaming amm:
    * - call @ref streamingAmm, if only A matrix will be streamed
    * - call @ref streamingAmm2S, if both A and B will be streamed
  * - call @ref getThroughput, and @ref getLatencyPercentage to get the streaming performance
  */
class BlockPartitionStreamer {
 protected:
  INTELLI::ConfigMapPtr cfgGlobal;
  LibAMM::CPPAlgoTable cppAlgoTable;
  uint64_t batchSize = 1;
  LibAMM::AbstractCPPAlgoPtr cppAlgoPtr = nullptr;
  LibAMM::TensorPtr matC = nullptr;
  double throughput = 0.0;
  uint64_t threads = 1;
  int coreBind;
  INTELLI::ConfigMapPtr metrics = newConfigMap();
 public:
  BlockPartitionStreamer() {}

  ~BlockPartitionStreamer() {}

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

#endif //INTELLISTREAM_BLOCKPARTITIONSTREAMER_H
