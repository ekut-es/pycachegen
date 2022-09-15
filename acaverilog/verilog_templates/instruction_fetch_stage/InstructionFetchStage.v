module {{ name }}_InstructionFetchStage
#(
	parameter DATA_WIDTH = {{ data_width }}
	parameter MAX_DATA_WORD_DISTANCE = {{ max_data_word_distance }}, 
	parameter PORT_WIDTH = {{ port_width }}
	parameter PORT_WIDTH_BITS = {{ data_width*port_width }}
	parameter ADDRESS_WIDTH = {{ address_width }}
)
(
	input clk_i,
	input reset_n_i,

	// connection to instruction memory
	output read_write_select_o,
	output unsigned[ADDRESS_WIDTH-1:0] address_o,
	output[$clog2(MAX_DATA_WORD_DISTANCE)-1:0] data_word_distance_o,
	output address_valid_o,
	output[PORT_WIDTH_BITS-1:0] write_data_o,
	output unsigned[PORT_WIDTH-1:0] write_data_valid_o,
	input write_done_i,
	input[PORT_WIDTH_BITS-1:0] read_data_i,
	input unsigned[PORT_WIDTH-1:0] read_data_valid_i,
	input port_ready_i
);

	reg[ADDRESS_WIDTH-1:0] address;
	reg address_valid;

	// instruction fetch stage only reads from instruction memory
	assign read_write_select_o = 1'b0;
	assign address_o = address;
	// data word distance is always 1
	assign data_word_distance_o = 1;
	assign address_valid_o = address_valid;
	// instruction fetch stage only reads from instruction memory
	assign write_data_o = {PORT_WIDTH_BITS{1'b0}};
	// instruction fetch stage only reads from instruction memory
	assign write_data_valid_o = {PORT_WIDTH{1'b0}}

	
	always @(posedge clk_i, negedge reset_n_i) begin
		if(reset_n_i == 1'b0) begin
			address <= {ADDRESS_WIDTH{1'b0}};
			address_valid <= 1'b0;
		end
	end

endmodule