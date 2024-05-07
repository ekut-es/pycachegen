# VInstructionMemoryAccessUnit_tb
add_executable(VInstructionMemoryAccessUnit_tb {{name}}_InstructionMemoryAccessUnit_tb.cc)

set_property(
	TARGET VInstructionMemoryAccessUnit_tb
	PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)

verilate(VInstructionMemoryAccessUnit_tb SYSTEMC COVERAGE TRACE
	INCLUDE_DIRECTORIES "."
	SOURCES {{name}}_InstructionMemoryAccessUnit.v
)

verilator_link_systemc(VInstructionMemoryAccessUnit_tb)