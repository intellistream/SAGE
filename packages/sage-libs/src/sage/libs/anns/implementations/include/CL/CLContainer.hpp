#pragma once
#ifndef _CL_CONTAINER_HPP_
#define _CL_CONTAINER_HPP_
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <memory>
#ifdef MAC
#include <OpenCL/cl.h>
#else
#include <CL/cl.h>
#endif
#include <string>
#include <memory>
#include <vector>
#include <stdint.h>
#include <sys/time.h>
using namespace std;
class HostPara {
 public:
  // the users should take care of the ptr, as container will NOT handle it
  void *ptr;
  size_t size;
  HostPara();
  HostPara(void *tptr, size_t tsize) {
    ptr = tptr;
    size = tsize;
  }
  ~HostPara() {

  }
};

namespace TONY_CL_HOST {
/*class:CLContainer
description:the container of an opencl call
usage: CLContainer->addHostInPara->addHostOutPar->execute
note:make sure your .cl follows hostOut, HostIn,  parboundArray order as pameters
date:20220115
*/
class CLContainer {
 private:
  /* data */
  vector<cl_platform_id> platforms;

  /* OpenCL 1.1 scalar data types */
  cl_uint numOfPlatforms;
  cl_int error;
  cl_device_id dev;
  cl_context context;               // context
  cl_command_queue queue;           // command queue
  cl_program program;               // program
  cl_kernel kernel;                 // kernel
  bool contentOK = false;
  bool programOK = false;
  bool kernelOK = false;
  //detect how many platforms avaliable
  void CLProbe();
  //get the specific device
  cl_int CLGetDevice(cl_uint id, cl_device_type tyepe);

  //output of host
  vector<HostPara> hostOut;
  vector<cl_mem> kernelIn;
  size_t houts = 0;
  //input of host (result)
  vector<HostPara> hostIn;
  vector<cl_mem> kernelOut;
  //boundary
  vector<uint64_t> boundArray;

  size_t hins = 0;
  int workDimensions = 1;
  //read a file from filename and build program
  void buildProgramFromFile(const char *filename);
  string myName;

 public:
  CLContainer(/* args */);
  //creat from source file with [kernelName],please delte the appendix "*.cl"
  CLContainer(cl_uint id, cl_device_type type, string kernelName);
  //creat from source file with [kernelName],please delte the appendix "*.cl"
  CLContainer(cl_uint id, cl_device_type type, string kernelName, string clName);
  //creat from binary file, kernelName is assigned when build the program
  CLContainer(cl_uint id, cl_device_type type, string kernelName, char *filenameFull);
  ~CLContainer();
  void setWorkDimension(int nd) {
    workDimensions = nd;
  }

  //save the created program file
  void saveProgram(char *outName);
  // set the parameter of host output
  void addHostOutPara(HostPara par);
  // set the parameter of host input
  void addHostInPara(HostPara par);
  //reset the [idx] parameter of host in
  void resetHostIn(size_t idx, HostPara par);
  //reset the [idx] parameter of host out
  void resetHostOut(size_t idx, HostPara par);
  void clearPar();
  //set the boundary of kernel
  void addBoundaryValue(uint64_t bnd) {
    if (contentOK == false) {
      return;
    }
    boundArray.push_back(bnd);
  }
  void resetBoundary(size_t idx, uint64_t bnd) {
    if (idx < boundArray.size()) {
      boundArray[idx] = bnd;
    }
  }
  uint64_t tIn, tRun, tOut;
  //real execution
  void execute(size_t globalSize, size_t localSize);
  //real execution
  void execute(std::vector<size_t> gs, std::vector<size_t> ls);
};
typedef std::shared_ptr<class TONY_CL_HOST::CLContainer> CLContainerPtr;
/**
 * @ingroup CANDY_CppAlgos
 * @def newCLMMCppAlgo
 * @brief (Macro) To creat a new @ref  CLMMCppAlgo shared pointer.
 */
#define newCLContainer std::make_shared<TONY_CL_HOST::CLContainer>
}

#endif
