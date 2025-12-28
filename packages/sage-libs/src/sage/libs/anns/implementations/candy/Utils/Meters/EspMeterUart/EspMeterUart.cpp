#include <Utils/Meters/EspMeterUart/EspMeterUart.hpp>
#include <unistd.h>
#include <stdint.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>
#include <sys/mman.h>
#include <stdio.h>
#include <stdint.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include     <stdio.h>
#include     <stdlib.h>
#include     <unistd.h>
#include     <sys/types.h>
#include     <sys/stat.h>
#include     <fcntl.h>
#include     <termios.h>
#include     <errno.h>
#include    <string.h>
#include <stdint.h>

using namespace DIVERSE_METER;
enum {
  UART_VCMD_START = 1,
  UART_VCMD_STOP,
  UART_VCMD_I,
  UART_VCMD_V,
  UART_VCMD_P,
  UART_VCMD_E,
  UART_VCMD_PEAK,

};

void EspMeterUart::setConfig(INTELLI::ConfigMapPtr _cfg) {
  AbstractMeter::setConfig(_cfg);
  meterAddress = cfg->tryString("meterAddress", "/dev/ttyUSB0", true);
  // openUartDev();
}

void EspMeterUart::openUartDev() {
  devFd = open(meterAddress.data(), O_RDWR | O_NOCTTY);
  if (devFd == -1) {

    METER_ERROR("can not open device meter");
  }
  //char *welcome="hello world";
  struct termios termios_p;
  tcgetattr(devFd, &termios_p);
  /**
   * @brief set up uart, 115200, maximum compatability
   */
  termios_p.c_iflag &= ~(IGNBRK | BRKINT | PARMRK | ISTRIP | INLCR | IGNCR | ICRNL | IXON);
  termios_p.c_oflag &= ~OPOST;
  termios_p.c_lflag &= ~(ECHO | ECHONL | ICANON | ISIG | IEXTEN);
  termios_p.c_cflag &= ~(CSIZE | PARENB);
  termios_p.c_cflag = B115200 | CS8 | CLOCAL | CREAD;
  termios_p.c_cc[VTIME] = 0;
  termios_p.c_cc[VMIN] = 1;
  tcsetattr(devFd, TCSANOW, &termios_p);
  tcflush(devFd, TCIOFLUSH);
  fcntl(devFd, F_SETFL, O_NONBLOCK);
  //close(devFd);
}

EspMeterUart::EspMeterUart(/* args */) {

}

/*
EspMeterUart::EspMeterUart(string name) {
  devFd = open(name.data(), O_RDWR);
  if (devFd == -1) {

    METER_ERROR("can not open device meter");
  }
}*/
EspMeterUart::~EspMeterUart() {
  /*if (devFd != -1) {
    close(devFd);
  }*/
}

void EspMeterUart::startMeter() {
  openUartDev();
  uint8_t cmdSend = UART_VCMD_START;
  //double ru=0;
  write(devFd, &cmdSend, 1);
  close(devFd);
}

void EspMeterUart::stopMeter() {
  openUartDev();
  uint8_t cmdSend = UART_VCMD_STOP;
  //double ru=0;
  write(devFd, &cmdSend, 1);
  close(devFd);
}

double EspMeterUart::getE() {
  openUartDev();
  double ru = 0;
  uint8_t cmdSend = UART_VCMD_E;
  write(devFd, &cmdSend, 1);
//usleep(1000);
//double ru;
  int ret = -1;
  uint64_t tryCnt = 0;
  while (ret < 0 && tryCnt < 1000) {
    ret = read(devFd, &ru, sizeof(double));
    tryCnt++;
    usleep(1000);
  }
  close(devFd);
  return ru;
}

double EspMeterUart::getPeak() {
  double ru = 0;
  uint8_t cmdSend = UART_VCMD_PEAK;
  write(devFd, &cmdSend, 1);
//usleep(1000);
//double ru;
  int ret = -1;
  uint64_t tryCnt = 0;
  while (ret < 0 && tryCnt < 1000) {
    ret = read(devFd, &ru, sizeof(double));
    tryCnt++;
    usleep(1000);
  }
  return ru;
}