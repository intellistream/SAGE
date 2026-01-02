
// Created by tony on 25/05/23.
//

#include <CPPAlgos/INT8CPPAlgo.h>
#include <Utils/UtilityFunctions.h>

torch::Tensor LibAMM::INT8CPPAlgo::fp32amm(torch::Tensor tensor1, torch::Tensor tensor2) {
  tensor1 = tensor1.contiguous();
  tensor2 = tensor2.contiguous();
  auto A_size = tensor1.sizes();
  auto B_size = tensor2.sizes();
  struct timeval tstart;
  gettimeofday(&tstart, NULL);
  int64_t rows1 = A_size[0];
  int64_t cols1 = A_size[1];
  int64_t cols2 = B_size[1];
  /**
   * @brief build A into std vector
   */
  std::vector<float> matrix1(tensor1.data_ptr<float>(), tensor1.data_ptr<float>() + rows1 * cols1);
  buildATime = INTELLI::UtilityFunctions::timeLastUs(tstart);
  std::vector<float> matrix2(tensor2.data_ptr<float>(), tensor2.data_ptr<float>() + cols1 * cols2);
  buildBTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime;
  // Create the output matrix
  std::vector<float> result(rows1 * cols2, 0.0);
  for (int64_t i = 0; i < rows1; ++i) {
    for (int64_t j = 0; j < cols2; ++j) {
      for (int64_t k = 0; k < cols1; ++k) {
        result[i * cols2 + j] += matrix1[i * cols1 + k] * matrix2[k * cols2 + j];
      }
    }
  }
  // exit(-1);
  fABTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime - buildBTime;
  torch::Tensor resultTensor = torch::from_blob(result.data(), {rows1, cols2});
  //torch::Tensor resultTensor = torch::zeros({rows1,cols2});
  postProcessTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime - buildBTime - fABTime;

  return resultTensor.clone();
}

torch::Tensor LibAMM::INT8CPPAlgo::fp64amm(torch::Tensor tensor1, torch::Tensor tensor2) {
  std::cout << "Scalar Type of the tensor1: " << torch::toString(tensor1.scalar_type()) << std::endl;
  std::cout << "Scalar Type of the tensor2: " << torch::toString(tensor2.scalar_type()) << std::endl;
  auto A_size = tensor1.sizes();
  auto B_size = tensor2.sizes();
  struct timeval tstart;
  INTELLI_INFO("fp64amm");
  gettimeofday(&tstart, NULL);
  int64_t rows1 = A_size[0];
  int64_t cols1 = A_size[1];
  int64_t cols2 = B_size[1];
  /**
   * @brief build A into std vector
   */
  std::vector<double> matrix1(tensor1.data_ptr<double>(), tensor1.data_ptr<double>() + rows1 * cols1);
  buildATime = INTELLI::UtilityFunctions::timeLastUs(tstart);
  std::vector<double> matrix2(tensor2.data_ptr<double>(), tensor2.data_ptr<double>() + cols1 * cols2);
  buildBTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime;
  // Create the output matrix
  std::vector<double> result(rows1 * cols2, 0.0);
  for (int64_t i = 0; i < rows1; ++i) {
    for (int64_t j = 0; j < cols2; ++j) {
      for (int64_t k = 0; k < cols1; ++k) {
        result[i * cols2 + j] += matrix1[i * cols1 + k] * matrix2[k * cols2 + j];
      }
    }
  }
  // exit(-1);
  fABTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime - buildBTime;
  torch::Tensor resultTensor = torch::from_blob(result.data(), {rows1, cols2}, torch::TensorOptions().dtype(torch::kFloat64));
  //torch::Tensor resultTensor = torch::zeros({rows1,cols2});
  postProcessTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime - buildBTime - fABTime;

  return resultTensor.clone();
}

static float getScaleingFactor(float scalingBase, std::vector<float> matrix1Float) {
  float maxa = *std::max_element(matrix1Float.begin(), matrix1Float.end());
  float minaAbs = abs(*std::min_element(matrix1Float.begin(), matrix1Float.end()));
  if (minaAbs > maxa) {
    maxa = minaAbs;
  }
  return scalingBase / maxa;
}

