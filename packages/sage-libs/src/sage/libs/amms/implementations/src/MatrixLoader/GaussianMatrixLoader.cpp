//
// Created by haolan on 6/5/23.
//
#include <MatrixLoader/GaussianMatrixLoader.h>
#include <Utils/IntelliLog.h>

void LibAMM::GaussianMatrixLoader::paraseConfig(INTELLI::ConfigMapPtr cfg) {
  aRow = cfg->tryU64("aRow", 100, true);
  aCol = cfg->tryU64("aCol", 1000, true);
  bCol = cfg->tryU64("bCol", 500, true);
  seed = cfg->tryU64("seed", 114514, true);
  randA = cfg->tryU64("randA", 0, false);
  randB = cfg->tryU64("randB", 0, false);
  avgA  = cfg->tryDouble("avgA", 0.0, false);
  sigmaA  = cfg->tryDouble("sigmaA", 1.0, false);
  avgB  = cfg->tryDouble("avgB", 0.0, false);
  sigmaB  = cfg->tryDouble("sigmaB", 1.0, false);
  INTELLI_INFO(
      "Generating [" + to_string(aRow) + "x" + to_string(aCol) + "]*[" + to_string(aCol) + "x" + to_string(bCol)
          + "]");
}

void LibAMM::GaussianMatrixLoader::generateAB() {
  torch::manual_seed(seed);
  if (randA)
  {
    INTELLI_INFO(
      "change A into random");
     A = torch::rand({(long) aRow, (long) aCol});
  }
  else{
    A = sigmaA*torch::randn({(long) aRow, (long) aCol})+avgA;
  }
  if(randB)
  {
     INTELLI_INFO(
      "change B into random");
      B = torch::rand({(long) aCol, (long) bCol});
  }
  else{
     B = sigmaB*torch::randn({(long) aCol, (long) bCol})+avgB;
  }

}

//do nothing in abstract class
bool LibAMM::GaussianMatrixLoader::setConfig(INTELLI::ConfigMapPtr cfg) {
  paraseConfig(cfg);
  generateAB();
  return true;
}

torch::Tensor LibAMM::GaussianMatrixLoader::getA() {
  return A;
}

torch::Tensor LibAMM::GaussianMatrixLoader::getB() {
  return B;
}
