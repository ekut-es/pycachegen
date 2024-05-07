# VMemoryAccessUnit_tb
add_executable(VMemoryAccessUnit_tb {{name}}_MemoryAccessUnit_tb.cc)

set_property(
	TARGET VMemoryAccessUnit_tb
	PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)

verilate(VMemoryAccessUnit_tb 
	SOURCES {{name}}_MemoryAccessUnit.v
	TRACE SYSTEMC COVERAGE
	INCLUDE_DIRECTORIES "."
)

verilator_link_systemc(VMemoryAccessUnit_tb)