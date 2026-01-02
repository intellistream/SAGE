#include <Utils/Meters/MeterTable.h>
#include <Utils/Meters/EspMeterUart/EspMeterUart.hpp>
#include <Utils/Meters/IntelMeter/IntelMeter.hpp>

namespace DIVERSE_METER {
/**
 * @note revise me if you need new loader
 */
DIVERSE_METER::MeterTable::MeterTable() {
  meterMap["espUart"] = newEspMeterUart();
  meterMap["intelMsr"] = newIntelMeter();
}

}
