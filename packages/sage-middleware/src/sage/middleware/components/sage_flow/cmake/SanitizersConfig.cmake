# ============================================================================
# Sanitizers Configuration Module - Enhanced Version
# ============================================================================
# This module provides comprehensive sanitizer configuration for SAGE Flow project
# Supports AddressSanitizer, MemorySanitizer, ThreadSanitizer, UndefinedBehaviorSanitizer, LeakSanitizer
# Includes conflict detection, compiler optimization, and CI/CD integration

# ============================================================================
# Sanitizer Options
# ============================================================================

option(SAGE_SANITIZER_ADDRESS "Enable AddressSanitizer for memory error detection" OFF)
option(SAGE_SANITIZER_MEMORY "Enable MemorySanitizer for uninitialized memory access" OFF)
option(SAGE_SANITIZER_THREAD "Enable ThreadSanitizer for data race detection" OFF)
option(SAGE_SANITIZER_UNDEFINED "Enable UndefinedBehaviorSanitizer for undefined behavior" OFF)
option(SAGE_SANITIZER_LEAK "Enable LeakSanitizer for memory leak detection" OFF)

# Advanced options
option(SAGE_SANITIZER_ENABLE_TESTS "Enable sanitizers for tests" ON)
option(SAGE_SANITIZER_VERBOSE "Enable verbose sanitizer output" OFF)
option(SAGE_SANITIZER_STACK_TRACE "Enable stack trace in sanitizer reports" ON)

# Sanitizer level options
set(SAGE_SANITIZER_LEVEL "medium" CACHE STRING "Sanitizer level (minimal, medium, aggressive, comprehensive)")
set_property(CACHE SAGE_SANITIZER_LEVEL PROPERTY STRINGS minimal medium aggressive comprehensive)

# ============================================================================
# Compiler and Platform Detection
# ============================================================================

# Detect compiler capabilities
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    set(SAGE_SANITIZER_COMPILER_CLANG TRUE)
    set(SAGE_SANITIZER_SUPPORTED TRUE)
elseif(CMAKE_CXX_COMPILER_ID MATCHES "GNU")
    set(SAGE_SANITIZER_COMPILER_GCC TRUE)
    set(SAGE_SANITIZER_SUPPORTED TRUE)
elseif(MSVC)
    set(SAGE_SANITIZER_COMPILER_MSVC TRUE)
    set(SAGE_SANITIZER_SUPPORTED TRUE)
else()
    set(SAGE_SANITIZER_SUPPORTED FALSE)
    message(WARNING "Sanitizers are not fully supported with ${CMAKE_CXX_COMPILER_ID} compiler")
endif()

# Detect platform
if(WIN32)
    set(SAGE_SANITIZER_PLATFORM_WINDOWS TRUE)
elseif(UNIX AND NOT APPLE)
    set(SAGE_SANITIZER_PLATFORM_LINUX TRUE)
elseif(APPLE)
    set(SAGE_SANITIZER_PLATFORM_MACOS TRUE)
endif()

# ============================================================================
# Sanitizer Conflict Detection
# ============================================================================

function(sage_check_sanitizer_conflicts)
    set(CONFLICTS_FOUND FALSE)

    # AddressSanitizer conflicts with MemorySanitizer
    if(SAGE_SANITIZER_ADDRESS AND SAGE_SANITIZER_MEMORY)
        message(FATAL_ERROR "AddressSanitizer and MemorySanitizer cannot be used together")
        set(CONFLICTS_FOUND TRUE)
    endif()

    # ThreadSanitizer conflicts with MemorySanitizer
    if(SAGE_SANITIZER_THREAD AND SAGE_SANITIZER_MEMORY)
        message(FATAL_ERROR "ThreadSanitizer and MemorySanitizer cannot be used together")
        set(CONFLICTS_FOUND TRUE)
    endif()

    # LeakSanitizer is automatically enabled with AddressSanitizer
    if(SAGE_SANITIZER_LEAK AND SAGE_SANITIZER_ADDRESS)
        message(WARNING "LeakSanitizer is automatically enabled with AddressSanitizer")
    endif()

    if(CONFLICTS_FOUND)
        message(FATAL_ERROR "Sanitizer configuration conflicts detected. Please fix the configuration.")
    endif()
