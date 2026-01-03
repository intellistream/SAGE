//
// Created by yuhao on 6/30/23.
//

#ifndef INTELLISTREAM_MediaMillMATRIXLOADER_H
#define INTELLISTREAM_MediaMillMATRIXLOADER_H

#include <MatrixLoader/CCAMatrixLoader.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_MatrixLOADER
 * @{
 */
/**
 * @ingroup LibAMM_MatrixLOADER_MediaMill The MediaMill 2005-2006 Feature Label Matrix
 * @{
 */
/**
 * @class MediaMillMatrixLoader MatrixLoader/MediaMillMatrixLoader.h
 * @brief Load MediaMill 2005-2006 data (https://rdrr.io/github/fcharte/mldr.datasets/man/mediamill.html)
 * @ingroup LibAMM_MatrixLOADER_MediaMill
 * @note:
 * - Must have a global config by @ref setConfig
 * @note  Default behavior
* - create
* - call @ref setConfig, this function will also generate the tensor A and B correspondingly
* - call @ref getA and @ref getB (assuming we are benchmarking torch.mm(A,B))
 * @note: does not need config
 * @note: default name tags
 * "MediaMill": @ref MediaMillMatrixLoader
 */
class MediaMillMatrixLoader : public CCAMatrixLoader {
 protected:
  std::string filePath="datasets/MediaMill/MediaMill.pth";
  torch::Tensor A, B, At, Bt;
  torch::Tensor Sxx, Syy, Sxy;
  torch::Tensor SxxNegativeHalf, SyyNegativeHalf, M, M1;
  torch::Tensor correlation;

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
  MediaMillMatrixLoader() = default;

  ~MediaMillMatrixLoader() = default;

  /**
     * @brief Set the GLOBAL config map related to this loader
     * @param cfg The config map
      * @return bool whether the config is successfully set
      * @note
     */
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);

  /**
     * @brief Calulate the correlation by mm, and generate tensor Sxx, Sxy, Syy, M, correlation
     */
  virtual void calculate_correlation();

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

  /**
   * @brief get the transpose of A matrix
   * @return the A.t().contiguous() matrix, which is not a view but has its own memory space
   */
  virtual torch::Tensor getAt();

  /**
  * @brief get the transpose of B matrix
  * @return the B.t().contiguous() matrix, which is not a view but has its own memory space
  */
  virtual torch::Tensor getBt();

  /**
  * @brief get the Sxx matrix
  * @return the generated Sxx matrix by calling calculate_correlation()
  */
  virtual torch::Tensor getSxx();

  /**
  * @brief get the Sxyymatrix
  * @return the generated Syy matrix by calling calculate_correlation()
  */
  virtual torch::Tensor getSyy();

  /**
  * @brief get the Sxy matrix
  * @return the generated Sxy matrix by calling calculate_correlation()
  */
  virtual torch::Tensor getSxy();

  /**
  * @brief get the SxxNegativeHalf matrix
  * @return the generated SxxNegativeHalf matrix by calling calculate_correlation()
  */
  virtual torch::Tensor getSxxNegativeHalf();

  /**
  * @brief get the SyyNegativeHalf matrix
  * @return the generated SyyNegativeHalf matrix by calling calculate_correlation()
  */
  virtual torch::Tensor getSyyNegativeHalf();

  /**
  * @brief M = mm(mm(SxxNegativeHalf.t(), Sxy), SyyNegativeHalf)
  * @return the generated M matrix by calling calculate_correlation()
  */
  virtual torch::Tensor getM();

  /**
  * @brief M1 = mm(SxxNegativeHalf.t(), Sxy)
  * @return the generated M1 matrix by calling calculate_correlation()
  */
  virtual torch::Tensor getM1();

  /**
  * @brief get the correlation value
  * @return the generated correlation by calling calculate_correlation()
  */
  virtual torch::Tensor getCorrelation();
};

/**
 * @ingroup LibAMM_MatrixLOADER_MediaMill
 * @typedef MediaMillMatrixLoaderPtr
 * @brief The class to describe a shared pointer to @ref MediaMillMatrixLoader

 */
typedef std::shared_ptr<class LibAMM::MediaMillMatrixLoader> MediaMillMatrixLoaderPtr;
/**
 * @ingroup LibAMM_MatrixLOADER_MediaMill
 * @def newMediaMillMatrixLoader
 * @brief (Macro) To creat a new @ref MediaMillMatrixLoader under shared pointer.
 */
#define newMediaMillMatrixLoader std::make_shared<LibAMM::MediaMillMatrixLoader>
/**
 * @}
 */
/**
 * @}
 */
}
#endif //INTELLISTREAM_MediaMillMATRIXLOADER_H
