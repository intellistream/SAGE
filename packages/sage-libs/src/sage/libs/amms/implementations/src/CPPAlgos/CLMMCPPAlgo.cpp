
// Created by tony on 25/05/23.
//

#include <CPPAlgos/CLMMCPPAlgo.h>
#include <Utils/UtilityFunctions.h>
void clTest(TONY_CL_HOST::CLContainerPtr clc,
            float *h_a,
            float *h_b,
            float *h_c,
            int64_t *params,
            uint64_t local0,
            uint64_t local1,
            uint64_t workDim = 2) {

  clc->addHostOutPara(HostPara(h_a, params[0] * params[1] * sizeof(float)));
  clc->addHostOutPara(HostPara(h_b, params[1] * params[2] * sizeof(float)));
  clc->addHostOutPara(HostPara(params, 3 * sizeof(int64_t)));
  clc->addHostInPara(HostPara(h_c, params[0] * params[2] * sizeof(float)));
  std::vector<size_t> localSz(2);
  std::vector<size_t> globalSz(2);
  localSz[0] = local0;
  localSz[1] = local1;
  globalSz[0] = params[0];
  globalSz[1] = params[2];

  clc->setWorkDimension(workDim);
  clc->execute(globalSz, localSz);

  return;
}
void clint8Test(TONY_CL_HOST::CLContainerPtr clc,
                int8_t *h_a,
                int8_t *h_b,
                int32_t *h_c,
                int64_t *params,
                uint64_t local0,
                uint64_t local1,
                uint64_t workDim = 2) {

  clc->addHostOutPara(HostPara(h_a, params[0] * params[1] * sizeof(int8_t)));
  clc->addHostOutPara(HostPara(h_b, params[1] * params[2] * sizeof(int8_t)));
  clc->addHostOutPara(HostPara(params, 3 * sizeof(int64_t)));
  clc->addHostInPara(HostPara(h_c, params[0] * params[2] * sizeof(int32_t)));
  std::vector<size_t> localSz(2);
  std::vector<size_t> globalSz(2);
  localSz[0] = local0;
  localSz[1] = local1;
  globalSz[0] = params[0];
  globalSz[1] = params[2];

  clc->setWorkDimension(workDim);
  clc->execute(globalSz, localSz);

  return;
}
torch::Tensor LibAMM::CLMMCPPAlgo::clmm(torch::Tensor tensor1, torch::Tensor tensor2) {
  auto A_size = tensor1.sizes();
  auto B_size = tensor2.sizes();
  struct timeval tstart;
  //INTELLI_INFO("I am mm");
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
  /* for (int64_t i = 0; i < rows1; ++i) {
     for (int64_t j = 0; j < cols2; ++j) {
       for (int64_t k = 0; k < cols1; ++k) {
         result[i * cols2 + j] += matrix1[i * cols1 + k] * matrix2[k * cols2 + j];
       }
     }
   }*/
  int64_t params[3];
  params[0] = rows1;
  params[1] = cols1;
  params[2] = cols2;
/* float *m1=(float*) malloc((rows1*cols1)*sizeof(float));
  float *m2=(float*) malloc((cols1*cols2)*sizeof(float));
  float *m3=(float *) malloc((rows1*cols2)*sizeof(float));*/



  /*
  clc->addHostOutPara(HostPara(m1,(rows1*cols1)*sizeof(float)));
  clc->addHostOutPara(HostPara(m2,(cols1*cols2)*sizeof(float)));
  clc->addHostOutPara(HostPara(params,3*sizeof(int64_t)));
  clc->addHostInPara(HostPara(m3,(rows1*cols2)*sizeof(float)));
*/
  clTest(clc, matrix1.data(), matrix2.data(), result.data(), params, localSize0, localSize1, clWorkDim);
  // exit(-1);
  fABTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime - buildBTime;

  torch::Tensor resultTensor = torch::from_blob(result.data(), {rows1, cols2});
  //torch::Tensor resultTensor = torch::zeros({rows1,cols2});
  postProcessTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime - buildBTime - fABTime;
  /**
   * @brief fix the time measure related to cl
   */
  fABTime -= clc->tIn + clc->tOut;
  buildATime += clc->tIn / 2;
  buildBTime += clc->tIn / 2;
  postProcessTime += clc->tOut;
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
torch::Tensor LibAMM::CLMMCPPAlgo::clint8(torch::Tensor tensor1, torch::Tensor tensor2) {
  auto A_size = tensor1.sizes();
  auto B_size = tensor2.sizes();
  struct timeval tstart;
  //INTELLI_INFO("I am mm");
  gettimeofday(&tstart, NULL);
  int64_t rows1 = A_size[0];
  int64_t cols1 = A_size[1];
  int64_t cols2 = B_size[1];
  /**
   * @brief build A into std vector
   */
  std::vector<float> matrix1Float(tensor1.data_ptr<float>(), tensor1.data_ptr<float>() + rows1 * cols1);
  std::vector<int8_t> matrix1(rows1 * cols1);
  float scale1 = getScaleingFactor(127.0, matrix1Float);
  for (int i = 0; i < rows1 * cols1; ++i) {
    matrix1[i] = static_cast<int8_t>(matrix1Float[i] * scale1);
  }
  buildATime = INTELLI::UtilityFunctions::timeLastUs(tstart);
  std::vector<float> matrix2Float(tensor2.data_ptr<float>(), tensor2.data_ptr<float>() + cols1 * cols2);
  std::vector<int8_t> matrix2(rows1 * cols1);
  float scale2 = getScaleingFactor(127.0, matrix2Float);
  for (int i = 0; i < cols1 * cols2; ++i) {
    matrix2[i] = static_cast<int8_t>(matrix2Float[i] * scale2);
  }
  buildBTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime;
  // Create the output matrix
  /**
    * @brief run fAB
    */
  std::vector<int32_t> result(rows1 * cols2, 0);

  int64_t params[3];
  params[0] = rows1;
  params[1] = cols1;
  params[2] = cols2;

  clint8Test(clc, matrix1.data(), matrix2.data(), result.data(), params, localSize0, localSize1, clWorkDim);
  fABTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime - buildBTime;

  // exit(-1);
  std::vector<float> resultFP32(rows1 * cols2);
  float scaleResult = 1.0 / (scale1 * scale2);
  for (int i = 0; i < rows1 * cols2; ++i) {
    resultFP32[i] = static_cast<float>(result[i] * scaleResult);
  }
  torch::Tensor resultTensor = torch::from_blob(resultFP32.data(), {rows1, cols2});
  postProcessTime = INTELLI::UtilityFunctions::timeLastUs(tstart) - buildATime - buildBTime - fABTime;
  //torch::Tensor resultTensor = torch::zeros({rows1,cols2});

  /**
   * @brief fix the time measure related to cl
   */
  fABTime -= clc->tIn + clc->tOut;
  buildATime += clc->tIn / 2;
  buildBTime += clc->tIn / 2;
  postProcessTime += clc->tOut;
  return resultTensor.clone();
}
void LibAMM::CLMMCPPAlgo::setConfig(INTELLI::ConfigMapPtr cfg) {
  AbstractCPPAlgo::setConfig(cfg);
  clFile = cfg->tryString("clFile", "CL/CLMM.cl", true);
  clc = newCLContainer(1, CL_DEVICE_TYPE_DEFAULT, "CLMM", clFile);
  localSize0 = cfg->tryU64("localSize0", 1, true);
  localSize1 = cfg->tryU64("localSize1", 1, true);
  clWorkDim = cfg->tryU64("clWorkDim", 2, true);
}
torch::Tensor LibAMM::CLMMCPPAlgo::amm(torch::Tensor A, torch::Tensor B, uint64_t sketchSize) {
  assert(sketchSize);
  if (clFile == "CL/CLINT8.cl") {
    return clint8(A, B);
  }
  return clmm(A, B);
}
