//
// Created by tony on 23/12/22.
//
#include <Utils/IntelliLog.h>
#include <string.h>
#include <mutex>

#define RESET   "\033[0m"
#define GREEN   "\033[32m"
#define BLUE    "\033[34m"
#define YELLOW  "\033[33m"
#define RED     "\033[31m"

INTELLI::IntelliLog_FileProtector fp_doNotTouchMe;

void INTELLI::IntelliLog::setupLoggingFile(string fname) {
  fp_doNotTouchMe.openLogFile(fname);
}

void INTELLI::IntelliLog::log(std::string level, std::string_view message, const std::source_location source) {
  time_t now = time(0);

  // 把 now 转换为字符串形式
  char *dt = ctime(&now);
  std::string str = level + ":";
  dt[strlen(dt) - 1] = 0;
  str += dt;
  //str+= static_cast<char>(level);
  str += ":";
  str += source.file_name();
  str += ":";
  str += to_string(source.line());
  str += +"|";
  str += +source.function_name();
  str += +"|";

  if (level == "DEBUG") {
    str += message;
  } else if (level == "INFO") {
    str += BLUE;
    str += message;
    str += RESET;
  } else if (level == "WARNING") {
    str += YELLOW;
    str += message;
    str += RESET;
  } else if (level == "ERROR") {
    str += RED;
    str += message;
    str += RESET;
  }

  cout << str + "\n";

  fp_doNotTouchMe.appendLogFile(str + "\n");
  //fp_doNotTouchMe.unlock();
}