endfunction()

# ============================================================================
# Sanitizer Flags Configuration
# ============================================================================

function(sage_get_sanitizer_flags OUT_VAR)
    set(FLAGS "")

    # Check for conflicts first
    sage_check_sanitizer_conflicts()

    # AddressSanitizer
    if(SAGE_SANITIZER_ADDRESS)
        if(SAGE_SANITIZER_COMPILER_CLANG OR SAGE_SANITIZER_COMPILER_GCC)
            list(APPEND FLAGS "-fsanitize=address")
        elseif(SAGE_SANITIZER_COMPILER_MSVC)
            list(APPEND FLAGS "/fsanitize=address")
        endif()
    endif()

    # MemorySanitizer (Clang only)
    if(SAGE_SANITIZER_MEMORY)
        if(SAGE_SANITIZER_COMPILER_CLANG)
            list(APPEND FLAGS "-fsanitize=memory")
        else()
            message(WARNING "MemorySanitizer is only supported with Clang compiler")
        endif()
    endif()

    # ThreadSanitizer
    if(SAGE_SANITIZER_THREAD)
        if(SAGE_SANITIZER_COMPILER_CLANG OR SAGE_SANITIZER_COMPILER_GCC)
            list(APPEND FLAGS "-fsanitize=thread")
        elseif(SAGE_SANITIZER_COMPILER_MSVC)
            list(APPEND FLAGS "/fsanitize=thread")
        endif()
    endif()

    # UndefinedBehaviorSanitizer
    if(SAGE_SANITIZER_UNDEFINED)
        if(SAGE_SANITIZER_COMPILER_CLANG OR SAGE_SANITIZER_COMPILER_GCC)
            list(APPEND FLAGS "-fsanitize=undefined")
        elseif(SAGE_SANITIZER_COMPILER_MSVC)
            list(APPEND FLAGS "/fsanitize=undefined")
        endif()
    endif()

    # LeakSanitizer
    if(SAGE_SANITIZER_LEAK)
        if(SAGE_SANITIZER_COMPILER_CLANG OR SAGE_SANITIZER_COMPILER_GCC)
            list(APPEND FLAGS "-fsanitize=leak")
        endif()
    endif()

    # Add common sanitizer flags
    if(FLAGS)
        # Compiler-specific common flags
        if(SAGE_SANITIZER_COMPILER_CLANG OR SAGE_SANITIZER_COMPILER_GCC)
            list(APPEND FLAGS "-fno-omit-frame-pointer")
            list(APPEND FLAGS "-g")

            if(SAGE_SANITIZER_STACK_TRACE)
                list(APPEND FLAGS "-fno-optimize-sibling-calls")
            endif()

            # Level-specific flags
            if(SAGE_SANITIZER_LEVEL STREQUAL "minimal")
                if(SAGE_SANITIZER_ADDRESS)
                    list(APPEND FLAGS "-fsanitize-recover=address")
                endif()
                if(SAGE_SANITIZER_UNDEFINED)
                    list(APPEND FLAGS "-fsanitize-recover=undefined")
                endif()
            elseif(SAGE_SANITIZER_LEVEL STREQUAL "medium")
                # Default settings - some recovery
                if(SAGE_SANITIZER_ADDRESS)
                    list(APPEND FLAGS "-fsanitize-recover=address")
                endif()
            elseif(SAGE_SANITIZER_LEVEL STREQUAL "aggressive")
                list(APPEND FLAGS "-fsanitize-trap=all")
                list(APPEND FLAGS "-fno-sanitize-recover=all")
            elseif(SAGE_SANITIZER_LEVEL STREQUAL "comprehensive")
                # Enable multiple sanitizers together (where compatible)
                if(NOT SAGE_SANITIZER_MEMORY AND NOT SAGE_SANITIZER_THREAD)
                    if(NOT SAGE_SANITIZER_ADDRESS)
                        list(APPEND FLAGS "-fsanitize=address")
                    endif()
                    if(NOT SAGE_SANITIZER_UNDEFINED)
                        list(APPEND FLAGS "-fsanitize=undefined")
                    endif()
                    if(NOT SAGE_SANITIZER_LEAK)
                        list(APPEND FLAGS "-fsanitize=leak")
                    endif()
                endif()
            endif()

            # Verbose output
            if(SAGE_SANITIZER_VERBOSE)
                list(APPEND FLAGS "-fsanitize-undefined-trap-on-error")
            endif()

        elseif(SAGE_SANITIZER_COMPILER_MSVC)
            # MSVC-specific flags would go here
            list(APPEND FLAGS "/Zi")  # Debug information
        endif()
    endif()

    set(${OUT_VAR} "${FLAGS}" PARENT_SCOPE)
