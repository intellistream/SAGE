/*! \file IntelliLog.hpp*/
#ifndef _UTILS_IntelliLog_H_
#define _UTILS_IntelliLog_H_
#pragma once

#include <string>
#include <iostream>
#include <sstream>
#include <chrono>
#include <iostream>
#include <source_location>
#include <ctime>
#include <mutex>
#include <fstream>
/**
 *  @ingroup INTELLI_UTIL
 *  @{
* @defgroup INTELLI_UTIL_INTELLILOG Log utils
* @{
 * This package is used for logging
*/
using namespace std;
namespace INTELLI {
/**
 * @ingroup INTELLI_UTIL_INTELLILOG
 * @class IntelliLog Utils/IntelliLog.hpp
 * @brief The log functions packed in class
 */
class IntelliLog {
 public:
  /**
   * @brief Produce a log
   * @param level The log level you want to indicate
   * @param message The log message you want to indicate
   * @param source reserved
   * @note message is automatically appended with a "\n"
   */
  static void log(std::string level,
                  std::string_view message,
                  std::source_location const source = std::source_location::current());

  /**
   * @brief set up the logging file by its name
   * @param fname the name of file
   */
  static void setupLoggingFile(string fname);
};

/**
 * @ingroup INTELLI_UTIL_INTELLILOG
 * @class IntelliLog_FileProtector Utils/IntelliLog.hpp
 * @brief The protector for concurrent log on a file
 * @warning This class is preserved for internal use only!
 */
class IntelliLog_FileProtector {
 private:
  std::mutex m_mut;
  ofstream of;
  bool isOpened = false;
 public:
  IntelliLog_FileProtector() = default;

  ~IntelliLog_FileProtector() {
    if (isOpened) {
      of.close();
    }
  }

  /**
 * @brief lock this protector
 */
  void lock() {
    while (!m_mut.try_lock());
  }

  /**
   * @brief unlock this protector
   */
  void unlock() {
    m_mut.unlock();
  }

  /**
   * @brief try to open a file
   * @param fname The name of file
   */
  void openLogFile(const string &fname) {
    of.open(fname, std::ios_base::app);
    if (of.fail()) {
      return;
    }
    isOpened = true;
  }

  /**
  * @brief try to appened something to the file, if it's opened
  * @param msg The message to appened
  */
  void appendLogFile(const string &msg) {
    if (!isOpened) {
      return;
    }
    lock();
    of << msg;
    unlock();
  }
};
/**
 * @ingroup INTELLI_UTIL_INTELLILOG
 * @def INTELLI_INFO
 * @brief (Macro) To log something as information
 */
#define INTELLI_INFO(n) INTELLI::IntelliLog::log("INFO",n)
/**
 * @ingroup INTELLI_UTIL_INTELLILOG
 * @def INTELLI_ERROR
 * @brief (Macro) To log something as error
 */
#define INTELLI_ERROR(n) INTELLI::IntelliLog::log("ERROR",n)
/**
 * @ingroup INTELLI_UTIL_INTELLILOG
 * @def INTELLI_Warning
 * @brief (Macro) To log something as warnning
 */
#define INTELLI_WARNING(n) INTELLI::IntelliLog::log("WARNING",n)
/**
 * @ingroup INTELLI_UTIL_INTELLILOG
 * @def INTELLI_DEBUG
 * @brief (Macro) To log something as debug
 */
#define INTELLI_DEBUG(n) IntelliLog::log("DEBUG",n)
}
#endif