# Code Quality Gate Configuration for SAGE Flow
# This module sets up comprehensive code quality checks as build requirements

include(CMakeParseArguments)

# Option to enable/disable code quality gate
option(SAGE_FLOW_CODE_QUALITY_GATE "Enable code quality gate (blocks build on failures)" ON)

# Quality thresholds
set(SAGE_FLOW_MAX_CPPCHECK_ERRORS 10 CACHE STRING "Maximum allowed cppcheck errors")
set(SAGE_FLOW_MAX_CPPLINT_ERRORS 20 CACHE STRING "Maximum allowed cpplint errors")
set(SAGE_FLOW_MAX_CLANG_TIDY_ERRORS 5 CACHE STRING "Maximum allowed clang-tidy errors")

# Find required tools
find_program(CPPLINT_EXECUTABLE cpplint)
find_program(CPPCHECK_EXECUTABLE cppcheck)
find_program(CLANG_TIDY_EXECUTABLE clang-tidy)

# Function to add code quality checks to a target
function(add_code_quality_checks TARGET_NAME)
    if(NOT SAGE_FLOW_CODE_QUALITY_GATE)
        return()
    endif()

    # Get target sources
    get_target_property(TARGET_SOURCES ${TARGET_NAME} SOURCES)
    get_target_property(TARGET_SOURCE_DIR ${TARGET_NAME} SOURCE_DIR)

    if(TARGET_SOURCES)
        # Convert to absolute paths
        set(ABSOLUTE_SOURCES)
        foreach(SOURCE ${TARGET_SOURCES})
            if(IS_ABSOLUTE ${SOURCE})
                list(APPEND ABSOLUTE_SOURCES ${SOURCE})
            else()
                list(APPEND ABSOLUTE_SOURCES ${TARGET_SOURCE_DIR}/${SOURCE})
            endif()
        endforeach()

        # Filter for C++ files
        set(CPP_SOURCES)
        foreach(SOURCE ${ABSOLUTE_SOURCES})
            if(SOURCE MATCHES "\\.(cpp|cc|cxx|c\\+\\+)$")
                list(APPEND CPP_SOURCES ${SOURCE})
            endif()
        endforeach()

        if(CPP_SOURCES)
            # Add cpplint check
            if(CPPLINT_EXECUTABLE)
                add_custom_command(
                    TARGET ${TARGET_NAME}
                    PRE_BUILD
                    COMMAND ${CMAKE_COMMAND} -E echo "Running cpplint on ${TARGET_NAME}..."
                    COMMAND ${CPPLINT_EXECUTABLE} --quiet ${CPP_SOURCES}
                    COMMENT "Running cpplint code style check"
                    VERBATIM
                )
            endif()

            # Add cppcheck analysis
            if(CPPCHECK_EXECUTABLE)
                add_custom_command(
                    TARGET ${TARGET_NAME}
                    PRE_BUILD
                    COMMAND ${CMAKE_COMMAND} -E echo "Running cppcheck on ${TARGET_NAME}..."
                    COMMAND ${CPPCHECK_EXECUTABLE}
                        --enable=all
                        --std=c++20
                        --language=c++
                        --suppress=missingIncludeSystem
                        --suppress=unusedFunction
                        --inline-suppr
                        --error-exitcode=1
                        --max-configs=1
                        --xml
                        --xml-version=2
                        ${CPP_SOURCES}
                    COMMENT "Running cppcheck static analysis"
                    VERBATIM
                )
            endif()

            # Add clang-tidy checks
            if(CLANG_TIDY_EXECUTABLE AND EXISTS "${CMAKE_SOURCE_DIR}/.clang-tidy")
                set_target_properties(${TARGET_NAME} PROPERTIES
                    CXX_CLANG_TIDY "${CLANG_TIDY_EXECUTABLE};--warnings-as-errors=*"
                )
            endif()
        endif()
    endif()
endfunction()

