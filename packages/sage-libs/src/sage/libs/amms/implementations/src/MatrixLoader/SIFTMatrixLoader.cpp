//
// Created by haolan on 6/5/23.
//
#include <MatrixLoader/SIFTMatrixLoader.h>
#include <Utils/IntelliLog.h>
#include <LibAMM.h>

void LibAMM::SIFTMatrixLoader::paraseConfig(INTELLI::ConfigMapPtr cfg) {
  filePath = cfg->tryString("filePath", "datasets/SIFT/siftsmall_base.fvecs", true);
}

void LibAMM::SIFTMatrixLoader::generateAB() {

  float *data = NULL;
  unsigned num, dim;

  // Step2. read in binary
  std::ifstream in(filePath, std::ios::binary);    //以二进制的方式打开文件
  if (!in.is_open()) {
    INTELLI_ERROR(
        "Double check your data path: " + filePath);
    exit(-1);
  }
  in.read((char *) &dim, 4);    //读取向量维度
  in.seekg(0, std::ios::end);    //光标定位到文件末尾
  std::ios::pos_type ss = in.tellg();    //获取文件大小（多少字节）
  size_t fsize = (size_t) ss;
  num = (unsigned) (fsize / (dim + 1) / 4);    //数据的个数
  data = new float[(size_t) num * (size_t) dim];

  in.seekg(0, std::ios::beg);    //光标定位到起始处
  for (size_t i = 0; i < num; i++) {
    in.seekg(4, std::ios::cur);    //光标向右移动4个字节
    in.read((char *) (data + i * dim), dim * 4);    //读取数据到一维数据data中
  }
  in.close();

  // Step3. convert to torch tensor and standardize the matrix
  torch::TensorOptions options(torch::kFloat32);
  B = torch::from_blob(data, {(int) num, (int) dim}, options).clone();

  // 3.1 Compute the mean and standard deviation along each feature (column)
  torch::Tensor mean = B.mean(/*dim=*/0);
  torch::Tensor std = B.std(/*dim=*/0);

  // 3.2 Standardize the matrix
  torch::Tensor standardizedB = (B - mean) / std;
  // torch::Tensor centeredB = B - mean;

  // 3.3 Check if need to resize
  B = standardizedB;
  // B = centeredB;

  A = B.t().contiguous(); //getting bug in int8 algorithm, as it traverse vertically in transpose

  int ACol = A.size(0);
  int ARow = A.size(1);
  int BCol = B.size(0);
  int BRow = B.size(1);
  INTELLI_INFO(
      "Generating [" + to_string(ACol) + "x" + to_string(ARow) + "]*[" + to_string(BCol) + "x" + to_string(BRow) + "]");

  delete[] data; // deallocate
}

//do nothing in abstract class
bool LibAMM::SIFTMatrixLoader::setConfig(INTELLI::ConfigMapPtr cfg) {
  paraseConfig(cfg);
  generateAB();
  return true;
}

torch::Tensor LibAMM::SIFTMatrixLoader::getA() {
  return A;
}

torch::Tensor LibAMM::SIFTMatrixLoader::getB() {
  return B;
}

// int main() {
//     LibAMM::MatrixLoaderTable mLoaderTable;
//     auto matLoaderPtr = mLoaderTable.findMatrixLoader("SIFT");
//     assert(matLoaderPtr);

//     INTELLI::ConfigMapPtr cfg = newConfigMap();
//     matLoaderPtr->setConfig(cfg);

//     auto A = matLoaderPtr->getA();
//     auto B = matLoaderPtr->getB();
//     std::cout << A.sizes() << endl;
//     std::cout << B.sizes() << endl;
// }