endfunction()

# ============================================================================
# Apply Sanitizers to Target
# ============================================================================

function(sage_apply_sanitizers TARGET_NAME)
    if(NOT SAGE_SANITIZER_SUPPORTED)
        return()
    endif()

    sage_get_sanitizer_flags(SANITIZER_FLAGS)

    if(SANITIZER_FLAGS)
        target_compile_options(${TARGET_NAME} PRIVATE ${SANITIZER_FLAGS})
        target_link_options(${TARGET_NAME} PRIVATE ${SANITIZER_FLAGS})

        message(STATUS "Applied sanitizers to ${TARGET_NAME}: ${SANITIZER_FLAGS}")
    endif()
endfunction()

# ============================================================================
# Environment Variables for Sanitizers
# ============================================================================

function(sage_get_sanitizer_env_vars OUT_VAR)
    set(ENV_VARS "")

    # AddressSanitizer options
    if(SAGE_SANITIZER_ADDRESS)
        set(ASAN_OPTS "detect_leaks=1:abort_on_error=1")
        if(SAGE_SANITIZER_VERBOSE)
            set(ASAN_OPTS "${ASAN_OPTS}:verbosity=1:debug=1")
        endif()
        if(SAGE_SANITIZER_STACK_TRACE)
            set(ASAN_OPTS "${ASAN_OPTS}:fast_unwind_on_malloc=0")
        endif()
        list(APPEND ENV_VARS "ASAN_OPTIONS=${ASAN_OPTS}")
    endif()

    # MemorySanitizer options
    if(SAGE_SANITIZER_MEMORY)
        set(MSAN_OPTS "abort_on_error=1")
        if(SAGE_SANITIZER_VERBOSE)
            set(MSAN_OPTS "${MSAN_OPTS}:verbosity=1")
        endif()
        list(APPEND ENV_VARS "MSAN_OPTIONS=${MSAN_OPTS}")
    endif()

    # ThreadSanitizer options
    if(SAGE_SANITIZER_THREAD)
        set(TSAN_OPTS "abort_on_error=1")
        if(SAGE_SANITIZER_VERBOSE)
            set(TSAN_OPTS "${TSAN_OPTS}:verbosity=1")
        endif()
        if(SAGE_SANITIZER_STACK_TRACE)
            set(TSAN_OPTS "${TSAN_OPTS}:history_size=7")
        endif()
        list(APPEND ENV_VARS "TSAN_OPTIONS=${TSAN_OPTS}")
    endif()

    # UndefinedBehaviorSanitizer options
    if(SAGE_SANITIZER_UNDEFINED)
        set(UBSAN_OPTS "abort_on_error=1")
        if(SAGE_SANITIZER_VERBOSE)
            set(UBSAN_OPTS "${UBSAN_OPTS}:verbosity=1")
        endif()
        if(SAGE_SANITIZER_STACK_TRACE)
            set(UBSAN_OPTS "${UBSAN_OPTS}:print_stacktrace=1")
        endif()
        list(APPEND ENV_VARS "UBSAN_OPTIONS=${UBSAN_OPTS}")
    endif()

    # LeakSanitizer options
    if(SAGE_SANITIZER_LEAK)
        set(LSAN_OPTS "abort_on_error=1")
        if(SAGE_SANITIZER_VERBOSE)
            set(LSAN_OPTS "${LSAN_OPTS}:verbosity=1")
        endif()
        list(APPEND ENV_VARS "LSAN_OPTIONS=${LSAN_OPTS}")
    endif()

    # Common environment variables for symbolization
    if(ENV_VARS)
        # Try to find llvm-symbolizer
        find_program(LLVM_SYMBOLIZER llvm-symbolizer)
        if(LLVM_SYMBOLIZER)
            list(APPEND ENV_VARS "ASAN_SYMBOLIZER_PATH=${LLVM_SYMBOLIZER}")
            list(APPEND ENV_VARS "UBSAN_SYMBOLIZER_PATH=${LLVM_SYMBOLIZER}")
            list(APPEND ENV_VARS "MSAN_SYMBOLIZER_PATH=${LLVM_SYMBOLIZER}")
        endif()

        # Additional common options
        if(SAGE_SANITIZER_PLATFORM_LINUX)
            list(APPEND ENV_VARS "LSAN_OPTIONS=suppressions=${CMAKE_SOURCE_DIR}/lsan.supp")
        endif()
    endif()

    set(${OUT_VAR} "${ENV_VARS}" PARENT_SCOPE)
