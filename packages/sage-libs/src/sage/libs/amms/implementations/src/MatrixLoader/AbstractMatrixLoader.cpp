//
// Created by tony on 10/05/23.
//

#include <MatrixLoader/AbstractMatrixLoader.h>

//do nothing in abstract class
bool LibAMM::AbstractMatrixLoader::setConfig(INTELLI::ConfigMapPtr cfg) {
  assert(cfg);
  return true;
}

torch::Tensor LibAMM::AbstractMatrixLoader::getA() {
  return torch::rand({1, 1});
}

torch::Tensor LibAMM::AbstractMatrixLoader::getB() {
  return torch::rand({1, 1});
}
