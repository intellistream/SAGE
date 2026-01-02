//
// Created by yuhao on 6/30/23.
//

#ifndef INTELLISTREAM_SIFTMATRIXLOADER_H
#define INTELLISTREAM_SIFTMATRIXLOADER_H

#include <MatrixLoader/AbstractMatrixLoader.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_MatrixLOADER
 * @{
 */
/**
 * @ingroup LibAMM_MatrixLOADER_SIFT The SIFTsmall dataset generator
 * @{
 */
/**
 * @class SIFTMatrixLoader MatrixLoader/SIFTMatrixLoader.h
 * @brief The SIFT class of matrix loader http://corpus-texmex.irisa.fr/
 * @ingroup LibAMM_MatrixLOADER_SIFT
 * @note:
 * - Must have a global config by @ref setConfig
 * @note  Default behavior
* - create
* - call @ref setConfig, this function will also generate the tensor A and B correspondingly
* - call @ref getA and @ref getB (assuming we are benchmarking torch.mm(A,B))
 * @note: does not need config
 * @note: default name tags
 * "SIFT": @ref SIFTMatrixLoader
 */
class SIFTMatrixLoader : public AbstractMatrixLoader {
 protected:
  torch::Tensor A, B;
  std::string filePath="datasets/SIFT/siftsmall_base.fvecs";

  /**
   * @brief Inline logic of reading a config file
   * @param cfg the config
   */
  void paraseConfig(INTELLI::ConfigMapPtr cfg);

  /**
   * @brief inline logic of generating A and B
   */
  void generateAB();

 public:
  SIFTMatrixLoader() = default;

  ~SIFTMatrixLoader() = default;

  /**
     * @brief Set the GLOBAL config map related to this loader
     * @param cfg The config map
      * @return bool whether the config is successfully set
      * @note
     */
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);

  /**
   * @brief get the A matrix
   * @return the generated A matrix
   */
  virtual torch::Tensor getA();

  /**
  * @brief get the B matrix
  * @return the generated B matrix
  */
  virtual torch::Tensor getB();
};

/**
 * @ingroup LibAMM_MatrixLOADER_SIFT
 * @typedef SIFTMatrixLoaderPtr
 * @brief The class to describe a shared pointer to @ref SIFTMatrixLoader

 */
typedef std::shared_ptr<class LibAMM::SIFTMatrixLoader> SIFTMatrixLoaderPtr;
/**
 * @ingroup LibAMM_MatrixLOADER_SIFT
 * @def newSIFTMatrixLoader
 * @brief (Macro) To creat a new @ref SIFTMatrixLoader under shared pointer.
 */
#define newSIFTMatrixLoader std::make_shared<LibAMM::SIFTMatrixLoader>
/**
 * @}
 */
/**
 * @}
 */
}
#endif //INTELLISTREAM_SIFTMATRIXLOADER_H
