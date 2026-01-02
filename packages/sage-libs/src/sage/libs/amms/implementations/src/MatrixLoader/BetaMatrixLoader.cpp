//
// Created by haolan on 6/6/23.
//
#include <MatrixLoader/BetaMatrixLoader.h>
#include <Utils/IntelliLog.h>

void LibAMM::BetaMatrixLoader::paraseConfig(INTELLI::ConfigMapPtr cfg) {
  aRow = cfg->tryU64("aRow", 100, true);
  aCol = cfg->tryU64("aCol", 1000, true);
  bCol = cfg->tryU64("bCol", 500, true);
  a = cfg->tryDouble("a", 2, true);
  b = cfg->tryDouble("b", 2, true);
  seed = cfg->tryU64("seed", 114514, true);
  INTELLI_INFO(
      "Generating [" + to_string(aRow) + "x" + to_string(aCol) + "]*[" + to_string(aCol) + "x" + to_string(bCol)
          + "]" + " Parameter: " + to_string(a) + ", " + to_string(b));
}

void LibAMM::BetaMatrixLoader::generateAB() {
  torch::manual_seed(seed);

  auto tensor1 = torch::randn({(long) aRow, (long) aCol}).abs_();
  auto tensor2 = torch::randn({(long) aRow, (long) aCol}).abs_();

  tensor1 = tensor1.pow(1. / a);
  tensor2 = tensor2.pow(1. / b);

  A = tensor1 / (tensor1 + tensor2);

  tensor1 = torch::randn({(long) aCol, (long) bCol}).abs_();
  tensor2 = torch::randn({(long) aCol, (long) bCol}).abs_();

  tensor1 = tensor1.pow(1. / a);
  tensor2 = tensor2.pow(1. / b);

  B = tensor1 / (tensor1 + tensor2);
}

//do nothing in abstract class
bool LibAMM::BetaMatrixLoader::setConfig(INTELLI::ConfigMapPtr cfg) {
  paraseConfig(cfg);
  generateAB();
  return true;
}

torch::Tensor LibAMM::BetaMatrixLoader::getA() {
  return A;
}

torch::Tensor LibAMM::BetaMatrixLoader::getB() {
  return B;
}
