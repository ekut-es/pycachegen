

module cache_wrapper
(
  input clk_i,
  input reset_n_i,
  input flush_i,
  output hit_o,
  input [8-1:0] address_0_i,
  input address_valid_0_i,
  input [16-1:0] write_data_0_i,
  input write_data_valid_0_i,
  input read_write_select_0_i,
  output [16-1:0] read_data_0_o,
  output read_data_valid_0_o,
  output write_done_0_o,
  output port_ready_0_o
);

  wire request_hit_0;
  wire [16-1:0] be_read_data_0;
  wire be_read_data_valid_0;
  wire be_write_done_0;
  wire be_port_ready_0;
  wire [8-1:0] be_address_0;
  wire be_address_valid_0;
  wire [16-1:0] be_write_data_0;
  wire be_write_data_valid_0;
  wire be_read_write_select_0;
  assign hit_o = request_hit_0;

  l1_cache
  l1_cache
  (
    .clk_i(clk_i),
    .reset_n_i(reset_n_i),
    .flush_i(flush_i),
    .fe_address_i(address_0_i),
    .fe_address_valid_i(address_valid_0_i),
    .fe_write_data_i(write_data_0_i),
    .fe_write_data_valid_i(write_data_valid_0_i),
    .fe_read_write_select_i(read_write_select_0_i),
    .fe_read_data_o(read_data_0_o),
    .fe_read_data_valid_o(read_data_valid_0_o),
    .fe_write_done_o(write_done_0_o),
    .fe_port_ready_o(port_ready_0_o),
    .fe_hit_o(request_hit_0),
    .be_read_data_i(be_read_data_0),
    .be_read_data_valid_i(be_read_data_valid_0),
    .be_write_done_i(be_write_done_0),
    .be_port_ready_i(be_port_ready_0),
    .be_address_o(be_address_0),
    .be_address_valid_o(be_address_valid_0),
    .be_write_data_o(be_write_data_0),
    .be_write_data_valid_o(be_write_data_valid_0),
    .be_read_write_select_o(be_read_write_select_0)
  );

  localparam memory_DATA_WIDTH = 16;
  localparam memory_ADDRESS_WIDTH = 8;

  functional_memory
  memory
  (
    .clk_i(clk_i),
    .reset_n_i(reset_n_i),
    .address_0_i(be_address_0),
    .address_valid_0_i(be_address_valid_0),
    .write_data_0_i(be_write_data_0),
    .write_data_valid_0_i(be_write_data_valid_0),
    .read_write_select_0_i(be_read_write_select_0),
    .read_data_0_o(be_read_data_0),
    .read_data_valid_0_o(be_read_data_valid_0),
    .write_done_0_o(be_write_done_0),
    .port_ready_0_o(be_port_ready_0)
  );


endmodule



