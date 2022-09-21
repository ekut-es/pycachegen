cmake_minimum_required(VERSION 3.16)
project(test CXX)

find_package(verilator HINTS ${VERILATOR_ROOT} $ENV{VERILATOR_ROOT})
if (NOT verilator_FOUND)
	message(FATAL_ERROR "Verilator was not found. Either install it, or set the VERILATOR_ROOT environment variable")
endif()

# SystemC dependencies
set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)

# Find SystemC using SystemC's CMake integration
find_package(SystemCLanguage PATHS ${SYSTEMC_HOME})

add_subdirectory(${VERILOG_OUT_DIR_PATH} sim)
