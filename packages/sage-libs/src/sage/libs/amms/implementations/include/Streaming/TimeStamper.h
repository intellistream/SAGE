/*! \file TimerStamper.h*/
//
// Created by tony on 23/06/23.
//

#ifndef INTELLISTREAM_TIMESTAMPER_H
#define INTELLISTREAM_TIMESTAMPER_H

#include <stdint.h>
#include <Utils/MicroDataSet.hpp>
#include <memory>
#include <vector>
#include <Utils/ConfigMap.hpp>

namespace LibAMM {
/**
 * @ingroup LibAMM_STREAMING
 * @{
 *
 */
/**
* @class AMMTimeStamp Streaming/TimeStamper.h
* @brief The class to define timestamp in streaming
* @ingroup LibAMM_STREAMING
*/
class AMMTimeStamp {
 public:
  /**
   * @brief The time when the related event (to a row or a column) happen
   */
  uint64_t eventTime = 0;
  /**
   * @brief The time when the related event (to a row or a column) arrive to the system
   */
  uint64_t arrivalTime = 0;
  /**
   * @brief the time when the related event is fully processed
   */
  uint64_t processedTime = 0;

  AMMTimeStamp() {}

  AMMTimeStamp(uint64_t te, uint64_t ta, uint64_t tp) {
    eventTime = te;
    arrivalTime = ta;
    processedTime = tp;
  }

  ~AMMTimeStamp() {}
};

/**
 * @cite AMMTimeStampPtr
 * @brief The class to describe a shared pointer to @ref AMMTimeStamp
 */
typedef std::shared_ptr<class AMMTimeStamp> AMMTimeStampPtr;
/**
 * @cite newAMMTimeStampPtr
 * @brief (Macro) To creat a new @ref AMMTimeStamp under shared pointer.
 */
#define newAMMTimeStamp std::make_shared<LibAMM::AMMTimeStamp>

/**
* @class TimeStamper Streaming/TimeStamper.h
* @brief The basic class to generate time stamps
* @ingroup LibAMM_STREAMING
* @note require configs:
*  - eventRateTps U64 The real-world rate of spawn event, in Tuples/s
*  - streamingTupleCnt U64 The number of "streaming tuples", can be set to the #rows or #cols of a matrix
*  - timeStamper_zipfEvent, U64, whether or not using the zipf for event rate, default 0
*  - timeStamper_zipfEventFactor, Double, the zpf factor for event rate, default 0.1, should be 0~1
*  - staticDataSet, U64, 0 , whether or not treat a dataset as static
* @note  Default behavior
* - create
* - call @ref setSetSeed if you want different seed, default seed is 114514
* - call @ref setConfig to generate the timestamp under instructions
* - call @ref getTimeStamps to get the timestamp
*/
class TimeStamper {
 protected:
  INTELLI::ConfigMapPtr cfgGlobal;
  INTELLI::MicroDataSet md;
  uint64_t timeStamper_zipfEvent = 0;
  double timeStamper_zipfEventFactor = 0;
  uint64_t testSize;
  std::vector<uint64_t> eventS;
  std::vector<uint64_t> arrivalS;
  uint64_t eventRateTps = 0;
  uint64_t timeStepUs = 40;
  uint64_t seed = 114514;
  uint64_t staticDataSet=0;
  /**
*
*  @brief generate the vector of event
*/
  void generateEvent();

  /**
   * @brief  generate the vector of arrival
   * @note As we do not consider OoO now, this is a dummy function
   */
  void generateArrival();

  /**
   * @brief generate the final result of s and r
   */
  void generateFinal();

  std::vector<LibAMM::AMMTimeStampPtr> constructTimeStamps(
      std::vector<uint64_t> eventS,
      std::vector<uint64_t> arrivalS);

 public:
  TimeStamper() {}

  ~TimeStamper() {}

  std::vector<LibAMM::AMMTimeStampPtr> myTs;
  /**
   * @brief to set the seed of this timestamer
   * @param _seed
   */
  void setSeed(uint64_t _seed) {
    seed = _seed;
  }
  /**
* @brief Set the GLOBAL config map related to this TimerStamper
* @param cfg The config map
 * @return bool whether the config is successfully set
*/
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);

  /**
  * @brief get the vector of R tuple
  * @return the vector
  */
  virtual std::vector<LibAMM::AMMTimeStampPtr> getTimeStamps() {
    return myTs;
  }
};
/**
 * @}
 */
} // LibAMM

#endif //INTELLISTREAM_TIMESTAMPER_H
