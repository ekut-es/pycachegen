module {{ name }}_PipelineStage 
#(
	parameter LATENCY = {{ latency }}
)
(
	input clk_i,
	input reset_n_i,

	input[{{ instruction_size }}-1:0] instruction_i,
	input instruction_valid_i,

	input next_stage_ready_i, 
	output[{{ instruction_size }}-1:0] instruction_o,
	output instruction_valid_o,

	output ready_o
);

	localparam LATENCY_COUNTER_SIZE = $clog2(LATENCY)+1;

	reg [{{ instruction_size }}-1:0] instruction;
	reg ready;
	assign ready_o = ready;

	reg [LATENCY_COUNTER_SIZE-1:0] latency_counter;

	reg [{{ instruction_size }}-1:0] instruction_o_reg;
	assign instruction_o = instruction_o_reg;
	reg instruction_valid_o_reg;
	assign instruction_valid_o = instruction_valid_o_reg;

	always @(posedge clk_i, negedge reset_n_i) begin
		if(reset_n_i == 1'b0) begin
			instruction <= { {{ instruction_size }} {1'b0}};
			ready <= 1'b1;
			latency_counter <= {LATENCY_COUNTER_SIZE{1'b0}};
			instruction_o_reg <= { {{ instruction_size }} {1'b0}};
			instruction_valid_o_reg <= 1'b0;
		end
		else begin
			// if an instruction was forwarded reset instruction output to 0
			if(instruction_o_reg != { {{ instruction_size }} {1'b0}}) begin
				instruction_o_reg <= { {{ instruction_size }} {1'b0}};
				instruction_valid_o_reg <= 1'b0;
			end
			if(ready == 1'b1) begin
				// accept new instruction
				if(instruction_valid_i == 1'b1) begin
					ready <= 1'b0;
					instruction <= instruction_i;
					latency_counter <= LATENCY-1;
					$display("t=%0t: received instruction: %08h", $time, instruction_i);
				end
			end
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
		end
	end
endmodule
