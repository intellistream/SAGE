/*! \file AbstractMeter.hpp*/
#ifndef ADB_INCLUDE_UTILS_AbstractMeter_HPP_
#define ADB_INCLUDE_UTILS_AbstractMeter_HPP_
//#include <Utils/Logger.hpp>
#include <stdio.h>
#include <stdlib.h>
#include <Utils/ConfigMap.hpp>
#include <Utils/IntelliLog.h>

#define METER_ERROR(n) INTELLI_ERROR(n)

#include <memory>

using namespace std;
namespace DIVERSE_METER {
/**
 *  @ingroup INTELLI_UTIL
 *  @{
* @defgroup INTELLI_UTIL_METER Energy Meter packs
* @{
 * This package is used for energy meter
*/
/**
 * @ingroup INTELLI_UTIL_METER
 * @class AbstractMeter Utils/Meters/AbstractMeter.hpp
 * @brief The abstract class for all meters
 * @note default behaviors:
 * - create
 * - call @ref setConfig() to config this meter
 * - (optional) call @ref testStaticPower() to automatically test the static power of a device or @ref setStaticPower to manually set the static power, if you want to exclude it
 * - call @ref startMeter() to start measurement
 * - (run your program)
 * - call @ref stopMeter() to stop measurement
 * - call @ref getE(), @ref getPeak(), etc to get the measurement resluts
 *
 */
class AbstractMeter {
 protected:
  /**
   * @brief static power of a system in W
   */
  double staticPower = 0;
  INTELLI::ConfigMapPtr cfg = nullptr;

 private:

 public:
  AbstractMeter(/* args */) {

  }
  //if exist in another name

  ~AbstractMeter() {

  }

  /**
  * @brief to set the configmap
   * @param cfg the config map
  */
  virtual void setConfig(INTELLI::ConfigMapPtr _cfg) {
    cfg = _cfg;
  }

  /**
   * @brief to manually set the static power
   * @param _sp
   */
  void setStaticPower(double _sp) {
    staticPower = _sp;
  }

  /**
   * @brief to test the static power of a system by sleeping
   * @param sleepingSecond The seconds for sleep
   */
  void testStaticPower(uint64_t sleepingSecond);

  /**
   * @brief to start the meter into some measuring tasks
   */
  virtual void startMeter() {

  }

  /**
  * @brief to stop the meter into some measuring tasks
  */
  virtual void stopMeter() {

  }
  //energy in J
  /**
 * @brief to get the energy in J, including static energy consumption of system
 */
  virtual double getE() {
    return 0.0;
  }

  /**
 * @brief to get the peak power in W, including static power of system
 */
  virtual double getPeak() {
    return 0.0;
  }

  virtual bool isValid() {
    return false;
  }

  /**
 * @brief to return the tested static power
   * return the @ref staticPower
 */
  double getStaticPower();

  /**
* @brief to return the static energy consumption of a system under several us
   * @param runningUs The time in us of a running
  * return the @ref staticPower
*/
  double getStaicEnergyConsumption(uint64_t runningUs);

};

typedef std::shared_ptr<DIVERSE_METER::AbstractMeter> AbstractMeterPtr;
/**
 * @}
 */
/**
 * @}
 */
}

#endif