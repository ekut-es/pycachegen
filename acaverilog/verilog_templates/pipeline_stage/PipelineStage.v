module {{ name }}_PipelineStage 
#(
	parameter LATENCY = {{ latency }}
)
(
	input clk_i,
	input reset_n_i,

	input[{{ instruction_size }}-1:0] instruction_i,
	input instruction_valid_i,

	{%- for i in range(forward_ports) %}
	input next_stage_ready_{{ i }}_i,
	output[{{ instruction_size }}-1:0] instruction_{{ i }}_o,
	output instruction_valid_{{ i }}_o,
	{% endfor %}

	output ready_o
);

	localparam LATENCY_COUNTER_SIZE = $clog2(LATENCY)+1;

	reg [{{ instruction_size }}-1:0] instruction;
	reg instruction_valid;
	reg ready;
	assign ready_o = ready;

	reg [LATENCY_COUNTER_SIZE-1:0] latency_counter;

	wire[{{ target_id_length }}-1:0] target_id;
	assign target_id = instruction[{{ target_id_start_bit }}+{{ target_id_length }}-1:{{ target_id_start_bit }}];

	wire [{{ forward_ports_size }}-1:0] forward_port_select;

	{{ name }}_ForwardLookupTable fwd_lut(
		.target_id_i(target_id),
		.forward_port_o(forward_port_select)
	);

	// DEMUX from instruction to forward_port
	{%- for key, value in forward_port_map.items() %}
	wire instruction_{{ value }}_cond;
	assign instruction_{{ value }}_cond = (target_id == {{ key }}) & (instruction_valid == 1'b1) & (latency_counter == {LATENCY_COUNTER_SIZE{1'b0}});
	assign instruction_{{ value }}_o = instruction_{{ value }}_cond ? instruction : { {{ instruction_size }} {1'b0}};
	assign instruction_valid_{{ value }}_o = instruction_{{ value }}_cond;
	{% endfor %}

	// MUX from next_stage_ready_is to next_stage_ready
	wire next_stage_ready;
	assign next_stage_ready = 
	{%- for key, value in forward_port_map.items() %}
		(target_id == {{ key }}) ? next_stage_ready_{{ value }}_i : 
	{% endfor -%}
	1'b0;


	always @(posedge clk_i, negedge reset_n_i) begin
		if(reset_n_i == 1'b0) begin
			instruction <= { {{ instruction_size }} {1'b0}};
			instruction_valid <= 1'b0;
			ready <= 1'b1;
			latency_counter <= {LATENCY_COUNTER_SIZE{1'b0}};
		end
		else begin
			if(ready == 1'b1) begin
				// accept new instruction
				if(instruction_valid_i == 1'b1) begin
					ready <= 1'b0;
					instruction <= instruction_i;
					instruction_valid <= 1'b1;
					latency_counter <= LATENCY-1;
					$display("t=%0t: %m received instruction: %08h", $time, instruction_i);
				end
			end
			// forward instruction if subsequent stage is ready
			if(latency_counter == {LATENCY_COUNTER_SIZE{1'b0}} && instruction_valid == 1'b1 && next_stage_ready) begin
				$display("t=%0t: %m instruction is forwarded: %08h", $time, instruction);
				ready <= 1'b1;
				instruction <= { {{ instruction_size }} {1'b0}};
				instruction_valid <= 1'b0;
			end
			// decrease latency
			if(latency_counter != {LATENCY_COUNTER_SIZE{1'b0}}) begin
				latency_counter <= latency_counter-1;
				$display("t=%0t: %m latency_counter=%d", $time, latency_counter);
			end
		end
	end
endmodule
