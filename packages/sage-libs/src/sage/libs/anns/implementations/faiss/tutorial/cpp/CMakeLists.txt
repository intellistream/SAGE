# Copyright (c) Facebook, Inc. and its affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

option (ENABLE_PAPI
        "Enable papi support, pls first compile papi manually or set REBUILD_PAPI to ON"
        OFF
)
# OPTIONAL PAPI
if (NOT ENABLE_PAPI)
    message(STATUS "I will NOT use PAPI ")
    set(AMMBENCH_PAPI 0)
else ()
    set(AMMBENCH_PAPI 1)
    message(STATUS "I will try to use PAPI for HW counters, pls make sure your arch supports it")
    option (REBUILD_PAPI
            "Rebuild the papi libs"
            OFF
    )
    if (REBUILD_PAPI)
        set (PAPISCRIPTPATH thirdparty)
        execute_process(COMMAND bash ${PAPISCRIPTPATH}/makeClean.sh WORKING_DIRECTORY ${PAPISCRIPTPATH})
        execute_process(COMMAND bash ${PAPISCRIPTPATH}/installPAPI.sh WORKING_DIRECTORY ${PAPISCRIPTPATH})
        message(STATUS "I have rebuilt PAPI" )
    endif()
    find_library (libPAPI libpapi.a thirdparty/papi_build/lib)
    message(STATUS "papiLibs= " ${libPAPI} )
    set(LIBRARIES ${LIBRARIES} ${libPAPI})

endif ()
configure_file (
        "include/papi_config.h.in"
        "include/papi_config.h"
)
