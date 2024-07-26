# VExecuteStage_tb
add_executable(VExecuteStage_tb {{name}}_ExecuteStage_tb.cc)

set_property(
	TARGET VExecuteStage_tb
	PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)

verilate(VExecuteStage_tb SYSTEMC COVERAGE TRACE
	INCLUDE_DIRECTORIES "."
	SOURCES {{name}}_ExecuteStage.v
)

verilator_link_systemc(VExecuteStage_tb)