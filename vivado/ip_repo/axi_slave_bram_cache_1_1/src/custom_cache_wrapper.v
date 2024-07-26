

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

  wire request_hit_0;
  wire [64-1:0] be_read_data_0;
  wire be_read_data_valid_0;
  wire be_write_done_0;
  wire be_port_ready_0;
  wire be_flush_done_0;
  wire [13-1:0] be_address_0;
  wire be_address_valid_0;
  wire [64-1:0] be_write_data_0;
  wire be_write_data_valid_0;
  wire be_read_write_select_0;
  wire [8-1:0] be_write_strobe_0;
  wire be_flush_0;
  assign hit_o = request_hit_0;
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
  assign be_flush_done_0 = 1;

  l1_cache
  l1_cache
  (
    .clk_i(clk_i),
    .reset_n_i(reset_n_i),
    .fe_flush_i(flush_i),
    .fe_address_i(l1_address),
    .fe_address_valid_i(l1_address_valid),
    .fe_write_data_i(l1_write_data),
    .fe_write_data_valid_i(l1_write_data_valid),
    .fe_read_write_select_i(l1_read_write_select),
    .fe_write_strobe_i(l1_write_strobe),
    .fe_read_data_o(l1_read_data),
    .fe_read_data_valid_o(l1_read_data_valid),
    .fe_write_done_o(l1_write_done),
    .fe_port_ready_o(l1_port_ready),
    .fe_hit_o(request_hit_0),
    .fe_flush_done_o(flush_done_o),
    .be_read_data_i(be_read_data_0),
    .be_read_data_valid_i(be_read_data_valid_0),
    .be_write_done_i(be_write_done_0),
    .be_port_ready_i(be_port_ready_0),
    .be_flush_done_i(be_flush_done_0),
    .be_address_o(be_address_0),
    .be_address_valid_o(be_address_valid_0),
    .be_write_data_o(be_write_data_0),
    .be_write_data_valid_o(be_write_data_valid_0),
    .be_read_write_select_o(be_read_write_select_0),
    .be_write_strobe_o(be_write_strobe_0),
    .be_flush_o(be_flush_0)
  );


  functional_memory
  memory
  (
    .clk_i(clk_i),
    .reset_n_i(reset_n_i),
    .address_i(be_address_0),
    .address_valid_i(be_address_valid_0),
    .write_data_i(be_write_data_0),
    .write_data_valid_i(be_write_data_valid_0),
    .read_write_select_i(be_read_write_select_0),
    .write_strobe_i(be_write_strobe_0),
    .read_data_o(be_read_data_0),
    .read_data_valid_o(be_read_data_valid_0),
    .write_done_o(be_write_done_0),
    .port_ready_o(be_port_ready_0)
  );


endmodule



