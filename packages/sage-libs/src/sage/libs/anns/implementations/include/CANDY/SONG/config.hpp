#ifndef CANDY_INCLUDE_ALGORITHMS_SONG_CONFIG_CUH
#define CANDY_INCLUDE_ALGORITHMS_SONG_CONFIG_CUH

//#define __ENABLE_HASH
namespace SONG_KERNEL {
typedef float data_value_t;

#ifdef __ENABLE_HASH
typedef unsigned int value_t;
typedef int dist_t;
#else
typedef float value_t;
typedef double dist_t;
#endif
typedef size_t idx_t;
typedef int UINT;
}  // namespace SONG_KERNEL

//#define ACC_BATCH_SIZE 4096
#define ACC_BATCH_SIZE 1000000

//for GPU
#define FIXED_DEGREE 31
#define FIXED_DEGREE_SHIFT 5

//for CPU construction
#define SEARCH_DEGREE 15
#define CONSTRUCT_SEARCH_BUDGET 150

#endif
