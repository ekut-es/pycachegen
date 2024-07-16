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

# SystemC dependencies
set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)

# Find SystemC using SystemC's CMake integration
find_package(SystemCLanguage PATHS "../../../external/systemc")

set(CACHE_WRAPPER_ARG_LIST
    "1 1 priority \"16 8 1 4 fifo 6 8 1 0 1\" \"16 8 10 15\""
    "2 1 priority \"16 8 2 4 fifo 6 8 1 0 1\" \"16 8 10 15\""
    "3 1 priority \"16 8 4 2 fifo 6 8 1 0 1\" \"16 8 10 15\""
    "4 1 priority \"16 8 4 2 plru_tree 6 8 1 0 1\" \"16 8 10 15\""
    "5 1 priority \"16 8 1 2 plru_tree 6 8 1 0 1\" \"16 8 10 15\""
    "6 1 priority \"16 8 4 2 plru_tree 4 11 0 1 1\" \"16 8 10 15\""
    "7 1 priority \"16 8 2 2 plru_tree 6 10 1 1 1\" \"16 8 10 15\""
    "8 1 priority \"16 8 2 2 plru_tree 4 11 0 0 1\" \"16 8 10 15\""
    "9 1 priority \"16 8 2 2 plru_tree 4 11 0 1 1\" \"16 8 10 15\""
    "10 1 priority \"16 8 2 2 plru_tree 4 11 0 1 1\" \"16 8 10 15\""
    "11 1 priority \"16 8 1 4 plru_tree 4 11 0 1 1\" \"16 8 10 15\""
    "12 1 priority \"16 8 1 4 plru_tree 4 11 0 1 1\" \"16 8 10 15\""
    "13 1 priority \"16 8 2 2 plru_tree 4 29 0 1 4\" \"16 8 10 15\""
    "14 1 priority \"16 8 4 1 plru_tree 4 11 0 1 1\" \"16 8 10 15\""
    "15 1 priority \"16 8 4 2 plru_mru 4 11 0 1 1\" \"16 8 10 15\""
    "16 2 priority \"16 8 4 2 plru_mru 4 11 0 1 1\" \"16 8 10 15\""
    "17 1 priority \"16 8 2 1 fifo 4 11 0 1 1\" \"16 8 2 2 fifo 4 11 0 1 1\" \"16 8 10 15\""
    "18 4 fifo \"16 8 4 2 plru_mru 4 11 0 1 1\" \"16 8 10 15\""
    "19 5 round_robin \"16 8 4 2 plru_mru 4 11 0 1 1\" \"16 8 10 15\""
    "20 1 priority \"8 6 1 4 plru_tree 4 11 0 1 1\" \"64 3 1 2 plru_tree 4 11 0 1 1\" \"128 2 10 15\""
    "21 1 priority \"8 6 1 2 plru_tree 6 11 1 0 4\" \"64 3 10 15\""
    "22 1 priority \"8 16 2 4 plru_tree 4 11 0 1 1\" \"8 16 10 15\""
    "23 1 priority \"8 6 1 2 plru_tree 6 13 1 0 4\" \"16 5 10 15\""
    "24 1 priority \"16 3 10 15\""
    "25 2 priority \"16 8 10 15\""
    "26 1 priority \"16 8 1 2 fifo 0 0 0 1 1\" \"16 8 10 15\""
)
list(LENGTH CACHE_WRAPPER_ARG_LIST NUM_TESTBENCHES)

# create src directory if not already there, remove all files from it
# this is for verilog source files
file(MAKE_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/src")
file(GLOB SRC_FILES ${CMAKE_CURRENT_SOURCE_DIR}/src/*)
if(SRC_FILES)
    file(REMOVE ${SRC_FILES})
endif()

# Cache wrapper test benches
foreach(i RANGE 1 ${NUM_TESTBENCHES})
    math(EXPR current_idx "${NUM_TESTBENCHES} - ${i} + 1")
    math(EXPR current_idx_dec "${NUM_TESTBENCHES} - ${i}")
    message(STATUS "Creating cache wrapper testbench ${current_idx}")
    list(GET CACHE_WRAPPER_ARG_LIST ${current_idx_dec} current_args)
    execute_process(
        COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/generators/cache_wrapper_generator.py ${current_args}"
    )
    add_executable(Vcache_wrapper_tb_${current_idx} tb/cache_wrapper_tb_${current_idx}.cpp)
    set_property(
        TARGET Vcache_wrapper_tb_${current_idx}
        PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
    )
    verilate(Vcache_wrapper_tb_${current_idx} SYSTEMC COVERAGE TRACE
    INCLUDE_DIRS "src"
    SOURCES src/cache_wrapper_${current_idx}.v
    )
    verilator_link_systemc(Vcache_wrapper_tb_${current_idx})
endforeach()