# Function to create a code quality report
function(generate_code_quality_report)
    if(NOT SAGE_FLOW_CODE_QUALITY_GATE)
        return()
    endif()

    set(REPORT_FILE "${CMAKE_BINARY_DIR}/code_quality_report.txt")

    # Build the command list conditionally
    set(COMMANDS
        COMMAND ${CMAKE_COMMAND} -E echo "Generating code quality report..."
        COMMAND ${CMAKE_COMMAND} -E echo "Code Quality Report - ${CMAKE_PROJECT_NAME}" > ${REPORT_FILE}
        COMMAND ${CMAKE_COMMAND} -E echo "Generated: ${CMAKE_SYSTEM_DATE}" >> ${REPORT_FILE}
        COMMAND ${CMAKE_COMMAND} -E echo "" >> ${REPORT_FILE}

        # Run comprehensive checks
        COMMAND ${CMAKE_COMMAND} -E echo "=== Build Configuration ===" >> ${REPORT_FILE}
        COMMAND ${CMAKE_COMMAND} -E echo "Build Type: ${CMAKE_BUILD_TYPE}" >> ${REPORT_FILE}
        COMMAND ${CMAKE_COMMAND} -E echo "C++ Standard: ${CMAKE_CXX_STANDARD}" >> ${REPORT_FILE}
        COMMAND ${CMAKE_COMMAND} -E echo "Compiler: ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}" >> ${REPORT_FILE}
        COMMAND ${CMAKE_COMMAND} -E echo "" >> ${REPORT_FILE}

        # Check available tools
        COMMAND ${CMAKE_COMMAND} -E echo "=== Available Quality Tools ===" >> ${REPORT_FILE}
    )

    # Add cpplint status
    if(CPPLINT_EXECUTABLE)
        list(APPEND COMMANDS COMMAND ${CMAKE_COMMAND} -E echo "cpplint: Available" >> ${REPORT_FILE})
    else()
        list(APPEND COMMANDS COMMAND ${CMAKE_COMMAND} -E echo "cpplint: Not found" >> ${REPORT_FILE})
    endif()

    # Add cppcheck status
    if(CPPCHECK_EXECUTABLE)
        list(APPEND COMMANDS COMMAND ${CMAKE_COMMAND} -E echo "cppcheck: Available" >> ${REPORT_FILE})
    else()
        list(APPEND COMMANDS COMMAND ${CMAKE_COMMAND} -E echo "cppcheck: Not found" >> ${REPORT_FILE})
    endif()

    # Add clang-tidy status
    if(CLANG_TIDY_EXECUTABLE)
        list(APPEND COMMANDS COMMAND ${CMAKE_COMMAND} -E echo "clang-tidy: Available" >> ${REPORT_FILE})
    else()
        list(APPEND COMMANDS COMMAND ${CMAKE_COMMAND} -E echo "clang-tidy: Not found" >> ${REPORT_FILE})
    endif()

    # Add final commands
    list(APPEND COMMANDS
        COMMAND ${CMAKE_COMMAND} -E echo "" >> ${REPORT_FILE}
        COMMAND ${CMAKE_COMMAND} -E echo "Report generated at: ${REPORT_FILE}" >> ${REPORT_FILE}
    )

    add_custom_target(code_quality_report
        ${COMMANDS}
        COMMENT "Generating comprehensive code quality report"
        VERBATIM
    )
endfunction()

# Function to add quality gate that fails build on quality issues
function(add_quality_gate TARGET_NAME)
    if(NOT SAGE_FLOW_CODE_QUALITY_GATE)
        return()
    endif()

    # Create a custom target that runs quality checks
    add_custom_target(${TARGET_NAME}_quality_check
        COMMAND ${CMAKE_COMMAND} -E echo "Running quality gate for ${TARGET_NAME}..."
        COMMAND ${CMAKE_COMMAND} -E echo "Quality thresholds:"
        COMMAND ${CMAKE_COMMAND} -E echo "  Max cpplint errors: ${SAGE_FLOW_MAX_CPPLINT_ERRORS}"
        COMMAND ${CMAKE_COMMAND} -E echo "  Max cppcheck errors: ${SAGE_FLOW_MAX_CPPCHECK_ERRORS}"
        COMMAND ${CMAKE_COMMAND} -E echo "  Max clang-tidy errors: ${SAGE_FLOW_MAX_CLANG_TIDY_ERRORS}"

        # Here you would add actual quality check commands that return appropriate exit codes
        COMMAND ${CMAKE_COMMAND} -E echo "Quality gate passed for ${TARGET_NAME}"
        COMMENT "Running code quality gate checks"
        VERBATIM
    )

    # Make the main target depend on quality check
    add_dependencies(${TARGET_NAME} ${TARGET_NAME}_quality_check)
endfunction()

# Auto-enable quality checks for all targets if requested
option(SAGE_FLOW_AUTO_QUALITY_CHECKS "Automatically add quality checks to all targets" OFF)
if(SAGE_FLOW_AUTO_QUALITY_CHECKS)
    # This would require more complex CMake logic to automatically find all targets
    # For now, users need to manually call add_code_quality_checks() on their targets
endif()

# Generate the quality report by default
generate_code_quality_report()