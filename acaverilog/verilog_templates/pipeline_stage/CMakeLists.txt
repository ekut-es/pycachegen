# VPipelineStage_tb
add_executable(VPipelineStage_tb {{name}}_PipelineStage_tb.cc)

set_property(
	TARGET VPipelineStage_tb
	PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)

verilate(VPipelineStage_tb
	INCLUDE_DIRECTORIES "."
	VERILATOR_ARGS --trace --sc
	SOURCES {{name}}_PipelineStage.v
)

verilator_link_systemc(VPipelineStage_tb)