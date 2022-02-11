module RegisterFile
#(
	parameter DATA_WIDTH /* verilator public */ = 32,
	parameter NUM_REGISTERS /* verilator public */ = 3,
	parameter READ_WRITE_PORTS /* verilator public */ = 2
)
(
	input clk_i,
	input reset_n_i,
	input[0:NUM_REGISTERS*READ_WRITE_PORTS-1] register_select_i,
	input[0:DATA_WIDTH*READ_WRITE_PORTS-1] data_i,
	input[0:READ_WRITE_PORTS-1] write_select_i,

	output[0:DATA_WIDTH*READ_WRITE_PORTS-1] data_o
);

	reg[0:DATA_WIDTH-1] registers[0:NUM_REGISTERS-1];


	generate
		genvar i, j;

		for(i=0;i<NUM_REGISTERS;i=i+1) begin
			for(j=0; j<READ_WRITE_PORTS; j=j+1) begin
				// output MUX
				assign data_o[(READ_WRITE_PORTS*i+j)*DATA_WIDTH:(READ_WRITE_PORTS*i+j+1)*DATA_WIDTH-1] = register_select_i[(READ_WRITE_PORTS*i+j)] ? registers[i] : {DATA_WIDTH{1'b0}};

				always @(posedge clk_i, negedge reset_n_i) begin
					if(reset_n_i == 1'b0) begin
						registers[i] <= 0;
					end
					else begin
						if(write_select_i[j] == 1'b1) begin
							registers[$clog2(register_select_i[j*NUM_REGISTERS:(j+1)*NUM_REGISTERS-1])] <= data_i[(READ_WRITE_PORTS*i+j)*DATA_WIDTH:(READ_WRITE_PORTS*i+j+1)*DATA_WIDTH-1];
						end
					end
				end
			end
		end


	endgenerate
	/*
	generate

		genvar i;
		genvar j;

		for(i=0; i<NUM_REGISTERS; i=i+1) begin
			for(j=0; j<READ_WRITE_PORTS; j=j+1) begin

				// example: NUM_REGISTERS = 2, READ_WRITE_PORTS = 2
				// data_o[0:DATA_WIDTH-1] = registers[0]
				// data_o[DATA_WIDTH:2*DATA_WIDTH-1] = registers[1]
				// data_o[2*DATA_WIDTH:3*DATA_WIDTH-1] = registers[0]
				// data_o[3*DATA_WIDTH:4*DATA_WIDTH-1] = registers[1]
				//assign data_o[(READ_WRITE_PORTS*i+j)*DATA_WIDTH:(READ_WRITE_PORTS*i+j+1)*DATA_WIDTH-1] = registers[i];
				assign data_o[(READ_WRITE_PORTS*i+j)*DATA_WIDTH:(READ_WRITE_PORTS*i+j+1)*DATA_WIDTH-1] = registers[i];

				always @(posedge clk_i, negedge reset_n_i) begin
					if(reset_n_i == 1'b0) begin
						registers[i] <= 0;
					end
					else begin
						if(write_select_i[READ_WRITE_PORTS*j+i] == 1'b1) begin
							registers[i] <= data_i[(READ_WRITE_PORTS*i+j)*DATA_WIDTH:(READ_WRITE_PORTS*i+j+1)*DATA_WIDTH-1];
						end
					end
				end
			end
		end
	endgenerate
	*/
endmodule
