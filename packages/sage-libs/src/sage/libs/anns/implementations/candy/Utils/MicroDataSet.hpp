/*! \file MicroDataSet.h*/
//Copyright (C) 2022 by the IntelliStream team (https://github.com/intellistream)
// Created by tony on 03/03/22.
//

#ifndef _UTILS_MICRODATASET_H_
#define _UTILS_MICRODATASET_H_
#pragma once

#include <stdint.h>
#include <vector>
#include <stddef.h>
#include <stdlib.h>
#include <time.h>
#include <random>
#include <cmath>
#include <iostream>
#include <algorithm>
using namespace std;
namespace INTELLI {
/**
 * @ingroup INTELLI_UTIL
 * @{
 * @note The STL and static headers will be named as *.hpp, while *.h means there are real, fixed classes
 * @warning Please use this file ONLY as STL, it may not work if you turn it into *.cpp!!!!!
 * @defgroup INTELLI_UTIL_Micro The Micro dataset
 * @{
 * This is the synthetic dataset Micro, firstly introduced in our SIGMOD 2021 paper
 * @verbatim
 @article{IntraWJoin21,
   author = {Zhang, Shuhao and Mao, Yancan and He, Jiong and Grulich, Philipp M and Zeuch, Steffen and He, Bingsheng and Ma, Richard TB and Markl, Volker},
   title = {Parallelizing Intra-Window Join on Multicores: An Experimental Study},
   booktitle = {Proceedings of the 2021 International Conference on Management of Data (SIGMOD '21), June 18--27, 2021, Virtual Event , China},
   series = {SIGMOD '21},
   year={2021},
   isbn = {978-1-4503-8343-1/21/06},
   url = {https://doi.org/10.1145/3448016.3452793},
   doi = {10.1145/3448016.3452793},
  }
  @endverbatim
  */

/**
* @class MicroDataSet Utils/MicroDataSet.hpp
* @brief The all-in-one class for the Micro dataset
*/
class MicroDataSet {
 private:
  std::random_device rd;
  std::default_random_engine e1;
  bool hasSeed = false;
  uint64_t seed;
  //uint64_t  runTime=0;
 public:
  /**
   * @brief default construction, with auto random generator
   */
  MicroDataSet() = default;

  /**
  * @brief  construction with seed
  * @param seed The seed for random generator
  */
  explicit MicroDataSet(uint64_t _seed) {
    seed = _seed;
    hasSeed = true;
  }

  /**
 * @brief  construction with seed
 * @param seed The seed for random generator
 */
  void setSeed(uint64_t _seed) {
    seed = _seed;
    hasSeed = true;
  }

  ~MicroDataSet() = default;
  /** @defgroup MICRO_GENERIC generic
   * @{
   * The functions for general generation of Micro
   */
  /**
   * @brief To generate incremental alphabet, starting from 0 and end at len
   * @tparam dType The data type in the alphabet, default uint32_t
   * @param len The length of alphabet
   * @return The output vector alphabet
   */
  template<class dType=uint32_t>
  vector<dType> genIncrementalAlphabet(size_t len) {
    vector<dType> ru(len);
    /* populate */
    for (size_t i = 0; i < len; i++) {
      ru[i] = i + 1;   /* don't let 0 be in the alphabet */
    }
    return ru;
  }

  /**
   * @brief The function to generate a vector of integers which has zipf distribution
   * @param tsType The data type of int, default is size_t
   * @param len The length of output vector
   * @param maxV The maximum value of integer
   * @param fac The zipf factor, in [0,1]
   * @return the output vector
   */
  template<class tsType=size_t>
  vector<tsType> genZipfInt(size_t len, tsType maxV, double fac) {
    vector<tsType> ret(len);
    vector<tsType> alphabet = genIncrementalAlphabet<tsType>(maxV);
    std::mt19937_64 gen;
    if (!hasSeed) {
      gen = std::mt19937_64(rd()); // 以 rd() 播种的标准 mersenne_twister_engine
    } else {
      gen = std::mt19937_64(seed);
      seed++;
    }

    std::uniform_real_distribution<> dis(0, 1);
    vector<double> lut = genZipfLut<double>(maxV, fac);
    for (size_t i = 0; i < len; i++) {
      /* take random number */
      double r = dis(gen);
      /* binary search in lookup table to determine item */
      size_t left = 0;
      size_t right = maxV - 1;
      size_t m;       /* middle between left and right */
      size_t pos;     /* position to take */

      if (lut[0] >= r)
        pos = 0;
      else {
        while (right - left > 1) {
          m = (left + right) / 2;

          if (lut[m] < r)
            left = m;
          else
            right = m;
        }

        pos = right;
      }
      ret[i] = alphabet[pos];
    }
    return ret;
  }

