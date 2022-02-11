module RegisterFile
#(
	parameter DATA_WIDTH /* verilator public */ = 32,
	parameter NUM_REGISTERS /* verilator public */ = 4,
	parameter READ_WRITE_PORTS /* verilator public */ = 2
)
(
	input clk_i,
	input reset_n_i,
	input[NUM_REGISTERS*READ_WRITE_PORTS-1:0] register_select_i, // one-hot
	input[DATA_WIDTH*READ_WRITE_PORTS-1:0] data_i,
	input[READ_WRITE_PORTS-1:0] write_select_i,

	output reg[DATA_WIDTH*READ_WRITE_PORTS-1:0] data_o
);

	reg[DATA_WIDTH-1:0] registers[NUM_REGISTERS-1:0];

	generate
		genvar i, j;

		for(i=0; i<NUM_REGISTERS; i=i+1) begin
			for(j=0; j<READ_WRITE_PORTS; j=j+1) begin

				// output MUX		
				always @(*) begin
					data_o[DATA_WIDTH*j+:DATA_WIDTH] = registers[$clog2(register_select_i[NUM_REGISTERS*j+:NUM_REGISTERS])];
				end

				always @(posedge clk_i, negedge reset_n_i) begin
					if(reset_n_i == 1'b0) begin
						registers[i] <= 0;
					end
					else begin
						if(write_select_i[j] == 1'b1) begin
							registers[$clog2(register_select_i[j*NUM_REGISTERS+:NUM_REGISTERS])] <= data_i[DATA_WIDTH*j+:DATA_WIDTH];
						end
					end
				end
			end
		end
	endgenerate
endmodule