torch::Tensor LibAMM::INT8CPPAlgo::int4amm(torch::Tensor tensor1, torch::Tensor tensor2) {
  auto A_size = tensor1.sizes();
  auto B_size = tensor2.sizes();
  struct timeval tstart;
  //INTELLI_INFO("I am mm");
  gettimeofday(&tstart, NULL);
  int64_t rows1 = A_size[0];
  int64_t cols1 = A_size[1];
  int64_t cols2 = B_size[1];
  /**
   * @brief build A
   */
  std::vector<float> matrix1Float(tensor1.data_ptr<float>(), tensor1.data_ptr<float>() + rows1 * cols1);
  // Convert the input matrices to int8
  std::vector<int8_t> matrix1(rows1 * cols1);

  float scale1 = getScaleingFactor(7.0, matrix1Float);
  for (int i = 0; i < rows1 * cols1; ++i) {
    matrix1[i] = static_cast<int8_t>(matrix1Float[i] * scale1);
  }
  buildATime = INTELLI::UtilityFunctions::timeLastUs(tstart);

  /**
   * @brief build B
   */
  std::vector<float> matrix2Float(tensor2.data_ptr<float>(), tensor2.data_ptr<float>() + cols1 * cols2);
  std::vector<int8_t> matrix2(cols1 * cols2);
  float scale2 = getScaleingFactor(7.0, matrix2Float);
  for (int i = 0; i < cols1 * cols2; ++i) {
    matrix2[i] = static_cast<int8_t>(matrix2Float[i] * scale2);
  }
  buildBTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime;
  /**
   * @brief run fAB
   */
  std::vector<int16_t> result(rows1 * cols2, 0);

  // Perform matrix multiplication using nested loops
  for (int64_t i = 0; i < rows1; ++i) {
    for (int64_t j = 0; j < cols2; ++j) {
      int16_t sRu = 0;
      int64_t k = 0;
      /**
       * @brief 32/4=8, so we simulate a 8-way SHARED-NOTHING speed up in one loop
       */
      while (k < cols1 - 8) {
        int8_t tru1 = matrix1[i * cols1 + k] * matrix2[k * cols2 + j];
        int8_t tru2 = matrix1[i * cols1 + k + 1] * matrix2[(k + 1) * cols2 + j];
        int8_t tru3 = matrix1[i * cols1 + (k + 2)] * matrix2[(k + 2) * cols2 + j];
        int8_t tru4 = matrix1[i * cols1 + (k + 3)] * matrix2[(k + 3) * cols2 + j];
        //
        int8_t tru5 = matrix1[i * cols1 + k + 4] * matrix2[(k + 4) * cols2 + j];
        int8_t tru6 = matrix1[i * cols1 + k + 5] * matrix2[(k + 5) * cols2 + j];
        int8_t tru7 = matrix1[i * cols1 + (k + 6)] * matrix2[(k + 6) * cols2 + j];
        int8_t tru8 = matrix1[i * cols1 + (k + 7)] * matrix2[(k + 7) * cols2 + j];
        sRu += tru1 + tru2 + tru3 + tru4 + tru5 + tru6 + tru7 + tru8;
        k += 8;
      }
      for (int64_t k2 = k; k2 < cols1; ++k2) {
        int16_t tru = matrix1[i * cols1 + k2] * matrix2[k2 * cols2 + j];
        sRu += tru;
      }
      result[i * cols2 + j] = sRu;
    }
  }
  fABTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime - buildBTime;

  // Scale the result back to int8
  /**
 * @brief post process
 */
  std::vector<float> resultFP32(rows1 * cols2);
  float scaleResult = 1.0 / (scale1 * scale2);
  for (int i = 0; i < rows1 * cols2; ++i) {
    resultFP32[i] = static_cast<float>(result[i] * scaleResult);
  }
  torch::Tensor resultTensor = torch::from_blob(resultFP32.data(), {rows1, cols2});
  //torch::Tensor resultTensor = torch::zeros({rows1,cols2});
  postProcessTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime - buildBTime - fABTime;

  return resultTensor.clone();
}

