//
// Created by tony on 06/01/24.
//
#include <Utils/IntelliTimeStampGenerator.h>

bool INTELLI::IntelliTimeStampGenerator::setConfig(INTELLI::ConfigMapPtr cfg) {
  cfgGlobal = cfg;
  eventRateTps = cfg->tryI64("eventRateTps", 100, true);
  timeStepUs = cfg->tryI64("timeStepUs", 100, true);
  timeStamper_zipfEvent = cfg->tryI64("timeStamper_zipfEvent", 0, true);
  timeStamper_zipfEventFactor = cfg->tryDouble("timeStamper_zipfEventFactor", 0.1, true);
  testSize = cfg->tryI64("streamingTupleCnt", 0, true);
  staticDataSet = cfg->tryI64("staticDataSet", 0, true);
  md.setSeed(seed);
  generateEvent();
  generateArrival();
  generateFinal();
  return true;
}

void INTELLI::IntelliTimeStampGenerator::generateEvent() {
  uint64_t maxTime = testSize * 1000 * 1000 / eventRateTps;
  if (staticDataSet) {
    eventS.resize(testSize);
    eventS.assign(testSize, 0);// Create vector of size 'size' with all elements set to 0
  } else if (timeStamper_zipfEvent) {
    INTELLI_INFO("Use zipf for event time, factor=" + to_string(timeStamper_zipfEventFactor));
    INTELLI_INFO("maxTime=" + to_string(maxTime) + "us" + "rate=" + to_string(eventRateTps) + "K, cnt=" +
        to_string(testSize));
    eventS =
        md.genZipfTimeStamp<uint64_t>(testSize, maxTime,
                                      timeStamper_zipfEventFactor);
  } else {
    // uint64_t tsGrow = 1000 * timeStepUs / eventRateKTps;
    eventS = md.genSmoothTimeStamp(testSize, maxTime);
  }
  INTELLI_INFO("Finish the generation of event time");
}

void INTELLI::IntelliTimeStampGenerator::generateArrival() {

  INTELLI_INFO("Finish the generation of arrival time");
}

std::vector<INTELLI::IntelliTimeStampPtr> INTELLI::IntelliTimeStampGenerator::constructTimeStamps(
    std::vector<uint64_t> _eventS,
    std::vector<uint64_t> _arrivalS) {
  size_t len = _eventS.size();
  std::vector<INTELLI::IntelliTimeStampPtr> ru = std::vector<INTELLI::IntelliTimeStampPtr>(len);
  for (size_t i = 0; i < len; i++) {
    ru[i] = newIntelliTimeStamp(_eventS[i], _arrivalS[i], 0);
  }
  return ru;
}

void INTELLI::IntelliTimeStampGenerator::generateFinal() {
  myTs = constructTimeStamps(eventS, eventS);
}
std::vector<INTELLI::IntelliTimeStampPtr> INTELLI::IntelliTimeStampGenerator::getTimeStamps() {
  return myTs;
}
