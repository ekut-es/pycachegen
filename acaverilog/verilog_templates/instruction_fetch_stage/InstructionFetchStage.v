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
	reg read_done;
	reg[DATA_WIDTH-1:0] issue_buffer [ISSUE_BUFFER_SIZE-1:0];
	reg[ISSUE_BUFFER_SIZE-1:0] issue_buffer_valid;
	wire[ISSUE_BUFFER_SIZE-1:0] issue_buffer_valid_pop_count;
	// signed is needed here to protect against an underflow when the number
	// of available buffer slots is calculated
	wire signed[ISSUE_BUFFER_SIZE-1:0] issue_buffer_available_slots;
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

	// wire that merges all next_stage_ready_is to make it possible to iterate over them
	wire next_stages_ready [{{ forward_ports }}-1:0];
	{%- for i in range(forward_ports) %}
	assign next_stages_ready[{{ i }}] = next_stage_ready_{{ i }}_i;
	{%- endfor %}

	// wire that merges all target_ids from the issue_buffer to make 
	// it possible to iterate over them
	wire [{{ target_id_length }}-1:0] issue_buffer_target_ids [{{ issue_buffer_size }}-1:0];
	{%- for j in range(issue_buffer_size) %}
	assign issue_buffer_target_ids[{{ j }}] = issue_buffer[{{ j }}][{{ target_id_start_bit }}+{{ target_id_length }}-1:{{ target_id_start_bit }}];
	{%- endfor %}

	// registers that track if an issue buffer slot was assigned
	reg issue_buffer_slot_assigned [{{ issue_buffer_size }}-1:0];
	reg forward_port_in_use [{{ forward_ports }}-1:0];
	reg [$clog2({{ issue_buffer_size }})-1:0] issue_buffer_slot_assigned_to_forward_port [{{ forward_ports }}-1:0];

	// registers that track which issue buffer slot has been freed after a forward
	reg issue_buffer_slot_freed [{{ issue_buffer_size }}-1:0];

	// registers that track how many slots an instruction has to be moved forward
	// after instruction in a slot before it was removed
	reg [$clog2({{ issue_buffer_size }})-1:0] issue_buffer_slot_move_up [{{ issue_buffer_size }}-1:0];
	
	// returns how much space there is in the issue buffer
	{{ name }}_PopCount
	#(
		.WORD_WIDTH(ISSUE_BUFFER_SIZE)
	) pop_counter (
		.word_i(issue_buffer_valid),
		.pop_count_o(issue_buffer_valid_pop_count)
	);

	// valid registers for forward ports
	reg [{{ forward_ports }}-1:0] instruction_valid;
	// when an instruction is assigned to a forward port wait delay cycles
	// until the valid signal is set to 1'b0 and the instruction is removed from
	// the issue buffer
	reg [0:0] instruction_valid_unassign_delay [{{ forward_ports }}-1:0];

	{%- for i in range(forward_ports) %}
	assign instruction_valid_{{ i }}_o = instruction_valid[{{ i }}];
	{%- endfor %}

	// MUX from each issue buffer slot to a forward port
	reg [$clog2({{ issue_buffer_size }})-1:0] issue_buffer_slot_to_forward_port_mux_select [{{ issue_buffer_size }}-1:0];

	{%- for i in range(forward_ports) %}	
	// MUX for forward port {{i}}
	assign instruction_{{ i }}_o = 
	{% for j in range(issue_buffer_size) -%}	
		(issue_buffer_slot_to_forward_port_mux_select[{{ i }}] == {{j}}) ? issue_buffer[{{j}}] : 
	{% endfor -%}
	{INSTRUCTION_SIZE{1'b0}};
	{% endfor %}

	// forward lookup tables for each issue buffer slot
	wire [$clog2({{ forward_ports }})-1:0] issue_buffer_forward_port [{{ issue_buffer_size }}-1:0];

	{%- for j in range(issue_buffer_size) %}
	{{ name }}_{{ j }}_ForwardLookupTable fwd_lut_{{ j }}(
		.target_id_i(issue_buffer_target_ids[{{ j }}]),
		.forward_port_o(issue_buffer_forward_port[{{ j }}])
	);
	{%- endfor %}

	assign issue_buffer_available_slots = ISSUE_BUFFER_SIZE - issue_buffer_valid_pop_count;

	integer i;
	integer j;
	integer k;
	integer freed_counter;
	
	always @(posedge clk_i, negedge reset_n_i) begin
		if(reset_n_i == 1'b0) begin
			program_counter <= {{ initial_address }};
			address_valid <= 1'b0;
			initialize_read <= 1'b1;
			read_in_progress <= 1'b0;
			read_done <= 1'b0;

			// reset issue buffer
			for(i = 0; i < ISSUE_BUFFER_SIZE; i = i + 1) begin
				issue_buffer[i] = {DATA_WIDTH{1'b0}};
			end

			issue_buffer_valid <= {ISSUE_BUFFER_SIZE{1'b0}};
			issue_buffer_first_free_slot <= 0;

			// reset select registers for MUXes
			{%- for i in range(forward_ports) %}	
			issue_buffer_slot_to_forward_port_mux_select[{{ i }}] <= 0;
			instruction_valid[{{ i }}] <= 0;
			{% endfor -%}
		end
		else begin
			// initialize a read from memory if:
			// - a read is done
			// - no read has been initialized yet
			// - the issue buffer has space left
			// - the instruction memory is ready
			if(read_done == 1'b1 && initialize_read == 1'b0 && issue_buffer_available_slots >= PORT_WIDTH && instruction_memory_ready_i == 1'b1) begin
				$display("t=%0t: HERE %d >= ", $time, issue_buffer_available_slots, PORT_WIDTH);
				initialize_read <= 1'b1;
				read_done <= 1'b0;
			end

			// start a read from memory if:
			// - a read was initialized
			// - the instruction memory is ready
			if(instruction_memory_ready_i == 1'b1 && initialize_read == 1'b1) begin
				$display("t=%0t: %m read initialized from address=%d.", $time, program_counter);
				address_valid <= 1'b1;
				read_in_progress <= 1'b1;
				initialize_read <= 1'b0;
				read_done <= 1'b0;
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

				// initialize a read from memory if:
				// - the issue buffer has space left
				// - the instruction memory is ready
				if((issue_buffer_available_slots - PORT_WIDTH >= PORT_WIDTH) && instruction_memory_ready_i == 1'b1) begin
					initialize_read <= 1'b1;
				end
				else begin
					read_done <= 1'b1;
				end

				address_valid <= 1'b0;
				read_in_progress <= 1'b0;
				program_counter <= program_counter + PORT_WIDTH;
			end

			// set all issue_buffer_slot_assigned to 0 to track if they have been
			// assigned in the next for loop
			for(j = 0; j < {{ issue_buffer_size }}; j = j + 1) begin
				issue_buffer_slot_assigned[j] = 1'b0;
				issue_buffer_slot_freed[j] = 1'b0;
			end

			for(i = 0; i < {{ forward_ports }}; i = i + 1) begin
				forward_port_in_use[i] = 1'b0;
			end

			// check each next_stage_ready_i if a subsequent stage is ready
			for(i = 0; i < {{ forward_ports }}; i = i + 1) begin
				if(next_stages_ready[i] == 1'b1) begin
					$display("t=%0t: %m next_stage_ready_%d_i", $time, i);
					// if a next stage is ready, check the issue buffer 
					// from [0] to [issue_buffer_size] if there is an instruction
					// that can be forwarded to this port that is not already assigned
					// to another port
					for(j = 0; j < {{ issue_buffer_size }}; j = j + 1) begin
						// check if the current issue buffer slot isn't assigned already,
						// check if current forward port is already in use,
						// and if the current issue buffer slot can be forwarded to current 
						/// forward port
						if((issue_buffer_slot_assigned[j] == 1'b0) && (forward_port_in_use[i] == 1'b0) && (issue_buffer_forward_port[j] == i[$clog2({{ forward_ports }})-1:0])) begin
							// assign issue buffer slot to current forward port
							forward_port_in_use[i] = 1'b1;
							issue_buffer_slot_assigned[j] = 1'b1;
							issue_buffer_slot_assigned_to_forward_port[i] <= j[$clog2({{ issue_buffer_size }})-1:0];

							// set forward port mux to issue buffer slot
							issue_buffer_slot_to_forward_port_mux_select[i] <= j[$clog2({{ issue_buffer_size }})-1:0];	
							// set forward port valid to 1'b1
							instruction_valid[i] <= 1'b1;
							instruction_valid_unassign_delay[i] <= 1'b1;

							$display("t=%0t: %m assigned issue_buffer[%d] to forward_port: %d", $time, j, issue_buffer_forward_port[j]);
						end
					end
				end
			end

			// check for each forward port an instructon was assigned to 
			// if instruction can be removed from issue buffer
			for(i = 0; i < {{ forward_ports }}; i = i + 1) begin
				if(instruction_valid[i] == 1'b1) begin
					if(instruction_valid_unassign_delay[i] != 1'b0) begin
						instruction_valid_unassign_delay[i] <= instruction_valid_unassign_delay[i] - 1;
					end
					else begin
						instruction_valid[i] <= 1'b0;
						$display("t=%0t: %m remove instruction from issue buffer slot %d", $time, issue_buffer_slot_assigned_to_forward_port[i]);

						// TODO instead of deleting contents of issue buffer slot move next
						// slot forward and adjust issue_buffer_first_free_slot
						//issue_buffer[issue_buffer_slot_assigned_to_forward_port[i]] <= { {{ data_width }}{1'b0}};
						//issue_buffer_valid[issue_buffer_slot_assigned_to_forward_port[i]] <= 1'b0;
						issue_buffer_slot_freed[issue_buffer_slot_assigned_to_forward_port[i]] = 1'b1;  
					end
				end
			end

			// determine how many slots an instruction in the issue buffer has to move up
			// after an instruction in a slot before it was removed (the first slot can be skipped
			// because it can not move up)
			for(j = 0; j < {{ issue_buffer_size }}; j = j + 1) begin
				$display("%d: %d", j, issue_buffer_slot_freed[j]);
			end

			for(j = 1; j < {{ issue_buffer_size }}; j = j + 1) begin
				freed_counter = 0;
				// iterate over all issue buffer slots infront of current issue buffer slot
				for(k = j-1; k >= 0; k = k - 1) begin
					if(issue_buffer_first_free_slot[k] == 1'b1) begin
						freed_counter = freed_counter + 1;
					end
					$display("current: %d, before: %d, freed: %d", j ,k, issue_buffer_first_free_slot[k]);
				end
				$display("freed_counter: %d\n", freed_counter);
			end
		end
	end
endmodule