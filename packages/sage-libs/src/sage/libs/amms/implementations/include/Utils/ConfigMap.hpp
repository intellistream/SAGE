/*! \file ConfigMap.hpp*/
#pragma once
#ifndef _UTILS_CONFIGMAP_HPP_
#define _UTILS_CONFIGMAP_HPP_

#include <map>
#include <vector>
#include <memory>
#include <string>
#include <fstream>
#include <iostream>
#include <sstream>
#include <assert.h>
#include <Utils/IntelliLog.h>
/**
 *  @defgroup INTELLI_UTIL
 *  @{
* @defgroup INTELLI_UTIL_CONFIGS Configurations
* @{
 * This package is used to store configuration information in an unified map and
 * get away from too many stand-alone functtions
 */
using namespace std;
namespace INTELLI {
/**
 * @ingroup INTELLI_UTIL_CONFIGS
 * @class ConfigMap Utils/ConfigMap.hpp
 * @note Require @ref IntelliLog Util package
 * @brief The unified map structure to store configurations in a key-value style
 */
class ConfigMap {
 protected:
  std::map<std::string, uint64_t> u64Map;
  std::map<std::string, int64_t> i64Map;
  std::map<std::string, double> doubleMap;
  std::map<std::string, std::string> strMap;

  static void spilt(const std::string s, const std::string &c, vector<std::string> &v) {
    std::string::size_type pos1, pos2;
    pos2 = s.find(c);
    pos1 = 0;
    while (std::string::npos != pos2) {
      v.push_back(s.substr(pos1, pos2 - pos1));

      pos1 = pos2 + c.size();
      pos2 = s.find(c, pos1);
    }
    if (pos1 != s.length())
      v.push_back(s.substr(pos1));
  }
  void smartParase(std::string key, std::string value) {
    std::string a = value;
    size_t quoteStart = a.find("'");
    size_t quoteEnd = a.find("'", quoteStart + 1);
    if ((std::isdigit(a[0]) || a[0] == '-' || a[0] == '+') && quoteStart == std::string::npos) {
      if ((a.find('.') != std::string::npos)) {
        double doubleValue;
        std::istringstream(a) >> doubleValue;
        edit(key, doubleValue);
        return;
      } else {
        int64_t intValue;
        std::istringstream(a) >> intValue;
        edit(key, intValue);
        return;
      }
      //  std::cout << "Converted to double: " << doubleValue << std::endl;
    }

    if (quoteStart != std::string::npos && quoteEnd != std::string::npos) {
      std::string contentBetweenQuotes = a.substr(quoteStart + 1, quoteEnd - quoteStart - 1);
      //std::cout << "Content between single quotes: " << contentBetweenQuotes << std::endl;
      edit(key, contentBetweenQuotes);
      return;
    }
      // 4. Otherwise, keep it as a string
    else {
      // std::cout << "Kept as a string: " << a << std::endl;
      edit(key, a);
    }
  }
 public:
  ConfigMap() = default;

  ~ConfigMap() = default;

  /**
 * @brief Edit the config map. If not exit the config, will create new, or will overwrite
 * @param key The look up key in std::string
 * @param value The u64 value
   */
  void edit(const std::string &key, uint64_t value) {
    u64Map[key] = value;
  }

  /**
 * @brief Edit the config map. If not exit the config, will create new, or will overwrite
 * @param key The look up key in std::string
 * @param value The i64 value
   */
  void edit(const std::string &key, int64_t value) {
    i64Map[key] = value;
  }

  /**
 * @brief Edit the config map. If not exit the config, will create new, or will overwrite
 * @param key The look up key in std::string
 * @param value The double value
   */
  void edit(const std::string &key, double value) {
    doubleMap[key] = value;
  }

  /**
 * @brief Edit the config map. If not exit the config, will create new, or will overwrite
 * @param key The look up key in std::string
 * @param value The std::string value
   */
  void edit(const std::string &key, std::string value) {
    strMap[key] = std::move(value);
  }

  /**
 * @brief To detect whether the key exists and related to a U64
 * @param key
 * @return bool for the result
   */
  bool existU64(const std::string &key) {
    return (u64Map.count(key) == 1);
  }

  /**
 * @brief To detect whether the key exists and related to a I64
 * @param key
 * @return bool for the result
   */
  bool existI64(const std::string &key) {
    return (i64Map.count(key) == 1);
  }

  /**
 * @brief To detect whether the key exists and related to a double
 * @param key
 * @return bool for the result
   */
  bool existDouble(const std::string &key) {
    return (doubleMap.count(key) == 1);
  }