endfunction()

# ============================================================================
# Get Active Sanitizers
# ============================================================================

function(sage_get_active_sanitizers OUT_VAR)
    set(ACTIVE_SANITIZERS "")

    if(SAGE_SANITIZER_ADDRESS)
        list(APPEND ACTIVE_SANITIZERS "address")
    endif()

    if(SAGE_SANITIZER_MEMORY)
        list(APPEND ACTIVE_SANITIZERS "memory")
    endif()

    if(SAGE_SANITIZER_THREAD)
        list(APPEND ACTIVE_SANITIZERS "thread")
    endif()

    if(SAGE_SANITIZER_UNDEFINED)
        list(APPEND ACTIVE_SANITIZERS "undefined")
    endif()

    if(SAGE_SANITIZER_LEAK)
        list(APPEND ACTIVE_SANITIZERS "leak")
    endif()

    set(${OUT_VAR} "${ACTIVE_SANITIZERS}" PARENT_SCOPE)
endfunction()

# ============================================================================
# Test Integration
# ============================================================================

function(sage_apply_sanitizers_to_tests)
    if(NOT SAGE_SANITIZER_ENABLE_TESTS)
        return()
    endif()

    # Apply sanitizers to all test targets
    get_property(TEST_TARGETS GLOBAL PROPERTY SGE_TEST_TARGETS)
    foreach(TEST_TARGET ${TEST_TARGETS})
        if(TARGET ${TEST_TARGET})
            sage_apply_sanitizers(${TEST_TARGET})
            message(STATUS "Applied sanitizers to test target: ${TEST_TARGET}")
        endif()
    endforeach()
endfunction()

# ============================================================================
# Print Sanitizer Configuration
# ============================================================================

function(sage_print_sanitizer_config)
    sage_get_active_sanitizers(ACTIVE_SANITIZERS)
    sage_get_sanitizer_flags(SANITIZER_FLAGS)
    sage_get_sanitizer_env_vars(ENV_VARS)

    message(STATUS "=== Sanitizer Configuration ===")
    message(STATUS "Level: ${SAGE_SANITIZER_LEVEL}")
    message(STATUS "Compiler: ${CMAKE_CXX_COMPILER_ID}")
    message(STATUS "Platform: ${CMAKE_SYSTEM_NAME}")
    message(STATUS "Active sanitizers: ${ACTIVE_SANITIZERS}")
    if(SANITIZER_FLAGS)
        message(STATUS "Compiler flags: ${SANITIZER_FLAGS}")
    endif()
    if(ENV_VARS)
        message(STATUS "Environment variables:")
        foreach(ENV_VAR ${ENV_VARS})
            message(STATUS "  ${ENV_VAR}")
        endforeach()
    endif()
    message(STATUS "Verbose output: ${SAGE_SANITIZER_VERBOSE}")
    message(STATUS "Stack traces: ${SAGE_SANITIZER_STACK_TRACE}")
    message(STATUS "Tests enabled: ${SAGE_SANITIZER_ENABLE_TESTS}")
    message(STATUS "===============================")
