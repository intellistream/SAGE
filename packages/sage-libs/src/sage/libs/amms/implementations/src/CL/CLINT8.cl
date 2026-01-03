__kernel void CLMM(
    __global  char* matrixA,
    __global  char* matrixB,
    __global  long* matrixSizes,
     __global int* result)
{
    long row = get_global_id(0);    // Row index of matrix A
    long col = get_global_id(1);    // Column index of matrix A
    long sizeA = matrixSizes[0];    // Rows of matrix A
    long sizeB = matrixSizes[1];    // Rows of matrix B
    long sizeC = matrixSizes[2];    // Columns of matrix C (result matrix)

    int sum = 0;
    for (long k = 0; k < sizeB; k++) {
        char elementA = matrixA[row * sizeB + k];    // Access element from matrix A
        char elementB = matrixB[k * sizeC + col];    // Access element from matrix B
        short mul=elementA*elementB;
        sum+=mul;
    }

    result[row * sizeC + col] = sum;    // Store the computed value in the result matrix
}
