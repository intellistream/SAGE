/*! \file AbstractC20Thread.hpp*/
//
// Created by tony on 07/03/22.
//

#ifndef _INCLUDE_UTILS_ABSTRACTC20THREAD_H_
#define _INCLUDE_UTILS_ABSTRACTC20THREAD_H_
#pragma once

#include <thread>
#include <memory>
#include <barrier>
/**
 * @defgroup INTELLI_UTIL Shared Utils with other Intelli Stream programs
 * @{
 * This group provides common functions to support the Intelli Stream programs.
 */
/**
* @defgroup INTELLI_UTIL_OTHERC20 Other common class or package under C++20 standard
* @{
 * This package covers some common C++20 new features, such as std::thread to ease the programming
*/
namespace INTELLI {
/**
 * @ingroup INTELLI_UTIL_OTHERC20
 * @class AbstractC20Thread  Utils/AbstractC20Thread.hpp
 * @brief The base class and abstraction of C++20 thread,
 * and it can be derived into other threads
 */
class AbstractC20Thread {
 protected:
  /**
   * @brief The inline 'main" function of thread, as an interface
   * @note Normally re-write this in derived classes
   */
  virtual void inlineMain() {

  }

  std::shared_ptr<std::thread> threadPtr;
 public:
  AbstractC20Thread() {}

  ~AbstractC20Thread() {}

  /**
   * @brief to start this thread
   */
  void startThread() {
    auto fun = [this]() {
      inlineMain();
    };
    threadPtr = std::make_shared<std::thread>(fun);
    // table=make_shared<MultiThreadHashTable>(5000);
  }

  /**
   * @brief the thread join function
   */
  void joinThread() {
    threadPtr->join();
  }

};

/**
 * @ingroup INTELLI_UTIL_OTHERC20
 * @typedef AbstractC20ThreadPtr
 * @brief The class to describe a shared pointer to @ref AbstractC20Thread
 */
typedef std::shared_ptr<AbstractC20Thread> AbstractC20ThreadPtr;
/**
 * @ingroup INTELLI_UTIL_OTHERC20
 * @def newAbstractC20Thread
 * @brief (Macro) To creat a new @ref newAbstractC20Thread under shared pointer.
 */
#define  newAbstractC20Thread std::make_shared<INTELLI::AbstractC20Thread>
typedef std::shared_ptr<std::barrier<>> BarrierPtr;
}



/**
 * @}
 */
/**
 * @}
 */
#endif //ALIANCEDB_INCLUDE_UTILS_ABSTRACTTHREAD_H_