endfunction()

# ============================================================================
# Generate Suppression Files
# ============================================================================

function(sage_generate_sanitizer_suppressions)
    # Create LSAN suppressions file for common false positives
    set(LSAN_SUPP_FILE "${CMAKE_BINARY_DIR}/lsan.supp")
    file(WRITE ${LSAN_SUPP_FILE}
        "# LeakSanitizer suppressions for SAGE Flow
# This file contains suppressions for known false positives

# Suppress leaks from system libraries
leak:libstdc++*
leak:libgcc*
leak:libc++*

# Suppress leaks from Python (if using Python bindings)
leak:libpython*

# Suppress leaks from external libraries
leak:libprotobuf*
leak:libgrpc*
"
    )
    message(STATUS "Generated LSAN suppressions file: ${LSAN_SUPP_FILE}")
endfunction()

# ============================================================================
# Initialize Sanitizer Configuration
# ============================================================================

# Set default environment variables
sage_get_sanitizer_env_vars(SAGE_SANITIZER_ENV_VARS)

# Generate suppression files if needed
if(SAGE_SANITIZER_LEAK OR SAGE_SANITIZER_ADDRESS)
    sage_generate_sanitizer_suppressions()
endif()

# Print configuration if any sanitizers are enabled
sage_get_active_sanitizers(ACTIVE_SANITIZERS)
if(ACTIVE_SANITIZERS)
    sage_print_sanitizer_config()
endif()

# ============================================================================
# Convenience Functions for Common Configurations
# ============================================================================

# Enable development-friendly sanitizer configuration
function(sage_enable_dev_sanitizers)
    set(SAGE_SANITIZER_ADDRESS ON PARENT_SCOPE)
    set(SAGE_SANITIZER_UNDEFINED ON PARENT_SCOPE)
    set(SAGE_SANITIZER_LEAK ON PARENT_SCOPE)
    set(SAGE_SANITIZER_LEVEL "medium" PARENT_SCOPE)
    set(SAGE_SANITIZER_VERBOSE ON PARENT_SCOPE)
    message(STATUS "Enabled development sanitizer configuration")
endfunction()

# Enable production-ready sanitizer configuration
function(sage_enable_prod_sanitizers)
    set(SAGE_SANITIZER_ADDRESS ON PARENT_SCOPE)
    set(SAGE_SANITIZER_UNDEFINED ON PARENT_SCOPE)
    set(SAGE_SANITIZER_LEVEL "minimal" PARENT_SCOPE)
    set(SAGE_SANITIZER_STACK_TRACE OFF PARENT_SCOPE)
    message(STATUS "Enabled production sanitizer configuration")
endfunction()

# Enable comprehensive testing sanitizer configuration
function(sage_enable_test_sanitizers)
    set(SAGE_SANITIZER_ADDRESS ON PARENT_SCOPE)
    set(SAGE_SANITIZER_UNDEFINED ON PARENT_SCOPE)
    set(SAGE_SANITIZER_THREAD ON PARENT_SCOPE)
    set(SAGE_SANITIZER_LEVEL "aggressive" PARENT_SCOPE)
    set(SAGE_SANITIZER_VERBOSE ON PARENT_SCOPE)
    set(SAGE_SANITIZER_STACK_TRACE ON PARENT_SCOPE)
    message(STATUS "Enabled comprehensive testing sanitizer configuration")
endfunction()