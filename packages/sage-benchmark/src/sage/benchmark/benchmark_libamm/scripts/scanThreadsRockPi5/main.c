#include <arm_neon.h>
#include <stdio.h>
int isFP32Supported() {
  float32x4_t a;
  // Perform a NEON vector addition of FP32 values
  float32_t result = vaddvq_f32(a);
  printf("ok\r\n");
  // If compilation succeeds, FP32 operations are supported
  return 1;
}
void main() {

  isFP32Supported();
}
