//
// Created by tony on 23/06/23.
//

#include <Streaming/TimeStamper.h>
#include <Utils/IntelliLog.h>

bool LibAMM::TimeStamper::setConfig(INTELLI::ConfigMapPtr cfg) {
  cfgGlobal = cfg;
  eventRateTps = cfg->tryU64("eventRateTps", 100, true);
  timeStepUs = cfg->tryU64("timeStepUs", 100, true);
  timeStamper_zipfEvent = cfg->tryU64("timeStamper_zipfEvent", 0, true);
  timeStamper_zipfEventFactor = cfg->tryDouble("timeStamper_zipfEventFactor", 0.1, true);
  testSize = cfg->tryU64("streamingTupleCnt", 0, true);
  staticDataSet = cfg->tryU64("staticDataSet",0,true);
  md.setSeed(seed);
  generateEvent();
  generateArrival();
  generateFinal();
  return true;
}

void LibAMM::TimeStamper::generateEvent() {
  uint64_t maxTime = testSize * 1000 * 1000 / eventRateTps;
  if(staticDataSet)
  { eventS.resize(testSize);
    eventS.assign(testSize,0);// Create vector of size 'size' with all elements set to 0
  }
  else if (timeStamper_zipfEvent) {
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

void LibAMM::TimeStamper::generateArrival() {

  INTELLI_INFO("Finish the generation of arrival time");
}

std::vector<LibAMM::AMMTimeStampPtr> LibAMM::TimeStamper::constructTimeStamps(
    std::vector<uint64_t> _eventS,
    std::vector<uint64_t> _arrivalS) {
  size_t len = _eventS.size();
  std::vector<LibAMM::AMMTimeStampPtr> ru = std::vector<LibAMM::AMMTimeStampPtr>(len);
  for (size_t i = 0; i < len; i++) {
    ru[i] = newAMMTimeStamp(_eventS[i], _arrivalS[i], 0);
  }
  return ru;
}

void LibAMM::TimeStamper::generateFinal() {
  myTs = constructTimeStamps(eventS, eventS);
}
