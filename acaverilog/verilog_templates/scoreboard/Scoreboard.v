module {{ name }}_Scoreboard
#(
	parameter MAX_INSTRUCTIONS = {{ max_instructions }},
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

	// registers for tracking instruction states 
	{%- for i in range(max_instructions) %}
	reg [1:0] instruction_state_{{ i }};
	{%- endfor %}

	always @(posedge clk_i, negedge reset_n_i) begin
		if(reset_n_i == 1'b0) begin
			full <= 0;

			{%- for i in range(max_instructions) %}
			instruction_state_{{ i }} <= ISSUE;
			{%- endfor %}
		end
		else begin
		end
	end
endmodule