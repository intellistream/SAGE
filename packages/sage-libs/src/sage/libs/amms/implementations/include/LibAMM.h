/*! \file LibAMM.h*/
//
// Created by tony on 22/11/22.
//

#ifndef INTELLISTREAM_LibAMM_H
#define INTELLISTREAM_LibAMM_H

#include <torch/torch.h>
#include <iostream>
#include <torch/script.h>
#include <string>
#include <memory>
/**
 *
 * @mainpage Introduction
 * This project is for benchmarking common (approximate) matrix multiplication algorithms under various archeitectures in as streaming setting
 * @section BENCH_MARK Benchmark Tips
 * usage: ./benchmark [configfile]
 * @note Require configs in configfile:
    * - aRow (U64) the rows of tensor A, required by @ref RandomMatrixLoader, @ref SparseMatrixLoader
    * - aCol (U64) the columns of tensor A, required by @ref RandomMatrixLoader, @ref SparseMatrixLoader
    * -  bCol (U64) the columns of tensor B, required by @ref RandomMatrixLoader, @ref SparseMatrixLoader
    * -  aDensity The density factor of matrix A, Double, 1.0, required by @ref SparseMatrixLoader
    * -  bDensity The density factor of matrix B, Double, 1.0, required by @ref SparseMatrixLoader
    * -  aReduce Reduce some rows of A to be linearly dependent, U64, 0, required by @ref SparseMatrixLoader
    * - "bReduce Reduce some rows of A to be linearly dependent, U64, 0, required by @ref SparseMatrixLoader
    * - sketchDimension (U64) the dimension of sketch matrix, default 50
    * - coreBind (U64) the specific core tor run this benchmark, default 0
    * - ptFile (String) the path for the *.pt to be loaded, default torchscripts/FDAMM.pt
    * - matrixLoaderTag (String) the nameTag of matrix loader, see @ref MatrixLoaderTable, default is random
    * - useCPP (U64) force the benchmark to use static and pure cpp implementation instead of pt, default 0
    * - cppAlgoTag (String) The algorithm tag to index a cpp algorithm, works only under useCPP=1, default "mm",
    * see also @ref CPPAlgoTable
    * - threads, U64, the number of worker threads, default 2
    * - osScheduling, U64, whether use default os scheduling instead of my own core bind, default 0
    * - firstCoreBind, U64, which core will the first thread be bound to, default 0, see also @ref BlockPartitionRunner
   * @note Additional tags for energy measurement (please validate usingMeter first) see also @ref INTELLI_UTIL_METER
   * - usingMeter (U64) set to 1 if you want to use some energy meter, default diabled
   * - meterTag (String) the tag of meter, see also @ref MeterTable, default is intelMsr
   * - staticPower (Double) set this to >0 if you want to manually config the static power of the device
   * - meterAddress (String) set this to the file system path of the meter, if it is different from the meter's default
   * - isStreaming (U64) whether or not use streaming, default 0
   * @note by default, we only make A matrix streaming, if also want yo streaming B, please also set streamingTwoMatrixes to 1
   * - streamingTwoMatrixes (U64) whether make B matrix also streaming, default 0, will only affect when isStreaming=1
   * @warning For some platforms, the staticPower automatically measured by sleep is not accurate. Please do this mannulally.
  See also the template config.csv
   * @note Additional tags for hardware counters
   * - usePAPI (U64) whether or not use PAPI if papi exists, default 1
   *        - if PAPI is used, please refer to class @ref ThreadPerfPAPI, otherwise, see class @ref ThreadPerf
   *        - under PAPI, here is an unified way to custoimize perf events without recompile
   *            - create a configmap readable csv for perfList at perfLists folder, the key is tag you want to display, and the value is inline PAPI tag, type should be String
   *            - set perfUseExternalList (U64) in top configfile to 1
   *            - set perfListSrc (String) in top configfile to perfLists/<your file name>
 * @section subsec_extend_operator How to extend a new algorithm (pt-based)
 * - go to the benchmark/torchscripts
 * - find any .python as an example
 * - copy and modify it and generate the *pt, please make it under hump style of naming
 * - the system will then support it by using the name of your pt.
 * @section subsec_extend_cpp_operator How to extend a new algorithm (pure static c++ based)
 * - go to the src/CPPAlgos and include/CPPAlgos
 * - copy the example class, such as CRSCPPAlgo, rename it, and implement your own @ref amm function
 *  - copy the cpp and h
 *  - rename the cpp and h
 *  - automatically conduct the IDE-full-replace over the CRSCPPAlgo by your own name in cpp and h
 *  - define your own function
 *  - @note Please use this copy-and-replace policy rather than creat your own, unless you know the doxygen comment style
 *  very well and can always keep it!!!
 *  - @warning  This copy-and-replace policy will also prevent from wrong parameter types of interface functions, please
 *  DO KEEP THE INTERFACE PARAMETER UNDER THE SAME TYPE!!!!!!!!!!!
 * - register tour function with a tag to src/CPPAlgos/CPPAlgoTable.cpp
 * - edit the CMakelist.txt at src/CPPAlgos to include your new algo and recompile
 * - remember to add a test bench, you can refer to CRSTest.cpp at test/SystemTest for example
 * - if your algorithms have specific parameters like beta, please additionally do the following in the XXXCPPAlgo class:
 *      - copy the  virtual void setConfig(INTELLI::ConfigMapPtr cfg) claim to your *.h
 *      - implement that function in your cpp
 * @section subsec_edit_test How to add a single point test
 * - copy your config file to test/scripts, and your pt file to test/torchscripts
 * - follow and copy the SketchTest.cpp to create your own, say A.cpp
 * - register A.cpp to test/CMakeLists.txt, please follow how we deal with the SketchTest.cpp
 * - assuming you have made A.cpp into a_test, append  ./a_test "--success" to the last row of .github/workflows/cmake.yml
 */
