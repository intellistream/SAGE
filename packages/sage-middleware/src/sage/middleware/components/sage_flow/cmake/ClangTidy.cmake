# Clang-Tidy Configuration
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    find_program(CLANG_TIDY_EXE clang-tidy)
    if(CLANG_TIDY_EXE)
        set(CMAKE_CXX_CLANG_TIDY
            ${CLANG_TIDY_EXE}
            -extra-arg=-Wno-unknown-warning-option
            -extra-arg=-Wno-ignored-qualifiers
            -config-file=${CMAKE_SOURCE_DIR}/.clang-tidy
        )
    endif()
endif()
