module MemoryAccessUnit 
#(
	parameter LATENCY /* verilator public */ = 4,
	parameter DATA_WIDTH /* verilator public */ = 32,

	parameter INSTRUCTION_LENGTH /* verilator public */ = 32,
	parameter OPCODE_LENGTH /* verilator public */ = 8,

	parameter REGISTER_READ_PORTS /* verilator public */ = 2,
	parameter NUM_READ_REGISTERS /* verilator public */ = 4,

	parameter REGISTER_WRITE_PORTS /* verilator public */ = 1,
	parameter NUM_WRITE_REGISTERS /* verilator public */ = 2,

	parameter MEMORY_READ_PORTS /* verilator public */ = 1,
	parameter NUM_READ_MEMORIES /* verilator public */ = 1,

	parameter MEMORY_WRITE_PORTS /* verilator public */ = 1,
	parameter NUM_WRITE_MEMORIES /* verilator public */ = 1
)
(
	input clk_i,
	input reset_n_i,

	input[INSTRUCTION_LENGTH-1:0] instruction_i,
	input instruction_valid_i,

	input[REGISTER_READ_PORTS*DATA_WIDTH-1:0] register_data_i,

	output[NUM_READ_MEMORIES*REGISTER_READ_PORTS-1:0] register_select_o,
	output[NUM_WRITE_MEMORIES*REGISTER_WRITE_PORTS-1:0] write_register_select_o,

	output[REGISTER_WRITE_PORTS*DATA_WIDTH-1:0] register_data_o,

	output ready_o,
	output instruction_done_o
);

	localparam LATENCY_BUFFER_SIZE = LATENCY;

	reg[LATENCY_BUFFER_SIZE-1:0] latency_buffer;
	reg[INSTRUCTION_LENGTH-1:0] instruction;
	reg ready;
	reg instruction_done;

	assign ready_o = ready;
	assign instruction_done_o = instruction_done;

	always @(posedge clk_i, negedge reset_n_i) begin
		if(reset_n_i == 1'b0) begin
			latency_buffer <= {LATENCY_BUFFER_SIZE{1'b0}};
			ready <= 1;
		end
		else begin
			// received new instruction
			if(instruction_valid_i == 1'b1 && ready == 1'b1) begin
				instruction <= instruction_i;
				latency_buffer <= {{LATENCY_BUFFER_SIZE-1{1'b0}},{1'b1}};
				ready <= 0;
				// TODO read regs
			end

			// processing of instruction in progress
			if(latency_buffer != {LATENCY_BUFFER_SIZE{1'b0}}) begin
				latency_buffer <= latency_buffer << 1;
			end

			// processing of instruction done
			if(latency_buffer[LATENCY_BUFFER_SIZE-1] == 1'b1) begin
				latency_buffer <= {LATENCY_BUFFER_SIZE{1'b0}};
				instruction <= 0;
				instruction_done <= 1;
				ready <= 1;
				// TODO write regs
			end

			if(instruction_done == 1'b1) begin
				instruction_done <= 0;
			end
		end
	end
endmodule
