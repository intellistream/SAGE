#include <CL/CLContainer.hpp>
using namespace TONY_CL_HOST;
using namespace std;
static int64_t getRunningUs(struct timeval tstart, struct timeval tend) {
  int64_t s0, e0, s1, e1;
  s0 = tstart.tv_sec;
  s1 = tstart.tv_usec;
  e0 = tend.tv_sec;
  e1 = tend.tv_usec;
  return 1000000 * (e0 - s0) + (e1 - s1);
}
CLContainer::CLContainer(/* args */) {
  CLProbe();
}
CLContainer::CLContainer(cl_uint id, cl_device_type type, string kernelName) {
  // CLProbe();
  myName = "";
  myName += kernelName;
  string sourceName = myName + ".cl";
  CLGetDevice(id, type);
  buildProgramFromFile(sourceName.data());
}
CLContainer::CLContainer(cl_uint id, cl_device_type type, string kernelName, string clName) {
  // CLProbe();

  myName = kernelName;
  string sourceName = clName;
  CLGetDevice(id, type);
  buildProgramFromFile(sourceName.data());
}
CLContainer::CLContainer(cl_uint id, cl_device_type type, string kernelName, char *filenameFull) {
  myName = kernelName;
  CLGetDevice(id, type);
  FILE *fp = fopen(filenameFull, "rb");

// 获取二进制的大小
  size_t binarySize;
  fseek(fp, 0, SEEK_END);
  binarySize = ftell(fp);
  rewind(fp);

// 加载二进制文件
  unsigned char *programBinary = new unsigned char[binarySize];
  fread(programBinary, 1, binarySize, fp);
  fclose(fp);
  program = clCreateProgramWithBinary(context,
                                      1,
                                      &dev,
                                      &binarySize,
                                      (const unsigned char **) &programBinary,
                                      NULL,
                                      NULL);

  delete[] programBinary;

  clBuildProgram(program, 0, NULL, NULL, NULL, NULL);
  programOK = true;
  // Create the compute kernel in the program we wish to run
  kernel = clCreateKernel(program, myName.data(), &error);
  //printf("kerror=%d\r\n",err);
  kernelOK = true;
}
CLContainer::~CLContainer() {
  for (size_t i = 0; i < kernelIn.size(); i++) {
    clReleaseMemObject(kernelIn[i]);
  }
  if (programOK == true) {  //printf("free program\r\n");
    clReleaseProgram(program);
  }
  if (kernelOK == true) {  // printf("free kernel\r\n");
    clReleaseKernel(kernel);
  }

  if (contentOK == true) {
    //clReleaseKernel(kernel);
    //printf("free context\r\n");
    clReleaseCommandQueue(queue);
    clReleaseContext(context);
  }

}
void CLContainer::CLProbe() {
  error = clGetPlatformIDs(0, NULL, &numOfPlatforms);
  if (error != CL_SUCCESS) {
    perror("Unable to find any OpenCL platforms");
    //exit(1);
  }

  printf("Number of OpenCL platforms found: %d\n", numOfPlatforms);

}
cl_int CLContainer::CLGetDevice(cl_uint id, cl_device_type type) {
  cl_platform_id platform;
  error = clGetPlatformIDs(id, &platform, NULL);
  error = clGetDeviceIDs(platform, type, 1, &dev, NULL);
  // Create a context
  context = clCreateContext(NULL,
                            1,
                            &dev,
                            NULL, NULL, NULL);

  // Create a command queue
  queue = clCreateCommandQueue(context,
                               dev,
                               CL_QUEUE_PROFILING_ENABLE, NULL);
  if (error != CL_SUCCESS) {
    perror("Unable to init CL");
    //exit(1);
  } else {
    contentOK = true;
  }
  return error;
}
void CLContainer::buildProgramFromFile(const char *filename) {
  FILE *program_handle;
  char *program_buffer, *program_log;
  size_t program_size, log_size;
  int err;

  /* Read program file and place content into buffer */
  program_handle = fopen(filename, "r");
  if (program_handle == NULL) {
    perror("Couldn't find the program file");
    exit(1);
  }
  fseek(program_handle, 0, SEEK_END);
  program_size = ftell(program_handle);
  rewind(program_handle);
  program_buffer = (char *) malloc(program_size + 1);
  program_buffer[program_size] = '\0';
  fread(program_buffer, sizeof(char), program_size, program_handle);
  fclose(program_handle);

  /* Create program from file
  */
  program = clCreateProgramWithSource(context, 1,
                                      (const char **) &program_buffer, &program_size, &err);
  if (err < 0) {
    perror("Couldn't create the program");
    exit(1);
  }
  free(program_buffer);

  /* Build program

  The fourth parameter accepts options that configure the compilation.
  These are similar to the flags used by gcc. For example, you can
  define a macro with the option -DMACRO=VALUE and turn off optimization
  with -cl-opt-disable.
  */
  err = clBuildProgram(program, 0, NULL, NULL, NULL, NULL);
  if (err < 0) {

    /* Find size of log and print to std output */
    clGetProgramBuildInfo(program, dev, CL_PROGRAM_BUILD_LOG,
                          0, NULL, &log_size);
    program_log = (char *) malloc(log_size + 1);
    program_log[log_size] = '\0';
    clGetProgramBuildInfo(program, dev, CL_PROGRAM_BUILD_LOG,
                          log_size + 1, program_log, NULL);
    printf("%s\n", program_log);
    free(program_log);
    // exit(1);
  }

  programOK = true;
  // Create the compute kernel in the program we wish to run
  kernel = clCreateKernel(program, myName.data(), &err);
  //printf("kerror=%d\r\n",err);
  kernelOK = true;
}

