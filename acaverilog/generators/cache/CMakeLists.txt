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

file(GLOB SRC_FILES ${CMAKE_CURRENT_SOURCE_DIR}/src/*)
file(REMOVE ${SRC_FILES})
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/../functional_memory_generator.py"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/../cache_wrapper_generator.py 1 16 8 1 4 fifo 8 10 0"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/../cache_wrapper_generator.py 2 16 8 2 4 fifo 8 10 0"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/../cache_wrapper_generator.py 3 16 8 4 2 fifo 8 10 0"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/../cache_wrapper_generator.py 4 16 8 4 2 plru_tree 8 10 0"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/../cache_wrapper_generator.py 5 16 8 1 2 plru_tree 6 6 0"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/../cache_wrapper_generator.py 6 16 8 4 2 plru_tree 8 10 1"
)

# SystemC dependencies
set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)

# Find SystemC using SystemC's CMake integration
find_package(SystemCLanguage PATHS "../../../external/systemc")

add_executable(Vfunctional_memory_tb functional_memory_tb.cpp)
add_executable(Vcache_wrapper_tb_1 cache_wrapper_tb_1.cpp)
add_executable(Vcache_wrapper_tb_2 cache_wrapper_tb_2.cpp)
add_executable(Vcache_wrapper_tb_3 cache_wrapper_tb_3.cpp)
add_executable(Vcache_wrapper_tb_4 cache_wrapper_tb_4.cpp)
add_executable(Vcache_wrapper_tb_5 cache_wrapper_tb_5.cpp)
add_executable(Vcache_wrapper_tb_6 cache_wrapper_tb_6.cpp)

set_property(
    TARGET Vfunctional_memory_tb Vcache_wrapper_tb_1 Vcache_wrapper_tb_2 Vcache_wrapper_tb_3 Vcache_wrapper_tb_4 Vcache_wrapper_tb_5 Vcache_wrapper_tb_6
    PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)

verilate(Vfunctional_memory_tb SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/functional_memory.v
)
verilate(Vcache_wrapper_tb_1 SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/cache_wrapper_1.v
)
verilate(Vcache_wrapper_tb_2 SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/cache_wrapper_2.v
)
verilate(Vcache_wrapper_tb_3 SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/cache_wrapper_3.v
)
verilate(Vcache_wrapper_tb_4 SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/cache_wrapper_4.v
)
verilate(Vcache_wrapper_tb_5 SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/cache_wrapper_5.v
)
verilate(Vcache_wrapper_tb_6 SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/cache_wrapper_6.v
)

verilator_link_systemc(Vfunctional_memory_tb)
verilator_link_systemc(Vcache_wrapper_tb_1)
verilator_link_systemc(Vcache_wrapper_tb_2)
verilator_link_systemc(Vcache_wrapper_tb_3)
verilator_link_systemc(Vcache_wrapper_tb_4)
verilator_link_systemc(Vcache_wrapper_tb_5)
verilator_link_systemc(Vcache_wrapper_tb_6)
