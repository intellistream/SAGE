/*! \file HDF5DataLoader.h*/
//
// Created by tony on 10/05/23.
//

#ifndef CANDY_INCLUDE_DATALOADER_HDF5DataLoader_H_
#define CANDY_INCLUDE_DATALOADER_HDF5DataLoader_H_

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
 * @class HDF5DataLoader DataLoader/HDF5DataLoader.h
 * @brief The class for loading *.hdf5 or *.h5 file, as specified in https://github.com/HDFGroup/hdf5
 * @ingroup CANDY_DataLOADER
 * @note:
 * - Must have a global config by @ref setConfig
 * @note  Default behavior
* - create
* - call @ref setConfig, this function will also generate the tensor A and B correspondingly
* - call @ref getData to get the raw data
* - call  @ref getQuery to get the query
* @note parameters of config
* - vecDim, the dimension of vectors, default 512 (for sun dataset), I64
* - vecVolume, the volume of vectors, default 10000, I64
* - normalizeTensor, whether or not normalize the tensors in L2, 1 (yes), I64
* - dataPath, the path to the data file, datasets/hdf5/sun/sun.hdf5, String
* - useSeparateQuery, whether or not load query separately, 1, I64
* - queryNoiseFraction, the fraction of noise in query, default 0, allow 0~1, Double
 * - no effect when query is loaded from separate file
* - querySize, the size of query, default 10, I64
* - seed, the random seed, default 7758258, I64
*  @note: default name tags
* - hdf5: @ref HDF5DataLoader
 */
class HDF5DataLoader : public AbstractDataLoader {
 protected:
  torch::Tensor A, B;
  int64_t vecDim, vecVolume, querySize, seed;
  int64_t normalizeTensor;
  double queryNoiseFraction;
  int64_t useSeparateQuery;
  bool generateData(std::string fname);
  bool generateQuery(std::string fname);

 public:
  HDF5DataLoader() = default;

  ~HDF5DataLoader() = default;

  /**
     * @brief Set the GLOBAL config map related to this loader
     * @param cfg The config map
      * @return bool whether the config is successfully set
      * @note
     */
  virtual bool setConfig(INTELLI::ConfigMapPtr cfg);

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
   * @brief the inline function to load tensor from *h5 or *.hdf5 file
   * @param fname the name of file
   * @param attr the attribute in hdf5 file
   * @return the genearetd tensor
   */
  static torch::Tensor tensorFromHDF5(std::string fname, std::string attr);
};

/**
 * @ingroup CANDY_MatrixLOADER_HDF5
 * @typedef HDF5DataLoaderPtr
 * @brief The class to describe a shared pointer to @ref HDF5DataLoader

 */
typedef std::shared_ptr<class CANDY::HDF5DataLoader> HDF5DataLoaderPtr;
/**
 * @ingroup CANDY_MatrixLOADER_HDF5
 * @def newHDF5DataLoader
 * @brief (Macro) To creat a new @ref HDF5DataLoader under shared pointer.
 */
#define newHDF5DataLoader std::make_shared<CANDY::HDF5DataLoader>
/**
 * @}
 */
} // CANDY

#endif //CANDY_INCLUDE_MATRIXLOADER_HDF5DataLoader_H_
