module {{ name }}_PipelineStage 
#(
	parameter LATENCY = {{ latency }}
)
(
	input clk_i,
	input reset_n_i,

	input[{{ instruction_size }}-1:0] instruction_i,
	input instruction_valid_i,

	{% for i in range(forward_ports) %}
	input next_stage_ready_{{ i }}_i,
	output[{{ instruction_size }}-1:0] instruction_{{ i }}_o,
	output instruction_valid_{{ i }}_o,
	{% endfor %}

	output ready_o
);

	localparam LATENCY_COUNTER_SIZE = $clog2(LATENCY)+1;

	reg [{{ instruction_size }}-1:0] instruction;
	reg ready;
	assign ready_o = ready;

	reg [LATENCY_COUNTER_SIZE-1:0] latency_counter;

	{% for i in range(forward_ports) %}
	reg [{{ instruction_size }}-1:0] instruction_{{ i }}_o_reg;
	assign instruction_{{ i }}_o = instruction_{{ i }}_o_reg;
	reg instruction_valid_{{ i }}_o_reg;
	assign instruction_valid_{{ i }}_o = instruction_valid_{{ i }}_o_reg;
	{% endfor -%}

	wire[{{ target_id_length }}-1:0] target_id;
	assign target_id = instruction[{{ target_id_start_bit }}+:{{ target_id_length }}];

	wire [{{ forward_ports_size }}-1:0] forward_port_select;

	{{ name }}_ForwardLookupTable fwd_lut(
		.target_id_i(target_id),
		.forward_port_o(forward_port_select)
	);

	// TODO DEMUX from instruction reg to instruction_o port and instruction_valid_o port
	
	always @(posedge clk_i, negedge reset_n_i) begin
		if(reset_n_i == 1'b0) begin
			instruction <= { {{ instruction_size }} {1'b0}};
			ready <= 1'b1;
			latency_counter <= {LATENCY_COUNTER_SIZE{1'b0}};

			{% for i in range(forward_ports) %}
			instruction_{{ i }}_o_reg <= { {{ instruction_size }} {1'b0}};
			instruction_valid_{{ i }}_o_reg <= 1'b0;
			{% endfor -%}
		end
		else begin
			/*
			// if an instruction was forwarded reset instruction output to 0
			if(instruction_o_reg != { {{ instruction_size }} {1'b0}}) begin
				instruction_o_reg <= { {{ instruction_size }} {1'b0}};
				instruction_valid_o_reg <= 1'b0;
			end
			*/
			if(ready == 1'b1) begin
				// accept new instruction
				if(instruction_valid_i == 1'b1) begin
					ready <= 1'b0;
					instruction <= instruction_i;
					latency_counter <= LATENCY-1;
					$display("t=%0t: received instruction: %08h", $time, instruction_i);
				end
			end
			/*
			// forward instruction if subsequent stage is ready
			if(latency_counter == {LATENCY_COUNTER_SIZE{1'b0}} && next_stage_ready_i && instruction != { {{ instruction_size }} {1'b0}}) begin
				$display("t=%0t: forward instruction: %08h", $time, instruction);
				instruction_o_reg <= instruction;
				instruction_valid_o_reg <= 1'b1;

				instruction <= { {{ instruction_size }} {1'b0}};
				ready <= 1'b1;
			end
			// decrease latency
			if(latency_counter != {LATENCY_COUNTER_SIZE{1'b0}}) begin
				latency_counter <= latency_counter-1;
				$display("t=%0t: latency_counter=%d", $time, latency_counter);
			end
			*/
		end
	end
endmodule
