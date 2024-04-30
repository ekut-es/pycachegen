`timescale 1ns / 1ps

`include "iob_cache_swreg_def.vh"
`include "iob_cache_conf.vh"

module iob_cache_sim_wrapper #(
   parameter                ADDR_W        = `IOB_CACHE_ADDR_W,
   parameter                DATA_W        = `IOB_CACHE_DATA_W,
   parameter                FE_ADDR_W     = `IOB_CACHE_FE_ADDR_W,
   parameter                FE_DATA_W     = `IOB_CACHE_FE_DATA_W,
   parameter                FE_NBYTES     = FE_DATA_W / 8,
   parameter                FE_NBYTES_W   = $clog2(FE_NBYTES),
   parameter                BE_ADDR_W     = `IOB_CACHE_BE_ADDR_W,
   parameter                BE_DATA_W     = `IOB_CACHE_BE_DATA_W,
   parameter                BE_NBYTES     = BE_DATA_W / 8,
   parameter                BE_NBYTES_W   = $clog2(BE_NBYTES),
   parameter                NWAYS_W       = `IOB_CACHE_NWAYS_W,
   parameter                NLINES_W      = `IOB_CACHE_NLINES_W,
   parameter                WORD_OFFSET_W = `IOB_CACHE_WORD_OFFSET_W,
   parameter                WTBUF_DEPTH_W = `IOB_CACHE_WTBUF_DEPTH_W,
   parameter                REP_POLICY    = `IOB_CACHE_REP_POLICY,
   parameter                WRITE_POL     = `IOB_CACHE_WRITE_THROUGH,
`ifdef IOB_CACHE_AXI
   parameter                AXI_ID_W      = `IOB_CACHE_AXI_ID_W,
   parameter [AXI_ID_W-1:0] AXI_ID        = `IOB_CACHE_AXI_ID,
   parameter                AXI_LEN_W     = `IOB_CACHE_AXI_LEN_W,
   parameter                AXI_ADDR_W    = BE_ADDR_W,
   parameter                AXI_DATA_W    = BE_DATA_W,
`endif
   parameter                USE_CTRL      = `IOB_CACHE_USE_CTRL,
   parameter                USE_CTRL_CNT  = `IOB_CACHE_USE_CTRL_CNT
) (
   // Front-end interface (IOb native slave)
   input  [                             1-1:0] iob_valid_i,
   input  [USE_CTRL+FE_ADDR_W-FE_NBYTES_W-1:0] iob_addr_i,
   input  [                        DATA_W-1:0] iob_wdata_i,
   input  [                     FE_NBYTES-1:0] iob_wstrb_i,
   output [                        DATA_W-1:0] iob_rdata_o,
   output [                             1-1:0] iob_rvalid_o,
   output [                             1-1:0] iob_ready_o,

   // Cache invalidate and write-trough buffer IO chain
   input  [1-1:0] invalidate_i,
   output [1-1:0] invalidate_o,
   input  [1-1:0] wtb_empty_i,
   output [1-1:0] wtb_empty_o,

   //General Interface Signals
   input [1-1:0] clk_i,
   input [1-1:0] arst_i
);

   wire cke_i;
   assign cke_i = 1'b1;

