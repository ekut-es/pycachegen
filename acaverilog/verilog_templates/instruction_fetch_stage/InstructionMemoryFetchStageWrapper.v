module {{ name }}_InstructionMemoryFetchStageWrapper
#(
	parameter DATA_WIDTH = {{ data_width }},
	parameter INSTRUCTION_SIZE = DATA_WIDTH,
	parameter MAX_DATA_WORD_DISTANCE = {{ max_data_word_distance }}, 
	parameter PORT_WIDTH = {{ port_width }},
	parameter PORT_WIDTH_BITS = {{ data_width*port_width }},
	parameter ADDRESS_WIDTH = {{ address_width }}
)
(
	input clk_i,
	input reset_n_i,

	// instruction fetch stage forward ports
	{%- for i in range(forward_ports) %}
	input next_stage_ready_{{ i }}_i,
	output[DATA_WIDTH-1:0] instruction_{{ i }}_o,
	output instruction_valid_{{ i }}_o{{ "," if not loop.last }}
	{% endfor %}
);

	wire read_write_select;
	wire [ADDRESS_WIDTH-1:0] address;
	wire [$clog2(MAX_DATA_WORD_DISTANCE)-1:0] data_word_distance;
	wire address_valid;
	wire [PORT_WIDTH_BITS-1:0] write_data;
	wire [PORT_WIDTH-1:0] write_data_valid;
	wire write_done;
	wire [PORT_WIDTH_BITS-1:0] read_data;
	wire [PORT_WIDTH-1:0] read_data_valid;
	wire port_ready;
	wire instruction_memory_ready;

	wire scoreboard_full;

	{{ instruction_memory_name }}_Memory imem(
		.clk_i(clk_i),
		.reset_n_i(reset_n_i),
		.read_write_select_0_i(read_write_select),
		.address_0_i(address),
		.data_word_distance_0_i(data_word_distance),
		.address_valid_0_i(address_valid),
		.write_data_0_i(write_data),
		.write_data_valid_0_i(write_data_valid),
		.write_done_0_o(write_done),
		.read_data_0_o(read_data),
		.read_data_valid_0_o(read_data_valid),
		.port_ready_0_o(port_ready),
		.ready_o(instruction_memory_ready)
	);

	{{ instruction_fetch_stage_name }}_InstructionFetchStage ifs(
		.clk_i(clk_i),
		.reset_n_i(reset_n_i),
		.read_write_select_o(read_write_select),
		.address_o(address),
		.data_word_distance_o(data_word_distance),
		.address_valid_o(address_valid),
		.write_data_o(write_data),
		.write_data_valid_o(write_data_valid),
		.write_done_i(write_done),
		.read_data_i(read_data),
		.read_data_valid_i(read_data_valid),
		.port_ready_i(port_ready),
		.instruction_memory_ready_i(instruction_memory_ready),

		.scoreboard_full_i(scoreboard_full),

		{%- for i in range(forward_ports) %}
		.next_stage_ready_{{ i }}_i(next_stage_ready_{{ i }}_i),
		.instruction_{{ i }}_o(instruction_{{ i }}_o),
		.instruction_valid_{{ i }}_o(instruction_valid_{{ i }}_o){{ "," if not loop.last }}
		{% endfor %}
	);

	{{ scoreboard_name }}_Scoreboard s(
		.clk_i(clk_i),
		.reset_n_i(reset_n_i),
		.full_o(scoreboard_full)
	);

endmodule