module l1_cache
(
  input clk_i,
  input reset_n_i,
  input fe_flush_i,
  input [15-1:0] fe_address_i,
  input fe_address_valid_i,
  input [16-1:0] fe_write_data_i,
  input fe_write_data_valid_i,
  input fe_read_write_select_i,
  input [2-1:0] fe_write_strobe_i,
  output [16-1:0] fe_read_data_o,
  output fe_read_data_valid_o,
  output fe_write_done_o,
  output fe_port_ready_o,
  output fe_hit_o,
  output fe_flush_done_o,
  input [64-1:0] be_read_data_i,
  input be_read_data_valid_i,
  input be_write_done_i,
  input be_port_ready_i,
  input be_flush_done_i,
  output [13-1:0] be_address_o,
  output be_address_valid_o,
  output [64-1:0] be_write_data_o,
  output be_write_data_valid_o,
  output be_read_write_select_o,
  output [8-1:0] be_write_strobe_o,
  output be_flush_o
);

  reg fe_flush_i_reg;
  reg [15-1:0] fe_address_i_reg;
  reg [16-1:0] fe_write_data_i_reg;
  reg fe_read_write_select_i_reg;
  reg [2-1:0] fe_write_strobe_i_reg;
  reg [8-1:0] fe_read_data_o_reg [0:2-1];
  reg fe_read_data_valid_o_reg;
  reg fe_write_done_o_reg;
  reg fe_flush_done_o_reg;
  reg [15-1:0] be_address_o_reg;
  reg be_address_valid_o_reg;
  reg [8-1:0] be_write_data_o_reg [0:2-1];
  reg be_write_data_valid_o_reg;
  reg be_read_write_select_o_reg;
  reg [2-1:0] be_write_strobe_o_reg;
  reg be_flush_o_reg;
  assign fe_read_data_o[7:0] = fe_read_data_o_reg[0];
  assign fe_read_data_o[15:8] = fe_read_data_o_reg[1];
  assign fe_read_data_valid_o = fe_read_data_valid_o_reg;
  assign fe_write_done_o = fe_write_done_o_reg;
  assign fe_flush_done_o = fe_flush_done_o_reg;
  assign be_write_data_valid_o = be_write_data_valid_o_reg;
  assign be_read_write_select_o = be_read_write_select_o_reg;
  assign be_address_o = be_address_o_reg[14:2];
  assign be_address_valid_o = be_address_valid_o_reg;
  assign be_flush_o = be_flush_o_reg;
  assign be_write_data_o[7:0] = (be_address_o_reg[1:0] == 0)? be_write_data_o_reg[0] : 0;
  assign be_write_strobe_o[0] = (be_address_o_reg[1:0] == 0)? be_write_strobe_o_reg[0] : 0;
  assign be_write_data_o[15:8] = (be_address_o_reg[1:0] == 0)? be_write_data_o_reg[1] : 0;
  assign be_write_strobe_o[1] = (be_address_o_reg[1:0] == 0)? be_write_strobe_o_reg[1] : 0;
  assign be_write_data_o[23:16] = (be_address_o_reg[1:0] == 1)? be_write_data_o_reg[0] : 0;
  assign be_write_strobe_o[2] = (be_address_o_reg[1:0] == 1)? be_write_strobe_o_reg[0] : 0;
  assign be_write_data_o[31:24] = (be_address_o_reg[1:0] == 1)? be_write_data_o_reg[1] : 0;
  assign be_write_strobe_o[3] = (be_address_o_reg[1:0] == 1)? be_write_strobe_o_reg[1] : 0;
  assign be_write_data_o[39:32] = (be_address_o_reg[1:0] == 2)? be_write_data_o_reg[0] : 0;
  assign be_write_strobe_o[4] = (be_address_o_reg[1:0] == 2)? be_write_strobe_o_reg[0] : 0;
  assign be_write_data_o[47:40] = (be_address_o_reg[1:0] == 2)? be_write_data_o_reg[1] : 0;
  assign be_write_strobe_o[5] = (be_address_o_reg[1:0] == 2)? be_write_strobe_o_reg[1] : 0;
  assign be_write_data_o[55:48] = (be_address_o_reg[1:0] == 3)? be_write_data_o_reg[0] : 0;
  assign be_write_strobe_o[6] = (be_address_o_reg[1:0] == 3)? be_write_strobe_o_reg[0] : 0;
  assign be_write_data_o[63:56] = (be_address_o_reg[1:0] == 3)? be_write_data_o_reg[1] : 0;
  assign be_write_strobe_o[7] = (be_address_o_reg[1:0] == 3)? be_write_strobe_o_reg[1] : 0;
  reg [4-1:0] state_reg;
  reg [1-1:0] latency_counter;
  reg hit_valid;
  reg [2-1:0] hit_vector;
  reg [4-1:0] send_mem_request_next_state;
  reg [2-1:0] read_block_word_offset;
  assign fe_port_ready_o = state_reg == 0;
  assign fe_hit_o = hit_vector != 0;
  wire [2-1:0] address_word_offset;
  assign address_word_offset = fe_address_i_reg[1:0];
  wire [2-1:0] address_index;
  assign address_index = fe_address_i_reg[3:2];
  wire [11-1:0] address_tag;
  assign address_tag = fe_address_i_reg[14:4];
  reg [16-1:0] resized_be_read_data;
  reg [2-1:0] be_read_data_word_offset;
  wire [2-1:0] be_read_data_total_word_offset;
  assign be_read_data_total_word_offset = be_read_data_word_offset;

  always @(be_read_data_i or be_address_o_reg or be_read_data_total_word_offset) begin
    case(be_read_data_total_word_offset)
      0: begin
        resized_be_read_data = be_read_data_i[15:0];
      end
      1: begin
        resized_be_read_data = be_read_data_i[31:16];
      end
      2: begin
        resized_be_read_data = be_read_data_i[47:32];
      end
      3: begin
        resized_be_read_data = be_read_data_i[63:48];
      end
    endcase
  end

  reg [11-1:0] tag_memory [0:2-1][0:4-1];
  reg [1-1:0] valid_memory [0:2-1][0:4-1];
  reg [8-1:0] data_memory [0:2-1][0:4-1][0:4-1][0:2-1];
  reg [1-1:0] dirty_memory [0:2-1][0:4-1];
  reg [2-1:0] write_back_address_index;
  reg [1-1:0] write_back_block_index;
  reg [11-1:0] write_back_tag;
  reg [2-1:0] write_back_word_offset;
  reg [4-1:0] write_back_next_state;
  wire [4-1:0] flush_encoder_input;
  wire [2-1:0] flush_next_set_index;
  reg [1-1:0] flush_current_block_index;
  assign flush_encoder_input[0] = valid_memory[flush_current_block_index][0] & dirty_memory[flush_current_block_index][0];
  assign flush_encoder_input[1] = valid_memory[flush_current_block_index][1] & dirty_memory[flush_current_block_index][1];
  assign flush_encoder_input[2] = valid_memory[flush_current_block_index][2] & dirty_memory[flush_current_block_index][2];
  assign flush_encoder_input[3] = valid_memory[flush_current_block_index][3] & dirty_memory[flush_current_block_index][3];

  l1_priority_encoder
  l1_flush_priority_encoder
  (
    .unencoded_i(flush_encoder_input),
    .encoded_o(flush_next_set_index)
  );

  wire [1-1:0] hit_index;
  reg [1-1:0] next_block_replacement;
  reg repl_pol_access;
  reg repl_pol_replace;
  reg [1-1:0] repl_pol_block_index_o;
  wire [1-1:0] next_replacements [0:4-1];

  l1_one_hot_to_bin
  l1_hit_one_hot_to_bin
  (
    .one_hot_i(hit_vector),
    .bin_o(hit_index)
  );


  l1_replacement_policy
  l1_replacement_policy
  (
    .reset_n_i(reset_n_i),
    .clk_i(clk_i),
    .access_i(repl_pol_access),
    .replace_i(repl_pol_replace),
    .set_index_i(address_index),
    .block_index_i(repl_pol_block_index_o),
    .next_replacement_0_o(next_replacements[0]),
    .next_replacement_1_o(next_replacements[1]),
    .next_replacement_2_o(next_replacements[2]),
    .next_replacement_3_o(next_replacements[3])
  );


  always @(posedge clk_i) begin
    if(0 & !reset_n_i) begin
      fe_flush_i_reg <= 0;
      fe_address_i_reg <= 0;
      fe_write_data_i_reg <= 0;
      fe_read_write_select_i_reg <= 0;
      fe_write_strobe_i_reg <= 0;
      fe_read_data_o_reg[0] <= 0;
      fe_read_data_o_reg[1] <= 0;
      fe_read_data_valid_o_reg <= 0;
      fe_write_done_o_reg <= 0;
      fe_flush_done_o_reg <= 0;
      be_address_o_reg <= 0;
      be_address_valid_o_reg <= 0;
      be_write_data_o_reg[0] <= 0;
      be_write_data_o_reg[1] <= 0;
      be_write_data_valid_o_reg <= 0;
      be_read_write_select_o_reg <= 0;
      be_write_strobe_o_reg <= 0;
      be_flush_o_reg <= 0;
      state_reg <= 0;
      latency_counter <= 0;
      hit_valid <= 0;
      hit_vector <= 0;
      send_mem_request_next_state <= 0;
      read_block_word_offset <= 0;
      tag_memory[0][0] <= 0;
      valid_memory[0][0] <= 0;
      data_memory[0][0][0][0] <= 0;
      data_memory[0][0][0][1] <= 0;
      data_memory[0][0][1][0] <= 0;
      data_memory[0][0][1][1] <= 0;
      data_memory[0][0][2][0] <= 0;
      data_memory[0][0][2][1] <= 0;
      data_memory[0][0][3][0] <= 0;
      data_memory[0][0][3][1] <= 0;
      tag_memory[0][1] <= 0;
      valid_memory[0][1] <= 0;
      data_memory[0][1][0][0] <= 0;
      data_memory[0][1][0][1] <= 0;
      data_memory[0][1][1][0] <= 0;
      data_memory[0][1][1][1] <= 0;
      data_memory[0][1][2][0] <= 0;
      data_memory[0][1][2][1] <= 0;
      data_memory[0][1][3][0] <= 0;
      data_memory[0][1][3][1] <= 0;
      tag_memory[0][2] <= 0;
      valid_memory[0][2] <= 0;
      data_memory[0][2][0][0] <= 0;
      data_memory[0][2][0][1] <= 0;
      data_memory[0][2][1][0] <= 0;
      data_memory[0][2][1][1] <= 0;
      data_memory[0][2][2][0] <= 0;
      data_memory[0][2][2][1] <= 0;
      data_memory[0][2][3][0] <= 0;
      data_memory[0][2][3][1] <= 0;
      tag_memory[0][3] <= 0;
      valid_memory[0][3] <= 0;
      data_memory[0][3][0][0] <= 0;
      data_memory[0][3][0][1] <= 0;
      data_memory[0][3][1][0] <= 0;
      data_memory[0][3][1][1] <= 0;
      data_memory[0][3][2][0] <= 0;
      data_memory[0][3][2][1] <= 0;
      data_memory[0][3][3][0] <= 0;
      data_memory[0][3][3][1] <= 0;
      tag_memory[1][0] <= 0;
      valid_memory[1][0] <= 0;
      data_memory[1][0][0][0] <= 0;
      data_memory[1][0][0][1] <= 0;
      data_memory[1][0][1][0] <= 0;
      data_memory[1][0][1][1] <= 0;
      data_memory[1][0][2][0] <= 0;
      data_memory[1][0][2][1] <= 0;
      data_memory[1][0][3][0] <= 0;
      data_memory[1][0][3][1] <= 0;
      tag_memory[1][1] <= 0;
      valid_memory[1][1] <= 0;
      data_memory[1][1][0][0] <= 0;
      data_memory[1][1][0][1] <= 0;
      data_memory[1][1][1][0] <= 0;
      data_memory[1][1][1][1] <= 0;
      data_memory[1][1][2][0] <= 0;
      data_memory[1][1][2][1] <= 0;
      data_memory[1][1][3][0] <= 0;
      data_memory[1][1][3][1] <= 0;
      tag_memory[1][2] <= 0;
      valid_memory[1][2] <= 0;
      data_memory[1][2][0][0] <= 0;
      data_memory[1][2][0][1] <= 0;
      data_memory[1][2][1][0] <= 0;
      data_memory[1][2][1][1] <= 0;
      data_memory[1][2][2][0] <= 0;
      data_memory[1][2][2][1] <= 0;
      data_memory[1][2][3][0] <= 0;
      data_memory[1][2][3][1] <= 0;
      tag_memory[1][3] <= 0;
      valid_memory[1][3] <= 0;
      data_memory[1][3][0][0] <= 0;
      data_memory[1][3][0][1] <= 0;
      data_memory[1][3][1][0] <= 0;
      data_memory[1][3][1][1] <= 0;
      data_memory[1][3][2][0] <= 0;
      data_memory[1][3][2][1] <= 0;
      data_memory[1][3][3][0] <= 0;
      data_memory[1][3][3][1] <= 0;
      write_back_address_index <= 0;
      write_back_block_index <= 0;
      write_back_next_state <= 0;
      write_back_tag <= 0;
      write_back_word_offset <= 0;
      flush_current_block_index <= 0;
      dirty_memory[0][0] <= 0;
      dirty_memory[0][1] <= 0;
      dirty_memory[0][2] <= 0;
      dirty_memory[0][3] <= 0;
      dirty_memory[1][0] <= 0;
      dirty_memory[1][1] <= 0;
      dirty_memory[1][2] <= 0;
      dirty_memory[1][3] <= 0;
      next_block_replacement <= 0;
      repl_pol_access <= 0;
      repl_pol_replace <= 0;
      repl_pol_block_index_o <= 0;
      be_read_data_word_offset <= 0;
    end else begin
      if(state_reg == 0) begin
        if(fe_flush_i || fe_flush_i_reg) begin
          state_reg <= 9;
        end else if((fe_read_write_select_i == 0) && (fe_address_valid_i == 1) || (fe_read_write_select_i == 1) && (fe_write_data_valid_i == 1) && (fe_address_valid_i == 1)) begin
          state_reg <= 1;
          fe_read_data_valid_o_reg <= 0;
          fe_write_done_o_reg <= 0;
          fe_address_i_reg <= fe_address_i;
          fe_write_data_i_reg <= fe_write_data_i;
          fe_read_write_select_i_reg <= fe_read_write_select_i;
          fe_write_strobe_i_reg <= fe_write_strobe_i;
          latency_counter <= latency_counter + 1;
          fe_flush_done_o_reg <= 0;
        end 
      end else if(state_reg == 1) begin
        hit_vector[0] <= (tag_memory[0][address_index] == address_tag) && (valid_memory[0][address_index] == 1);
        hit_vector[1] <= (tag_memory[1][address_index] == address_tag) && (valid_memory[1][address_index] == 1);
        hit_valid <= 1;
        latency_counter <= latency_counter + 1;
        next_block_replacement <= next_replacements[address_index];
        state_reg <= 2;
      end else if(state_reg == 2) begin
        latency_counter <= latency_counter + 1;
        if(fe_hit_o) begin
          repl_pol_access <= 1;
          repl_pol_block_index_o <= hit_index;
          if(fe_read_write_select_i_reg) begin
            if(fe_write_strobe_i_reg[0]) begin
              data_memory[hit_index][address_index][address_word_offset][0] <= fe_write_data_i_reg[7:0];
            end 
            if(fe_write_strobe_i_reg[1]) begin
              data_memory[hit_index][address_index][address_word_offset][1] <= fe_write_data_i_reg[15:8];
            end 
            dirty_memory[hit_index][address_index] <= 1;
            state_reg <= 8;
          end else begin
            fe_read_data_o_reg[0] <= data_memory[hit_index][address_index][address_word_offset][0];
            fe_read_data_o_reg[1] <= data_memory[hit_index][address_index][address_word_offset][1];
            state_reg <= 8;
          end
        end else if(0 & fe_read_write_select_i_reg) begin
          be_address_o_reg <= fe_address_i_reg;
          be_write_data_o_reg[0] <= fe_write_data_i_reg[7:0];
          be_write_data_o_reg[1] <= fe_write_data_i_reg[15:8];
          be_write_data_valid_o_reg <= 1;
          be_read_write_select_o_reg <= 1;
          be_write_strobe_o_reg <= fe_write_strobe_i_reg;
          state_reg <= 6;
          send_mem_request_next_state <= 8;
        end else begin
          valid_memory[next_block_replacement][address_index] <= 1;
          tag_memory[next_block_replacement][address_index] <= address_tag;
          dirty_memory[next_block_replacement][address_index] <= fe_read_write_select_i_reg;
          repl_pol_access <= 1;
          repl_pol_replace <= 1;
          repl_pol_block_index_o <= next_block_replacement;
          if(dirty_memory[next_block_replacement][address_index] & (!fe_read_write_select_i_reg | 1)) begin
            state_reg <= 3;
            write_back_address_index <= address_index;
            write_back_block_index <= next_block_replacement;
            write_back_tag <= tag_memory[next_block_replacement][address_index];
            if(!fe_read_write_select_i_reg || 1 || (fe_write_strobe_i_reg != 3)) begin
              write_back_next_state <= 4;
            end else begin
              write_back_next_state <= 5;
            end
          end else if(!fe_read_write_select_i_reg || 1 || (fe_write_strobe_i_reg != 3)) begin
            state_reg <= 4;
          end else begin
            state_reg <= 5;
          end
        end
      end else if(state_reg == 3) begin
        latency_counter <= latency_counter + 1;
        repl_pol_access <= 0;
        repl_pol_replace <= 0;
        be_address_o_reg[1:0] <= write_back_word_offset;
        write_back_word_offset <= write_back_word_offset + 1;
        be_address_o_reg[3:2] <= write_back_address_index;
        be_address_o_reg[14:4] <= write_back_tag;
        be_write_strobe_o_reg <= 3;
        be_read_write_select_o_reg <= 1;
        be_write_data_o_reg[0] <= data_memory[write_back_block_index][write_back_address_index][write_back_word_offset][0];
        be_write_data_o_reg[1] <= data_memory[write_back_block_index][write_back_address_index][write_back_word_offset][1];
        be_write_data_valid_o_reg <= 1;
        state_reg <= 6;
        if(write_back_word_offset == 3) begin
          send_mem_request_next_state <= write_back_next_state;
        end else begin
          send_mem_request_next_state <= 3;
        end
      end else if(state_reg == 6) begin
        if(be_port_ready_i) begin
          latency_counter <= latency_counter + 1;
          be_address_valid_o_reg <= 1;
          state_reg <= 7;
        end 
      end else if(state_reg == 7) begin
        be_address_valid_o_reg <= 0;
        if(!be_address_valid_o_reg & (be_read_write_select_o_reg & be_write_done_i | !be_read_write_select_o_reg & be_read_data_valid_i)) begin
          latency_counter <= latency_counter + 1;
          if(be_read_write_select_o_reg) begin
            state_reg <= send_mem_request_next_state;
          end else begin
            if(be_read_data_word_offset == 3) begin
              state_reg <= send_mem_request_next_state;
              be_read_data_word_offset <= 0;
            end else begin
              be_read_data_word_offset <= be_read_data_word_offset + 1;
            end
            data_memory[next_block_replacement][address_index][be_address_o_reg[1:0] + be_read_data_word_offset][0] <= resized_be_read_data[7:0];
            data_memory[next_block_replacement][address_index][be_address_o_reg[1:0] + be_read_data_word_offset][1] <= resized_be_read_data[15:8];
          end
        end 
      end else if(state_reg == 4) begin
        latency_counter <= latency_counter + 1;
        repl_pol_access <= 0;
        repl_pol_replace <= 0;
        be_address_o_reg[1:0] <= read_block_word_offset;
        be_address_o_reg[14:2] <= fe_address_i_reg[14:2];
        be_read_write_select_o_reg <= 0;
        if(read_block_word_offset == 0) begin
          send_mem_request_next_state <= 5;
        end else begin
          send_mem_request_next_state <= 4;
        end
        if(!(fe_read_write_select_i_reg && (address_word_offset == read_block_word_offset) && (fe_write_strobe_i_reg + 1 == 0) && 0)) begin
          state_reg <= 6;
        end else if(read_block_word_offset + 1 == 0) begin
          state_reg <= 5;
        end 
      end else if(state_reg == 5) begin
        latency_counter <= latency_counter + 1;
        repl_pol_access <= 0;
        repl_pol_replace <= 0;
        if(fe_read_write_select_i_reg) begin
          if(fe_write_strobe_i_reg[0]) begin
            data_memory[next_block_replacement][address_index][address_word_offset][0] <= fe_write_data_i_reg[7:0];
          end 
          if(fe_write_strobe_i_reg[1]) begin
            data_memory[next_block_replacement][address_index][address_word_offset][1] <= fe_write_data_i_reg[15:8];
          end 
          state_reg <= 8;
        end else begin
          fe_read_data_o_reg[0] <= data_memory[next_block_replacement][address_index][address_word_offset][0];
          fe_read_data_o_reg[1] <= data_memory[next_block_replacement][address_index][address_word_offset][1];
          state_reg <= 8;
        end
      end else if(state_reg == 8) begin
        repl_pol_access <= 0;
        repl_pol_replace <= 0;
        if(1 | (latency_counter == -1) && (fe_hit_o == 1) || 1 | (latency_counter == -1) && (fe_hit_o == 0)) begin
          fe_read_data_valid_o_reg <= !fe_read_write_select_i_reg;
          fe_write_done_o_reg <= fe_read_write_select_i_reg;
          hit_valid <= 0;
          latency_counter <= 0;
          if(fe_flush_i_reg) begin
            state_reg <= 9;
          end else begin
            state_reg <= 0;
          end
        end else begin
          latency_counter <= latency_counter + 1;
        end
      end else if(state_reg == 9) begin
        fe_flush_done_o_reg <= 0;
        if(flush_encoder_input == 0) begin
          if(flush_current_block_index == 1) begin
            state_reg <= 11;
            be_flush_o_reg <= 1;
          end else begin
            flush_current_block_index <= flush_current_block_index + 1;
          end
        end else begin
          state_reg <= 10;
        end
      end else if(state_reg == 10) begin
        write_back_address_index <= flush_next_set_index;
        write_back_tag <= tag_memory[flush_current_block_index][flush_next_set_index];
        write_back_block_index <= flush_current_block_index;
        write_back_next_state <= 9;
        state_reg <= 3;
        dirty_memory[flush_current_block_index][flush_next_set_index] <= 0;
      end else if(state_reg == 11) begin
        be_flush_o_reg <= 0;
        if(be_flush_done_i & !be_flush_o_reg) begin
          flush_current_block_index <= 0;
          state_reg <= 0;
          fe_flush_i_reg <= 0;
          latency_counter <= 0;
          fe_flush_done_o_reg <= 1;
        end 
      end 
      if((state_reg != 9) && (state_reg != 10) && (state_reg != 11)) begin
        fe_flush_i_reg <= fe_flush_i_reg | fe_flush_i;
      end 
    end
  end


