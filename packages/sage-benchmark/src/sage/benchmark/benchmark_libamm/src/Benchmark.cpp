/*! \file Benchmark.h*/

/**
 * @brief This is the main entry point of the entire program.
 * We use this as the entry point for benchmarking.
 */
#include <LibAMM.h>
#include <Utils/UtilityFunctions.h>
#include <include/papi_config.h>
#include <Utils/ThreadPerf.hpp>
#if LibAMM_PAPI == 1
#include <Utils/ThreadPerfPAPI.hpp>
#endif
using namespace std;
using namespace INTELLI;
using namespace torch;
using namespace DIVERSE_METER;

void streamingTest(std::string configName) {
  ConfigMapPtr cfg = newConfigMap();
  cfg->fromFile(configName);
  LibAMM::MatrixLoaderTable mLoaderTable;
  uint64_t sketchDimension;
  ConfigMapPtr breakDownResult = nullptr;
  sketchDimension = cfg->tryU64("sketchDimension", 50, true);
  uint64_t coreBind = cfg->tryU64("coreBind", 0, true);
  //uint64_t usingMeter = cfg->tryU64("usingMeter", 0, true);
  std::string meterTag = cfg->tryString("meterTag", "intelMsr", true);
  //uint64_t useCPP = cfg->tryU64("useCPP", 0, true);
  UtilityFunctions::bind2Core((int) coreBind);

 // uint64_t threads = cfg->tryU64("threads", 1, true);
  uint64_t streamingTwoMatrixes = cfg->tryU64("streamingTwoMatrixes", 0, true);
  INTELLI_INFO("Place me at core" + to_string(coreBind));
  INTELLI_INFO("with sketch" + to_string(sketchDimension));
  std::string matrixLoaderTag = cfg->tryString("matrixLoaderTag", "random", true);
  auto matLoaderPtr = mLoaderTable.findMatrixLoader(matrixLoaderTag);
  assert(matLoaderPtr);
  matLoaderPtr->setConfig(cfg);
  auto A = matLoaderPtr->getA();
  auto B = matLoaderPtr->getB();
  auto ACopy=A.clone();
  auto BCopy=B.clone();
  torch::Tensor C;
  LibAMM::SingleThreadStreamer ss;
  ss.setConfig(cfg);
  ss.prepareRun(A, B);
  torch::Tensor ssC;
  ThreadPerfPtr pef;
#if LibAMM_PAPI == 1
  if (cfg->tryU64("usePAPI", 1)) {
    pef = newThreadPerfPAPI(-1);
  } else {
    pef = newThreadPerf(-1);
  }
#else
  pef=newThreadPerf(-1);
#endif
  pef->initEventsByCfg(cfg);
  torch::manual_seed(999);
  pef->start();
  if (streamingTwoMatrixes) {
    INTELLI_INFO("Both A,B will be streaming");
    ssC = ss.streamingAmm2S(A, B, sketchDimension);
  } else {
    INTELLI_INFO("Only A will be streaming");
    ssC = ss.streamingAmm(A, B, sketchDimension);
  }
  pef->end();
  auto resultCsv = pef->resultToConfigMap();
  resultCsv->edit("throughput", (double) ss.getThroughput());
  resultCsv->edit("throughputByElements", (double) (ss.getThroughput() * A.size(1)));
  resultCsv->edit("95%latency", (double) ss.getLatencyPercentage(0.95));
  INTELLI_WARNING("evaluating the error, may takes some time");
  torch::Tensor rawC = torch::matmul(ACopy, BCopy);
  double froError = INTELLI::UtilityFunctions::relativeFrobeniusNorm(rawC, ssC);
  double froBNormal = B.norm().item<double>();
  double errorBoundRatio = froError / froBNormal;
  INTELLI_INFO("B normal is " + to_string(froBNormal));
  resultCsv->edit("froError", (double) froError);
  resultCsv->edit("errorBoundRatio", (double) errorBoundRatio);
  resultCsv->toFile("result_streaming.csv");
  INTELLI_INFO("Done. here is overall result");
  std::cout << resultCsv->toString() << endl;
  return;
}

