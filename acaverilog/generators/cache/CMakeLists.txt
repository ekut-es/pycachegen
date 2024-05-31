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
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/generators/functional_memory_generator.py"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/generators/cache_wrapper_generator.py 1 16 8 1 4 fifo 8 10 1 0 1"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/generators/cache_wrapper_generator.py 2 16 8 2 4 fifo 8 10 1 0 1"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/generators/cache_wrapper_generator.py 3 16 8 4 2 fifo 8 10 1 0 1"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/generators/cache_wrapper_generator.py 4 16 8 4 2 plru_tree 8 10 1 0 1"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/generators/cache_wrapper_generator.py 5 16 8 1 2 plru_tree 6 6 1 0 1"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/generators/cache_wrapper_generator.py 6 16 8 4 2 plru_tree 8 10 0 1 1"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/generators/cache_wrapper_generator.py 7 16 8 2 2 plru_tree 8 10 1 1 1"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/generators/cache_wrapper_generator.py 8 16 8 2 2 plru_tree 8 10 0 0 1"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/generators/cache_wrapper_generator.py 9 16 8 2 2 plru_tree 8 10 0 1 1"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/generators/cache_wrapper_generator.py 10 16 8 2 2 plru_tree 8 10 0 1 1"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/generators/cache_wrapper_generator.py 11 16 8 1 4 plru_tree 8 10 0 1 1"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/generators/cache_wrapper_generator.py 12 16 8 1 4 plru_tree 8 10 0 1 1"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/generators/cache_wrapper_generator.py 13 16 8 2 2 plru_tree 8 10 0 1 4"
)
execute_process(
    COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/generators/cache_wrapper_generator.py 14 16 8 4 1 plru_tree 8 10 0 1 1"
)

# SystemC dependencies
set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)

# Find SystemC using SystemC's CMake integration
find_package(SystemCLanguage PATHS "../../../external/systemc")

add_executable(Vfunctional_memory_tb tb/functional_memory_tb.cpp)
add_executable(Vcache_wrapper_tb_1 tb/cache_wrapper_tb_1.cpp)
add_executable(Vcache_wrapper_tb_2 tb/cache_wrapper_tb_2.cpp)
add_executable(Vcache_wrapper_tb_3 tb/cache_wrapper_tb_3.cpp)
add_executable(Vcache_wrapper_tb_4 tb/cache_wrapper_tb_4.cpp)
add_executable(Vcache_wrapper_tb_5 tb/cache_wrapper_tb_5.cpp)
add_executable(Vcache_wrapper_tb_6 tb/cache_wrapper_tb_6.cpp)
add_executable(Vcache_wrapper_tb_7 tb/cache_wrapper_tb_7.cpp)
add_executable(Vcache_wrapper_tb_8 tb/cache_wrapper_tb_8.cpp)
add_executable(Vcache_wrapper_tb_9 tb/cache_wrapper_tb_9.cpp)
add_executable(Vcache_wrapper_tb_10 tb/cache_wrapper_tb_10.cpp)
add_executable(Vcache_wrapper_tb_11 tb/cache_wrapper_tb_11.cpp)
add_executable(Vcache_wrapper_tb_12 tb/cache_wrapper_tb_12.cpp)
add_executable(Vcache_wrapper_tb_13 tb/cache_wrapper_tb_13.cpp)
add_executable(Vcache_wrapper_tb_14 tb/cache_wrapper_tb_14.cpp)

set_property(
    TARGET Vfunctional_memory_tb Vcache_wrapper_tb_1 Vcache_wrapper_tb_2 Vcache_wrapper_tb_3 Vcache_wrapper_tb_4 Vcache_wrapper_tb_5 Vcache_wrapper_tb_6 Vcache_wrapper_tb_7 Vcache_wrapper_tb_8 Vcache_wrapper_tb_9 Vcache_wrapper_tb_10 Vcache_wrapper_tb_11 Vcache_wrapper_tb_12 Vcache_wrapper_tb_13 Vcache_wrapper_tb_14
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
verilate(Vcache_wrapper_tb_7 SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/cache_wrapper_7.v
)
verilate(Vcache_wrapper_tb_8 SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/cache_wrapper_8.v
)
verilate(Vcache_wrapper_tb_9 SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/cache_wrapper_9.v
)
verilate(Vcache_wrapper_tb_10 SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/cache_wrapper_10.v
)
verilate(Vcache_wrapper_tb_11 SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/cache_wrapper_11.v
)
verilate(Vcache_wrapper_tb_12 SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/cache_wrapper_12.v
)
verilate(Vcache_wrapper_tb_13 SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/cache_wrapper_13.v
)
verilate(Vcache_wrapper_tb_13 SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/cache_wrapper_13.v
)
verilate(Vcache_wrapper_tb_14 SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/cache_wrapper_14.v
)

verilator_link_systemc(Vfunctional_memory_tb)
verilator_link_systemc(Vcache_wrapper_tb_1)
verilator_link_systemc(Vcache_wrapper_tb_2)
verilator_link_systemc(Vcache_wrapper_tb_3)
verilator_link_systemc(Vcache_wrapper_tb_4)
verilator_link_systemc(Vcache_wrapper_tb_5)
verilator_link_systemc(Vcache_wrapper_tb_6)
verilator_link_systemc(Vcache_wrapper_tb_7)
verilator_link_systemc(Vcache_wrapper_tb_8)
verilator_link_systemc(Vcache_wrapper_tb_9)
verilator_link_systemc(Vcache_wrapper_tb_10)
verilator_link_systemc(Vcache_wrapper_tb_11)
verilator_link_systemc(Vcache_wrapper_tb_12)
verilator_link_systemc(Vcache_wrapper_tb_13)
verilator_link_systemc(Vcache_wrapper_tb_14)