  /**
 * @brief To detect whether the key exists and related to a std::string
 * @param key
 * @return bool for the result
   */
  bool existString(const std::string &key) {
    return (strMap.count(key) == 1);
  }

  /**
 * @brief To detect whether the key exists
 * @param key
 * @return bool for the result
   */
  bool exist(const std::string &key) {
    return existU64(key) || existI64(key) || existDouble(key) || existString(key);
  }

  /**
 * @brief To get a U64 value by key
 * @param key
 * @return value
 * @warning the key must exist!!
   */
  uint64_t getU64(const std::string &key) {
    return u64Map.at(key);
  }

  /**
 * @brief To get a I64 value by key
 * @param key
 * @return value
 * @warning the key must exist!!
   */
  int64_t getI64(const std::string &key) {
    return i64Map.at(key);
  }

  /**
* @brief To get a double value by key
* @param key
* @return value
* @warning the key must exist!!
   */
  double getDouble(const std::string &key) {
    return doubleMap.at(key);
  }

  /**
* @brief To get a std::string value by key
* @param key
* @return value
* @warning the key must exist!!
   */
  std::string getString(const std::string &key) {
    return strMap.at(key);
  }

  /**
 * @brief convert the whole map to std::string and retuen
 * @param separator The separator std::string, default "\t"
 * @param newLine The newline std::string, default "\n"
 * @return the result
   */
  std::string toString(const std::string &separator = "\t", std::string newLine = "\n") {
    std::string str = "key" + separator + "value" + separator + "type" + newLine;
    for (auto &iter : u64Map) {
      std::string col = iter.first + separator + to_string(iter.second) + separator + "U64" + newLine;
      str += col;
    }
    for (auto &iter : i64Map) {
      std::string col = iter.first + separator + to_string(iter.second) + separator + "I64" + newLine;
      str += col;
    }
    for (auto &iter : doubleMap) {
      std::string col = iter.first + separator + to_string(iter.second) + separator + "Double" + newLine;
      str += col;
    }
    for (auto &iter : strMap) {
      std::string col = iter.first + separator + (iter.second) + separator + "String" + newLine;
      str += col;
    }
    return str;
  }
/**
 * @brief load the map from some external string
 * @param src, the string
 * @param separator The separator std::string, default "\t"
 * @param newLine The newline std::string, default "\n"
 * @return bool whether successful
   */
  bool fromString(const std::string src, const std::string &separator = "\t", std::string newLine = "\n") {
    std::istringstream ins(src);
    std::string readStr;
    // cout << "read file\r\n";
    while (std::getline(ins, readStr, newLine[0])) {
      vector<std::string> cols;
      // readStr.erase(readStr.size()-1);
      spilt(readStr, separator, cols);
      // cout<<readStr+"\n";
      if (cols.size() >= 3) {
        istringstream iss(cols[1]);
        if (cols[2] == "U64" || cols[2] == "U64\r") {
          uint64_t value;
          iss >> value;
          edit(cols[0], (uint64_t) value);
        } else if (cols[2] == "I64" || cols[2] == "I64\r") {
          int64_t value;
          iss >> value;
          edit(cols[0], (int64_t)
              value);
        } else if (cols[2] == "Double" || cols[2] == "Double\r") {
          double value;
          iss >> value;
          edit(cols[0], (double) value);
        } else if (cols[2] == "String" || cols[2] == "String\r") {
          edit(cols[0], (std::string) cols[1]);
        }
      }
    }
    return true;
  }
  /**
 * @brief clone this config into destination
 * @param dest The clone destination
   */
  void cloneInto(ConfigMap &dest) {
    for (auto &iter : u64Map) {
      dest.edit(iter.first, (uint64_t) iter.second);
    }
    for (auto &iter : i64Map) {
      dest.edit(iter.first, (int64_t)
          iter.second);
    }
    for (auto &iter : doubleMap) {
      dest.edit(iter.first, (double) iter.second);
    }
    for (auto &iter : strMap) {
      dest.edit(iter.first, (std::string) iter.second);
    }
  }
  /**
 * @brief load some information an external one
 * @param src The clone destination
   */
  void loadFrom(ConfigMap &src) {
    for (auto &iter : src.u64Map) {
      edit(iter.first, (uint64_t) iter.second);
    }
    for (auto &iter : src.i64Map) {
      edit(iter.first, (int64_t)
          iter.second);
    }
    for (auto &iter : src.doubleMap) {
      edit(iter.first, (double) iter.second);
    }
    for (auto &iter : src.strMap) {
      edit(iter.first, (std::string) iter.second);
    }
  }

