/*! \file RBTDataLoader.h*/
//
// Created by tony on 10/05/23.
//

#ifndef CANDY_INCLUDE_DATALOADER_RBTDataLoader_H_
#define CANDY_INCLUDE_DATALOADER_RBTDataLoader_H_

#include <Utils/ConfigMap.hpp>
#include <Utils/IntelliTensorOP.hpp>
#include <assert.h>
//#include <torch/torch.h>
#include <memory>
#include <DataLoader/AbstractDataLoader.h>
namespace CANDY {
/**
 * @ingroup CANDY_DataLOADER
 * @{
 */
/**
 * @ingroup CANDY_DataLOADER_RBT The dataloader OF raw binary tensor (RBT)
 * @{
 */
/**
 * @class RBTDataLoader DataLoader/RBTDataLoader.h
 * @brief The class of RBT data loader,
 * @ingroup CANDY_DataLOADER
 * @note:
 * - Must have a global config by @ref setConfig
 * - This one support out-of-memory large data, but not work well with onlineInsert benchmark, please use onlineCUD instead
 * @note  Default behavior
* - create
* - call @ref setConfig, this function will also generate the tensor A and B correspondingly
* - call @ref getDataAt to get the raw data
* - call  @ref getQueryAt to get the query
* @note parameters of config
* - vecDim, the dimension of vectors, default 768, I64
* - vecVolume, the volume of vectors, default 1000, I64
* - querySize, the size of query, default 10, I64
* - seed, the random seed, default 7758258, I64
* - dataPath, the path to the data file, datasets/rbt/example.rbt, String
* - normalizeTensor, whether or not normalize the tensors in L2, 1 (yes), I64
* - useSeparateQuery, whether or not load query separately, 1, I64
* - queryPath, the path to query file,  datasets/rbt/example.rbt. String
*  @note: default name tags
 * "rbt": @ref RBTDataLoader
 */
class RBTDataLoader : public AbstractDataLoader {
 protected:
  int64_t vecDim, vecVolume, querySize, useSeparateQuery;
  std::string dataPath,queryPath;
  std::vector<int64_t> dataSizes;
 public:
  RBTDataLoader() = default;

  ~RBTDataLoader() = default;

  /**
     * @brief Set the GLOBAL config map related to this loader
     * @param cfg The config map
      * @return bool whether the config is successfully set
      * @note
     */
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);

  /**
   * @brief get the data tensor at specific offset
   * @note implement and use this when the whole data tensor does not fit into main memory
   * @return the generated data tensor
   */
  virtual torch::Tensor getDataAt(int64_t startPos, int64_t endPos);

  /**
   * @brief get the data tensor
   * @return the generated data tensor
   */
  virtual torch::Tensor getData();
  /**
  * @brief get the query tensor
  * @return the generated query tensor
  */
  virtual torch::Tensor getQuery();

  /**
   * @brief get the dimension of data
   * @return the dimension
   */
  virtual int64_t getDimension();
  /**
   * @brief get the number of rows of data
   * @return the rows
   */
  virtual int64_t size();
  /**
   * @brief create a RBT file from tensor
   * @param fname the file name
   * @param t the tensor to initialize RBT
   * @return whether it is successful
   */
  static int64_t createRBT(std::string fname,torch::Tensor &t);
  /**
   * @brief Append tensor to an RBT file
   * @param fname the file name
   * @param t the tensor to initialize RBT
   * @return whether it is successful
   */
  static int64_t appendTensorToRBT(std::string fname,torch::Tensor &t);
  /**
   * @brief read certain rows form RBT file
   * @param fname the file name
   * @param startPos the start position of rows
   * @param endPos the end position of rows
   * @return the read tensor
   */
  static torch::Tensor readRowsFromRBT(std::string fname,int64_t startPos, int64_t endPos);
  /**
   * @brief get the sizes of RBT file
   * @param fname the file name
   * @return the vector of size, [0] for rows, [1] for cols
   */
  static std::vector<int64_t> getSizesFromRBT(std::string fname);
};

/**
 * @ingroup CANDY_MatrixLOADER_Random
 * @typedef RBTDataLoaderPtr
 * @brief The class to describe a shared pointer to @ref RBTDataLoader

 */
typedef std::shared_ptr<class CANDY::RBTDataLoader> RBTDataLoaderPtr;
/**
 * @ingroup CANDY_MatrixLOADER_Random
 * @def newRBTDataLoader
 * @brief (Macro) To creat a new @ref RBTDataLoader under shared pointer.
 */
#define newRBTDataLoader std::make_shared<CANDY::RBTDataLoader>
/**
 * @}
 */
/**
 * @}
 */
} // CANDY

#endif //CANDY_INCLUDE_MATRIXLOADER_RBTDataLoader_H_
