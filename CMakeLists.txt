cmake_minimum_required(VERSION 3.8)
project(register_file_tb CXX)

find_package(verilator HINTS $ENV{VERILATOR_ROOT} ${VERILATOR_ROOT})
if (NOT verilator_FOUND)
	message(FATAL_ERROR "Verilator was not found. Either install it, or set the VERILATOR_ROOT environment variable")
endif()

# SystemC dependencies
set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)

# Find SystemC using SystemC's CMake integration
find_package(SystemCLanguage QUIET)


# VRegisterFile_tv
add_executable(VRegisterFile_tb ./register_file/RegisterFile_tb.cpp)

set_property(
	TARGET VRegisterFile_tb
	PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)

verilate(VRegisterFile_tb
	INCLUDE_DIRECTORIES "./register_file"
	VERILATOR_ARGS --trace --sc
	SOURCES ./register_file/RegisterFile.v
)

verilator_link_systemc(VRegisterFile_tb)

# MemoryAccessUnit_tb
add_executable(VMemoryAccessUnit_tb ./memory_access_unit/MemoryAccessUnit_tb.cpp)

set_property(
	TARGET VMemoryAccessUnit_tb
	PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)

verilate(VMemoryAccessUnit_tb
	INCLUDE_DIRECTORIES "./memory_access_unit"
	VERILATOR_ARGS --trace --sc
	SOURCES ./memory_access_unit/MemoryAccessUnit.v
)

verilator_link_systemc(VMemoryAccessUnit_tb)
