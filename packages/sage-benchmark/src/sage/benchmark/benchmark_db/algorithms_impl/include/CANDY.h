/*! \file CANDY.h*/
//
// Created by tony on 22/12/23.
// Simplified version for benchmark_anns
//

#ifndef INTELLISTREAM_CANDY_H
#define INTELLISTREAM_CANDY_H

#include <torch/torch.h>
#include <iostream>
#include <torch/script.h>
#include <string>
#include <memory>

/**
* @defgroup CANDY_lib The main body of CANDY's indexing approaches
* @{
**/
#include <IndexTable.h>

/**
* @defgroup   CANDY_lib_bottom The bottom tier of indexing alorithms
* @{
**/
#include <AbstractIndex.h>
#include <FlatIndex.h>

/**
 * @}
 */


/**
* @defgroup   CANDY_lib_container The upper tier of indexing alorithms, can be container of other indexing ways
* @{
**/
#include <ParallelPartitionIndex.h>
/**
 * @}
 */

/**
 * @}
 */

/**
* @defgroup  CANDY_DataLOADER The data loader of CANDY
* @{
* We define the data loader classes . here
**/
#include <DataLoader/AbstractDataLoader.h>
#include <DataLoader/DataLoaderTable.h>
#include <DataLoader/RandomDataLoader.h>
#include <DataLoader/FVECSDataLoader.h>
/**
 * @}
 *
 */

/**
* @defgroup INTELLI_UTIL Shared Utils
* @{
*/
#include <Utils/ConfigMap.hpp>
#include <Utils/Meters/MeterTable.h>

/**
 * @ingroup INTELLI_UTIL
* @defgroup INTELLI_UTIL_OTHERC20 Other common class or package under C++20 standard
* @{
* This package covers some common C++20 new features, such as std::thread to ease the programming
*/
#include <Utils/C20Buffers.hpp>
#include <Utils/ThreadPerf.hpp>
#include <papi_config.h>
#if CANDY_PAPI == 1
#include <Utils/ThreadPerfPAPI.hpp>
#endif
#include <Utils/IntelliLog.h>
#include <Utils/UtilityFunctions.h>
#include <Utils/IntelliTensorOP.hpp>
#include <Utils/IntelliTimeStampGenerator.h>

/**
 * @}
 */
/**
 *
 * @}
 */

#endif