endmodule



module l1_priority_encoder
(
  input [4-1:0] unencoded_i,
  output reg [2-1:0] encoded_o
);


  always @(unencoded_i) begin
    encoded_o = 0;
    if(unencoded_i[3]) begin
      encoded_o = 3;
    end 
    if(unencoded_i[2]) begin
      encoded_o = 2;
    end 
    if(unencoded_i[1]) begin
      encoded_o = 1;
    end 
    if(unencoded_i[0]) begin
      encoded_o = 0;
    end 
  end


endmodule



module l1_one_hot_to_bin
(
  input [2-1:0] one_hot_i,
  output [1-1:0] bin_o
);

  reg [1-1:0] bin_o_reg;
  reg [1-1:0] tmp_bin;
  assign bin_o = bin_o_reg;

  always @(one_hot_i) begin
    tmp_bin = 0;
    if(one_hot_i[0] == 1) begin
      tmp_bin = tmp_bin | 0;
    end 
    if(one_hot_i[1] == 1) begin
      tmp_bin = tmp_bin | 1;
    end 
    bin_o_reg = tmp_bin;
  end


endmodule



module l1_replacement_policy
(
  input reset_n_i,
  input clk_i,
  input access_i,
  input replace_i,
  input [2-1:0] set_index_i,
  input [1-1:0] block_index_i,
  output [1-1:0] next_replacement_0_o,
  output [1-1:0] next_replacement_1_o,
  output [1-1:0] next_replacement_2_o,
  output [1-1:0] next_replacement_3_o
);

  reg [1-1:0] next_replacement_o_reg [0:4-1];
  assign next_replacement_0_o = next_replacement_o_reg[0];
  assign next_replacement_1_o = next_replacement_o_reg[1];
  assign next_replacement_2_o = next_replacement_o_reg[2];
  assign next_replacement_3_o = next_replacement_o_reg[3];
  reg [1-1:0] plru_bits [0:4-1];
  reg [2-1:0] tmp_repl;

  always @(posedge clk_i) begin
    if(0 & !reset_n_i) begin
      plru_bits[0] <= 0;
      next_replacement_o_reg[0] <= 1;
      plru_bits[1] <= 0;
      next_replacement_o_reg[1] <= 1;
      plru_bits[2] <= 0;
      next_replacement_o_reg[2] <= 1;
      plru_bits[3] <= 0;
      next_replacement_o_reg[3] <= 1;
    end else begin
      if(access_i) begin
        plru_bits[set_index_i][(block_index_i >> 1) + 0] = block_index_i[0];
        tmp_repl = 0;
        if(plru_bits[set_index_i][tmp_repl[0:0]]) begin
          tmp_repl = 2 * tmp_repl + 1;
        end else begin
          tmp_repl = 2 * tmp_repl + 2;
        end
        tmp_repl = tmp_repl - 2 + 1;
        next_replacement_o_reg[set_index_i] = tmp_repl[0:0];
      end 
    end
  end


