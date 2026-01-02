/*! \file DataLoaderTable.h*/
//
// Created by tony on 10/05/23.
//

#ifndef CANDY_INCLUDE_DataLOADER_DataLOADERTABLE_H_
#define CANDY_INCLUDE_DataLOADER_DataLOADERTABLE_H_

#include <map>
#include <DataLoader/AbstractDataLoader.h>

namespace CANDY {
/**
 * @ingroup CANDY_DataLOADER
 * @{
 */
/**
 * @ingroup CANDY_DataLOADER_Table The Table to index all Data loaders
 * @{
 */
/**
 * @class DataLoaderTable DataLoader/DataLoaderTable.h
 * @brief The table class to index all Data loaders
 * @ingroup CANDY_DataLOADER
 * @note  Default behavior
* - create
* - (optional) call @ref registerNewDataLoader for new loader
* - find a loader by @ref findDataLoader using its tag
 * @note default tags
 * - random @ref RandomDataLoader
 * - fvecs @ref FVECSDataLoader
 * - hdf5 @ref HDF5DataLoader
 * - zipf @ref ZipfDataLoader
 * - expFamily @ref ExpFamilyDataLoader
 * - exp, the exponential distribution in  @ref ExpFamilyDataLoader
 * - beta, the beta distribution in  @ref ExpFamilyDataLoader
 * - gaussian, the beta distribution in  @ref ExpFamilyDataLoader
 * - poisson, the poisson distribution in  @ref ExpFamilyDataLoader
 */
class DataLoaderTable {
 protected:
  std::map<std::string, CANDY::AbstractDataLoaderPtr> loaderMap;
 public:
  /**
   * @brief The constructing function
   * @note  If new DataLoader wants to be included by default, please revise the following in *.cpp
   */
  DataLoaderTable();

  ~DataLoaderTable() {
  }

  /**
    * @brief To register a new loader
    * @param onew The new operator
    * @param tag THe name tag
    */
  void registerNewDataLoader(CANDY::AbstractDataLoaderPtr dnew, std::string tag) {
    loaderMap[tag] = dnew;
  }

  /**
   * @brief find a dataloader in the table according to its name
   * @param name The nameTag of loader
   * @return The DataLoader, nullptr if not found
   */
  CANDY::AbstractDataLoaderPtr findDataLoader(std::string name) {
    if (loaderMap.count(name)) {
      return loaderMap[name];
    }
    return nullptr;
  }

  /**
 * @ingroup CANDY_DataLOADER_Table
 * @typedef DataLoaderTablePtr
 * @brief The class to describe a shared pointer to @ref DataLoaderTable

 */
  typedef std::shared_ptr<class CANDY::DataLoaderTable> DataLoaderTablePtr;
/**
 * @ingroup CANDY_DataLOADER_Table
 * @def newDataLoaderTable
 * @brief (Macro) To creat a new @ref  DataLoaderTable under shared pointer.
 */
#define newDataLoaderTable std::make_shared<CANDY::DataLoaderTable>
};
/**
 * @}
 */
/**
 * @}
 */
} // CANDY

#endif //INTELLISTREAM_INCLUDE_DataLOADER_DataLOADERTABLE_H_
