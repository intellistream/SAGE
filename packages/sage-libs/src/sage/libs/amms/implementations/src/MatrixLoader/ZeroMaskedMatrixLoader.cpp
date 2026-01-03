//
// Created by tony on 10/05/23.
//

#include <MatrixLoader/ZeroMaskedMatrixLoader.h>
#include <Utils/IntelliLog.h>

void LibAMM::ZeroMaskedMatrixLoader::paraseConfig(INTELLI::ConfigMapPtr cfg) {
  aRow = cfg->tryU64("aRow", 100, true);
  aCol = cfg->tryU64("aCol", 1000, true);
  bCol = cfg->tryU64("bCol", 500, true);
  seed = cfg->tryU64("seed", 114514, true);
  nnzA = cfg->tryDouble("nnzA",1.0,true);
  nnzB = cfg->tryDouble("nnzB",1.0,true);
  INTELLI_INFO(
      "Generating [" + to_string(aRow) + "x" + to_string(aCol) + "]*[" + to_string(aCol) + "x" + to_string(bCol)
          + "]");
}

void LibAMM::ZeroMaskedMatrixLoader::generateAB() {
  torch::manual_seed(seed);
  auto maskedA = torch::rand({(long) (aRow*nnzA), (long) (aCol*nnzA)});
  auto maskedB = torch::rand({(long) (aCol*nnzB), (long) (bCol*nnzB)});
  A = torch::zeros({(long) aRow, (long) aCol});
  A.slice(0, 0, (long) (aRow*nnzA)).slice(1, 0,(long) (aCol*nnzA) ).copy_(maskedA);
  B = torch::zeros({(long) aCol, (long) bCol});
  B.slice(0, 0, (long) (aCol*nnzB)).slice(1, 0,(long) (bCol*nnzB) ).copy_(maskedB);
}

//do nothing in abstract class
bool LibAMM::ZeroMaskedMatrixLoader::setConfig(INTELLI::ConfigMapPtr cfg) {
  paraseConfig(cfg);
  generateAB();
  return true;
}

torch::Tensor LibAMM::ZeroMaskedMatrixLoader::getA() {
  return A.clone();
}

torch::Tensor LibAMM::ZeroMaskedMatrixLoader::getB() {
  return B.clone();
}
