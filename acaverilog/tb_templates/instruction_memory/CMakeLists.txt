# VInstructionMemory_tb
add_executable(VInstructionMemory_tb {{name}}_InstructionMemory_tb.cc)

set_property(
	TARGET VInstructionMemory_tb
	PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)

verilate(VInstructionMemory_tb 
	SOURCES {{name}}_Memory.v {{name}}_AddressTranslator.v
	TRACE SYSTEMC COVERAGE
	INCLUDE_DIRECTORIES "."
)

verilator_link_systemc(VInstructionMemory_tb)