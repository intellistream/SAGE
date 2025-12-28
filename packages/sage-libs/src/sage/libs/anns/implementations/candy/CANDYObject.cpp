//
// Created by tony on 19/03/24.
//

#include <CANDYObject.h>

namespace CANDY {
void CANDYObject::setStr(std::string str) {
  objStr = str;
  objSize = str.size();
}
std::string CANDYObject::getStr() {
  return objStr;
}

} // CANDY
