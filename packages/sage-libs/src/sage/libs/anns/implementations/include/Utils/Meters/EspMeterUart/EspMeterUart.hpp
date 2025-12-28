/*! \file EspMeterUart.hpp*/
#ifndef ADB_INCLUDE_UTILS_EspMeterUartUARY_HPP_
#define ADB_INCLUDE_UTILS_EspMeterUartUART_HPP_
//#include <Utils/Logger.hpp>

#include <Utils/Meters/AbstractMeter.hpp>
//#include <Utils/UtilityFunctions.hpp>
using namespace std;
namespace DIVERSE_METER {

/**
 * @ingroup INTELLI_UTIL_METER
 * @class EspMeterUart Utils/Meters/EspMeterUart.hpp
 * @brief the entity of an esp32s2-based power meter, connected by uart 115200
 * @note default behaviors:
 * - create
 * - call @ref setConfig() to config this meter
 * - (optional) call @ref testStaticPower() to test the static power of a device, if you want to exclude it
 * - call @ref startMeter() to start measurement
 * - (run your program)
 * - call @ref stopMeter() to stop measurement
 * - call @ref getE(), @ref getPeak(), etc to get the measurement resluts
 * @note config parameters:
 * - meterAddress, String, The file system path of meter, default "/dev/ttyUSB0";
 * @note tag is "espUart"
 */
class EspMeterUart : public AbstractMeter {
 private:
  int devFd = -1;
  /**
   * @brief The file system path of meter
   */
  std::string meterAddress = "/dev/ttyUSB0";

  void openUartDev();
  // uint64_t accessEsp32(uint64_t cmd);
 public:
  EspMeterUart(/* args */);

  ~EspMeterUart();

  /**
 * @brief to set the configmap
  * @param cfg the config map
 */
  virtual void setConfig(INTELLI::ConfigMapPtr _cfg);

  /**
    * @brief to start the meter into some measuring tasks
    */
  void startMeter();

  /**
  * @brief to stop the meter into some measuring tasks
  */
  void stopMeter();

  /**
* @brief to get the energy in J, including static energy consumption of system
*/
  double getE();
  //peak power in mW
  /**
 * @brief to get the peak power in W, including static power of system
 */
  double getPeak();

  bool isValid() {
    return (devFd != -1);
  }
};

typedef std::shared_ptr<DIVERSE_METER::EspMeterUart> EspMeterUartPtr;
#define newEspMeterUart() std::make_shared<EspMeterUart>();
}

#endif