# FindBLASLAPACK.cmake
# 增强的 BLAS/LAPACK 查找模块，支持多种环境
# 适用于 Ubuntu, CentOS, macOS, Conda 等环境

# 设置查找路径
list(APPEND CMAKE_PREFIX_PATH
    ${CMAKE_INSTALL_PREFIX}
    $ENV{CONDA_PREFIX}
    /usr/local
    /usr
    /opt/local
    /opt/homebrew
)

# 设置库文件搜索路径
set(BLAS_LAPACK_SEARCH_PATHS
    # Conda 环境
    $ENV{CONDA_PREFIX}/lib
    $ENV{CONDA_PREFIX}/lib64
    
    # 系统标准路径
    /usr/lib
    /usr/lib64
    /usr/lib/x86_64-linux-gnu
    /usr/lib/i386-linux-gnu
    /usr/lib/aarch64-linux-gnu
    /usr/lib/arm-linux-gnueabihf
    
    # macOS 路径
    /usr/local/lib
    /opt/local/lib
    /opt/homebrew/lib
    /System/Library/Frameworks/Accelerate.framework/Versions/Current/Frameworks/vecLib.framework/Versions/Current
    
    # 其他可能路径
    /opt/intel/mkl/lib/intel64
    /opt/atlas/lib
)

# 尝试不同的 BLAS 实现
set(BLAS_VENDOR_OPTIONS "OpenBLAS" "ATLAS" "Intel10_64lp" "Generic")

foreach(VENDOR ${BLAS_VENDOR_OPTIONS})
    set(BLA_VENDOR ${VENDOR})
    find_package(BLAS QUIET)
    if(BLAS_FOUND)
        message(STATUS "Found BLAS implementation: ${VENDOR}")
        break()
    endif()
endforeach()

# 如果标准查找失败，手动搜索
if(NOT BLAS_FOUND)
    message(STATUS "Standard BLAS search failed, trying manual search...")
    
    # 手动查找 OpenBLAS
    find_library(OPENBLAS_LIB 
        NAMES openblas libopenblas
        PATHS ${BLAS_LAPACK_SEARCH_PATHS}
        NO_DEFAULT_PATH
    )
    
    if(OPENBLAS_LIB)
        set(BLAS_LIBRARIES ${OPENBLAS_LIB})
        set(BLAS_FOUND TRUE)
        message(STATUS "Found OpenBLAS manually: ${OPENBLAS_LIB}")
    else()
        # 尝试查找系统 BLAS
        find_library(BLAS_LIB
            NAMES blas libblas cblas libcblas
            PATHS ${BLAS_LAPACK_SEARCH_PATHS}
            NO_DEFAULT_PATH
        )
        
        if(BLAS_LIB)
            set(BLAS_LIBRARIES ${BLAS_LIB})
            set(BLAS_FOUND TRUE)
            message(STATUS "Found system BLAS manually: ${BLAS_LIB}")
        endif()
    endif()
endif()

# 查找 LAPACK
find_package(LAPACK QUIET)

if(NOT LAPACK_FOUND)
    message(STATUS "Standard LAPACK search failed, trying manual search...")
    
    # 手动查找 LAPACK
    find_library(LAPACK_LIB
        NAMES lapack liblapack
        PATHS ${BLAS_LAPACK_SEARCH_PATHS}
        NO_DEFAULT_PATH
    )
    
    if(LAPACK_LIB)
        set(LAPACK_LIBRARIES ${LAPACK_LIB})
        set(LAPACK_FOUND TRUE)
        message(STATUS "Found LAPACK manually: ${LAPACK_LIB}")
    endif()
endif()

# 结果报告
if(BLAS_FOUND AND LAPACK_FOUND)
    message(STATUS "✅ BLAS and LAPACK found successfully")
    message(STATUS "   BLAS libraries: ${BLAS_LIBRARIES}")
    message(STATUS "   LAPACK libraries: ${LAPACK_LIBRARIES}")
    set(HAVE_BLAS_LAPACK TRUE CACHE BOOL "BLAS and LAPACK available")
else()
    message(WARNING "❌ BLAS or LAPACK not found")
    if(NOT BLAS_FOUND)
        message(WARNING "   BLAS not found")
    endif()
    if(NOT LAPACK_FOUND)
        message(WARNING "   LAPACK not found")
    endif()
    message(STATUS "")
    message(STATUS "🔧 To install BLAS/LAPACK:")
    message(STATUS "   Ubuntu/Debian: sudo apt-get install libopenblas-dev liblapack-dev")
    message(STATUS "   CentOS/RHEL: sudo yum install openblas-devel lapack-devel")
    message(STATUS "   macOS: brew install openblas lapack")
    message(STATUS "   Conda: conda install -c conda-forge openblas liblapack")
    message(STATUS "")
    set(HAVE_BLAS_LAPACK FALSE CACHE BOOL "BLAS and LAPACK not available")
endif()