endmodule



module functional_memory
(
  input clk_i,
  input reset_n_i,
  input [13-1:0] address_i,
  input address_valid_i,
  input [64-1:0] write_data_i,
  input write_data_valid_i,
  input read_write_select_i,
  input [8-1:0] write_strobe_i,
  output [64-1:0] read_data_o,
  output read_data_valid_o,
  output write_done_o,
  output port_ready_o
);

  reg [13-1:0] address;
  reg [64-1:0] write_data;
  reg read_write_select;
  reg [8-1:0] write_strobe;
  reg [8-1:0] read_data [0:8-1];
  reg read_data_valid;
  reg write_done;
  reg [6-1:0] latency_counter;
  reg [8-1:0] data_memory_0 [0:8192-1];
  reg [8-1:0] data_memory_1 [0:8192-1];
  reg [8-1:0] data_memory_2 [0:8192-1];
  reg [8-1:0] data_memory_3 [0:8192-1];
  reg [8-1:0] data_memory_4 [0:8192-1];
  reg [8-1:0] data_memory_5 [0:8192-1];
  reg [8-1:0] data_memory_6 [0:8192-1];
  reg [8-1:0] data_memory_7 [0:8192-1];
  reg processing_request;
  assign read_data_o[7:0] = read_data[0];
  assign read_data_o[15:8] = read_data[1];
  assign read_data_o[23:16] = read_data[2];
  assign read_data_o[31:24] = read_data[3];
  assign read_data_o[39:32] = read_data[4];
  assign read_data_o[47:40] = read_data[5];
  assign read_data_o[55:48] = read_data[6];
  assign read_data_o[63:56] = read_data[7];
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
      read_data[2] <= 0;
      read_data[3] <= 0;
      read_data[4] <= 0;
      read_data[5] <= 0;
      read_data[6] <= 0;
      read_data[7] <= 0;
      read_data_valid <= 0;
      write_done <= 0;
      processing_request <= 0;
      write_strobe <= 0;
    end else begin
      if(!processing_request) begin
        if((address_valid_i == 1) && (read_write_select_i == 0) | (read_write_select_i == 1) & (write_data_valid_i == 1) && 1 && 1) begin
          address <= address_i;
          write_data <= write_data_i;
          write_strobe <= write_strobe_i;
          read_write_select <= read_write_select_i;
          read_data_valid <= 0;
          write_done <= 0;
          processing_request <= 1;
          latency_counter <= latency_counter + 1;
        end 
      end else if(!((read_write_select == 0) & (latency_counter == 59) | (read_write_select == 1) & (latency_counter == 59))) begin
        latency_counter <= latency_counter + 1;
      end else begin
        processing_request <= 0;
        latency_counter <= 0;
        if(read_write_select == 0) begin
          read_data[0] <= data_memory_0[address - 0];
          read_data[1] <= data_memory_1[address - 0];
          read_data[2] <= data_memory_2[address - 0];
          read_data[3] <= data_memory_3[address - 0];
          read_data[4] <= data_memory_4[address - 0];
          read_data[5] <= data_memory_5[address - 0];
          read_data[6] <= data_memory_6[address - 0];
          read_data[7] <= data_memory_7[address - 0];
          read_data_valid <= 1;
        end else begin
          write_done <= 1;
          if(write_strobe[0]) begin
            data_memory_0[address - 0] <= write_data[7:0];
          end 
          if(write_strobe[1]) begin
            data_memory_1[address - 0] <= write_data[15:8];
          end 
          if(write_strobe[2]) begin
            data_memory_2[address - 0] <= write_data[23:16];
          end 
          if(write_strobe[3]) begin
            data_memory_3[address - 0] <= write_data[31:24];
          end 
          if(write_strobe[4]) begin
            data_memory_4[address - 0] <= write_data[39:32];
          end 
          if(write_strobe[5]) begin
            data_memory_5[address - 0] <= write_data[47:40];
          end 
          if(write_strobe[6]) begin
            data_memory_6[address - 0] <= write_data[55:48];
          end 
          if(write_strobe[7]) begin
            data_memory_7[address - 0] <= write_data[63:56];
          end 
        end
      end
    end
  end


endmodule

