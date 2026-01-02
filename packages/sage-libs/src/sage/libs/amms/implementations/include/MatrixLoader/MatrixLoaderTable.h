//
// Created by tony on 10/05/23.
//

#ifndef INTELLISTREAM_INCLUDE_MATRIXLOADER_MATRIXLOADERTABLE_H_
#define INTELLISTREAM_INCLUDE_MATRIXLOADER_MATRIXLOADERTABLE_H_

#include <map>
#include <MatrixLoader/AbstractMatrixLoader.h>

namespace LibAMM {
/**
 * @ingroup LibAMM_MatrixLOADER
 * @{
 */
/**
 * @ingroup LibAMM_MatrixLOADER_Table The Table to index all matrix loaders
 * @{
 */
/**
 * @class MatrixLoaderTable MatrixLoader/MatrixLoaderTable.h
 * @brief The table class to index all matrix loaders
 * @ingroup LibAMM_MatrixLOADER_Table
 * @note  Default behavior
* - create
* - (optional) call @ref registerNewDataLoader for new loader
* - find a loader by @ref findMatrixLoader using its tag
 * @note default tags
 * - random @ref RandomMatrixLoader
 * - sparse @ref SparseMatrixLoader
 */
class MatrixLoaderTable {
 protected:
  std::map<std::string, LibAMM::AbstractMatrixLoaderPtr> loaderMap;
 public:
  /**
   * @brief The constructing function
   * @note  If new MatrixLoader wants to be included by default, please revise the following in *.cpp
   */
  MatrixLoaderTable();

  ~MatrixLoaderTable() {
  }

  /**
    * @brief To register a new loader
    * @param onew The new operator
    * @param tag THe name tag
    */
  void registerNewDataLoader(LibAMM::AbstractMatrixLoaderPtr dnew, std::string tag) {
    loaderMap[tag] = dnew;
  }

  /**
   * @brief find a dataloader in the table according to its name
   * @param name The nameTag of loader
   * @return The MatrixLoader, nullptr if not found
   */
  LibAMM::AbstractMatrixLoaderPtr findMatrixLoader(std::string name) {
    if (loaderMap.count(name)) {
      return loaderMap[name];
    }
    return nullptr;
  }

  /**
 * @ingroup LibAMM_MatrixLOADER_Table
 * @typedef MatrixLoaderTablePtr
 * @brief The class to describe a shared pointer to @ref MatrixLoaderTable

 */
  typedef std::shared_ptr<class LibAMM::MatrixLoaderTable> MatrixLoaderTablePtr;
/**
 * @ingroup LibAMM_MatrixLOADER_Table
 * @def newMatrixLoaderTable
 * @brief (Macro) To creat a new @ref  MatrixLoaderTable under shared pointer.
 */
#define newMatrixLoaderTable std::make_shared<LibAMM::MatrixLoaderTable>
};
/**
 * @}
 */
/**
 * @}
 */
} // LibAMM

#endif //INTELLISTREAM_INCLUDE_MATRIXLOADER_MATRIXLOADERTABLE_H_
