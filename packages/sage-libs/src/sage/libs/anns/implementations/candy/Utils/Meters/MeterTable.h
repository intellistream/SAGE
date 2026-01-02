/*! \file MeterTable.hpp*/
#ifndef INTELLISTREAM_UTILS_METERTABLE_H_
#define INTELLISTREAM_UTILS_METERTABLE_H_

#include <Utils/Meters/AbstractMeter.hpp>
#include <map>

namespace DIVERSE_METER {

/**
 * @ingroup INTELLI_UTIL_METER
 * @class MeterTable Utils/Meter/MeterTable.h
 * @brief The table class to index all meters
 * @note  Default behavior
* - create
* - (optional) call @ref registerNewMeter for new meter
* - find a loader by @ref findMeter using its tag
 * @note default tags
 * - espUart @ref EspMeterUart
 * - intelMsr @ref IntelMeter
 */
class MeterTable {
 protected:
  std::map<std::string, DIVERSE_METER::AbstractMeterPtr> meterMap;
 public:
  /**
   * @brief The constructing function
   * @note  If new MatrixLoader wants to be included by default, please revise the following in *.cpp
   */
  MeterTable();

  ~MeterTable() {
  }

  /**
    * @brief To register a new meter
    * @param onew The new operator
    * @param tag THe name tag
    */
  void registerNewMeter(DIVERSE_METER::AbstractMeterPtr dnew, std::string tag) {
    meterMap[tag] = dnew;
  }

  /**
   * @brief find a meter in the table according to its name
   * @param name The nameTag of loader
   * @return The Meter, nullptr if not found
   */
  DIVERSE_METER::AbstractMeterPtr findMeter(std::string name) {
    if (meterMap.count(name)) {
      return meterMap[name];
    }
    return nullptr;
  }

  /**
 * @ingroup INTELLI_UTIL_METER
 * @typedef MeterTablePtr
 * @brief The class to describe a shared pointer to @ref MeterTable

 */
  typedef std::shared_ptr<class DIVERSE_METER::MeterTable> MeterTablePtr;
/**
 * @ingroup INTELLI_UTIL_METER
 * @def newMeterTable
 * @brief (Macro) To creat a new @ref  MeterTable under shared pointer.
 */
#define newMeterTable std::make_shared<DIVERSE_METER::MeterTable>
};
}
/**
 * @}
 */



#endif //INTELLISTREAM_INCLUDE_MATRIXLOADER_MeterTable_H_
