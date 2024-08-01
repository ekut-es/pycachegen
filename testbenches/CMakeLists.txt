cmake_minimum_required(VERSION 3.16)
project(Cache CXX)

if(NOT CMAKE_VERSION VERSION_LESS "3.27.0")
    cmake_policy(SET CMP0144 NEW)
endif()

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

set(CACHE_WRAPPER_ARG_LIST
    "1 priority 8 0 9 \"16 1 4 fifo 6 8 1 0 1\" \"16 10 15 0 512\"" # 1
    "1 priority 8 0 9 \"16 2 4 fifo 6 8 1 0 1\" \"16 10 15 0 512\"" # 2
    "1 priority 8 0 9 \"16 4 2 fifo 6 8 1 0 1\" \"16 10 15 0 512\"" # 3
    "1 priority 8 0 9 \"16 4 2 plru_tree 6 8 1 0 1\" \"16 10 15 0 512\"" # 4
    "1 priority 8 0 9 \"16 1 2 plru_tree 6 8 1 0 1\" \"16 10 15 0 512\"" # 5
    "1 priority 8 0 9 \"16 4 2 plru_tree 4 11 0 1 1\" \"16 10 15 0 512\"" # 6
    "1 priority 8 0 9 \"16 2 2 plru_tree 6 10 1 1 1\" \"16 10 15 0 512\"" # 7
    "1 priority 8 0 9 \"16 2 2 plru_tree 4 11 0 0 1\" \"16 10 15 0 512\"" # 8
    "1 priority 8 1 9 \"16 2 2 plru_tree 4 11 0 1 1\" \"16 10 15 0 512\"" # 9
    "1 priority 8 0 9 \"16 2 2 plru_tree 4 11 0 1 1\" \"16 10 15 0 512\"" # 10
    "1 priority 8 0 9 \"16 1 4 plru_tree 4 11 0 1 1\" \"16 10 15 0 512\"" # 11
    "1 priority 8 0 9 \"16 1 4 plru_tree 4 11 0 1 1\" \"16 10 15 0 512\"" # 12
    "1 priority 8 0 9 \"16 2 2 plru_tree 4 29 0 1 4\" \"16 10 15 0 512\"" # 13
    "1 priority 8 0 9 \"16 4 1 plru_tree 4 11 0 1 1\" \"16 10 15 0 512\"" # 14
    "1 priority 8 0 9 \"16 4 2 plru_mru 4 11 0 1 1\" \"16 10 15 0 512\"" # 15
    "2 priority 8 0 9 \"16 4 2 plru_mru 4 11 0 1 1\" \"16 10 15 0 512\"" # 16
    "1 priority 8 0 9 \"16 2 1 fifo 4 11 0 1 1\" \"16 2 2 fifo 4 11 0 1 1\" \"16 10 15 0 512\"" # 17
    "4 fifo 8 0 9 \"16 4 2 plru_mru 4 11 0 1 1\" \"16 10 15 0 512\"" # 18
    "5 round_robin 8 0 9 \"16 4 2 plru_mru 4 11 0 1 1\" \"16 10 15 0 512\"" # 19
    "1 priority 8 0 6 \"8 1 4 plru_tree 4 11 0 1 1\" \"64 1 2 plru_tree 4 11 0 1 1\" \"128 10 15 0 64\"" # 20
    "1 priority 8 0 6 \"8 1 2 plru_tree 6 11 1 0 4\" \"64 10 15 0 64\"" # 21
    "1 priority 8 0 16 \"8 2 4 plru_tree 4 11 0 1 1\" \"8 10 15 0 0x10000\"" # 22
    "1 priority 8 0 6 \"8 1 2 plru_tree 6 13 1 0 4\" \"16 10 15 0 64\"" # 23
    "1 priority 8 0 4 \"16 10 15 0 16\"" # 24
    "2 priority 8 0 9 \"16 10 15 0 512\"" # 25
    "1 priority 8 0 9 \"16 1 2 fifo 0 0 0 1 1\" \"16 10 15 0 512\"" # 26
    "1 priority 13 0 4 \"13 2 2 plru_tree 0 0 0 1 2\" \"26 10 15 0 16\"" # 27
    "1 priority 8 0 9 \"16 10 15 84 98\"" # 28
    "1 priority 8 0 3 \"8 1 2 plru_tree 0 0 0 1 1\" \"8 1 2 plru_tree 0 0 1 0 1\" \"8 1 2 plru_tree 0 0 0 1 1\" \"8 3 5 0 8\"" # 29
)
list(LENGTH CACHE_WRAPPER_ARG_LIST NUM_TESTBENCHES)

# Cache wrapper test benches
foreach(i RANGE 1 ${NUM_TESTBENCHES})
    # start with the last testbench to detect errors in new testbenches sooner
    math(EXPR current_idx "${NUM_TESTBENCHES} - ${i} + 1")
    math(EXPR current_idx_dec "${NUM_TESTBENCHES} - ${i}")
    message(STATUS "Creating cache wrapper testbench ${current_idx}")
    list(GET CACHE_WRAPPER_ARG_LIST ${current_idx_dec} current_args)
    execute_process(
        COMMAND bash -c "python ${CMAKE_CURRENT_SOURCE_DIR}/tb_cache_wrapper_generator.py cache_wrapper_${current_idx}.v ${current_args}"
        RESULT_VARIABLE return_code
    )
    if(return_code AND NOT return_code EQUAL 0)
        message(FATAL_ERROR "Cache wrapper generation FAILED")
    endif()
    add_executable(Vcache_wrapper_tb_${current_idx} tb/cache_wrapper_tb_${current_idx}.cpp)
    set_property(
        TARGET Vcache_wrapper_tb_${current_idx}
        PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
    )
    verilate(Vcache_wrapper_tb_${current_idx} SYSTEMC COVERAGE TRACE
    SOURCES ${CMAKE_CURRENT_BINARY_DIR}/cache_wrapper_${current_idx}.v
    )
    verilator_link_systemc(Vcache_wrapper_tb_${current_idx})
endforeach()
