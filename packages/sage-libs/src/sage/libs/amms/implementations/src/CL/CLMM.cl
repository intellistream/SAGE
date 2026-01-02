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
    for (long k = 0; k < sizeB; k++) {
        float elementA = matrixA[row * sizeB + k];    // Access element from matrix A
        float elementB = matrixB[k * sizeC + col];    // Access element from matrix B
        sum += elementA * elementB;
    }

    result[row * sizeC + col] = sum;    // Store the computed value in the result matrix
}