  /**
* @brief convert the whole map to file
 * @param fname The file name
* @param separator The separator std::string, default "," for csv style
* @param newLine The newline std::string, default "\n"
* @return bool, whether the file is created
   */
  bool toFile(const std::string &fname, const std::string &separator = ",", std::string newLine = "\n") {
    ofstream of;
    of.open(fname);
    if (of.fail()) {
      return false;
    }
    of << toString(separator, std::move(newLine));
    of.close();
    return true;
  }

  /**
* @brief update the whole map from file
 * @param fname The file name
* @param separator The separator std::string, default "," for csv style
* @param newLine The newline std::string, default "\n"
* @return bool, whether the file is loaded
   */
  bool fromFile(const std::string &fname, std::string separator = ",", std::string newLine = "\n") {
    ifstream ins;
    ins.open(fname);
    assert(separator.data());
    assert(newLine.data());
    if (ins.fail()) {
      return false;
    }
    std::string readStr;
    // cout << "read file\r\n";
    while (std::getline(ins, readStr, newLine[0])) {
      vector<std::string> cols;
      // readStr.erase(readStr.size()-1);
      spilt(readStr, separator, cols);
      // cout<<readStr+"\n";
      if (cols.size() >= 3) {
        istringstream iss(cols[1]);
        if (cols[2] == "U64" || cols[2] == "U64\r") {
          uint64_t value;
          iss >> value;
          edit(cols[0], (uint64_t) value);
        } else if (cols[2] == "I64" || cols[2] == "I64\r") {
          int64_t value;
          iss >> value;
          edit(cols[0], (int64_t)
              value);
        } else if (cols[2] == "Double" || cols[2] == "Double\r") {
          double value;
          iss >> value;
          edit(cols[0], (double) value);
        } else if (cols[2] == "String" || cols[2] == "String\r") {
          edit(cols[0], (std::string) cols[1]);
        }
      }
    }
    //ins>>readStr;
    ins.close();
    return true;
  }
  /**
* @brief update the whole map from c/c++ program's args
 * @param argc the count of input args
 * @param argv the arg list in chars
 * @note Will automatically detect int64, double, and string
* @return bool, whether the file is loaded
   */
  bool fromCArg(const int argc, char **argv) {

    if (argc <= 1) {
      return false;
    }
    for (int argPos = 1; argPos < argc; argPos++) {
      std::string prob = "";
      prob += argv[argPos];
      size_t found = prob.find('-');
      size_t equalPos = prob.find('=');
      if (found == std::string::npos) {
        return false;
      }
      std::string key = prob.substr(1, equalPos - 1); // Skip the leading '-'
      std::string value = prob.substr(equalPos + 1);
      // Print the parsed key and value
      smartParase(key, value);
      // std::cout << "Key: " << key << ", Value: " << value << std::endl;
    }

    return true;
  }

  /**
 * @brief Try to get an I64 from config map, if not exist, use default value instead
 * @param key The key
 * @param defaultValue The default
 * @param showWarning Whether show warning logs if not found
 * @return The returned value
   */
  int64_t tryI64(const string &key, int64_t defaultValue = 0, bool showWarning = false) {
    int64_t ru = defaultValue;
    if (this->existI64(key)) {
      ru = this->getI64(key);
      // INTELLI_INFO(key + " = " + to_string(ru));
    } else {
      if (showWarning) {
        //INTELLI_WARNING("Leaving " + key + " as blank, will use " + to_string(defaultValue) + " instead");
      }
      //  WM_WARNNING("Leaving " + key + " as blank, will use " + to_string(defaultValue) + " instead");
    }
    return ru;
  }

  /**
 * @brief return the map of string
 * @return the strMap variable
   */
  std::map<std::string, std::string> getStrMap() {
    return strMap;
  }
  /**
* @brief return the map of I64
* @return the i64Map variable
 */
  std::map<std::string, int64_t> getI64Map() {
    return i64Map;
  }
  /**
* @brief return the map of U64
* @return the u64Map variable
*/
  std::map<std::string, uint64_t> getU64Map() {
    return u64Map;
  }
  /**
* @brief return the map of I64
* @return the doubleMap variable
*/
  std::map<std::string, double> getDoubleMap() {
    return doubleMap;
  }
  /**
 * @brief Try to get an U64 from config map, if not exist, use default value instead
 * @param key The key
 * @param defaultValue The default
 *  @param showWarning Whether show warning logs if not found
 * @return The returned value
   */
  uint64_t tryU64(const string &key, uint64_t defaultValue = 0, bool showWarning = false) {
    uint64_t ru = defaultValue;
    if (this->existU64(key)) {
      ru = this->getU64(key);
      // INTELLI_INFO(key + " = " + to_string(ru));
    } else {
      if (showWarning) {
        //   INTELLI_WARNING("Leaving " + key + " as blank, will use " + to_string(defaultValue) + " instead");
      }
      //  WM_WARNNING("Leaving " + key + " as blank, will use " + to_string(defaultValue) + " instead");
    }
    return ru;
  }

