module {{ name }}_Scoreboard
#(
	parameter SIZE = {{ size }}
) (
	input clk_i,
	input reset_n_i,

	output full_o
);

	reg full;
	assign full_o = full;

	always @(posedge clk_i, negedge reset_n_i) begin
		if(reset_n_i == 1'b0) begin
			full <= 0;
		end
		else begin
		end
	end
endmodule