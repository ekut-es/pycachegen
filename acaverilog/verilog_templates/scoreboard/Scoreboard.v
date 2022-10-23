module {{ name }}_Scoreboard
#(
	parameter MAX_INSTRUCTIONS = {{ max_instructions }},
	parameter FUNCTIONAL_UNITS = {{ functional_units }},
	parameter MAX_SOURCE_REGISTERS = {{ max_source_registers }},
	parameter MAX_DESTINATION_REGISTERS = {{ max_destination_registers }},
	parameter REGISTER_SIZE = {{ register_size|default(32, true)}},
	parameter MAX_INSTRUCTION_ISSUES = {{ max_instruction_issues }},
	parameter INSTRUCTION_SIZE = {{ instruction_size }}
) (
	input clk_i,
	input reset_n_i,

	{%- for i in range(max_instruction_issues) %}
	input [INSTRUCTION_SIZE-1:0] issued_instruction_{{ i }}_i,
	input issued_instruction_valid_{{ i }}_i,
	{% endfor -%}

	// 0 if there are enough instruction slots available for MAX_INSTRUCTION_ISSUES
	output full_o
);

	reg full;
	assign full_o = full;

	typedef enum[1:0] {ISSUE = 0, READ_REGISTERS = 1, EXECUTION = 2, WRITE_REGSISTER = 3} instruction_state;

	// registers for tracking instruction states 
	reg [1:0] instruction_status [MAX_INSTRUCTIONS-1:0];

	reg busy [FUNCTIONAL_UNITS-1:0];
	reg [REGISTER_SIZE-1:0] operation [FUNCTIONAL_UNITS-1:0]; // TODO check if it is really needed

	// content is the register id
	// first index is the register number, 
	// second index is the target id of the functional unit
	// F_i
	reg [REGISTER_SIZE-1:0] destination_register [$clog2(MAX_DESTINATION_REGISTERS):0][FUNCTIONAL_UNITS-1:0];
	// F_j, F_k
	reg [REGISTER_SIZE-1:0] source_register [$clog2(MAX_SOURCE_REGISTERS):0][FUNCTIONAL_UNITS-1:0];

	// content is the functional unit target id that produces the value
	// first index is the register
	// second index is the target id of the functional unit
	// Q_j, Q_k
	reg [REGISTER_SIZE-1:0] source_functional_unit [$clog2(MAX_SOURCE_REGISTERS):0][FUNCTIONAL_UNITS-1:0];

	// content is the functional unit target id that produces the value is ready
	// first index is the register
	// second index is the target id of the functional unit
	// R_j, R_k
	reg [REGISTER_SIZE-1:0] functional_unit_ready [$clog2(MAX_SOURCE_REGISTERS):0][FUNCTIONAL_UNITS-1:0];

	// content is the functional unit target id that writes into register
	// Result
	reg [REGISTER_SIZE-1:0] register_writer [$clog2(MAX_SOURCE_REGISTERS):0];

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