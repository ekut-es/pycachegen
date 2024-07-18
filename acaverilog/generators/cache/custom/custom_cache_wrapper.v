

module cache_wrapper
(
  input clk_i,
  input reset_n_i,
  input flush_i,
  output flush_done_o,
  output hit_o,
  input [15-1:0] address_0_i,
  input address_valid_0_i,
  input [16-1:0] write_data_0_i,
  input write_data_valid_0_i,
  input read_write_select_0_i,
  output [16-1:0] read_data_0_o,
  output read_data_valid_0_o,
  output write_done_0_o,
  output port_ready_0_o
);

  assign hit_o = 0;
  wire [15-1:0] l1_address;
  wire l1_address_valid;
  wire [16-1:0] l1_write_data;
  wire l1_write_data_valid;
  wire l1_read_write_select;
  wire [16-1:0] l1_read_data;
  wire l1_read_data_valid;
  wire l1_write_done;
  wire l1_port_ready;
  wire [2-1:0] l1_write_strobe;
  assign l1_write_strobe = 3;
  assign l1_address = address_0_i;
  assign l1_address_valid = address_valid_0_i;
  assign l1_write_data = write_data_0_i;
  assign l1_write_data_valid = write_data_valid_0_i;
  assign l1_read_write_select = read_write_select_0_i;
  assign read_data_0_o = l1_read_data;
  assign read_data_valid_0_o = l1_read_data_valid;
  assign write_done_0_o = l1_write_done;
  assign port_ready_0_o = l1_port_ready;
  assign flush_done_o = 1;

  functional_memory
  memory
  (
    .clk_i(clk_i),
    .reset_n_i(reset_n_i),
    .address_i(l1_address),
    .address_valid_i(l1_address_valid),
    .write_data_i(l1_write_data),
    .write_data_valid_i(l1_write_data_valid),
    .read_write_select_i(l1_read_write_select),
    .write_strobe_i(l1_write_strobe),
    .read_data_o(l1_read_data),
    .read_data_valid_o(l1_read_data_valid),
    .write_done_o(l1_write_done),
    .port_ready_o(l1_port_ready)
  );


endmodule



module functional_memory
(
  input clk_i,
  input reset_n_i,
  input [15-1:0] address_i,
  input address_valid_i,
  input [16-1:0] write_data_i,
  input write_data_valid_i,
  input read_write_select_i,
  input [2-1:0] write_strobe_i,
  output [16-1:0] read_data_o,
  output read_data_valid_o,
  output write_done_o,
  output port_ready_o
);

  reg [15-1:0] address;
  reg [16-1:0] write_data;
  reg read_write_select;
  reg [2-1:0] write_strobe;
  reg [8-1:0] read_data [0:2-1];
  reg read_data_valid;
  reg write_done;
  reg [4-1:0] latency_counter;
  reg [8-1:0] data_memory_0 [0:8192-1];
  reg [8-1:0] data_memory_1 [0:8192-1];
  reg processing_request;
  assign read_data_o[7:0] = read_data[0];
  assign read_data_o[15:8] = read_data[1];
  assign read_data_valid_o = read_data_valid;
  assign write_done_o = write_done;
  assign port_ready_o = !processing_request;

  always @(posedge clk_i) begin
    if(0 & !reset_n_i) begin
      latency_counter <= 0;
      address <= 0;
      write_data <= 0;
      read_write_select <= 0;
      read_data[0] <= 0;
      read_data[1] <= 0;
      read_data_valid <= 0;
      write_done <= 0;
      processing_request <= 0;
      write_strobe <= 0;
    end else begin
      if(!processing_request) begin
        if((address_valid_i == 1) && (read_write_select_i == 0) | (read_write_select_i == 1) & (write_data_valid_i == 1) && (address_i <= 8190) && 1) begin
          address <= address_i;
          write_data <= write_data_i;
          write_strobe <= write_strobe_i;
          read_write_select <= read_write_select_i;
          read_data_valid <= 0;
          write_done <= 0;
          processing_request <= 1;
          latency_counter <= latency_counter + 1;
        end 
      end else if(!((read_write_select == 0) & (latency_counter == 4) | (read_write_select == 1) & (latency_counter == 9))) begin
        latency_counter <= latency_counter + 1;
      end else begin
        processing_request <= 0;
        latency_counter <= 0;
        if(read_write_select == 0) begin
          read_data[0] <= data_memory_0[address - 0];
          read_data[1] <= data_memory_1[address - 0];
          read_data_valid <= 1;
        end else begin
          write_done <= 1;
          if(write_strobe[0]) begin
            data_memory_0[address - 0] <= write_data[7:0];
          end 
          if(write_strobe[1]) begin
            data_memory_1[address - 0] <= write_data[15:8];
          end 
        end
      end
    end
  end


endmodule

