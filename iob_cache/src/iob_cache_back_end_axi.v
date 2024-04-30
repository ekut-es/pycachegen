`timescale 1ns / 1ps

`include "iob_cache_swreg_def.vh"
`include "iob_cache_conf.vh"

module iob_cache_back_end_axi #(
   parameter                FE_ADDR_W     = `IOB_CACHE_ADDR_W,
   parameter                FE_DATA_W     = `IOB_CACHE_DATA_W,
   parameter                BE_ADDR_W     = `IOB_CACHE_BE_ADDR_W,
   parameter                BE_DATA_W     = `IOB_CACHE_BE_DATA_W,
   parameter                WORD_OFFSET_W = `IOB_CACHE_WORD_OFFSET_W,
   parameter                WRITE_POL     = `IOB_CACHE_WRITE_THROUGH,
   parameter                AXI_ID_W      = `IOB_CACHE_AXI_ID_W,
   parameter [AXI_ID_W-1:0] AXI_ID        = `IOB_CACHE_AXI_ID,
   parameter                AXI_LEN_W     = `IOB_CACHE_AXI_LEN_W,
   parameter                AXI_ADDR_W    = BE_ADDR_W,
   parameter                AXI_DATA_W    = BE_DATA_W,
   //derived parameters
   parameter                FE_NBYTES     = FE_DATA_W / 8,
   parameter                FE_NBYTES_W   = $clog2(FE_NBYTES),
   parameter                BE_NBYTES     = BE_DATA_W / 8,
   parameter                BE_NBYTES_W   = $clog2(BE_NBYTES),
   parameter                LINE2BE_W     = WORD_OFFSET_W - $clog2(BE_DATA_W / FE_DATA_W)
) (
   // write-through-buffer
   input                                                                     write_valid_i,
   input  [             FE_ADDR_W-1 : FE_NBYTES_W + WRITE_POL*WORD_OFFSET_W] write_addr_i,
   input  [FE_DATA_W+WRITE_POL*(FE_DATA_W*(2**WORD_OFFSET_W)-FE_DATA_W)-1:0] write_wdata_i,
   input  [                                                   FE_NBYTES-1:0] write_wstrb_i,
   output                                                                    write_ready_o,

   // cache-line replacement
   input                                        replace_valid_i,
   input  [FE_ADDR_W-1:BE_NBYTES_W + LINE2BE_W] replace_addr_i,
   output                                       replace_o,
   output                                       read_valid_o,
   output [                     LINE2BE_W -1:0] read_addr_o,
   output [                    AXI_DATA_W -1:0] read_rdata_o,

   // Back-end interface (AXI4 master)
   output [AXI_ID_W-1:0] axi_awid_o,
   output [AXI_ADDR_W-1:0] axi_awaddr_o,
   output [AXI_LEN_W-1:0] axi_awlen_o,
   output [3-1:0] axi_awsize_o,
   output [2-1:0] axi_awburst_o,
   output [2-1:0] axi_awlock_o,
   output [4-1:0] axi_awcache_o,
   output [3-1:0] axi_awprot_o,
   output [4-1:0] axi_awqos_o,
   output [1-1:0] axi_awvalid_o,
   input [1-1:0] axi_awready_i,
   output [AXI_DATA_W-1:0] axi_wdata_o,
   output [(AXI_DATA_W/8)-1:0] axi_wstrb_o,
   output [1-1:0] axi_wlast_o,
   output [1-1:0] axi_wvalid_o,
   input [1-1:0] axi_wready_i,
   input [AXI_ID_W-1:0] axi_bid_i,
   input [2-1:0] axi_bresp_i,
   input [1-1:0] axi_bvalid_i,
   output [1-1:0] axi_bready_o,
   output [AXI_ID_W-1:0] axi_arid_o,
   output [AXI_ADDR_W-1:0] axi_araddr_o,
   output [AXI_LEN_W-1:0] axi_arlen_o,
   output [3-1:0] axi_arsize_o,
   output [2-1:0] axi_arburst_o,
   output [2-1:0] axi_arlock_o,
   output [4-1:0] axi_arcache_o,
   output [3-1:0] axi_arprot_o,
   output [4-1:0] axi_arqos_o,
   output [1-1:0] axi_arvalid_o,
   input [1-1:0] axi_arready_i,
   input [AXI_ID_W-1:0] axi_rid_i,
   input [AXI_DATA_W-1:0] axi_rdata_i,
   input [2-1:0] axi_rresp_i,
   input [1-1:0] axi_rlast_i,
   input [1-1:0] axi_rvalid_i,
   output [1-1:0] axi_rready_o,
   input [1-1:0] clk_i,  //V2TEX_IO System clock input.
   input [1-1:0] rst_i  //V2TEX_IO System reset, asynchronous and active high.
);

   iob_cache_read_channel_axi #(
      .ADDR_W       (FE_ADDR_W),
      .DATA_W       (FE_DATA_W),
      .BE_ADDR_W    (AXI_ADDR_W),
      .BE_DATA_W    (AXI_DATA_W),
      .WORD_OFFSET_W(WORD_OFFSET_W),
      .AXI_ADDR_W   (AXI_ADDR_W),
      .AXI_DATA_W   (AXI_DATA_W),
      .AXI_ID_W     (AXI_ID_W),
      .AXI_LEN_W    (AXI_LEN_W),
      .AXI_ID       (AXI_ID)
   ) read_fsm (
      .replace_valid_i(replace_valid_i),
      .replace_addr_i(replace_addr_i),
      .replace_o(replace_o),
      .read_valid_o(read_valid_o),
      .read_addr_o(read_addr_o),
      .read_rdata_o(read_rdata_o),
      .axi_arid_o(axi_arid_o),  //Address read channel ID.
      .axi_araddr_o(axi_araddr_o),  //Address read channel address.
      .axi_arlen_o(axi_arlen_o),  //Address read channel burst length.
      .axi_arsize_o(axi_arsize_o), //Address read channel burst size. This signal indicates the size of each transfer in the burst.
      .axi_arburst_o(axi_arburst_o),  //Address read channel burst type.
      .axi_arlock_o(axi_arlock_o),  //Address read channel lock type.
      .axi_arcache_o(axi_arcache_o), //Address read channel memory type. Set to 0000 if master output; ignored if slave input.
      .axi_arprot_o(axi_arprot_o), //Address read channel protection type. Set to 000 if master output; ignored if slave input.
      .axi_arqos_o(axi_arqos_o),  //Address read channel quality of service.
      .axi_arvalid_o(axi_arvalid_o),  //Address read channel valid.
      .axi_arready_i(axi_arready_i),  //Address read channel ready.
      .axi_rid_i(axi_rid_i),  //Read channel ID.
      .axi_rdata_i(axi_rdata_i),  //Read channel data.
      .axi_rresp_i(axi_rresp_i),  //Read channel response.
      .axi_rlast_i(axi_rlast_i),  //Read channel last word.
      .axi_rvalid_i(axi_rvalid_i),  //Read channel valid.
      .axi_rready_o(axi_rready_o),  //Read channel ready.
      .clk_i(clk_i),
      .reset_i(rst_i)
   );

   iob_cache_write_channel_axi #(
      .ADDR_W       (FE_ADDR_W),
      .DATA_W       (FE_DATA_W),
      .BE_ADDR_W    (AXI_ADDR_W),
      .BE_DATA_W    (AXI_DATA_W),
      .WRITE_POL    (WRITE_POL),
      .WORD_OFFSET_W(WORD_OFFSET_W),
      .AXI_ADDR_W   (AXI_ADDR_W),
      .AXI_DATA_W   (AXI_DATA_W),
      .AXI_ID_W     (AXI_ID_W),
      .AXI_LEN_W    (AXI_LEN_W),
      .AXI_ID       (AXI_ID)
   ) write_fsm (
      .valid_i(write_valid_i),
      .addr_i(write_addr_i),
      .wstrb_i(write_wstrb_i),
      .wdata_i(write_wdata_i),
      .ready_o(write_ready_o),
      .axi_awid_o(axi_awid_o),  //Address write channel ID.
      .axi_awaddr_o(axi_awaddr_o),  //Address write channel address.
      .axi_awlen_o(axi_awlen_o),  //Address write channel burst length.
      .axi_awsize_o(axi_awsize_o), //Address write channel burst size. This signal indicates the size of each transfer in the burst.
      .axi_awburst_o(axi_awburst_o),  //Address write channel burst type.
      .axi_awlock_o(axi_awlock_o),  //Address write channel lock type.
      .axi_awcache_o(axi_awcache_o), //Address write channel memory type. Set to 0000 if master output; ignored if slave input.
      .axi_awprot_o(axi_awprot_o), //Address write channel protection type. Set to 000 if master output; ignored if slave input.
      .axi_awqos_o(axi_awqos_o),  //Address write channel quality of service.
      .axi_awvalid_o(axi_awvalid_o),  //Address write channel valid.
      .axi_awready_i(axi_awready_i),  //Address write channel ready.
      .axi_wdata_o(axi_wdata_o),  //Write channel data.
      .axi_wstrb_o(axi_wstrb_o),  //Write channel write strobe.
      .axi_wlast_o(axi_wlast_o),  //Write channel last word flag.
      .axi_wvalid_o(axi_wvalid_o),  //Write channel valid.
      .axi_wready_i(axi_wready_i),  //Write channel ready.
      .axi_bid_i(axi_bid_i),  //Write response channel ID.
      .axi_bresp_i(axi_bresp_i),  //Write response channel response.
      .axi_bvalid_i(axi_bvalid_i),  //Write response channel valid.
      .axi_bready_o(axi_bready_o),  //Write response channel ready.
      .clk_i(clk_i),
      .reset_i(rst_i)
   );

endmodule
