cmake_minimum_required(VERSION 3.16)
project(IObCache CXX)

cmake_policy(SET CMP0144 NEW)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

find_package(verilator PATHS "../external/verilator")
if(NOT verilator_FOUND)
    message(
        FATAL_ERROR
            "Verilator was not found."
    )
endif()

# SystemC dependencies
set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)

# Find SystemC using SystemC's CMake integration
find_package(SystemCLanguage PATHS "../external/systemc")

add_executable(Vcache_tb cache_tb.cpp)

set_property(
    TARGET Vcache_tb
    PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)

verilate(Vcache_tb SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/iob_cache_sim_wrapper.v
    VERILATOR_ARGS "-Wno-lint"
)

verilator_link_systemc(Vcache_tb)
