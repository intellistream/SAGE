//
// Created by tony on 27/11/23.
//
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

float qcdMSE(const torch::Tensor& A, const torch::Tensor& B) {
    // Compute the square difference
    auto A2=torch::pow(A, 2);

    auto B2=torch::pow(B, 2);

    torch::Tensor square_difference = (A2-B2)/A2;
    // Compute the mean
    torch::Tensor mean_square_difference = torch::mean(square_difference);

    // Return as a float
    return std::abs(mean_square_difference.item<float>());
}
class QCDPairs
{
private:

    /* data */
public:
    torch::Tensor U,Ut;
    uint64_t prepareTime;
    QCDPairs(/* args */){}
    ~QCDPairs(){}
    void genPairs(torch::Tensor qcdMat,double sigma);

};
void QCDPairs::genPairs(torch::Tensor qcd_matrix,double alpha_real)
{    torch::manual_seed(123);

      auto A_size = qcd_matrix.sizes();
    int64_t size=A_size[0];
    torch::Tensor a_real = torch::randn({size, size});
      // Compute the real-valued displacement operator matrix U
    U = std::cos(alpha_real) * torch::exp(-0.5 * (a_real + a_real.t()));
    Ut=U.t();
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

  sketchDimension = cfg->tryU64("sketchDimension", 50, true);
  uint64_t coreBind = cfg->tryU64("coreBind", 0, true);
  uint64_t usingMeter = cfg->tryU64("usingMeter", 0, true);
  std::string meterTag = cfg->tryString("meterTag", "intelMsr", true);
  uint64_t useCPP = cfg->tryU64("useCPP", 0, true);
  //uint64_t forceMP = cfg->tryU64("forceMP", 0, true);
  QCDPairs qcdp;
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

  std::string matrixLoaderTag = cfg->tryString("matrixLoaderTag", "random", true);
  auto matLoaderPtr = mLoaderTable.findMatrixLoader(matrixLoaderTag);
  assert(matLoaderPtr);
  matLoaderPtr->setConfig(cfg);
  qcdp.genPairs(matLoaderPtr->getA(),0.5);
  INTELLI_INFO("Pre-amm time for QCD ="+to_string(qcdp.prepareTime));
  auto U = qcdp.U;
  auto Ut = qcdp.Ut;
  auto A=matLoaderPtr->getA();
  torch::Tensor C,C2;

  //555
  /*torch::manual_seed(114514);
//555
auto A = torch::rand({(long) aRow, (long) aCol});
auto B = torch::rand({(long) aCol, (long) bCol});*/
  INTELLI_INFO("Generation done, conducting...");
  //uint64_t threads = cfg->tryU64("threads", 0, true);
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
  LibAMM::BlockPartitionRunner br,br2;

  LibAMM::CPPAlgoTable cppAlgoTable;
  std::string cppAlgoTag = cfg->tryString("cppAlgoTag", "mm", true);
  LibAMM::AbstractCPPAlgoPtr cppAlgoPtr = cppAlgoTable.findCppAlgo(cppAlgoTag);
  LibAMM::AbstractCPPAlgoPtr cppAlgoPtr2 = cppAlgoTable.findCppAlgo(cppAlgoTag);
  if(cppAlgoTag=="pq")
  {
    cfg->edit("pqvqCodewordLookUpTablePath","qcdS1_m10.pth");
  }
  else{
    cfg->edit("pqvqCodewordLookUpTablePath","qcdS1_m1.pth");
  }
  cppAlgoPtr->setConfig(cfg);
    if(cppAlgoTag=="pq")
  {
    cfg->edit("pqvqCodewordLookUpTablePath","qcdS2_m10.pth");
  }
  else{
    cfg->edit("pqvqCodewordLookUpTablePath","qcdS2_m1.pth");
  }
  cppAlgoPtr2->setConfig(cfg);
    INTELLI_WARNING("single thread, algo " + cppAlgoTag);
    if (eMeter != nullptr) {
      eMeter->startMeter();
    }
    pef->start();

    INTELLI_WARNING("this is pure c++");
    C = cppAlgoPtr->amm(U, A, sketchDimension);
    C2= cppAlgoPtr2->amm(C, Ut, sketchDimension);
    pef->end();
    if (eMeter != nullptr) {
      eMeter->stopMeter();
    }
    if (useCPP && cppAlgoPtr) {
      breakDownResult = cppAlgoPtr->getBreakDown();
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

  // error
   torch::Tensor realC,realC2;
  INTELLI_WARNING("evaluating the error, may takes some time");

  realC = torch::matmul(U, A);
  realC2=torch::matmul(realC, Ut);

 // uint64_t otherTime=qcdp.prepareTime;
  double froError = INTELLI::UtilityFunctions::relativeFrobeniusNorm(realC, C);
  double froError2 = INTELLI::UtilityFunctions::relativeFrobeniusNorm(realC2, C2);
  double qcdError= qcdMSE(realC2, C2);
  double froBNormal = A.norm().item<double>();
  double errorBoundRatio = froError / froBNormal;
  INTELLI_INFO("A normal is " + to_string(froBNormal));
  resultCsv->edit("froError", (double) (froError+froError2)/2);
  resultCsv->edit("qcdError", (double) qcdError);
  resultCsv->edit("errorBoundRatio", (double) errorBoundRatio);
  //resultCsv->edit("otherTime", (uint64_t)otherTime);
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
