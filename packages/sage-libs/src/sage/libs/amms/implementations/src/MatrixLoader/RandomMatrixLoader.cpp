//
// Created by tony on 10/05/23.
//

#include <MatrixLoader/RandomMatrixLoader.h>
#include <Utils/IntelliLog.h>

void LibAMM::RandomMatrixLoader::paraseConfig(INTELLI::ConfigMapPtr cfg) {
  aRow = cfg->tryU64("aRow", 100, true);
  aCol = cfg->tryU64("aCol", 1000, true);
  bCol = cfg->tryU64("bCol", 500, true);
  seed = cfg->tryU64("seed", 114514, true);
  INTELLI_INFO(
      "Generating [" + to_string(aRow) + "x" + to_string(aCol) + "]*[" + to_string(aCol) + "x" + to_string(bCol)
          + "]");
}

void LibAMM::RandomMatrixLoader::generateAB() {
  torch::manual_seed(seed);
  A = torch::rand({(long) aRow, (long) aCol});
  B = torch::rand({(long) aCol, (long) bCol});
}

//do nothing in abstract class
bool LibAMM::RandomMatrixLoader::setConfig(INTELLI::ConfigMapPtr cfg) {
  paraseConfig(cfg);
  generateAB();
  return true;
}

torch::Tensor LibAMM::RandomMatrixLoader::getA() {
  return A;
}

torch::Tensor LibAMM::RandomMatrixLoader::getB() {
  return B;
}
