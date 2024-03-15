# VFunctionalUnit_tb
add_executable(VFunctionalUnit_tb {{name}}_FunctionalUnit_tb.cc)

set_property(
	TARGET VFunctionalUnit_tb
	PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)

verilate(VFunctionalUnit_tb SYSTEMC COVERAGE TRACE
	INCLUDE_DIRECTORIES "."
	SOURCES {{name}}_FunctionalUnit.v
)

verilator_link_systemc(VFunctionalUnit_tb)