`ifdef IOB_CACHE_AXI
   wire [AXI_ID_W-1:0] axi_awid;  //Address write channel ID.
   wire [AXI_ADDR_W-1:0] axi_awaddr;  //Address write channel address.
   wire [AXI_LEN_W-1:0] axi_awlen;  //Address write channel burst length.
   wire [3-1:0] axi_awsize; //Address write channel burst size. This signal indicates the size of each transfer in the burst.
   wire [2-1:0] axi_awburst;  //Address write channel burst type.
   wire [2-1:0] axi_awlock;  //Address write channel lock type.
   wire [4-1:0] axi_awcache; //Address write channel memory type. Set to 0000 if master output; ignored if slave input.
   wire [3-1:0] axi_awprot; //Address write channel protection type. Set to 000 if master output; ignored if slave input.
   wire [4-1:0] axi_awqos;  //Address write channel quality of service.
   wire [1-1:0] axi_awvalid;  //Address write channel valid.
   wire [1-1:0] axi_awready;  //Address write channel ready.
   wire [AXI_DATA_W-1:0] axi_wdata;  //Write channel data.
   wire [(AXI_DATA_W/8)-1:0] axi_wstrb;  //Write channel write strobe.
   wire [1-1:0] axi_wlast;  //Write channel last word flag.
   wire [1-1:0] axi_wvalid;  //Write channel valid.
   wire [1-1:0] axi_wready;  //Write channel ready.
   wire [AXI_ID_W-1:0] axi_bid;  //Write response channel ID.
   wire [2-1:0] axi_bresp;  //Write response channel response.
   wire [1-1:0] axi_bvalid;  //Write response channel valid.
   wire [1-1:0] axi_bready;  //Write response channel ready.
   wire [AXI_ID_W-1:0] axi_arid;  //Address read channel ID.
   wire [AXI_ADDR_W-1:0] axi_araddr;  //Address read channel address.
   wire [AXI_LEN_W-1:0] axi_arlen;  //Address read channel burst length.
   wire [3-1:0] axi_arsize; //Address read channel burst size. This signal indicates the size of each transfer in the burst.
   wire [2-1:0] axi_arburst;  //Address read channel burst type.
   wire [2-1:0] axi_arlock;  //Address read channel lock type.
   wire [4-1:0] axi_arcache; //Address read channel memory type. Set to 0000 if master output; ignored if slave input.
   wire [3-1:0] axi_arprot; //Address read channel protection type. Set to 000 if master output; ignored if slave input.
   wire [4-1:0] axi_arqos;  //Address read channel quality of service.
   wire [1-1:0] axi_arvalid;  //Address read channel valid.
   wire [1-1:0] axi_arready;  //Address read channel ready.
   wire [AXI_ID_W-1:0] axi_rid;  //Read channel ID.
   wire [AXI_DATA_W-1:0] axi_rdata;  //Read channel data.
   wire [2-1:0] axi_rresp;  //Read channel response.
   wire [1-1:0] axi_rlast;  //Read channel last word.
   wire [1-1:0] axi_rvalid;  //Read channel valid.
   wire [1-1:0] axi_rready;  //Read channel ready.

   iob_cache_axi cache (
      //front-end
      .iob_valid_i(iob_valid_i),  //Request valid.
      .iob_addr_i(iob_addr_i),  //Address.
      .iob_wdata_i(iob_wdata_i),  //Write data.
      .iob_wstrb_i(iob_wstrb_i),  //Write strobe.
      .iob_rvalid_o(iob_rvalid_o),  //Read data valid.
      .iob_rdata_o(iob_rdata_o),  //Read data.
      .iob_ready_o(iob_ready_o),  //Interface ready.
      //invalidate / wtb empty
      .invalidate_i(1'b0),
      .invalidate_o(invalidate_o),
      .wtb_empty_i(1'b1),
      .wtb_empty_o(wtb_empty_o),
      .axi_awid_o(axi_awid),  //Address write channel ID.
      .axi_awaddr_o(axi_awaddr),  //Address write channel address.
      .axi_awlen_o(axi_awlen),  //Address write channel burst length.
      .axi_awsize_o(axi_awsize), //Address write channel burst size. This signal indicates the size of each transfer in the burst.
      .axi_awburst_o(axi_awburst),  //Address write channel burst type.
      .axi_awlock_o(axi_awlock),  //Address write channel lock type.
      .axi_awcache_o(axi_awcache), //Address write channel memory type. Set to 0000 if master output; ignored if slave input.
      .axi_awprot_o(axi_awprot), //Address write channel protection type. Set to 000 if master output; ignored if slave input.
      .axi_awqos_o(axi_awqos),  //Address write channel quality of service.
      .axi_awvalid_o(axi_awvalid),  //Address write channel valid.
      .axi_awready_i(axi_awready),  //Address write channel ready.
      .axi_wdata_o(axi_wdata),  //Write channel data.
      .axi_wstrb_o(axi_wstrb),  //Write channel write strobe.
      .axi_wlast_o(axi_wlast),  //Write channel last word flag.
      .axi_wvalid_o(axi_wvalid),  //Write channel valid.
      .axi_wready_i(axi_wready),  //Write channel ready.
      .axi_bid_i(axi_bid),  //Write response channel ID.
      .axi_bresp_i(axi_bresp),  //Write response channel response.
      .axi_bvalid_i(axi_bvalid),  //Write response channel valid.
      .axi_bready_o(axi_bready),  //Write response channel ready.
      .axi_arid_o(axi_arid),  //Address read channel ID.
      .axi_araddr_o(axi_araddr),  //Address read channel address.
      .axi_arlen_o(axi_arlen),  //Address read channel burst length.
      .axi_arsize_o(axi_arsize), //Address read channel burst size. This signal indicates the size of each transfer in the burst.
      .axi_arburst_o(axi_arburst),  //Address read channel burst type.
      .axi_arlock_o(axi_arlock),  //Address read channel lock type.
      .axi_arcache_o(axi_arcache), //Address read channel memory type. Set to 0000 if master output; ignored if slave input.
      .axi_arprot_o(axi_arprot), //Address read channel protection type. Set to 000 if master output; ignored if slave input.
      .axi_arqos_o(axi_arqos),  //Address read channel quality of service.
      .axi_arvalid_o(axi_arvalid),  //Address read channel valid.
      .axi_arready_i(axi_arready),  //Address read channel ready.
      .axi_rid_i(axi_rid),  //Read channel ID.
      .axi_rdata_i(axi_rdata),  //Read channel data.
      .axi_rresp_i(axi_rresp),  //Read channel response.
      .axi_rlast_i(axi_rlast),  //Read channel last word.
      .axi_rvalid_i(axi_rvalid),  //Read channel valid.
      .axi_rready_o(axi_rready),  //Read channel ready.
      .clk_i(clk_i),  //clock signal
      .cke_i(cke_i),  //clock enable
      .arst_i(arst_i)  //asynchronous reset
   );
`else
   wire                   be_valid;
   wire [  BE_ADDR_W-1:0] be_addr;
   wire [  BE_DATA_W-1:0] be_wdata;
   wire [BE_DATA_W/8-1:0] be_wstrb;
   wire [  BE_DATA_W-1:0] be_rdata;
   wire                   be_rvalid;
   wire                   be_ready;

   iob_cache_iob cache (
      //front-end
      .iob_valid_i (iob_valid_i),   //Request valid.
      .iob_addr_i  (iob_addr_i),    //Address.
      .iob_wdata_i (iob_wdata_i),   //Write data.
      .iob_wstrb_i (iob_wstrb_i),   //Write strobe.
      .iob_rvalid_o(iob_rvalid_o),  //Read data valid.
      .iob_rdata_o (iob_rdata_o),   //Read data.
      .iob_ready_o (iob_ready_o),   //Interface ready.
      //invalidate / wtb empty
      .invalidate_i(1'b0),
      .invalidate_o(invalidate_o),
      .wtb_empty_i (1'b1),
      .wtb_empty_o (wtb_empty_o),

      .be_valid_o (be_valid),
      .be_addr_o  (be_addr),
      .be_wdata_o (be_wdata),
      .be_wstrb_o (be_wstrb),
      .be_rdata_i (be_rdata),
      .be_rvalid_i(be_rvalid),
      .be_ready_i (be_ready),

      .clk_i (clk_i),
      .cke_i (cke_i),
      .arst_i(arst_i)
   );
`endif

`ifdef IOB_CACHE_AXI
   axi_ram #(
      .ID_WIDTH  (AXI_ID_W),
      .LEN_WIDTH (AXI_LEN_W),
      .DATA_WIDTH(BE_DATA_W),
      .ADDR_WIDTH(BE_ADDR_W)
   ) axi_ram (
      .axi_awid_i(axi_awid),  //Address write channel ID.
      .axi_awaddr_i(axi_awaddr),  //Address write channel address.
      .axi_awlen_i(axi_awlen),  //Address write channel burst length.
      .axi_awsize_i(axi_awsize), //Address write channel burst size. This signal indicates the size of each transfer in the burst.
      .axi_awburst_i(axi_awburst),  //Address write channel burst type.
      .axi_awlock_i(axi_awlock),  //Address write channel lock type.
      .axi_awcache_i(axi_awcache), //Address write channel memory type. Set to 0000 if master output; ignored if slave input.
      .axi_awprot_i(axi_awprot), //Address write channel protection type. Set to 000 if master output; ignored if slave input.
      .axi_awqos_i(axi_awqos),  //Address write channel quality of service.
      .axi_awvalid_i(axi_awvalid),  //Address write channel valid.
      .axi_awready_o(axi_awready),  //Address write channel ready.
      .axi_wdata_i(axi_wdata),  //Write channel data.
      .axi_wstrb_i(axi_wstrb),  //Write channel write strobe.
      .axi_wlast_i(axi_wlast),  //Write channel last word flag.
      .axi_wvalid_i(axi_wvalid),  //Write channel valid.
      .axi_wready_o(axi_wready),  //Write channel ready.
      .axi_bid_o(axi_bid),  //Write response channel ID.
      .axi_bresp_o(axi_bresp),  //Write response channel response.
      .axi_bvalid_o(axi_bvalid),  //Write response channel valid.
      .axi_bready_i(axi_bready),  //Write response channel ready.
      .axi_arid_i(axi_arid),  //Address read channel ID.
      .axi_araddr_i(axi_araddr),  //Address read channel address.
      .axi_arlen_i(axi_arlen),  //Address read channel burst length.
      .axi_arsize_i(axi_arsize), //Address read channel burst size. This signal indicates the size of each transfer in the burst.
      .axi_arburst_i(axi_arburst),  //Address read channel burst type.
      .axi_arlock_i(axi_arlock),  //Address read channel lock type.
      .axi_arcache_i(axi_arcache), //Address read channel memory type. Set to 0000 if master output; ignored if slave input.
      .axi_arprot_i(axi_arprot), //Address read channel protection type. Set to 000 if master output; ignored if slave input.
      .axi_arqos_i(axi_arqos),  //Address read channel quality of service.
      .axi_arvalid_i(axi_arvalid),  //Address read channel valid.
      .axi_arready_o(axi_arready),  //Address read channel ready.
      .axi_rid_o(axi_rid),  //Read channel ID.
      .axi_rdata_o(axi_rdata),  //Read channel data.
      .axi_rresp_o(axi_rresp),  //Read channel response.
      .axi_rlast_o(axi_rlast),  //Read channel last word.
      .axi_rvalid_o(axi_rvalid),  //Read channel valid.
      .axi_rready_i(axi_rready),  //Read channel ready.
      .clk_i(clk_i),
      .rst_i(arst_i)
   );
`else
   iob_ram_sp_be #(
      .DATA_W(BE_DATA_W),
      .ADDR_W(BE_ADDR_W)
   ) native_ram (
      .clk_i (clk_i),
      .en_i  (be_valid),
      .we_i  (be_wstrb),
      .addr_i(be_addr),
      .d_o   (be_rdata),
      .d_i   (be_wdata)
   );

   assign be_ready = 1'b1;
   iob_reg_re #(
      .DATA_W (1),
      .RST_VAL(0)
   ) iob_reg_rvalid (
      .clk_i (clk_i),
      .arst_i(arst_i),
      .cke_i (cke_i),
      .rst_i (1'b0),
      .en_i  (1'b1),
      .data_i(be_valid & (~(|be_wstrb))),
      .data_o(be_rvalid)
   );
`endif

endmodule
