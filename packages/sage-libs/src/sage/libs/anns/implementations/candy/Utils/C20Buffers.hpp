/*! \file C20Buffers.hpp*/
//
// Created by tony on 11/03/22.
//
#pragma once
#ifndef _UTILS_C20BUFFERS_HPP_
#define _UTILS_C20BUFFERS_HPP_

#include <vector>
#include <memory>

#if defined(__GNUC__) && (__GNUC__ >= 4)
#define ADB_memcpy(dst, src, size) __builtin_memcpy(dst, src, size)
#else
#define ADB_memcpy(dst, src, size) memcpy(dst, src, size)
#endif
/**
 * @ingroup INTELLI_UTIL
 * @{
 */
/**
* @ingroup INTELLI_UTIL_OTHERC20
* @{
*/
namespace INTELLI {
/**
 * @ingroup INTELLI_UTIL_OTHERC20
 * @class C20Buffer Utils/C20Buffers.hpp
 * @tparam dataType The type of your buffering element
 */
template<typename dataType>
class C20Buffer {
 protected:
  size_t pos = 0;
 public:
  std::vector<dataType> area;

  /**
  * @brief reset this buffer, set pos back to 0
  */
  void reset() {
    pos = 0;
  }

  C20Buffer() { reset(); }

  ~C20Buffer() {}

  /**
   * @brief Init with original length of buffer
   * @param len THe original length of buffer
   */
  C20Buffer(size_t len) {
    area = std::vector<dataType>(len);
    reset();
  }

  /**
   * @brief To get how many elements are allowed in the buffer
   * @return The size of buffer area, i.e., area.size()
   * @note: This is NOT the size of valid data
   * @see size
   */
  size_t bufferSize() {
    return area.size();
  }

  /**
  * @brief To get how many VALID elements are existed in the buffer
  * @return The size of VALID elements
  * @note: This is NOT the size of total buffer
   * @see bufferSize
  */
  size_t size() {
    return pos;
  }

  /**
   * @brief To get the original memory area ponter of data
   * @return The memory area address (pointer) that stores the data
   */
  dataType *data() {
    return &area[0];
  }

  /**
   * @brief To get the original memory area ponter of data, with offset
   * @param offset Offset of data
   * @return The memory area address (pointer) that stores the data
   * @warning Please ensure the offset is NOT larger than the area.size()-1
   */
  dataType *data(size_t offset) {
    return &area[offset];
  }

  /**
   * @brief Append the data to the buffer
   * @param da Data to be appended
   * @note Exceed length will lead to a push_back in vector
   * @return The valid size after this append
   */
  size_t append(dataType da) {
    /*if(pos<area.size())
    {
      area[pos]=da;
      pos++;
    }
    else
    {
      area.push_back(da);
      pos=area.size();
    }*/
    area[pos] = da;
    pos++;
    return pos;
  }

  /**
  * @brief Append the data to the buffer
  * @param da Data to be appended, a buffer
   * @param len the length of data
  * @note Exceed length will lead to a push_back in vector
  * @return The valid size after this append
  */
  size_t append(dataType *da, size_t len) {
    ADB_memcpy(&area[pos], da, len * sizeof(dataType));
    pos += len;
    return pos;
  }
};
/**
 * @}
 */
}
#endif //ALIANCEDB_INCLUDE_UTILS_C20BUFFERS_HPP_
