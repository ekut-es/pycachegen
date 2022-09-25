module {{ name }}_InstructionFetchStage
#(
	parameter DATA_WIDTH = {{ data_width }},
	parameter INSTRUCTION_SIZE = DATA_WIDTH,
	parameter MAX_DATA_WORD_DISTANCE = {{ max_data_word_distance }}, 
	parameter PORT_WIDTH = {{ port_width }},
	parameter PORT_WIDTH_BITS = {{ data_width*port_width }},
	parameter ADDRESS_WIDTH = {{ address_width }},
	parameter ISSUE_BUFFER_SIZE = {{ issue_buffer_size }}
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
	input port_ready_i,
	input instruction_memory_ready_i,

	// forward ports
	{%- for i in range(forward_ports) %}
	input next_stage_ready_{{ i }}_i,
	output[DATA_WIDTH-1:0] instruction_{{ i }}_o,
	output instruction_valid_{{ i }}_o{{ "," if not loop.last }}
	{% endfor %}
);

	reg[ADDRESS_WIDTH-1:0] program_counter;
	reg address_valid;
	reg[PORT_WIDTH_BITS-1:0] read_data;
	reg initialize_read;
	reg read_in_progress;
	reg[DATA_WIDTH-1:0] issue_buffer [ISSUE_BUFFER_SIZE-1:0];
	reg[ISSUE_BUFFER_SIZE-1:0] issue_buffer_valid;
	wire[ISSUE_BUFFER_SIZE-1:0] issue_buffer_valid_pop_count;
	wire[ISSUE_BUFFER_SIZE-1:0] issue_buffer_available_slots;
	integer issue_buffer_first_free_slot;

	// instruction fetch stage only reads from instruction memory
	assign read_write_select_o = 1'b0;
	assign address_o = program_counter;
	// data word distance is always 1
	assign data_word_distance_o = 1;
	assign address_valid_o = address_valid;
	// instruction fetch stage only reads from instruction memory
	assign write_data_o = {PORT_WIDTH_BITS{1'b0}};
	// instruction fetch stage only reads from instruction memory
	assign write_data_valid_o = {PORT_WIDTH{1'b0}};

	// returns how much space there is in the issue buffer
	{{ name }}_PopCount
	#(
		.WORD_WIDTH(ISSUE_BUFFER_SIZE)
	) pop_counter (
		.word_i(issue_buffer_valid),
		.pop_count_o(issue_buffer_valid_pop_count)
	);

	assign issue_buffer_available_slots = ISSUE_BUFFER_SIZE - issue_buffer_valid_pop_count;

	integer i;

	always @(posedge clk_i, negedge reset_n_i) begin
		if(reset_n_i == 1'b0) begin
			program_counter <= {{ initial_address }};
			address_valid <= 1'b0;
			initialize_read <= 1'b1;
			read_in_progress <= 1'b0;

			// reset issue buffer
			for(i = 0; i < ISSUE_BUFFER_SIZE; i = i + 1) begin
				issue_buffer[i] = {DATA_WIDTH{1'b0}};
			end

			issue_buffer_valid <= {ISSUE_BUFFER_SIZE{1'b0}};
			issue_buffer_first_free_slot <= 0;
		end
		else begin
			// initialize a read from memory when instruction memory is ready
			if(instruction_memory_ready_i == 1'b1 && initialize_read == 1'b1) begin
				address_valid <= 1'b1;
				read_in_progress <= 1'b1;
				initialize_read <= 1'b0;
			end

			// a read is in progress and the instruction memory has valid data
			if(read_in_progress == 1'b1 && initialize_read == 1'b0 && read_data_valid_i > 0) begin
				$display("t=%0t: %m read from address=%d with data=%h.", $time, program_counter, read_data_i);
				read_data <= read_data_i;

				for(i = issue_buffer_first_free_slot; i < issue_buffer_first_free_slot+PORT_WIDTH; i = i + 1) begin
					issue_buffer[i] = read_data_i[i*DATA_WIDTH +: DATA_WIDTH];
					issue_buffer_valid[i] <= 1'b1;
				end

				issue_buffer_first_free_slot <= issue_buffer_first_free_slot + PORT_WIDTH;

				initialize_read <= 1'b1;

				address_valid <= 1'b0;
				program_counter <= program_counter + PORT_WIDTH;
			end
		end
	end

endmodule