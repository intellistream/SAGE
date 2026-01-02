add_subdirectory(Utils)
add_subdirectory(MatrixLoader)
add_subdirectory(Parallelization)
add_subdirectory(CPPAlgos)
add_subdirectory(Streaming)
add_sources(
        myVecAdd.cpp
        pythonBoundings.cpp
)
#gcc options
if (DEFINED ENV{LibAMM_CL})
    add_sources(
            CLContainer.cpp
    )
endif ()

include_directories("../include/")