  /**
   * @brief generate the vector of random integer
   * @tparam tsType The data type, default uint32_t
   * @tparam genType The generator type, default mt19937 (32 bit rand)
   * @param len The length of output vector
   * @param maxV The maximum value of output
   * @param minV The minimum value of output
   * @return The output vector
   * @note Both signed and unsigned int are support, just make sure you have right tsType
   * @note Other options for genType:
   * \li mt19937_64: 64 bit rand
   * \li ranlux24: 24 bit
   * \li ranlux48:  48 bit
   */
  template<class tsType=uint32_t, class genType=std::mt19937>
  vector<tsType> genRandInt(size_t len, tsType maxV, tsType minV = 0) {
    genType gen;
    if (!hasSeed) {
      gen = genType(rd());
    } else {
      seed++;
      gen = genType(seed);
    }
    std::uniform_int_distribution<> dis(minV, maxV);
    vector<tsType> ret(len);
    for (size_t i = 0; i < len; i++) {
      ret[i] = (tsType) dis(gen);
    }
    return ret;
  }

  /**
   * @brief To generate the zipf Lut
   * @tparam dType The data type in the alphabet, default double
   * @param len The length of alphabet
   * @param fac The zipf factor, in [0,1]
   * @return The output vector lut
   */
  template<class dType=double>
  vector<dType> genZipfLut(size_t len, dType fac) {
    dType scaling_factor;
    dType sum;
    vector<dType> lut(len);
    /**
     * Compute scaling factor such that
     *
     *   sum (lut[i], i=1..alphabet_size) = 1.0
     *
     */
    scaling_factor = 0.0;
    for (size_t i = 1; i <= len; i++) { scaling_factor += 1.0 / pow(i, fac); }
    /**
     * Generate the lookup table
     */
    sum = 0.0;
    for (size_t i = 1; i <= len; i++) {
      sum += 1.0 / std::pow(i, fac);
      lut[i - 1] = sum / scaling_factor;
    }
    return lut;
  }

  /**
   * @}
   */
  /**
   * @defgroup MICRO_TS time stamp
   * @{
   * This group is specialized for time stamps, as they should follow an incremental order
   */
  /**
  * @brief The function to generate a vector of timestamp which grows smoothly
  * @tparam tsType The data type of time stamp, default is size_t
  * @param len The length of output vector
  * @param step Within the step, timestamp will remain the same
  * @param interval The incremental value between two steps
  * @return The vector of time stamp
  */
  template<class tsType=size_t>
  vector<tsType> genSmoothTimeStamp(size_t len, size_t step, size_t interval) {
    vector<tsType> ret(len);
    tsType ts = 0;
    for (size_t i = 0; i < len; i++) {
      ret[i] = ts;
      if (i % (step) == 0) {
        ts += interval;
      }

    }
    return ret;
  }

  template<class tsType=size_t>
  vector<tsType> genSmoothTimeStamp(size_t len, size_t maxTime) {
    vector<tsType> ret = genRandInt<tsType>(len, maxTime);
    std::sort(ret.begin(), ret.end()); //just incremental re-arrange
    return ret;
  }

  /**
   * @brief The function to generate a vector of timestamp which has zipf distribution
   * @param tsType The data type of time stamp, default is size_t
   * @param len The length of output vector
   * @param maxTime The maximum value of time stamp
   * @param fac The zipf factor, in [0,1]
   * @return the output vector
   * @see genZipfInt
   */
  template<class tsType=size_t>
  vector<tsType> genZipfTimeStamp(size_t len, tsType maxTime, double fac) {
    vector<tsType> ret = genZipfInt<tsType>(len, maxTime, fac);
    std::sort(ret.begin(), ret.end()); //just incremental re-arrange
    return ret;
  }
  /**
   * @}
   */
};
}
/**
 * @}
 * @}
 */
#endif //ALIANCEDB_INCLUDE_UTILS_MICRODATASET_H_
