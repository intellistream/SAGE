//#pragma OPENCL EXTENSION cl_khr_fp16 : enable

 __kernel void CLMM(
    __global  float* matrixA,
    __global  float* matrixB,
    __global  long* matrixSizes,
     __global float* result)
{
    long row = get_global_id(0);    // Row index of matrix A
    long col = get_global_id(1);    // Column index of matrix A
    long sizeA = matrixSizes[0];    // Rows of matrix A
    long sizeB = matrixSizes[1];    // Rows of matrix B
    long sizeC = matrixSizes[2];    // Columns of matrix C (result matrix)

    float sum = 0.0f;
    long sampleSize =25;    // Define the sample size
    float scalingFactor = (float)(sizeB) / (float)(sampleSize);
    //srand(114514);
    int seed=114514;
    for (long k = 0; k < sampleSize; k++) {
        // Sample random row and column indices
        long k2=((seed*k * 0x5DEECE66DL + 0xBL) & ((1L << 48) - 1))%sizeB;
         float elementA,elementB;
         elementA = (matrixA[row * sizeB + k2]);    // Access element from matrix A
         elementB = (matrixB[k2 * sizeC + col]);    // Access element from matrix B

        sum += (elementA*elementB);
    }


    result[row * sizeC + col] = sum*scalingFactor;    // Store the computed value in the result matrix
}
