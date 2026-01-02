//
// Created by tony on 10/05/23.
//

#include <MatrixLoader/ZipfMatrixLoader.h>
#include <Utils/IntelliLog.h>
#include <iostream>
#include <vector>
#include <random>
#include <cmath>
void LibAMM::ZipfMatrixLoader::paraseConfig(INTELLI::ConfigMapPtr cfg) {
  aRow = cfg->tryU64("aRow", 100, true);
  aCol = cfg->tryU64("aCol", 1000, true);
  bCol = cfg->tryU64("bCol", 500, true);
  seed = cfg->tryU64("seed", 114514, true);
  zipfAlphaA  = cfg->tryDouble("zipfAlphaA", 0.0, false);
  zipfAlphaB  = cfg->tryDouble("zipfAlphaB", 0.0, false);
  randA = cfg->tryU64("randA", 0, false);
  randB = cfg->tryU64("randB", 0, false);
  INTELLI_INFO(
      "Generating [" + to_string(aRow) + "x" + to_string(aCol) + "]*[" + to_string(aCol) + "x" + to_string(bCol)
          + "]");
}
torch::Tensor LibAMM::ZipfMatrixLoader::generateZipfDistribution(int64_t n, int64_t m, double alpha) {
  torch::Tensor indices = torch::arange(1, n * m + 1, torch::kFloat32);
  torch::Tensor probabilities = 1.0 / torch::pow(indices, alpha);
  torch::Tensor normalizedProbabilities = probabilities / torch::sum(probabilities);

  // Generate Zipf-distributed samples
  torch::Tensor zipfSamples = torch::multinomial(normalizedProbabilities, n * m, true);
  torch::Tensor zipfMatrix = zipfSamples.view({n, m}).clone();

  // Normalize the values to the range [0, 1]
  auto ru = zipfMatrix / (zipfMatrix.max());
  // Reshape the 1D tensor to an nxm tensor
  return ru;
}
void LibAMM::ZipfMatrixLoader::generateAB() {
  torch::manual_seed(seed);
  if(randA)
  {
    A = torch::rand({(long) aRow, (long) aCol});
  }
  else
  {
    A=generateZipfDistribution((int64_t)aRow,(int64_t)aCol,zipfAlphaA);
  }
  if(randB)
  {
    B = torch::rand({(long) aCol, (long) bCol});
  }
  else{
    B=generateZipfDistribution((int64_t)aCol,(int64_t)bCol,zipfAlphaB);
  }



}

//do nothing in abstract class
bool LibAMM::ZipfMatrixLoader::setConfig(INTELLI::ConfigMapPtr cfg) {
  paraseConfig(cfg);
  generateAB();
  return true;
}

torch::Tensor LibAMM::ZipfMatrixLoader::getA() {
  return A;
}

torch::Tensor LibAMM::ZipfMatrixLoader::getB() {
  return B;
}
