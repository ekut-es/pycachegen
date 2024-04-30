`timescale 1ns / 1ps

`include "iob_utils.vh"
`include "iob_cache_conf.vh"
`include "iob_cache_swreg_def.vh"

module iob_cache_swreg_gen #(

   parameter ADDR_W        = `IOB_CACHE_ADDR_W,
   parameter DATA_W        = `IOB_CACHE_DATA_W,
   parameter FE_ADDR_W     = `IOB_CACHE_FE_ADDR_W,
   parameter FE_DATA_W     = `IOB_CACHE_FE_DATA_W,
   parameter BE_ADDR_W     = `IOB_CACHE_BE_ADDR_W,
   parameter BE_DATA_W     = `IOB_CACHE_BE_DATA_W,
   parameter NWAYS_W       = `IOB_CACHE_NWAYS_W,
   parameter NLINES_W      = `IOB_CACHE_NLINES_W,
   parameter WORD_OFFSET_W = `IOB_CACHE_WORD_OFFSET_W,
   parameter WTBUF_DEPTH_W = `IOB_CACHE_WTBUF_DEPTH_W,
   parameter REP_POLICY    = `IOB_CACHE_REP_POLICY,
   parameter WRITE_POL     = `IOB_CACHE_WRITE_POL,
   parameter USE_CTRL      = `IOB_CACHE_USE_CTRL,
   parameter USE_CTRL_CNT  = `IOB_CACHE_USE_CTRL_CNT
) (

   input  [1-1:0] WTB_EMPTY_rdata_i,
   input          WTB_EMPTY_rvalid_i,
   output         WTB_EMPTY_ren_o,
   input          WTB_EMPTY_rready_i,

   input  [1-1:0] WTB_FULL_rdata_i,
   input          WTB_FULL_rvalid_i,
   output         WTB_FULL_ren_o,
   input          WTB_FULL_rready_i,

   input  [32-1:0] RW_HIT_rdata_i,
   input           RW_HIT_rvalid_i,
   output          RW_HIT_ren_o,
   input           RW_HIT_rready_i,

   input  [32-1:0] RW_MISS_rdata_i,
   input           RW_MISS_rvalid_i,
   output          RW_MISS_ren_o,
   input           RW_MISS_rready_i,

   input  [32-1:0] READ_HIT_rdata_i,
   input           READ_HIT_rvalid_i,
   output          READ_HIT_ren_o,
   input           READ_HIT_rready_i,

   input  [32-1:0] READ_MISS_rdata_i,
   input           READ_MISS_rvalid_i,
   output          READ_MISS_ren_o,
   input           READ_MISS_rready_i,

   input  [32-1:0] WRITE_HIT_rdata_i,
   input           WRITE_HIT_rvalid_i,
   output          WRITE_HIT_ren_o,
   input           WRITE_HIT_rready_i,

   input  [        32-1:0] WRITE_MISS_rdata_i,
   input                   WRITE_MISS_rvalid_i,
   output                  WRITE_MISS_ren_o,
   input                   WRITE_MISS_rready_i,
   output [         1-1:0] RST_CNTRS_wdata_o,
   output                  RST_CNTRS_wen_o,
   input                   RST_CNTRS_wready_i,
   output [         1-1:0] INVALIDATE_wdata_o,
   output                  INVALIDATE_wen_o,
   input                   INVALIDATE_wready_i,
   input  [         1-1:0] iob_valid_i,
   input  [    ADDR_W-1:0] iob_addr_i,
   input  [    DATA_W-1:0] iob_wdata_i,
   input  [(DATA_W/8)-1:0] iob_wstrb_i,
   output [         1-1:0] iob_rvalid_o,
   output [    DATA_W-1:0] iob_rdata_o,
   output [         1-1:0] iob_ready_o,
   //General Interface Signals
   input                   clk_i,
   input                   cke_i,
   input                   arst_i
);


   localparam WSTRB_W = DATA_W / 8;

   //FSM states
   localparam WAIT_REQ = 1'd0;
   localparam WAIT_RVALID = 1'd1;

   wire state;
   reg  state_nxt;

   //FSM register
   iob_reg #(
      .DATA_W (1),
      .RST_VAL(WAIT_REQ)
   ) fsm_reg_inst (
      .clk_i (clk_i),
      .cke_i (cke_i),
      .arst_i(arst_i),
      .data_i(state_nxt),
      .data_o(state)
   );

   //write address
   wire [($clog2(WSTRB_W)+1)-1:0] byte_offset;
   iob_ctls #(
      .W     (WSTRB_W),
      .MODE  (0),
      .SYMBOL(0)
   ) bo_inst (
      .data_i (iob_wstrb_i),
      .count_o(byte_offset)
   );
   wire [ADDR_W-1:0] waddr;
   assign waddr = `IOB_WORD_ADDR(iob_addr_i) + byte_offset;


   //NAME: RST_CNTRS;
   //TYPE: W; WIDTH: 1; RST_VAL: 0; ADDR: 28; SPACE (bytes): 1 (max); AUTO: False

   wire [1-1:0] RST_CNTRS_wdata;
   assign RST_CNTRS_wdata = iob_wdata_i[0+:1];
   wire RST_CNTRS_addressed;
   assign RST_CNTRS_addressed = (waddr >= 28) && (waddr < 29);
   assign RST_CNTRS_wen_o = (RST_CNTRS_addressed & (iob_valid_i & iob_ready_o))? |iob_wstrb_i: 1'b0;
   assign RST_CNTRS_wdata_o = RST_CNTRS_wdata;


   //NAME: INVALIDATE;
   //TYPE: W; WIDTH: 1; RST_VAL: 0; ADDR: 32; SPACE (bytes): 1 (max); AUTO: False

   wire [1-1:0] INVALIDATE_wdata;
   assign INVALIDATE_wdata = iob_wdata_i[0+:1];
   wire INVALIDATE_addressed;
   assign INVALIDATE_addressed = (waddr >= 32) && (waddr < 33);
   assign INVALIDATE_wen_o = (INVALIDATE_addressed & (iob_valid_i & iob_ready_o))? |iob_wstrb_i: 1'b0;
   assign INVALIDATE_wdata_o = INVALIDATE_wdata;


   //NAME: WTB_EMPTY;
   //TYPE: R; WIDTH: 1; RST_VAL: 0; ADDR: 0; SPACE (bytes): 1 (max); AUTO: False

   wire WTB_EMPTY_addressed;
   assign WTB_EMPTY_addressed = (iob_addr_i >= 0) && (iob_addr_i < (0 + (2 ** (0))));
   assign WTB_EMPTY_ren_o     = WTB_EMPTY_addressed & (iob_valid_i & iob_ready_o) & (~|iob_wstrb_i);


   //NAME: WTB_FULL;
   //TYPE: R; WIDTH: 1; RST_VAL: 0; ADDR: 1; SPACE (bytes): 1 (max); AUTO: False

   wire WTB_FULL_addressed;
   assign WTB_FULL_addressed = (iob_addr_i >= 1) && (iob_addr_i < (1 + (2 ** (0))));
   assign WTB_FULL_ren_o     = WTB_FULL_addressed & (iob_valid_i & iob_ready_o) & (~|iob_wstrb_i);


   //NAME: RW_HIT;
   //TYPE: R; WIDTH: 32; RST_VAL: 0; ADDR: 4; SPACE (bytes): 4 (max); AUTO: False

   wire RW_HIT_addressed;
   assign RW_HIT_addressed = (iob_addr_i >= 4) && (iob_addr_i < (4 + (2 ** (2))));
   assign RW_HIT_ren_o     = RW_HIT_addressed & (iob_valid_i & iob_ready_o) & (~|iob_wstrb_i);


   //NAME: RW_MISS;
   //TYPE: R; WIDTH: 32; RST_VAL: 0; ADDR: 8; SPACE (bytes): 4 (max); AUTO: False

   wire RW_MISS_addressed;
   assign RW_MISS_addressed = (iob_addr_i >= 8) && (iob_addr_i < (8 + (2 ** (2))));
   assign RW_MISS_ren_o     = RW_MISS_addressed & (iob_valid_i & iob_ready_o) & (~|iob_wstrb_i);


   //NAME: READ_HIT;
   //TYPE: R; WIDTH: 32; RST_VAL: 0; ADDR: 12; SPACE (bytes): 4 (max); AUTO: False

   wire READ_HIT_addressed;
   assign READ_HIT_addressed = (iob_addr_i >= 12) && (iob_addr_i < (12 + (2 ** (2))));
   assign READ_HIT_ren_o     = READ_HIT_addressed & (iob_valid_i & iob_ready_o) & (~|iob_wstrb_i);


   //NAME: READ_MISS;
   //TYPE: R; WIDTH: 32; RST_VAL: 0; ADDR: 16; SPACE (bytes): 4 (max); AUTO: False

   wire READ_MISS_addressed;
   assign READ_MISS_addressed = (iob_addr_i >= 16) && (iob_addr_i < (16 + (2 ** (2))));
   assign READ_MISS_ren_o     = READ_MISS_addressed & (iob_valid_i & iob_ready_o) & (~|iob_wstrb_i);


   //NAME: WRITE_HIT;
   //TYPE: R; WIDTH: 32; RST_VAL: 0; ADDR: 20; SPACE (bytes): 4 (max); AUTO: False

   wire WRITE_HIT_addressed;
   assign WRITE_HIT_addressed = (iob_addr_i >= 20) && (iob_addr_i < (20 + (2 ** (2))));
   assign WRITE_HIT_ren_o     = WRITE_HIT_addressed & (iob_valid_i & iob_ready_o) & (~|iob_wstrb_i);


   //NAME: WRITE_MISS;
   //TYPE: R; WIDTH: 32; RST_VAL: 0; ADDR: 24; SPACE (bytes): 4 (max); AUTO: False

   wire WRITE_MISS_addressed;
   assign WRITE_MISS_addressed = (iob_addr_i >= 24) && (iob_addr_i < (24 + (2 ** (2))));
   assign WRITE_MISS_ren_o = WRITE_MISS_addressed & (iob_valid_i & iob_ready_o) & (~|iob_wstrb_i);


   //NAME: VERSION;
   //TYPE: R; WIDTH: 16; RST_VAL: 0010; ADDR: 34; SPACE (bytes): 2 (max); AUTO: True



   //RESPONSE SWITCH


   reg          rvalid_nxt;
   reg          rvalid_int;
   reg [32-1:0] rdata_nxt;
   reg          wready_int;
   reg          rready_int;

   reg          iob_addr_i_0_0;
   reg          iob_addr_i_0_8;
   reg          iob_addr_i_4_0;
   reg          iob_addr_i_8_0;
   reg          iob_addr_i_12_0;
   reg          iob_addr_i_16_0;
   reg          iob_addr_i_20_0;
   reg          iob_addr_i_24_0;
   reg          iob_addr_i_32_16;


   reg          ready_nxt;

   always @* begin
      rdata_nxt      = 32'd0;
      rvalid_int     = (iob_valid_i & iob_ready_o) & (~(|iob_wstrb_i));
      rready_int     = 1'b1;
      wready_int     = 1'b1;

      iob_addr_i_0_0 = (`IOB_WORD_ADDR(iob_addr_i) == 0);
      if (iob_addr_i_0_0) begin
         rdata_nxt[0+:8] = WTB_EMPTY_rdata_i | 8'd0;
         rvalid_int      = WTB_EMPTY_rvalid_i;
         rready_int      = WTB_EMPTY_rready_i;
      end

      iob_addr_i_0_8 = (`IOB_WORD_ADDR(iob_addr_i) == 0);
      if (iob_addr_i_0_8) begin
         rdata_nxt[8+:8] = WTB_FULL_rdata_i | 8'd0;
         rvalid_int      = WTB_FULL_rvalid_i;
         rready_int      = WTB_FULL_rready_i;
      end

      iob_addr_i_4_0 = ((`IOB_WORD_ADDR(iob_addr_i) >= 4) && (`IOB_WORD_ADDR(iob_addr_i) < 8));
      if (iob_addr_i_4_0) begin
         rdata_nxt[0+:32] = RW_HIT_rdata_i | 32'd0;
         rvalid_int       = RW_HIT_rvalid_i;
         rready_int       = RW_HIT_rready_i;
      end

      iob_addr_i_8_0 = ((`IOB_WORD_ADDR(iob_addr_i) >= 8) && (`IOB_WORD_ADDR(iob_addr_i) < 12));
      if (iob_addr_i_8_0) begin
         rdata_nxt[0+:32] = RW_MISS_rdata_i | 32'd0;
         rvalid_int       = RW_MISS_rvalid_i;
         rready_int       = RW_MISS_rready_i;
      end

      iob_addr_i_12_0 = ((`IOB_WORD_ADDR(iob_addr_i) >= 12) && (`IOB_WORD_ADDR(iob_addr_i) < 16));
      if (iob_addr_i_12_0) begin
         rdata_nxt[0+:32] = READ_HIT_rdata_i | 32'd0;
         rvalid_int       = READ_HIT_rvalid_i;
         rready_int       = READ_HIT_rready_i;
      end

      iob_addr_i_16_0 = ((`IOB_WORD_ADDR(iob_addr_i) >= 16) && (`IOB_WORD_ADDR(iob_addr_i) < 20));
      if (iob_addr_i_16_0) begin
         rdata_nxt[0+:32] = READ_MISS_rdata_i | 32'd0;
         rvalid_int       = READ_MISS_rvalid_i;
         rready_int       = READ_MISS_rready_i;
      end

      iob_addr_i_20_0 = ((`IOB_WORD_ADDR(iob_addr_i) >= 20) && (`IOB_WORD_ADDR(iob_addr_i) < 24));
      if (iob_addr_i_20_0) begin
         rdata_nxt[0+:32] = WRITE_HIT_rdata_i | 32'd0;
         rvalid_int       = WRITE_HIT_rvalid_i;
         rready_int       = WRITE_HIT_rready_i;
      end

      iob_addr_i_24_0 = ((`IOB_WORD_ADDR(iob_addr_i) >= 24) && (`IOB_WORD_ADDR(iob_addr_i) < 28));
      if (iob_addr_i_24_0) begin
         rdata_nxt[0+:32] = WRITE_MISS_rdata_i | 32'd0;
         rvalid_int       = WRITE_MISS_rvalid_i;
         rready_int       = WRITE_MISS_rready_i;
      end

      iob_addr_i_32_16 = ((`IOB_WORD_ADDR(iob_addr_i) >= 32) && (`IOB_WORD_ADDR(iob_addr_i) < 36));
      if (iob_addr_i_32_16) begin
         rdata_nxt[16+:16] = 16'h0010 | 16'd0;
      end

      if ((waddr >= 28) && (waddr < 29)) begin
         wready_int = RST_CNTRS_wready_i;
      end
      if ((waddr >= 32) && (waddr < 33)) begin
         wready_int = INVALIDATE_wready_i;
      end


      // ######  FSM  #############

      //FSM default values
      ready_nxt  = 1'b0;
      rvalid_nxt = 1'b0;
      state_nxt  = state;

      //FSM state machine
      case (state)
         WAIT_REQ: begin
            if (iob_valid_i & (!iob_ready_o)) begin  // Wait for a valid request
               ready_nxt = |iob_wstrb_i ? wready_int : rready_int;
               // If is read and ready, go to WAIT_RVALID
               if (ready_nxt && (!(|iob_wstrb_i))) begin
                  state_nxt = WAIT_RVALID;
               end
            end
         end

         default: begin  // WAIT_RVALID
            if (rvalid_int) begin
               rvalid_nxt = 1'b1;
               state_nxt  = WAIT_REQ;
            end
         end
      endcase

   end  //always @*

   //rdata output
   iob_reg #(
      .DATA_W (DATA_W),
      .RST_VAL({DATA_W{1'd0}})
   ) rdata_reg_inst (
      .clk_i (clk_i),
      .cke_i (cke_i),
      .arst_i(arst_i),
      .data_i(rdata_nxt),
      .data_o(iob_rdata_o)
   );

   //rvalid output
   iob_reg #(
      .DATA_W (1),
      .RST_VAL(1'd0)
   ) rvalid_reg_inst (
      .clk_i (clk_i),
      .cke_i (cke_i),
      .arst_i(arst_i),
      .data_i(rvalid_nxt),
      .data_o(iob_rvalid_o)
   );

   //ready output
   iob_reg #(
      .DATA_W (1),
      .RST_VAL(1'd0)
   ) ready_reg_inst (
      .clk_i (clk_i),
      .cke_i (cke_i),
      .arst_i(arst_i),
      .data_i(ready_nxt),
      .data_o(iob_ready_o)
   );

endmodule