/**
*
*/
//The groups of modules
/**
 * @mainpage Code Structure
 *  @section Code_Structure  Code Structure
 */
/**
 * @subsection code_stru_matrixloader MatrixLoader
 * This folder contains the loader to matrixes under different generation rules
 * @defgroup LibAMM_MatrixLOADER The matrix loaders
 * @{
 * We define the generation classes of matrixes. here
 **/
#include <MatrixLoader/AbstractMatrixLoader.h>
#include <MatrixLoader/RandomMatrixLoader.h>
#include <MatrixLoader/SparseMatrixLoader.h>
#include <MatrixLoader/GaussianMatrixLoader.h>
#include <MatrixLoader/ExponentialMatrixLoader.h>
#include <MatrixLoader/BinomialMatrixLoader.h>
#include <MatrixLoader/PoissonMatrixLoader.h>
#include <MatrixLoader/BetaMatrixLoader.h>
#include <MatrixLoader/SIFTMatrixLoader.h>
#include <MatrixLoader/MNISTMatrixLoader.h>
#include <MatrixLoader/MediaMillMatrixLoader.h>
#include <MatrixLoader/CCAMatrixLoader.h>
#include <MatrixLoader/MatrixLoaderTable.h>
/**
 * @}
 */
/**
* @subsection code_stru_parallelization Parallelization
* This folder contains the parallelization approaches
* @defgroup  LibAMM_PARALLELIZATION The parallelization classes
* @{
* We define the parallelization classes of AMM. here
**/
#include <Parallelization/BlockPartitionRunner.h>
/**
 * @}
 *
 */
/**
* @subsection code_stru_STREAMING STREAMING
* This folder contains the STREAMING approaches
* @defgroup  LibAMM_STREAMING The streaming classes
* @{
* We define the streaming classes of AMM. here
**/
#include <Streaming/TimeStamper.h>
#include <Streaming/Streamer.h>
#include <Streaming/SingleThreadStreamer.h>
#include <Streaming/BlockPartitionStreamer.h>
/**
 * @}
 *
 */
/**
* @subsection code_stru_cppalgo c++ algorithms
* This folder contains the agorithms implemented under pure c++
* @defgroup  LibAMM_CppAlgos The c++ amm algorithms
* @{
* We define the c++ algorithm classes of AMM. here
**/
#include <CPPAlgos/AbstractCPPAlgo.h>
#include <CPPAlgos/CPPAlgoTable.h>
#include <CPPAlgos/CRSCPPAlgo.h>
#include <CPPAlgos/CRSV2CPPAlgo.h>
#include <CPPAlgos/CountSketchCPPAlgo.h>
#include <CPPAlgos/BCRSCPPAlgo.h>
#include <CPPAlgos/EWSCPPAlgo.h>
#include <CPPAlgos/CoOccurringFDCPPAlgo.h>
#include <CPPAlgos/BetaCoOFDCPPAlgo.h>
#include <CPPAlgos/ProductQuantizationRaw.h>
#include <CPPAlgos/ProductQuantizationHash.h>
#include <CPPAlgos/VectorQuantization.h>
#include <CPPAlgos/INT8CPPAlgo.h>
#include <CPPAlgos/TugOfWarCPPAlgo.h>
#include <CPPAlgos/WeightedCRCPPAlgo.h>
#include <CPPAlgos/SMPPCACPPAlgo.h>

#include <CPPAlgos/FastJLTCPPAlgo.h>
#include <CPPAlgos/RIPCPPAlgo.h>
#include <CPPAlgos/BlockLRACPPAlgo.h>

#include <CPPAlgos/CLMMCPPAlgo.h>

/**
 * @}
 *
 */
/***
 *  @subsection code_stru_utils Utils
* This folder contains the public utils shared by INTELISTREAM team and some third party dependencies.
 **/
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
#include <Utils/IntelliLog.h>
#include <Utils/UtilityFunctions.h>
#include <Utils/BS_thread_pool.hpp>
/**
 * @}
 */
/**
 *
 * @}
 */

#endif
