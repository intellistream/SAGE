#ifndef ADB_INCLUDE_UTILS_IntelMeter_HPP_
#define ADB_INCLUDE_UTILS_IntelMeter_HPP_

#include <Utils/Meters/AbstractMeter.hpp>
#include <vector>
#include <unistd.h>
#include <stdint.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <sys/mman.h>
#include <stdio.h>
#include <stdint.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <signal.h>

using namespace std;
namespace DIVERSE_METER {
typedef struct rapl_power_unit {
  double PU;       //power units
  double ESU;      //energy status units
  double TU;       //time units
} rapl_power_unit;
/*class:IntelMeter
description:the entity of intel msr-based power meter, providing all function including:
E,PeakPower
note: the meter and bus rate is about 1ms, you must run on intel x64 with modprobe msr and cpuid
date:20211202
*/

/**
 * @ingroup INTELLI_UTIL_METER
 * @class IntelMeter Utils/Meters/IntelMeter.hpp
 * @brief the entity of intel msr-based power meter, may be not support for some newer architectures
 * - create
 * - call @ref setConfig() to config this meter
 * - (optional) call @ref testStaticPower() to test the static power of a device, if you want to exclude it
 * - call @ref startMeter() to start measurement
 * - (run your program)
 * - call @ref stopMeter() to stop measurement
 * - call @ref getE(), @ref getPeak(), etc to get the measurement resluts
 * @warning: only works for some x64 machines
 * @note: no peak power support, tag is "intelMsr"
 */
class IntelMeter : public AbstractMeter {
 private:
  int devFd;

  uint64_t rdmsr(int cpu, uint32_t reg);

  rapl_power_unit get_rapl_power_unit();

  double eSum = 0;

  uint32_t maxCpu = 0;
  vector<int> cpus;
  vector<double> st;
  vector<double> en;
  vector<double> count;
  rapl_power_unit power_units;
 public:
  /**
* @brief to set the configmap
* @param cfg the config map
*/
  virtual void setConfig(INTELLI::ConfigMapPtr _cfg);

  IntelMeter(/* args */);

  ~IntelMeter();

  void startMeter();

  void stopMeter();

  //energy in J
  double getE();
  //peak power in mW
  // double getPeak();

  bool isValid() {
    return (devFd != -1);
  }
};

typedef std::shared_ptr<DIVERSE_METER::IntelMeter> IntelMeterPtr;
#define newIntelMeter() std::make_shared<IntelMeter>();
}

#endif