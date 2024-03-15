# VRegisterFile_tb
add_executable(VRegisterFile_tb {{name}}_RegisterFile_tb.cc)

set_property(
	TARGET VRegisterFile_tb
	PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)

verilate(VRegisterFile_tb SYSTEMC COVERAGE TRACE
	INCLUDE_DIRECTORIES "."
	SOURCES {{name}}_RegisterFile.v
)

verilator_link_systemc(VRegisterFile_tb)