  /**
 * @brief Try to get a double from config map, if not exist, use default value instead
 * @param key The key
 * @param defaultValue The default
 * @param showWarning Whether show warning logs if not found
 * @return The returned value
   */
  double tryDouble(const string &key, double defaultValue = 0, bool showWarning = false) {
    double ru = defaultValue;
    if (this->existDouble(key)) {
      ru = this->getDouble(key);
      // INTELLI_INFO(key + " = " + to_string(ru));
    } else {
      if (showWarning) {
        //     INTELLI_WARNING("Leaving " + key + " as blank, will use " + to_string(defaultValue) + " instead");
      }
      //  WM_WARNNING("Leaving " + key + " as blank, will use " + to_string(defaultValue) + " instead");
    }
    return ru;
  }

  /**
 * @brief Try to get an String from config map, if not exist, use default value instead
 * @param key The key
 * @param defaultValue The default
 * @param showWarning Whether show warning logs if not found
 * @return The returned value
   */
  string tryString(const string &key, const string &defaultValue = "", bool showWarning = false) {
    string ru = defaultValue;
    if (this->existString(key)) {
      ru = this->getString(key);
      //INTELLI_INFO(key + " = " + (ru));
    } else {
      if (showWarning) {
        //    INTELLI_WARNING("Leaving " + key + " as blank, will use " + (defaultValue) + " instead");
      }
      // WM_WARNNING("Leaving " + key + " as blank, will use " + (defaultValue) + " instead");
    }
    return ru;
  }
  /**
   * @brief Add prefix to the front of keys, it is useful in downstream task where we need to generate metric config file for each components in the downstream task e.g. instructions -> ${prefix}Instructions
   * @param prefix The prefix you want to add to the front of keys
   * @return void
   */
  void addPrefixToKeys(std::string prefix){
    std::map<std::string, uint64_t> uint64ModifiedMap;
    for (const auto& entry : u64Map) { // Iterate through the original map and add the prefix to the keys
      std::string modifiedKey = entry.first;
      modifiedKey[0] = std::toupper(modifiedKey[0]);
      modifiedKey = prefix + modifiedKey;
      uint64ModifiedMap[modifiedKey] = entry.second;
    }
    u64Map = std::move(uint64ModifiedMap); // Replace the original map with the modified map

    std::map<std::string, int64_t> i64ModifiedMap;
    for (const auto& entry : i64Map) {
      std::string modifiedKey = entry.first;
      modifiedKey[0] = std::toupper(modifiedKey[0]);
      modifiedKey = prefix + modifiedKey;
      i64ModifiedMap[modifiedKey] = entry.second;
    }
    i64Map = std::move(i64ModifiedMap);

    std::map<std::string, double> doubleModifiedMap;
    for (const auto& entry : doubleMap) {
      std::string modifiedKey = entry.first;
      modifiedKey[0] = std::toupper(modifiedKey[0]);
      modifiedKey = prefix + modifiedKey;
      doubleModifiedMap[modifiedKey] = entry.second;
    }
    doubleMap = std::move(doubleModifiedMap);

    std::map<std::string, std::string> stringModifiedMap;
    for (const auto& entry : strMap) {
      std::string modifiedKey = entry.first;
      modifiedKey[0] = std::toupper(modifiedKey[0]);
      modifiedKey = prefix + modifiedKey;
      stringModifiedMap[modifiedKey] = entry.second;
    }
    strMap = std::move(stringModifiedMap);
  }
};

/**
 * @ingroup INTELLI_UTIL_CONFIGS
 * @typedef ConfigMapPtr
 * @brief The class to describe a shared pointer to @ref ConfigMap
 */
typedef std::shared_ptr<ConfigMap> ConfigMapPtr;
/**
 * @ingroup INTELLI_UTIL_CONFIGS
 * @def newConfigMap
 * @brief (Macro) To creat a new @ref ConfigMap under shared pointer.
 */
#define  newConfigMap make_shared<INTELLI::ConfigMap>
}

/**
 * @}
 * $}
 */


#endif
