/*! \file IntelliTensorOP.hpp*/
#ifndef _UTILS_IntelliTensorOP_H_
#define _UTILS_IntelliTensorOP_H_
#pragma once
#include <vector>
#include <torch/torch.h>
#include <ATen/ATen.h>
#include <assert.h>
#include <algorithm>
#include <iostream>
#include <fstream>
/**
 *  @ingroup INTELLI_UTIL
 *  @{
* @defgroup INTELLI_UTIL_INTELLItensor tensor operations
* @{
 * This package is used for some common tensor operations
*/
using namespace std;
using namespace torch;
namespace INTELLI {

/**
 * @ingroup INTELLI_UTIL_INTELLItensor
 * @typedef TensorPtr
 * @brief The class to describe a shared pointer to torch::Tensor
 */
typedef std::shared_ptr<torch::Tensor> TensorPtr;
/**
 * @ingroup INTELLI_UTIL_INTELLItensor
 * @def newTensor
 * @brief (Macro) To creat a new @ref Tensor under shared pointer.
 */
#define  newTensor make_shared<torch::Tensor>

/**
 * @ingroup INTELLI_UTIL_INTELLItensor
 * @class INTELLITensorOP Utils/INTELLITensorOP.hpp
 * @brief The common tensor functions packed in class
 * @note Most are static functions
 */
class IntelliTensorOP {
 public:
  IntelliTensorOP() {}
  ~IntelliTensorOP() {}
  /**
   * @brief delete a row of a tensor
   * @param t the tensor pointer
   * @param rowIdx the row to be deleted
   * @return bool, whether the operation is successful
  */
  static bool deleteRow(torch::Tensor *tensor, int64_t rowIdx) {
    int64_t rowIndexToDelete = rowIdx;
    if (rowIndexToDelete >= tensor->size(0)) {
      return false;
    }
    // Get the number of rows and columns in the original tensor
    int64_t numRows = tensor->size(0);
    // Create a mask to select rows excluding the one to delete
    auto rowMask = torch::arange(numRows).to(torch::kLong).ne(rowIndexToDelete);

    // Use the mask to create a new tensor without the specified row
    *tensor = tensor->index({rowMask.nonzero().squeeze()});
    return true;
  }
  /**
   * @brief delete a row of a tensor
   * @param t the tensor under shared pointer
   * @param rowIdx the row to be deleted
   * @return bool, whether the operation is successful
  */
  static bool deleteRow(TensorPtr tp, int64_t rowIdx) {
    return deleteRow(tp.get(), rowIdx);
  }
  /**
  * @brief delete rows of a tensor
  * @param t the tensor pointer
  * @param rowIdx the rows to be deleted
  * @return bool, whether the operation is successful
 */
  static bool deleteRows(torch::Tensor *tensor, std::vector<int64_t> &rowIdx) {
    // Get the number of rows and columns in the original tensor
    int64_t numRows = tensor->size(0);
    // Create a mask to select rows excluding the ones to delete
    auto rowMask = torch::ones({numRows}).to(torch::kLong);
    for (int64_t row : rowIdx) {
      if (row >= numRows) {
        return false;
      }
      rowMask[row] = 0;
    }
    // Use the mask to create a new tensor without the specified row
    *tensor = tensor->index({rowMask.nonzero().squeeze()});
    return true;
  }
  /**
  * @brief delete rows of a tensor
  * @param t the tensor under shared pointer
  * @param rowIdx the rows to be deleted
  * @return bool, whether the operation is successful
 */
  static bool deleteRows(TensorPtr tp, std::vector<int64_t> &rowIdx) {
    return deleteRows(tp.get(), rowIdx);
  }

  /**
  * @brief append rows to the head tensor
  * @param tHead the head tensor, using pointer
  * @param tTail the tail tensor, using poniter
  * @note The number of columnes must be matched
  * @return bool, whether the operation is successful
  */
  static bool appendRows(torch::Tensor *tHead, torch::Tensor *tTail) {
    if (tHead->size(1) != tTail->size(1)) {
      return false;
    }

    // Use torch::cat to concatenate the original tensor and the new row
    *tHead = torch::cat({*tHead, *tTail}, 0);
    return true;
  }
  /**
* @brief append rows to the head tensor
* @param tHead the head tensor, using shared pointer
* @param tTail the tail tensor, using shared pointer
* @note The number of columnes must be matched
* @return bool, whether the operation is successful
*/
  static bool appendRows(TensorPtr tHeadP, TensorPtr tTailP) {
    return appendRows(tHeadP.get(), tTailP.get());
  }

