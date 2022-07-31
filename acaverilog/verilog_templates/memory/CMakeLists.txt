# VMemory_tb
add_executable(VMemory_tb {{name}}_Memory_tb.cc)

set_property(
	TARGET VMemory_tb
	PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)

verilate(VMemory_tb SYSTEMC COVERAGE TRACE
	INCLUDE_DIRECTORIES "."
	SOURCES {{name}}_Memory.v {{name}}_AddressTranslator.v
)

verilator_link_systemc(VMemory_tb)