void CLContainer::clearPar() {
  hostIn.clear();
  hostOut.clear();
}

void CLContainer::addHostOutPara(HostPara par) {
  if (contentOK == false) {
    return;
  }
  hostOut.push_back(par);
  cl_mem clt;
  clt = clCreateBuffer(context, CL_MEM_READ_ONLY, par.size, NULL, NULL);
  kernelIn.push_back(clt);
}

void CLContainer::resetHostOut(size_t idx, HostPara par) {
  if (idx > hostOut.size() - 1) {
    return;
  }
  hostOut[idx] = par;
  clReleaseMemObject(kernelIn[idx]);
  kernelIn[idx] = clCreateBuffer(context, CL_MEM_READ_ONLY, par.size, NULL, NULL);
}
void CLContainer::addHostInPara(HostPara par) {
  if (contentOK == false) {
    return;
  }
  hostIn.push_back(par);
  cl_mem clt;
  clt = clCreateBuffer(context, CL_MEM_WRITE_ONLY, par.size, NULL, NULL);
  kernelOut.push_back(clt);
}

void CLContainer::resetHostIn(size_t idx, HostPara par) {
  if (idx > hostIn.size() - 1) {
    return;
  }
  hostIn[idx] = par;
  clReleaseMemObject(kernelOut[idx]);
  kernelOut[idx] = clCreateBuffer(context, CL_MEM_WRITE_ONLY, par.size, NULL, NULL);
}

void CLContainer::execute(size_t gs, size_t ls) {
  struct timeval ts, te;
  cl_uint pars = 0;
  int err;
  if (kernelOK == false) {
    return;
  }
  //prepare host out
  for (size_t i = 0; i < hostOut.size(); i++) {  //err = clEnqueueWriteBuffer(queue, kernelIn[i], CL_TRUE, 0,
    //  hostOut[i].size, hostOut[i].ptr, 0, NULL, NULL);

    err = clSetKernelArg(kernel, pars, sizeof(cl_mem), &kernelIn[i]);

    pars++;
  }



  //prepare host in
  for (size_t i = 0; i < hostIn.size(); i++) {
    err |= clSetKernelArg(kernel, pars, sizeof(cl_mem), &kernelOut[i]);
    pars++;
  }

  //prepare boundarys
  for (size_t i = 0; i < boundArray.size(); i++) {
    err |= clSetKernelArg(kernel, pars, sizeof(uint64_t), &boundArray[i]);
    pars++;
  }
  // Execute the kernel over the entire range of the data set
  size_t globalSize, localSize, off;
  globalSize = gs;
  localSize = ls;
  off = 0;

  gettimeofday(&ts, NULL);
  for (size_t i = 0; i < hostOut.size(); i++) {
    err = clEnqueueWriteBuffer(queue, kernelIn[i], CL_TRUE, 0,
                               hostOut[i].size, hostOut[i].ptr, 0, NULL, NULL);

  }
  gettimeofday(&te, NULL);
  tIn = getRunningUs(ts, te);

  gettimeofday(&ts, NULL);
  err = clEnqueueNDRangeKernel(queue, kernel, workDimensions, &off, &globalSize, &localSize,
                               0, NULL, NULL);
  //printf("error=%d\r\n",err);
  // Wait for the command queue to get serviced before reading back results
  clFinish(queue);
  gettimeofday(&te, NULL);
  tRun = getRunningUs(ts, te);

  gettimeofday(&ts, NULL);
  for (size_t i = 0; i < hostIn.size(); i++) {
    clEnqueueReadBuffer(queue, kernelOut[i], CL_TRUE, 0,
                        hostIn[i].size, hostIn[i].ptr, 0, NULL, NULL);
  }
  gettimeofday(&te, NULL);
  tOut = getRunningUs(ts, te);
}

