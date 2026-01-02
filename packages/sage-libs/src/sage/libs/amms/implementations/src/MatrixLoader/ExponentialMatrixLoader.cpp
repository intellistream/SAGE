//
// Created by haolan on 6/5/23.
//
#include <MatrixLoader/ExponentialMatrixLoader.h>
#include <Utils/IntelliLog.h>

void LibAMM::ExponentialMatrixLoader::paraseConfig(INTELLI::ConfigMapPtr cfg) {
  aRow = cfg->tryU64("aRow", 100, true);
  aCol = cfg->tryU64("aCol", 1000, true);
  bCol = cfg->tryU64("bCol", 500, true);
  seed = cfg->tryU64("seed", 114514, true);
  INTELLI_INFO(
      "Generating [" + to_string(aRow) + "x" + to_string(aCol) + "]*[" + to_string(aCol) + "x" + to_string(bCol)
          + "]");
}

void LibAMM::ExponentialMatrixLoader::generateAB() {
  torch::manual_seed(seed);
  A = torch::exponential(torch::empty({(long) aRow, (long) aCol}));
  B = torch::exponential(torch::empty({(long) aCol, (long) bCol}));
}

//do nothing in abstract class
bool LibAMM::ExponentialMatrixLoader::setConfig(INTELLI::ConfigMapPtr cfg) {
  paraseConfig(cfg);
  generateAB();
  return true;
}

torch::Tensor LibAMM::ExponentialMatrixLoader::getA() {
  return A;
}

torch::Tensor LibAMM::ExponentialMatrixLoader::getB() {
  return B;
}
