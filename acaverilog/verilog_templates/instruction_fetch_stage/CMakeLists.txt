# VInstructionFetchStage_tb
add_executable(VInstructionFetchStage_tb {{ instruction_fetch_stage_name }}_InstructionFetchStage_tb.cc)

set_property(
	TARGET VInstructionFetchStage_tb
	PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)

verilate(VInstructionFetchStage_tb
	SOURCES 
		{{ instruction_memory_fetch_stage_wrapper_name }}_InstructionMemoryFetchStageWrapper.v
		{{ instruction_memory_name }}_Memory.v 
		{{ instruction_memory_name }}_AddressTranslator.v 
		{{ instruction_fetch_stage_name }}_InstructionFetchStage.v
		{{ instruction_fetch_stage_name }}_PopCount.v
		{%- for j in range(issue_buffer_size) %}
		{{ instruction_fetch_stage_name }}_{{ j }}_ForwardLookupTable.v
		{%- endfor %}
		{{ scoreboard_name }}_Scoreboard.v
	TRACE SYSTEMC COVERAGE
	INCLUDE_DIRECTORIES "."
)

verilator_link_systemc(VInstructionFetchStage_tb)