module l1_cache
(
  input clk_i,
  input reset_n_i,
  input flush_i,
  input [8-1:0] fe_address_i,
  input fe_address_valid_i,
  input [16-1:0] fe_write_data_i,
  input fe_write_data_valid_i,
  input fe_read_write_select_i,
  output [16-1:0] fe_read_data_o,
  output fe_read_data_valid_o,
  output fe_write_done_o,
  output fe_port_ready_o,
  output fe_hit_o,
  input [16-1:0] be_read_data_i,
  input be_read_data_valid_i,
  input be_write_done_i,
  input be_port_ready_i,
  output [8-1:0] be_address_o,
  output be_address_valid_o,
  output [16-1:0] be_write_data_o,
  output be_write_data_valid_o,
  output be_read_write_select_o
);

  reg flush_i_reg;
  reg [8-1:0] fe_address_i_reg;
  reg [16-1:0] fe_write_data_i_reg;
  reg fe_read_write_select_i_reg;
  reg [16-1:0] fe_read_data_o_reg;
  reg fe_read_data_valid_o_reg;
  reg fe_write_done_o_reg;
  reg [8-1:0] be_address_o_reg;
  reg be_address_valid_o_reg;
  reg [16-1:0] be_write_data_o_reg;
  reg be_write_data_valid_o_reg;
  reg be_read_write_select_o_reg;
  assign fe_read_data_o = fe_read_data_o_reg;
  assign fe_read_data_valid_o = fe_read_data_valid_o_reg;
  assign fe_write_done_o = fe_write_done_o_reg;
  assign be_address_o = be_address_o_reg;
  assign be_address_valid_o = be_address_valid_o_reg;
  assign be_write_data_o = be_write_data_o_reg;
  assign be_write_data_valid_o = be_write_data_valid_o_reg;
  assign be_read_write_select_o = be_read_write_select_o_reg;
  reg [4-1:0] state_reg;
  reg [3-1:0] latency_counter;
  reg hit_valid;
  reg [1-1:0] hit_vector;
  reg [4-1:0] send_mem_request_next_state;
  reg [1-1:0] read_block_word_offset;
  assign fe_port_ready_o = state_reg == 0;
  assign fe_hit_o = hit_vector != 0;
  wire [1-1:0] address_word_offset;
  wire [2-1:0] address_index;
  wire [6-1:0] address_tag;
  assign address_word_offset = 0;
  assign address_index = fe_address_i_reg[1:0];
  assign address_tag = fe_address_i_reg[7:2];
  reg [6-1:0] tag_memory [0:1-1][0:4-1];
  reg [1-1:0] valid_memory [0:1-1][0:4-1];
  reg [16-1:0] data_memory [0:1-1][0:4-1][0:1-1];
  wire hit_index;
  wire next_block_replacement;
  assign hit_index = 0;
  assign next_block_replacement = 0;

  always @(negedge reset_n_i or posedge clk_i) begin
    if(!reset_n_i) begin
      fe_address_i_reg <= 0;
      fe_write_data_i_reg <= 0;
      fe_read_write_select_i_reg <= 0;
      fe_read_data_o_reg <= 0;
      fe_read_data_valid_o_reg <= 0;
      fe_write_done_o_reg <= 0;
      be_address_o_reg <= 0;
      be_address_valid_o_reg <= 0;
      be_write_data_o_reg <= 0;
      be_write_data_valid_o_reg <= 0;
      be_read_write_select_o_reg <= 0;
      state_reg <= 0;
      latency_counter <= 0;
      hit_valid <= 0;
      hit_vector <= 0;
      send_mem_request_next_state <= 0;
      read_block_word_offset <= 0;
      tag_memory[0][0] <= 0;
      valid_memory[0][0] <= 0;
      data_memory[0][0][0] <= 0;
      tag_memory[0][1] <= 0;
      valid_memory[0][1] <= 0;
      data_memory[0][1][0] <= 0;
      tag_memory[0][2] <= 0;
      valid_memory[0][2] <= 0;
      data_memory[0][2][0] <= 0;
      tag_memory[0][3] <= 0;
      valid_memory[0][3] <= 0;
      data_memory[0][3][0] <= 0;
    end else begin
      if(state_reg == 0) begin
        flush_i_reg <= flush_i_reg | flush_i;
        if(0 && (flush_i || flush_i_reg)) begin
          state_reg <= 9;
        end else if((fe_read_write_select_i == 0) && (fe_address_valid_i == 1) || (fe_read_write_select_i == 1) && (fe_write_data_valid_i == 1) && (fe_address_valid_i == 1)) begin
          state_reg <= 1;
          fe_read_data_valid_o_reg <= 0;
          fe_write_done_o_reg <= 0;
          fe_address_i_reg <= fe_address_i;
          fe_write_data_i_reg <= fe_write_data_i;
          fe_read_write_select_i_reg <= fe_read_write_select_i;
          latency_counter <= latency_counter + 1;
        end 
      end else if(state_reg == 1) begin
        hit_vector[0] <= (tag_memory[0][address_index] == address_tag) && (valid_memory[0][address_index] == 1);
        hit_valid <= 1;
        latency_counter <= latency_counter + 1;
        state_reg <= 2;
      end else if(state_reg == 2) begin
        latency_counter <= latency_counter + 1;
        if(fe_hit_o) begin
          if(fe_read_write_select_i_reg) begin
            data_memory[hit_index][address_index][address_word_offset] <= fe_write_data_i_reg;
            be_address_o_reg <= fe_address_i_reg;
            be_write_data_valid_o_reg <= 1;
            be_write_data_o_reg <= fe_write_data_i_reg;
            be_read_write_select_o_reg <= 1;
            state_reg <= 6;
            send_mem_request_next_state <= 8;
          end else begin
            fe_read_data_o_reg <= data_memory[hit_index][address_index][address_word_offset];
            state_reg <= 8;
          end
        end else if(1 & fe_read_write_select_i_reg) begin
          be_address_o_reg <= fe_address_i_reg;
          be_write_data_o_reg <= fe_write_data_i_reg;
          be_write_data_valid_o_reg <= 1;
          be_read_write_select_o_reg <= 1;
          state_reg <= 6;
          send_mem_request_next_state <= 8;
        end else begin
          valid_memory[next_block_replacement][address_index] <= 1;
          tag_memory[next_block_replacement][address_index] <= address_tag;
          if(0) begin
          end else if(!fe_read_write_select_i_reg | 0) begin
            state_reg <= 4;
          end else begin
            state_reg <= 5;
          end
        end
      end else if(state_reg == 3) begin
      end else if(state_reg == 6) begin
        if(be_port_ready_i) begin
          latency_counter <= latency_counter + 1;
          be_address_valid_o_reg <= 1;
          state_reg <= 7;
        end 
      end else if(state_reg == 7) begin
        be_address_valid_o_reg <= 0;
        if(!be_address_valid_o_reg & be_port_ready_i) begin
          latency_counter <= latency_counter + 1;
          state_reg <= send_mem_request_next_state;
          if(!be_read_write_select_o_reg) begin
            data_memory[next_block_replacement][address_index][0] <= be_read_data_i;
          end 
        end 
      end else if(state_reg == 4) begin
        latency_counter <= latency_counter + 1;
        be_address_o_reg <= fe_address_i_reg;
        be_address_o_reg[7:0] <= fe_address_i_reg[7:0];
        be_read_write_select_o_reg <= 0;
        if(read_block_word_offset == 0) begin
          send_mem_request_next_state <= 5;
        end else begin
          send_mem_request_next_state <= 4;
        end
        if(!(fe_read_write_select_i_reg & (address_word_offset == read_block_word_offset))) begin
          state_reg <= 6;
        end else if(read_block_word_offset + 1 == 0) begin
          state_reg <= 5;
        end 
      end else if(state_reg == 5) begin
        latency_counter <= latency_counter + 1;
        if(fe_read_write_select_i_reg) begin
          data_memory[next_block_replacement][address_index][address_word_offset] <= fe_write_data_i_reg;
          be_address_o_reg <= fe_address_i_reg;
          be_write_data_o_reg <= fe_write_data_i_reg;
          be_read_write_select_o_reg <= 1;
          be_write_data_valid_o_reg <= 1;
          send_mem_request_next_state <= 8;
          state_reg <= 6;
        end else begin
          fe_read_data_o_reg <= data_memory[next_block_replacement][address_index][address_word_offset];
          state_reg <= 8;
        end
      end else if(state_reg == 8) begin
        if((latency_counter == 5) && (fe_hit_o == 1) || (latency_counter == 7) && (fe_hit_o == 0)) begin
          fe_read_data_valid_o_reg <= !fe_read_write_select_i_reg;
          fe_write_done_o_reg <= fe_read_write_select_i_reg;
          hit_valid <= 0;
          latency_counter <= 0;
          if(flush_i_reg) begin
            state_reg <= 9;
          end else begin
            state_reg <= 0;
          end
        end else begin
          latency_counter <= latency_counter + 1;
        end
      end else begin
      end
    end
    if((state_reg != 0) && (state_reg != 9) && (state_reg != 10)) begin
      flush_i_reg <= flush_i_reg | flush_i;
    end 
  end


endmodule



module functional_memory #
(
  parameter READ_LATENCY = 9,
  parameter WRITE_LATENCY = 14,
  parameter DATA_WIDTH = 16,
  parameter ADDRESS_WIDTH = 8
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
  reg port_ready_0;
  reg [DATA_WIDTH-1:0] data_memory [0:256-1];
  reg read_in_progress_0;
  reg write_in_progress_0;
  assign port_ready_0 = (read_in_progress_0 == 0) && (write_in_progress_0 == 0);
  assign read_data_0_o = read_data_0;
  assign read_data_valid_0_o = read_data_valid_0;
  assign write_done_0_o = write_done_0;
  assign port_ready_0_o = port_ready_0;

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
    end else begin
      if(port_ready_0 == 1) begin
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
    if(write_done_0 == 1) begin
      write_done_0 <= 0;
    end 
  end


endmodule