torch::Tensor LibAMM::INT8CPPAlgo::int8amm(torch::Tensor tensor1, torch::Tensor tensor2) {

  tensor1 = tensor1.contiguous();
  tensor2 = tensor2.contiguous();
  // if tensor is double, convert it to float, and remember to convert back to double at the end
  bool isdouble = false;
  if (tensor1.dtype() == torch::kDouble){isdouble=true;}
  if (isdouble){
    tensor1=tensor1.to(torch::kFloat);
    tensor2=tensor2.to(torch::kFloat);
  }

  auto A_size = tensor1.sizes();
  auto B_size = tensor2.sizes();
  struct timeval tstart;
  //INTELLI_INFO("I am mm");
  gettimeofday(&tstart, NULL);
  int64_t rows1 = A_size[0];
  int64_t cols1 = A_size[1];
  int64_t cols2 = B_size[1];
  /**
   * @brief build A
   */
  std::vector<float> matrix1Float(tensor1.data_ptr<float>(), tensor1.data_ptr<float>() + rows1 * cols1);
  // Convert the input matrices to int8
  std::vector<int8_t> matrix1(rows1 * cols1);
  float scale1 = getScaleingFactor(127.0, matrix1Float);
  for (int i = 0; i < rows1 * cols1; ++i) {
    matrix1[i] = static_cast<int8_t>(matrix1Float[i] * scale1);
  }
  buildATime = INTELLI::UtilityFunctions::timeLastUs(tstart);

  /**
   * @brief build B
   */
  std::vector<float> matrix2Float(tensor2.data_ptr<float>(), tensor2.data_ptr<float>() + cols1 * cols2);
  std::vector<int8_t> matrix2(cols1 * cols2);
  float scale2 = getScaleingFactor(127.0, matrix2Float);
  for (int i = 0; i < cols1 * cols2; ++i) {
    matrix2[i] = static_cast<int8_t>(matrix2Float[i] * scale2);
  }
  buildBTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime;
  /**
   * @brief run fAB
   */
  std::vector<int32_t> result(rows1 * cols2, 0);

  // Perform matrix multiplication using nested loops
  for (int64_t i = 0; i < rows1; ++i) {
    for (int64_t j = 0; j < cols2; ++j) {
      int32_t sRu = 0;
      int64_t k = 0;
      /**
       * @brief 32/8=4, so we simulate a 4-way SHARED-NOTHING speed up in one loop
       */
      while (k < cols1 - 4) {
        int16_t tru1 = matrix1[i * cols1 + k] * matrix2[k * cols2 + j];
        int16_t tru2 = matrix1[i * cols1 + k + 1] * matrix2[(k + 1) * cols2 + j];
        int16_t tru3 = matrix1[i * cols1 + (k + 2)] * matrix2[(k + 2) * cols2 + j];
        int16_t tru4 = matrix1[i * cols1 + (k + 3)] * matrix2[(k + 3) * cols2 + j];
        sRu += tru1 + tru2 + tru3 + tru4;
        k += 4;
      }
      for (int64_t k2 = k; k2 < cols1; ++k2) {
        int16_t tru = matrix1[i * cols1 + k2] * matrix2[k2 * cols2 + j];
        sRu += tru;
      }
      result[i * cols2 + j] = sRu;
    }
  }
  fABTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime - buildBTime;

  // Scale the result back to int8
  /**
 * @brief post process
 */
  std::vector<float> resultFP32(rows1 * cols2);
  float scaleResult = 1.0 / (scale1 * scale2);
  for (int i = 0; i < rows1 * cols2; ++i) {
    resultFP32[i] = static_cast<float>(result[i] * scaleResult);
  }
  torch::Tensor resultTensor = torch::from_blob(resultFP32.data(), {rows1, cols2});
  //torch::Tensor resultTensor = torch::zeros({rows1,cols2});
  postProcessTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime - buildBTime - fABTime;

  if (isdouble){
    tensor1=tensor1.to(torch::kDouble);
    tensor2=tensor2.to(torch::kDouble);
    return resultTensor.clone().to(torch::kDouble);
  }
  return resultTensor.clone();
}

