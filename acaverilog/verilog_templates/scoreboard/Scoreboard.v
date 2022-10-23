module {{ name }}_Scoreboard
#(
) (
	input clk_i,
	input reset_n_i
);

	reg [3:0] counter;

	always @(posedge clk_i, negedge reset_n_i) begin
		if(reset_n_i == 1'b0) begin
			counter <= 0;
		end
		else begin
			counter <= counter + 1;
		end
	end
endmodule