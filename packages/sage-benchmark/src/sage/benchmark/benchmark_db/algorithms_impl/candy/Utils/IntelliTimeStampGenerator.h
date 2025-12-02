/*! \file IntelliTimeStampGenerator.h*/
//
// Created by tony on 06/01/24.
//

#ifndef _UTILS_INTELLITIMESTAMPGENERATOR_H_
#define _UTILS_INTELLITIMESTAMPGENERATOR_H_
#pragma once
#include <stdint.h>
#include <vector>
#include <memory>
#include <Utils/ConfigMap.hpp>
#include <Utils/MicroDataSet.hpp>
/**
 *  @ingroup INTELLI_UTIL
 *  @{
* @defgroup INTELLI_UTIL_TIMESTAMP time stamps
* @{
 * This package is used for basic time stamp functions
*/
namespace INTELLI {
/**
* @class IntelliTimeStamp Utils/IntelliTimeStampGenerator.h
* @brief The class to define a timestamp
* @ingroup INTELLI_UTIL_TIMESTAMP
*/
class IntelliTimeStamp {
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

  IntelliTimeStamp() {}

  IntelliTimeStamp(uint64_t te, uint64_t ta, uint64_t tp) {
    eventTime = te;
    arrivalTime = ta;
    processedTime = tp;
  }

  ~IntelliTimeStamp() {}
};

/**
 * @ingroup INTELLI_UTIL_TIMESTAMP
 * @typedef IntelliTimeStampPtr
 * @brief The class to describe a shared pointer to @ref IntelliTimeStamp
 */
typedef std::shared_ptr<INTELLI::IntelliTimeStamp> IntelliTimeStampPtr;
/**
 * @ingroup INTELLI_UTIL_TIMESTAMP
 * @def newIntelliTimeStamp
 * @brief (Macro) To creat a new @ref IntelliTimeStamp under shared pointer.
 */
#define newIntelliTimeStamp std::make_shared<INTELLI::IntelliTimeStamp>

/**
* @class IntelliTimeStampGenerator  Utils/IntelliTimeStampGenerator.h
* @brief The basic class to generate time stamps
* @ingroup INTELLI_UTIL_TIMESTAMP
* @note require configs:
*  - eventRateTps I64 The real-world rate of spawn event, in Tuples/s
*  - streamingTupleCnt I64 The number of "streaming tuples", can be set to the #rows or #cols of a matrix
*  - timeStamper_zipfEvent, I64, whether or not using the zipf for event rate, default 0
*  - timeStamper_zipfEventFactor, Double, the zpf factor for event rate, default 0.1, should be 0~1
*  - staticDataSet, I64, 0 , whether or not treat a dataset as static
* @note  Default behavior
* - create
* - call @ref setConfig to generate the timestamp under instructions
* - call @ref getTimeStamps to get the timestamp
*/
class IntelliTimeStampGenerator {
 protected:
  INTELLI::ConfigMapPtr cfgGlobal;
  INTELLI::MicroDataSet md;
  int64_t timeStamper_zipfEvent = 0;
  double timeStamper_zipfEventFactor = 0;
  int64_t testSize;
  std::vector<uint64_t> eventS;
  std::vector<uint64_t> arrivalS;
  int64_t eventRateTps = 0;
  int64_t timeStepUs = 40;
  int64_t seed = 114514;
  int64_t staticDataSet = 0;
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

  std::vector<INTELLI::IntelliTimeStampPtr> constructTimeStamps(
      std::vector<uint64_t> eventS,
      std::vector<uint64_t> arrivalS);

 public:
  IntelliTimeStampGenerator() {}

  ~IntelliTimeStampGenerator() {}

  std::vector<INTELLI::IntelliTimeStampPtr> myTs;

  /**
* @brief Set the GLOBAL config map related to this TimerStamper
* @param cfg The config map
 * @return bool whether the config is successfully set
*/
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);

  /**
  * @brief get the vector of time stamps
  * @return the vector
  */
  virtual std::vector<INTELLI::IntelliTimeStampPtr> getTimeStamps();
};

}

/**
 * @}
 */
/**
 * @}
 */

#endif //CANDY_INCLUDE_UTILS_INTELLITIMESTAMPGENERATOR_H_