torch::Tensor LibAMM::INT8CPPAlgo::int16amm(torch::Tensor tensor1, torch::Tensor tensor2) {
  auto A_size = tensor1.sizes();
  auto B_size = tensor2.sizes();
  struct timeval tstart;
  //INTELLI_INFO("I am mm");
  gettimeofday(&tstart, NULL);
  int64_t rows1 = A_size[0];
  int64_t cols1 = A_size[1];
  int64_t cols2 = B_size[1];
  /**
   * @brief build A
   */
  std::vector<float> matrix1Float(tensor1.data_ptr<float>(), tensor1.data_ptr<float>() + rows1 * cols1);
  // Convert the input matrices to int8
  std::vector<int16_t> matrix1(rows1 * cols1);
  float scale1 = getScaleingFactor(32767.0, matrix1Float);
  for (int i = 0; i < rows1 * cols1; ++i) {
    matrix1[i] = static_cast<int16_t>(matrix1Float[i] * scale1);
  }
  buildATime = INTELLI::UtilityFunctions::timeLastUs(tstart);

  /**
   * @brief build B
   */
  std::vector<float> matrix2Float(tensor2.data_ptr<float>(), tensor2.data_ptr<float>() + cols1 * cols2);
  std::vector<int16_t> matrix2(cols1 * cols2);
  float scale2 = getScaleingFactor(32767.0, matrix2Float);
  for (int i = 0; i < cols1 * cols2; ++i) {
    matrix2[i] = static_cast<int16_t>(matrix2Float[i] * scale2);
  }
  buildBTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime;
  /**
   * @brief run fAB
   */
  std::vector<int64_t> result(rows1 * cols2, 0);

  // Perform matrix multiplication using nested loops
  for (int64_t i = 0; i < rows1; ++i) {
    for (int64_t j = 0; j < cols2; ++j) {
      int64_t sRu = 0;
      int64_t k = 0;
      /**
       * @brief 32/16=2, so we simulate a 2-way SHARED-NOTHING speed up in one loop
       */
      while (k < cols1 - 2) {
        int32_t tru1 = matrix1[i * cols1 + k] * matrix2[k * cols2 + j];
        int32_t tru2 = matrix1[i * cols1 + k + 1] * matrix2[(k + 1) * cols2 + j];
        sRu += tru1 + tru2;
        k += 2;
      }
      for (int64_t k2 = k; k2 < cols1; ++k2) {
        int32_t tru = matrix1[i * cols1 + k2] * matrix2[k2 * cols2 + j];
        sRu += tru;
      }
      result[i * cols2 + j] = sRu;
    }
  }
  fABTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime - buildBTime;

  // Scale the result back to int8
  /**
 * @brief post process
 */
  std::vector<float> resultFP32(rows1 * cols2);
  float scaleResult = 1.0 / (scale1 * scale2);
  for (int i = 0; i < rows1 * cols2; ++i) {
    resultFP32[i] = static_cast<float>(result[i] * scaleResult);
  }
  torch::Tensor resultTensor = torch::from_blob(resultFP32.data(), {rows1, cols2});
  //torch::Tensor resultTensor = torch::zeros({rows1,cols2});
  postProcessTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime - buildBTime - fABTime;

  return resultTensor.clone();
}

void LibAMM::INT8CPPAlgo::setConfig(INTELLI::ConfigMapPtr cfg) {
  AbstractCPPAlgo::setConfig(cfg);
  fpMode = cfg->tryString("fpMode", "INT8", true);
  INTELLI_INFO("fpMode: "+fpMode);
}

torch::Tensor LibAMM::INT8CPPAlgo::amm(torch::Tensor A, torch::Tensor B, uint64_t sketchSize) {
  assert(sketchSize);
  if (fpMode == "INT4") {
    return int4amm(A, B);
  } else if (fpMode == "INT8") {
    return int8amm(A, B);
  } else if (fpMode == "INT16") {
    return int16amm(A, B);
  }
  else if (fpMode == "fp64") {
    return fp64amm(A, B);
  }
  else {
    return fp32amm(A, B);
  }
}
