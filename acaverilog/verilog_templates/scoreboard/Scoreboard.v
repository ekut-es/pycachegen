module {{ name }}_Scoreboard
#(
	parameter MAX_INSTRUCTIONS = {{ max_instructions }},
	parameter FUNCTIONAL_UNITS = {{ functional_units }},
	parameter MAX_SOURCE_REGISTERS = {{ max_source_registers }},
	parameter MAX_TARGET_REGISTERS = {{ max_target_registers }},
	parameter REGISTER_SIZE = {{ register_size|default(32, true)}}
) (
	input clk_i,
	input reset_n_i,

	output full_o
);

	reg full;
	assign full_o = full;

	typedef enum[1:0] {ISSUE = 0, READ_REGISTERS = 1, EXECUTION = 2, WRITE_REGSISTER = 3} instruction_state;

	// registers for tracking instruction states 
	reg [1:0] instruction_status [MAX_INSTRUCTIONS-1:0];

	reg busy [FUNCTIONAL_UNITS-1:0];
	reg [REGISTER_SIZE-1:0] operation [FUNCTIONAL_UNITS-1:0]; // TODO check if it is really needed
	// TODO add data structure
	//reg [REGISTER_SIZE-1:0] 

	integer i;

	always @(posedge clk_i, negedge reset_n_i) begin
		if(reset_n_i == 1'b0) begin
			full <= 0;

			for(i = 0; i < FUNCTIONAL_UNITS; i = i + 1) begin
				instruction_status[i] = ISSUE;
			end
		end
		else begin
		end
	end
endmodule