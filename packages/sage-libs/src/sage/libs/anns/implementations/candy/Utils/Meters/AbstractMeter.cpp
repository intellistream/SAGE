#include <Utils/Meters/AbstractMeter.hpp>

void DIVERSE_METER::AbstractMeter::testStaticPower(uint64_t sleepingSecond) {
  startMeter();
  sleep(sleepingSecond);
  stopMeter();
  staticPower = getE();
  staticPower = staticPower / sleepingSecond;
}

double DIVERSE_METER::AbstractMeter::getStaicEnergyConsumption(uint64_t runningUs) {
  double t = runningUs;
  t = t * staticPower / 1e6;
  return t;
}

double DIVERSE_METER::AbstractMeter::getStaticPower() {
  return staticPower;
}