cmake_minimum_required(VERSION 3.16)
project(Cache CXX)

cmake_policy(SET CMP0144 NEW)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

find_package(verilator HINTS ${VERILATOR_ROOT} $ENV{VERILATOR_ROOT})
if(NOT verilator_FOUND)
    message(
        FATAL_ERROR
            "Verilator was not found. Either install it, or set the VERILATOR_ROOT environment variable"
    )
endif()

# SystemC dependencies
set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)

# Find SystemC using SystemC's CMake integration
find_package(SystemCLanguage PATHS ${SYSTEMC_HOME})

# Call python script to generate verilog code, then verilate it
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/custom_cache_wrapper_generator.py custom_cache_wrapper.v"
    RESULT_VARIABLE return_code
)
if(return_code AND NOT return_code EQUAL 0)
    message(FATAL_ERROR "Cache wrapper generation FAILED")
endif()
add_executable(Vtracing_tb tracing_tb.cpp)
set_property(
    TARGET Vtracing_tb
    PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)
verilate(Vtracing_tb SYSTEMC COVERAGE TRACE
SOURCES ${CMAKE_CURRENT_BINARY_DIR}/custom_cache_wrapper.v
)
verilator_link_systemc(Vtracing_tb)
