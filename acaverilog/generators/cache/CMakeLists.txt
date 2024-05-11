cmake_minimum_required(VERSION 3.16)
project(Cache CXX)

cmake_policy(SET CMP0144 NEW)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

find_package(verilator PATHS "../../../external/verilator")
if(NOT verilator_FOUND)
    message(
        FATAL_ERROR
            "Verilator was not found."
    )
endif()

execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/../cache_generator.py"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/../functional_memory_generator.py"
)

# SystemC dependencies
set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)

# Find SystemC using SystemC's CMake integration
find_package(SystemCLanguage PATHS "../../../external/systemc")

add_executable(Vcache_tb cache_tb.cpp)
add_executable(Vfunctional_memory_tb functional_memory_tb.cpp)

set_property(
    TARGET Vcache_tb
    PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)
set_property(
    TARGET Vfunctional_memory_tb
    PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)

verilate(Vcache_tb SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/cache.v
)
verilate(Vfunctional_memory_tb SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/functional_memory.v
)

verilator_link_systemc(Vcache_tb)
verilator_link_systemc(Vfunctional_memory_tb)

