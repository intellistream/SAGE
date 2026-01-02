//
// Created by tony on 25/12/22.
//

// 内存优化：使用必要的头文件
// torch/extension.h 会引入 Python.h 依赖，CI 缺少 python-dev 导致失败
// torch/torch.h 提供同样的 API（Tensor/Library）但不强制绑定 Python
#include <torch/torch.h>

using namespace torch;

/**
 *
 * @brief The c++ extension operation to pytorch
 * @param a
 * @param b
 * @note please keep input and output as tensors
 * @return tensor
 */
torch::Tensor myVecAdd(torch::Tensor a, torch::Tensor b) {
  c10::IntArrayRef tsize = a.sizes();
  int h = tsize[0];
  int w = tsize[1];
  /**
   * @brief convert tensor to vector
   */
  auto ta = a.reshape({1, h * w});
  auto tb = b.reshape({1, h * w});
  std::vector<float> va(ta.data_ptr<float>(), ta.data_ptr<float>() + ta.numel());
  std::vector<float> vb(tb.data_ptr<float>(), tb.data_ptr<float>() + tb.numel());
  std::vector<float> vc = std::vector<float>(va.size());
  for (size_t i = 0; i < vc.size(); i++) {
    vc[i] = va[i] + vb[i];
  }
  /**
   * @brief convert vector back to tensor
   */
  auto opts = torch::TensorOptions().dtype(torch::kFloat32);
  auto tensor2 = torch::from_blob(vc.data(), {int64_t(vc.size())}, opts).clone();
  tensor2 = tensor2.reshape({h, w});

  return tensor2.clone();
  // END output_tensor
}

torch::Tensor myVecSub(torch::Tensor a, torch::Tensor b) {
  c10::IntArrayRef tsize = a.sizes();
  int h = tsize[0];
  int w = tsize[1];
  /**
   * @brief convert tensor to vector
   */
  auto ta = a.reshape({1, h * w});
  auto tb = b.reshape({1, h * w});
  std::vector<float> va(ta.data_ptr<float>(), ta.data_ptr<float>() + ta.numel());
  std::vector<float> vb(tb.data_ptr<float>(), tb.data_ptr<float>() + tb.numel());
  std::vector<float> vc = std::vector<float>(va.size());
  for (size_t i = 0; i < vc.size(); i++) {
    vc[i] = va[i] - vb[i];
  }
  /**
   * @brief convert vector back to tensor
   */
  auto opts = torch::TensorOptions().dtype(torch::kFloat32);
  auto tensor2 = torch::from_blob(vc.data(), {int64_t(vc.size())}, opts).clone();
  tensor2 = tensor2.reshape({h, w});
  return tensor2.clone();
  // END output_tensor
}
/**
 * @brief Declare the function to pytorch
 * @note The of lib is myLib
 */
TORCH_LIBRARY(myLib, m) {
  m.def("myVecAdd", myVecAdd);
  m.def("myVecSub", myVecSub);
}