void runSingleThreadTest(std::string configName) {
  MeterTable meterTable;
  AbstractMeterPtr eMeter = nullptr;
  ConfigMapPtr cfg = newConfigMap();
  cfg->fromFile(configName);
  LibAMM::MatrixLoaderTable mLoaderTable;
  uint64_t sketchDimension;
  ConfigMapPtr breakDownResult = nullptr;
  INTELLI_INFO("cppAlgoTag: "+cfg->tryString("cppAlgoTag", "mm", true));
  uint64_t isStreaming = cfg->tryU64("isStreaming", 0, true);
  if (isStreaming) {
    streamingTest(configName);
    return;
  }
  sketchDimension = cfg->tryU64("sketchDimension", 50, true);
  uint64_t coreBind = cfg->tryU64("coreBind", 0, true);
  uint64_t usingMeter = cfg->tryU64("usingMeter", 0, true);
  std::string meterTag = cfg->tryString("meterTag", "intelMsr", true);
  uint64_t useCPP = cfg->tryU64("useCPP", 0, true);
  uint64_t forceMP = cfg->tryU64("forceMP", 0, true);
  if (usingMeter) {
    eMeter = meterTable.findMeter(meterTag);
    if (eMeter != nullptr) {
      eMeter->setConfig(cfg);
      double staticPower = cfg->tryDouble("staticPower", 0.0, false);
      if (staticPower == 0.0) {
        eMeter->testStaticPower(2);
      } else {
        INTELLI_INFO("use pre-defined static power");
        eMeter->setStaticPower(staticPower);
      }
      INTELLI_INFO("static power is " + to_string(eMeter->getStaticPower()) + " W");
    } else {
      INTELLI_ERROR("No meter found: " + meterTag);
    }

  }
  UtilityFunctions::bind2Core((int) coreBind);
  //torch::set_num_threads(1);
  std::string ptFile = cfg->tryString("ptFile", "torchscripts/FDAMM.pt", true);

  //uint64_t customResultName = cfg->tryU64("customResultName", 0, true);
  INTELLI_INFO("Place me at core" + to_string(coreBind));
  INTELLI_INFO("with sketch" + to_string(sketchDimension));
  torch::jit::script::Module module;
  INTELLI_INFO("Try pt file " + ptFile);
  //module = torch::jit::load(ptFile);
  std::string matrixLoaderTag = cfg->tryString("matrixLoaderTag", "random", true);
  auto matLoaderPtr = mLoaderTable.findMatrixLoader(matrixLoaderTag);
  assert(matLoaderPtr);
  matLoaderPtr->setConfig(cfg);
  auto A = matLoaderPtr->getA();
  auto B = matLoaderPtr->getB();
  torch::Tensor C;

  //555
  /*torch::manual_seed(114514);
//555
auto A = torch::rand({(long) aRow, (long) aCol});
auto B = torch::rand({(long) aCol, (long) bCol});*/
  INTELLI_INFO("Generation done, conducting...");
  uint64_t threads = cfg->tryU64("threads", 0, true);
  ThreadPerfPtr pef;
#if LibAMM_PAPI == 1
  if (cfg->tryU64("usePAPI", 1)) {
    pef = newThreadPerfPAPI(-1);
  } else {
    pef = newThreadPerf(-1);
  }
#else
  pef=newThreadPerf(-1);
#endif
  pef->initEventsByCfg(cfg);
  LibAMM::BlockPartitionRunner br;
  if (threads > 1 || forceMP) {
    INTELLI_WARNING("use multithread");
    br.setConfig(cfg);
    br.createABC(A, B);
    if (eMeter != nullptr) {
      eMeter->startMeter();
    }
    pef->start();
    C = br.parallelForward();
    pef->end();
    if (eMeter != nullptr) {
      eMeter->stopMeter();
    }
    breakDownResult = br.getBreakDown();
  } else {
    LibAMM::CPPAlgoTable cppAlgoTable;
    std::string cppAlgoTag = cfg->tryString("cppAlgoTag", "mm", true);
    LibAMM::AbstractCPPAlgoPtr cppAlgoPtr = cppAlgoTable.findCppAlgo(cppAlgoTag);
    cppAlgoPtr->setConfig(cfg);
    INTELLI_WARNING("single thread, algo " + cppAlgoTag);
    if (eMeter != nullptr) {
      eMeter->startMeter();
    }
    pef->start();
    if (useCPP && cppAlgoPtr) {
      INTELLI_WARNING("this is pure c++");
      C = cppAlgoPtr->amm(A, B, sketchDimension);
    } else {
      C = module.forward({A, B, (long) sketchDimension}).toTensor();
    }
    pef->end();
    if (eMeter != nullptr) {
      eMeter->stopMeter();
    }
    if (useCPP && cppAlgoPtr) {
      breakDownResult = cppAlgoPtr->getBreakDown();
    }
  }

  std::string ruName = "default";

  auto resultCsv = pef->resultToConfigMap();
  if (eMeter != nullptr) {
    eMeter->stopMeter();
    double energyConsumption = eMeter->getE();
    double staticEnergyConsumption = eMeter->getStaicEnergyConsumption(
        resultCsv->tryU64("perfElapsedTime", 0, false));
    double pureEnergy = energyConsumption - staticEnergyConsumption;
    resultCsv->edit("energyAll", (double) energyConsumption);
    resultCsv->edit("energyOnlyMe", (double) pureEnergy);
  }
  if (threads > 1 || forceMP) {
    INTELLI_WARNING("consider multithread elapsed time");
    resultCsv->edit("perfElapsedTime", (uint64_t) br.getElapsedTime());
    br.appendThreadInfo(resultCsv);
  }
  // error
  INTELLI_WARNING("evaluating the error, may takes some time");
  torch::Tensor realC = torch::matmul(A, B);
  double froError = INTELLI::UtilityFunctions::relativeFrobeniusNorm(realC, C);
  double froBNormal = B.norm().item<double>();
  double errorBoundRatio = froError / froBNormal;
  INTELLI_INFO("B normal is " + to_string(froBNormal));
  resultCsv->edit("froError", (double) froError);
  resultCsv->edit("errorBoundRatio", (double) errorBoundRatio);
  resultCsv->toFile(ruName + ".csv");
  INTELLI_INFO("Done. here is overall result");
  std::cout << resultCsv->toString() << endl;
  if (breakDownResult) {
    INTELLI_INFO("I also have some break down result");
    std::cout << breakDownResult->toString() << endl;
    breakDownResult->toFile(ruName + "_breakdown.csv");
  }

}

int main(int argc, char **argv) {
  string configName, outPrefix = "";
  if (argc >= 2) {
    configName += argv[1];
  } else {
    configName = "config.csv";
  }
  runSingleThreadTest(configName);
  return 0;
}
