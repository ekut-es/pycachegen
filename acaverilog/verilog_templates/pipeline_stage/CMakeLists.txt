# VPipelineStage_tb
add_executable(VPipelineStage_tb {{name}}_PipelineStage_tb.cc)

set_property(
	TARGET VPipelineStage_tb
	PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)

verilate(VPipelineStage_tb SYSTEMC COVERAGE TRACE
	INCLUDE_DIRECTORIES "."
	SOURCES {{name}}_PipelineStage.v {{name}}_ForwardLookupTable.v
)

verilator_link_systemc(VPipelineStage_tb)