/*! \file Benchmark.h*/

/**
 * @brief This is the main entry point of the entire program.
 * We use this as the entry point for benchmarking.
 */
#include <LibAMM.h>
#include <Utils/UtilityFunctions.h>
#include <Streaming/Streamer.h>

using namespace std;
using namespace INTELLI;
using namespace torch;
using namespace DIVERSE_METER;
using namespace LibAMM;

void benchmarkPCA(std::string configName) {

  INTELLI_INFO("Running Benchmark PCA");

  // 1. Set up environments
  ConfigMapPtr cfg = newConfigMap();
  cfg->fromFile(configName);

  INTELLI_INFO("cppAlgoTag: " + cfg->tryString("cppAlgoTag", "mm", true));

  uint64_t coreBind = cfg->tryU64("coreBind", 0, true);
  UtilityFunctions::bind2Core((int) coreBind);

  LibAMM::MatrixLoaderTable mLoaderTable;
  std::string matrixLoaderTag = cfg->tryString("matrixLoaderTag", "SIFT", true);
  INTELLI_INFO("matrixLoaderTag: " + matrixLoaderTag);
  auto matLoaderPtr = mLoaderTable.findMatrixLoader(matrixLoaderTag);
  assert(matLoaderPtr);
  matLoaderPtr->setConfig(cfg);
  auto A = matLoaderPtr->getA();
  auto B = A.t();

  uint64_t sketchDimension;
  sketchDimension = cfg->tryU64("sketchDimension", 1, true);
  INTELLI_INFO("sketchDimension: " + to_string(sketchDimension));

  // 2. Get metrics of AMM in streaming and parallelism
  INTELLI_INFO("Run AMM");
  Streamer streamer;
  torch::Tensor C = streamer.run(cfg, A, B, sketchDimension, "AMM");
  ConfigMapPtr allMetrics = streamer.getMetrics();

  // 3. Get metrics of the rest of PCA except AMM, we call it elseMetrics
  INTELLI_INFO("Start SVD task..");
  ThreadPerf pef(-1);
  pef.setPerfList();
  torch::manual_seed(999);
  pef.start();
  torch::Tensor U, S, Vh;
  std::tie(U, S, Vh) = torch::linalg::svd(torch::div(C, A.size(1)), false, c10::nullopt); // // covirance matrix estimator
  int k = 5; // use eigenvector 0-5
  torch::Tensor Ak = torch::matmul(Vh.narrow(0, 0, k), A); // Ak feature dimension reduced to k
  pef.end();
  // cout << "A.sizes(): " << A.sizes() << endl; // [128, 10000]
  // cout << "Vh.narrow(0, 0, k).sizes(): " << Vh.narrow(0, 0, k).sizes() << endl; // [5, 128]
  // cout << "Ak.sizes(): " << Ak.sizes() << endl; // [5, 10000] dimension of each vector reduces from 128 to 5
  ConfigMapPtr elseMetrics = pef.resultToConfigMap();
  elseMetrics->addPrefixToKeys("else");
  elseMetrics->cloneInto(*allMetrics);

  // 4. Calculate end-to-end error
  Ak =  torch::matmul(U.narrow(1, 0, k), Ak); // back to original feature dimension [128, 10000] for error evaluation

  torch::Tensor realC = torch::matmul(A, B);
  torch::Tensor realU, realS, realVh;
  std::tie(realU, realS, realVh) = torch::linalg::svd(torch::div(realC, A.size(1)), false, c10::nullopt); // || ATB || spectral norm
  INTELLI_INFO("realS[0]: "+to_string(realS[0].item<double>()));
  INTELLI_INFO("realS[k]: "+to_string(realS[k].item<double>()));

  torch::Tensor UError, SError, VhError;
  std::tie(UError, SError, VhError) = torch::linalg::svd((torch::div(torch::matmul(A, A.t()), A.size(1)) - torch::div(torch::matmul(Ak, Ak.t()), A.size(1))), false, c10::nullopt); // || ATB - ATBr || spectral norm
  INTELLI_INFO("SError[0]: "+to_string(SError[0].item<double>()));

  // double relativeSpectralNormError = torch::div(SError[0], realS[k]).item<double>()-1; // SError[0] is the spectral norm of (A-Ak), real[k] is the spectral norm of (A-realAk)
  double relativeSpectralNormError = torch::div(SError[0], realS[0]).item<double>(); // || ATB - ATBr || / || ATB ||
  allMetrics->edit("PCAError", relativeSpectralNormError);

  // 5 Save results
  std::string ruName = "PCA";
  allMetrics->toFile(ruName + ".csv");
  INTELLI_INFO("Done. here is overall result");
  INTELLI_INFO(allMetrics->toString());
}

int main(int argc, char **argv) {
  string configName, outPrefix = "";
  if (argc >= 2) {
    configName += argv[1];
  } else {
    configName = "config.csv";
  }
  benchmarkPCA(configName);
  return 0;
}
