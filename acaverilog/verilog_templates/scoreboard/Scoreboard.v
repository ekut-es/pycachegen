module {{ name }}_Scoreboard
#(
	parameter SIZE = {{ size }},
	parameter MAX_SOURCE_REGISTERS = {{ max_source_registers }},
	parameter MAX_TARGET_REGISTERS = {{ max_target_registers }}
) (
	input clk_i,
	input reset_n_i,

	output full_o
);

	reg full;
	assign full_o = full;

	typedef enum[1:0] {ISSUE = 0, READ_REGISTERS = 1, EXECUTION = 2, WRITE_REGSISTER = 3} instruction_state;

	// data structure for scoreboarding
	{%- for i in range(size) %}
	reg [1:0] instruction_{{ i }}_status;
	{%- endfor %}

	always @(posedge clk_i, negedge reset_n_i) begin
		if(reset_n_i == 1'b0) begin
			full <= 0;

			{%- for i in range(size) %}
			instruction_{{ i }}_status <= ISSUE;
			{%- endfor %}
		end
		else begin
		end
	end
endmodule