  /**
 * @brief insert rows to the head tensor
 * @param tHead the head tensor, using pointer
 * @param tTail the tail tensor, using poniter
 * @param startRow, the starRow of tTail to be appeared afeter insertion
 * @note The number of columnes must be matched
 *  @return bool, whether the operation is successful
 */
  static bool insertRows(torch::Tensor *tHead, torch::Tensor *tTail, int64_t startRow) {
    if (tHead->size(1) != tTail->size(1)) {
      return false;
    }
    int64_t insertRow = startRow;
    torch::Tensor topPart = tHead->index({torch::indexing::Slice(torch::indexing::None, insertRow)});
    torch::Tensor bottomPart = tHead->index({torch::indexing::Slice(insertRow, torch::indexing::None)});
    // Concatenate the parts with the tensor to insert in between
    *tHead = torch::cat({topPart, *tTail, bottomPart});
    return true;
  }
  /**
 * @brief insert rows to the head tensor
 * @param tHead the head tensor, using shared pointer
 * @param tTail the tail tensor, using shared poniter
 * @param startRow, the starRow of tTail to be appeared afeter insertion
 *  @return bool, whether the operation is successful
 */
  static bool insertRows(TensorPtr tHead, TensorPtr tTail, int64_t startRow) {
    return insertRows(tHead.get(), tTail.get(), startRow);
  }
  /**
 * @brief edit rows in the head tensor
 * @param tHead the head tensor, using pointer
 * @param tTail the tail tensor, using poniter
 * @param startRow, the starRow of tTail to be appeared afeter insertion
 * @note The number of columnes must be matched
 * @return bool, whether the operation is successful
 */
  static bool editRows(torch::Tensor *tHead, torch::Tensor *tTail, int64_t startRow) {
    if (tHead->size(1) != tTail->size(1)) {
      return false;
    }
    int64_t endRow = startRow + tTail->size(0);
    if (endRow > tHead->size(0)) {
      tHead->slice(/*dim=*/0, /*start=*/startRow, /*end=*/tHead->size(0)) =
          tTail->slice(0, 0, tHead->size(0) - startRow);
    } else {
      tHead->slice(/*dim=*/0, /*start=*/startRow, /*end=*/endRow) = *tTail;
    }
    return true;
  }
  /**
 * @brief edit rows in the head tensor
 * @param tHead the head tensor, using shared pointer
 * @param tTail the tail tensor, using shared poniter
 * @param startRow, the starRow of tTail to be appeared afeter insertion
 * @note The number of columnes must be matched
 */
  static bool editRows(TensorPtr tHead, TensorPtr tTail, int64_t startRow) {
    return editRows(tHead.get(), tTail.get(), startRow);
  }
  /**
  * @brief delete a row of a tensor, shift this row with last nnz, and does not re-create the tensor
  * @param tensor the tensor pointer
  * @param rowIdx the row to be deleted
  * @param *lastNNZ the original last non zero row in tensor, will be changed
  * @return bool, whether the operation is successful
 */
  static bool deleteRowBufferMode(torch::Tensor *tensor, int64_t rowIdx, int64_t *lastNNZ) {
    int64_t rowIndexToDelete = rowIdx;
    if (rowIndexToDelete >= tensor->size(0) || *lastNNZ >= tensor->size(0) || rowIndexToDelete > *lastNNZ) {
      return false;
    }

    // Get the number of rows and columns in the original tensor
    tensor->slice(/*dim=*/0, /*start=*/rowIndexToDelete, /*end=*/rowIndexToDelete + 1) =
        tensor->slice(0, *lastNNZ, *lastNNZ + 1);
    // Use the mask to create a new tensor without the specified row
    tensor->slice(0, *lastNNZ, *lastNNZ + 1) = torch::zeros({(int64_t) 1, tensor->size(1)});
    if (*lastNNZ > 0) {
      *lastNNZ = *lastNNZ - 1;
    }
    return true;
  }
  /**
   * @brief delete a row of a tensor, shift this row with last nnz, and does not re-create the tensor
   * @param tensor the tensor shared pointer
   * @param rowIdx the row to be deleted
   * @param *lastNNZ the original last non zero row in tensor, will be changed
   * @return bool, whether the operation is successful
  */
  static bool deleteRowBufferMode(TensorPtr tensor, int64_t rowIdx, int64_t *lastNNZ) {
    return deleteRowBufferMode(tensor.get(), rowIdx, lastNNZ);
  }
  /**
* @brief delete rows of a tensor, shift this row with last nnz, and does not re-create the tensor
* @param tensor the tensor pointer
* @param rowIdx the rows to be deleted
* @param *lastNNZ the original last non zero row in tensor, will be changed
* @return bool, whether the operation is successful
*/
  static bool deleteRowsBufferMode(torch::Tensor *tensor, std::vector<int64_t> &rowIdx, int64_t *lastNNZ) {
    std::sort(rowIdx.begin(), rowIdx.end(), std::greater<int64_t>());
    int64_t rowIndexMax = rowIdx[0];
    if (rowIndexMax >= tensor->size(0) || *lastNNZ >= tensor->size(0) || rowIndexMax > *lastNNZ) {
      return false;
    }
    //int64_t deletedRows=0;
    for (int64_t value : rowIdx) {
      //std::cout<<value<<value-deletedRows<<std::endl;
      deleteRowBufferMode(tensor, value, lastNNZ);
      //deletedRows++;
    }
    return true;
  }
  /**
  * @brief delete rows of a tensor, shift this row with last nnz, and does not re-create the tensor
  * @param tensor the tensor shared pointer
  * @param rowIdx the rows to be deleted
  * @param *lastNNZ the original last non zero row in tensor, will be changed
  * @return bool, whether the operation is successful
 */
  static bool deleteRowsBufferMode(TensorPtr tensor, std::vector<int64_t> &rowIdx, int64_t *lastNNZ) {
    return deleteRowsBufferMode(tensor.get(), rowIdx, lastNNZ);
  }
  /**
 * @brief append rows to the head tensor, under the buffer mode
 * @param tHead the head tensor, using pointer
 * @param tTail the tail tensor, using poniter
 * @param *lastNNZ the original last non zero row in tHead, will be changed
 * @param customExpandSize the customized expansion size of buffer,
 * @note The number of columnes must be matched
 * @return bool, whether the operation is successful
 */
  static bool appendRowsBufferMode(torch::Tensor *tHead,
                                   torch::Tensor *tTail,
                                   int64_t *lastNNZ,
                                   int64_t customExpandSize = 0) {
    if (tHead->size(1) != tTail->size(1)) {
      return false;
    }
    if (*lastNNZ + tTail->size(0) < tHead->size(0)) {   //std::cout<<"no need to expand"<<std::endl;
      //return true;
      if (editRows(tHead, tTail, *lastNNZ + 1)) {
        *lastNNZ = *lastNNZ + tTail->size(0);
        return true;
      }
    } else {
      //std::cout<<"need to expand"<<std::endl;
      // return true;
      int64_t requiredExpandSize = *lastNNZ + tTail->size(0) + 1 - tHead->size(0);
      int64_t expandSize = std::max(requiredExpandSize, customExpandSize);
      *tHead = torch::cat({*tHead, torch::zeros({expandSize, tHead->size(1)})}, 0);
      if (editRows(tHead, tTail, *lastNNZ + 1)) {
        *lastNNZ = *lastNNZ + tTail->size(0);
        return true;
      }
    }
    return false;
  }
  /**
* @brief append rows to the head tensor, under the buffer mode
* @param tHead the head tensor, using shared pointer
* @param tTail the tail tensor, using sahred poniter
* @param *lastNNZ the original last non zero row in tHead, will be changed
* @param customExpandSize the customized expansion size of buffer,
* @note The number of columnes must be matched
* @return bool, whether the operation is successful
*/
  static bool appendRowsBufferMode(TensorPtr tHead, TensorPtr tTail, int64_t *lastNNZ, int64_t customExpandSize = 0) {
    return appendRowsBufferMode(tHead.get(), tTail.get(), lastNNZ, customExpandSize);
  }
  /**
   * @brief convert a tensor to flat binary form, i.e., <rows> <cols> <flat data>
   * @param A the tensor
   * @return std::vector<uint8_t> the binary form
   */
  static std::vector<uint8_t> tensorToFlatBin(torch::Tensor *A) {
    auto A_size = A->sizes();

    int64_t rows1 = A_size[0];
    int64_t cols1 = A_size[1];
    uint64_t packedSize = (A->numel()) * sizeof(float) + sizeof(int64_t) * 2;
    std::vector<uint8_t> ru(packedSize);
    auto ruIter = ru.begin();
    std::copy(reinterpret_cast<const uint8_t *>(&rows1),
              reinterpret_cast<const uint8_t *>(&rows1) + sizeof(int64_t),
              ruIter);
    ruIter += sizeof(int64_t);
    std::copy(reinterpret_cast<const uint8_t *>(&cols1),
              reinterpret_cast<const uint8_t *>(&cols1) + sizeof(int64_t),
              ruIter);
    // Copy the binary data of the first tensor
    std::copy(reinterpret_cast<const uint8_t *>(A->data_ptr<float>()),
              reinterpret_cast<const uint8_t *>(A->data_ptr<float>() + A->numel()),
              ru.begin() + sizeof(int64_t) * 2);
    return ru;
  }
  /**
  * @brief convert a tensor to flat binary form and stored in a file, i.e., <rows> <cols> <flat data>
  * @param A the tensor
   * @param fname the name of file
  * @return  bool, the output is successful or not
  */
  static bool tensorToFile(torch::Tensor *A, std::string fname) {
    std::ofstream file(fname, std::ios::binary);
    if (!file.is_open()) {
      return false;
    }
    auto vec = tensorToFlatBin(A);
    file.write(reinterpret_cast<const char *>(vec.data()), vec.size());
    // Check for write errors
    if (!file) {
      return false;
    }
    // Close the file
    file.close();
    return true;
  }
  /**
  * @brief load a tensor from flat binary form, i.e., <rows> <cols> <flat data>
  * @param A the tensor
  * @param ru the binart in std::vector<uint8_t>
  * @return  bool, the load is successful or not
  */
  static bool tensorFromFlatBin(torch::Tensor *A, std::vector<uint8_t> &ru) {
    int64_t rows1;
    int64_t cols1;
    if (ru.size() < sizeof(int64_t) * 2) {
      return false;
    }
    std::copy(ru.begin(), ru.begin() + sizeof(int64_t), reinterpret_cast<uint8_t *>(&rows1));
    std::copy(ru.begin() + sizeof(int64_t), ru.begin() + 2 * sizeof(int64_t), reinterpret_cast<uint8_t *>(&cols1));
    uint64_t expectedSize = (rows1 * cols1) * sizeof(float) + sizeof(int64_t) * 2;
    if (ru.size() < expectedSize) {
      return false;
    }
    int64_t tensorStart = 2 * sizeof(int64_t);
    int64_t tensorASize = rows1 * cols1 * sizeof(float);
    *A = torch::from_blob(ru.data() + tensorStart,
                          {(int64_t) (tensorASize / sizeof(float))},
                          torch::kFloat32).clone().reshape({rows1, cols1});
    return true;
  }
  /**
  * @brief load a tensor from a file of flat binary form, i.e., <rows> <cols> <flat data>
  * @param A the tensor
  * @param fname the name of file
  * @return  bool, the load is successful or not
  */
  static bool tensorFromFile(torch::Tensor *A, std::string fname) {
    std::ifstream file(fname, std::ios::binary);
    if (!file.is_open()) {
      return false;
    }
    // Determine the size of the file
    file.seekg(0, std::ios::end);
    std::streamsize fileSize = file.tellg();
    file.seekg(0, std::ios::beg);

    // Create a vector to store the binary data
    std::vector<uint8_t> binaryData(fileSize);

    // Read the binary data from the file
    file.read(reinterpret_cast<char *>(binaryData.data()), fileSize);

    // Check for read errors
    if (!file) {
      return false;
    }
    // Close the file
    file.close();
    return tensorFromFlatBin(A, binaryData);
  }
  /**
 * @brief to sample some rows of an input tensor and return
 * @param a the input tensor
 * @param sampledRows the number of rows to be sampled
 * @return  the result tensor
 */
  static torch::Tensor rowSampling(torch::Tensor &a, int64_t sampledRows) {
    if (sampledRows >= a.size(0) || sampledRows <= 0) {
      return a.clone();
    }
    auto indices = torch::randperm(a.size(0), torch::kLong).slice(/*dim=*/0, /*start=*/0, /*end=*/sampledRows);
    // Use the random indices to select rows from tensor A
    auto ru = a.index_select(/*dim=*/0, indices);
    return ru;
  }
  /**
 * @brief to normalize the tensor in each column, using l2
 * @param a the input tensor
 * @return  the result tensor
 */
  static torch::Tensor l2Normalize(torch::Tensor &a) {
    /* torch::Tensor min_value = std::get<0>(torch::min(a,0));
     torch::Tensor max_value =  std::get<0>(torch::max(a,0));
     // Normalize the tensor to -1 to 1
     torch::Tensor normalized_tensor = 2 * (a - min_value) / (max_value - min_value) - 1;
     return normalized_tensor;*/
    torch::Tensor norm = torch::norm(a, 2, 0, true);
    // Divide the input tensor by its norm
    return a / norm;
  }
};
}
/**
 * @}
 */
/**
 * @}
 */
#endif