void CLContainer::execute(std::vector<size_t> gs, std::vector<size_t> ls) {
  struct timeval ts, te;
  cl_uint pars = 0;
  int err;
  if (kernelOK == false) {
    return;
  }
  //prepare host out
  for (size_t i = 0; i < hostOut.size(); i++) {  //err = clEnqueueWriteBuffer(queue, kernelIn[i], CL_TRUE, 0,
    //  hostOut[i].size, hostOut[i].ptr, 0, NULL, NULL);

    err = clSetKernelArg(kernel, pars, sizeof(cl_mem), &kernelIn[i]);

    pars++;
  }



  //prepare host in
  for (size_t i = 0; i < hostIn.size(); i++) {
    err |= clSetKernelArg(kernel, pars, sizeof(cl_mem), &kernelOut[i]);
    pars++;
  }

  //prepare boundarys
  for (size_t i = 0; i < boundArray.size(); i++) {
    err |= clSetKernelArg(kernel, pars, sizeof(uint64_t), &boundArray[i]);
    pars++;
  }
  // Execute the kernel over the entire range of the data set


  gettimeofday(&ts, NULL);
  for (size_t i = 0; i < hostOut.size(); i++) {
    err = clEnqueueWriteBuffer(queue, kernelIn[i], CL_TRUE, 0,
                               hostOut[i].size, hostOut[i].ptr, 0, NULL, NULL);

  }
  gettimeofday(&te, NULL);
  tIn = getRunningUs(ts, te);

  gettimeofday(&ts, NULL);
  err = clEnqueueNDRangeKernel(queue, kernel, workDimensions, NULL, gs.data(), ls.data(),
                               0, NULL, NULL);
  //printf("error=%d\r\n",err);
  // Wait for the command queue to get serviced before reading back results
  clFinish(queue);
  gettimeofday(&te, NULL);
  tRun = getRunningUs(ts, te);

  gettimeofday(&ts, NULL);
  for (size_t i = 0; i < hostIn.size(); i++) {
    clEnqueueReadBuffer(queue, kernelOut[i], CL_TRUE, 0,
                        hostIn[i].size, hostIn[i].ptr, 0, NULL, NULL);
  }
  gettimeofday(&te, NULL);
  tOut = getRunningUs(ts, te);
}
void CLContainer::saveProgram(char *outName) {
  cl_uint numDevices = 0;

// 获取 program 绑定过的 device 数量
  clGetProgramInfo(program,
                   CL_PROGRAM_NUM_DEVICES,
                   sizeof(cl_uint),
                   &numDevices,
                   NULL);

// 获取所有的 device ID
  cl_device_id *devices = new cl_device_id[numDevices];
  clGetProgramInfo(program,
                   CL_PROGRAM_DEVICES,
                   sizeof(cl_device_id) * numDevices,
                   devices,
                   NULL);

// 决定每个 program 二进制的大小
  size_t *programBinarySizes = new size_t[numDevices];
  clGetProgramInfo(program,
                   CL_PROGRAM_BINARY_SIZES,
                   sizeof(size_t) * numDevices,
                   programBinarySizes,
                   NULL);

  unsigned char **programBinaries = new unsigned char *[numDevices];
  for (cl_uint i = 0; i < numDevices; ++i)
    programBinaries[i] = new unsigned char[programBinarySizes[i]];

// 获取所有的 program 二进制
  clGetProgramInfo(program,
                   CL_PROGRAM_BINARIES,
                   sizeof(unsigned char *) * numDevices,
                   programBinaries,
                   NULL);

// 存储 device 所需要的二进制
  for (cl_uint i = 0; i < numDevices; ++i) {
    // 只存储 device 需要的二进制，多个 device 需要存储多个二进制
    if (devices[i] == dev) {
      FILE *fp = fopen(outName, "wb");
      fwrite(programBinaries[i], 1, programBinarySizes[i], fp);
      fclose(fp);
      break;
    }
  }

// 清理
  delete[] devices;
  delete[] programBinarySizes;
  for (cl_uint i = 0; i < numDevices; ++i)
    delete[] programBinaries[i];
  delete[] programBinaries;
//free(tpro);
}
