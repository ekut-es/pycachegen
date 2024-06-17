

module functional_memory #
(
  parameter READ_LATENCY = 9,
  parameter WRITE_LATENCY = 14,
  parameter DATA_WIDTH = 16,
  parameter ADDRESS_WIDTH = 3
)
(
  input clk_i,
  input reset_n_i,
  input [ADDRESS_WIDTH-1:0] address_0_i,
  input address_valid_0_i,
  input [DATA_WIDTH-1:0] write_data_0_i,
  input write_data_valid_0_i,
  input read_write_select_0_i,
  output [DATA_WIDTH-1:0] read_data_0_o,
  output read_data_valid_0_o,
  output write_done_0_o,
  output port_ready_0_o
);

  localparam READ_LATENCY_COUNTER_SIZE = 4;
  localparam WRITE_LATENCY_COUNTER_SIZE = 4;
  reg [READ_LATENCY_COUNTER_SIZE-1:0] read_latency_counter_0;
  reg [WRITE_LATENCY_COUNTER_SIZE-1:0] write_latency_counter_0;
  reg [ADDRESS_WIDTH-1:0] address_0;
  reg address_valid_0;
  reg [DATA_WIDTH-1:0] write_data_0;
  reg write_data_valid_0;
  reg read_write_select_0;
  reg [DATA_WIDTH-1:0] read_data_0;
  reg read_data_valid_0;
  reg write_done_0;
  reg [DATA_WIDTH-1:0] data_memory [0:8-1];
  reg read_in_progress_0;
  reg write_in_progress_0;
  assign port_ready_0_o = (read_in_progress_0 == 0) && (write_in_progress_0 == 0);
  assign read_data_0_o = read_data_0;
  assign read_data_valid_0_o = read_data_valid_0;
  assign write_done_0_o = write_done_0;

  always @(posedge clk_i or negedge reset_n_i) begin
    if(reset_n_i == 0) begin
      read_latency_counter_0 <= READ_LATENCY;
      write_latency_counter_0 <= WRITE_LATENCY;
      address_0 <= 0;
      address_valid_0 <= 0;
      write_data_0 <= 0;
      write_data_valid_0 <= 0;
      read_write_select_0 <= 0;
      read_data_0 <= 0;
      read_data_valid_0 <= 0;
      write_done_0 <= 0;
      read_in_progress_0 <= 0;
      write_in_progress_0 <= 0;
    end else begin
      if(port_ready_0_o == 1) begin
        if((read_write_select_0_i == 0) && (address_valid_0_i == 1)) begin
          read_in_progress_0 <= 1;
          read_latency_counter_0 <= READ_LATENCY;
          address_0 <= address_0_i;
          address_valid_0 <= 1;
          read_data_valid_0 <= 0;
          write_done_0 <= 0;
        end 
        if((read_write_select_0_i == 1) && (address_valid_0_i == 1) && (write_data_valid_0_i == 1)) begin
          write_in_progress_0 <= 1;
          write_latency_counter_0 <= WRITE_LATENCY;
          address_0 <= address_0_i;
          address_valid_0 <= 1;
          write_data_0 <= write_data_0_i;
          read_data_valid_0 <= 0;
          write_done_0 <= 0;
        end 
      end else begin
        if((read_in_progress_0 == 1) && (read_latency_counter_0 != 0)) begin
          read_latency_counter_0 <= read_latency_counter_0 - 1;
        end 
        if((write_in_progress_0 == 1) && (write_latency_counter_0 != 0)) begin
          write_latency_counter_0 <= write_latency_counter_0 - 1;
        end 
        if((read_in_progress_0 == 1) && (read_latency_counter_0 == 0)) begin
          read_in_progress_0 <= 0;
          address_valid_0 <= 0;
          read_data_0 <= data_memory[address_0];
          read_data_valid_0 <= 1;
        end 
        if((write_in_progress_0 == 1) && (write_latency_counter_0 == 0)) begin
          write_in_progress_0 <= 0;
          address_valid_0 <= 0;
          write_done_0 <= 1;
          data_memory[address_0] <= write_data_0;
        end 
      end
    end
  end


endmodule

