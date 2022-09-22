module {{ name }}_InstructionMemoryFetchStageWrapper
#(
	parameter DATA_WIDTH = {{ data_width }},
	parameter MAX_DATA_WORD_DISTANCE = {{ max_data_word_distance }}, 
	parameter PORT_WIDTH = {{ port_width }},
	parameter PORT_WIDTH_BITS = {{ data_width*port_width }},
	parameter ADDRESS_WIDTH = {{ address_width }}
)
(
	input clk_i,
	input reset_n_i,

	output read_write_select_o,
	output [ADDRESS_WIDTH-1:0] address_o,
	output [$clog2(MAX_DATA_WORD_DISTANCE)-1:0] data_word_distance_o,
	output address_valid_o,
	output [PORT_WIDTH_BITS-1:0] write_data_o,
	output [PORT_WIDTH-1:0] write_data_valid_o,
	output write_done_o,
	output [PORT_WIDTH_BITS-1:0] read_data_o,
	output [PORT_WIDTH-1:0] read_data_valid_o,
	output port_ready_o,
	output instruction_memory_ready_o
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

	/*
	assign read_write_select_o = read_write_select;
	assign address_o = address;
	assign data_word_distance_o = data_word_distance;
	assign address_valid_o = address_valid;
	assign write_data_o = write_data;
	assign write_data_valid_o= write_data_valid;
	assign write_done_o = write_done;
	assign read_data_o = read_data;
	assign read_data_valid_o = read_data_valid;
	assign port_ready_o = port_ready;
	assign instruction_memory_ready_o = instruction_memory_ready;
	*/

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
		.instruction_memory_ready_i(instruction_memory_ready)
	);

endmodule