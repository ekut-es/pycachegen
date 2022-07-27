module {{ name }}_PipelineStage (
	input clk_i,
	input reset_i,

	input[{{ instruction_size }}-1:0] instruction_i,
	input instruction_valid_i,

	output ready_o
);

	reg [{{ instruction_size }}-1:0] instruction;

	always @(posedge clk_i, negedge reset_n_i) begin
		if(reset_n_i == 1'b0) begin
			instruction <= { {{ instruction_size }} {1'b0}};
		end
		else begin
			if(instruction_valid_i == 1'b1) begin
				instruction <= instruction_i;
				ready_o <= 1'b1;
			end
		end
	end
endmodule