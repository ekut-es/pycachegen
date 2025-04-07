// Module for integrating a PyCacheGen data cache into SoCs based on the pulp_soc, like the Pulpissimo
// This module can take several TCDM requesters as tcdm_in. The request addresses will be used to check
// whether the request should go to private bank 0. Such requests will go through the cache.
// The cache's own request interface is output as tcdm_priv0. All other requests are simply output on
// tcdm_out again.
module pulpissimo_cache_subsystem_wrapper #(
  parameter int NR_MASTER_PORTS = 4,
  parameter int PRIV_BANK_0_MIN_ADDR = 32'h1C00_0000,
  parameter int PRIV_BANK_0_MAX_ADDR = 32'h1C02_0000
)(
  input logic clk_i,
  input logic rst_ni,
  XBAR_TCDM_BUS.Slave tcdm_in[NR_MASTER_PORTS],
  XBAR_TCDM_BUS.Master tcdm_out[NR_MASTER_PORTS],
  XBAR_TCDM_BUS.Master tcdm_priv0
);
  localparam int unsigned BE_WIDTH = 4;
  localparam int unsigned ADDR_WIDTH = 32;
  localparam int unsigned DATA_WIDTH = 32;
  localparam int unsigned REQ_AGG_DATA_WIDTH  = 1+BE_WIDTH+ADDR_WIDTH+DATA_WIDTH; // +1 is for wen

  logic outstanding_cache_response; // Whether we're awaiting a response from the cache

  // indices of the next request (as outputted by the arbiter) and of the previously granted request
  logic [$clog2(NR_MASTER_PORTS)-1:0] arb_next_idx;
  logic [$clog2(NR_MASTER_PORTS)-1:0] arb_curr_idx;

  // (Requesters<->Arbiter)
  logic [NR_MASTER_PORTS-1:0] req_2_arb_gnt;
  logic [NR_MASTER_PORTS-1:0] req_2_arb_req;
  logic [NR_MASTER_PORTS-1:0][REQ_AGG_DATA_WIDTH-1:0] req_2_arb_data_agg; // Aggreagate the input data for the arbiter
  for (genvar i = 0; i < NR_MASTER_PORTS; i++) begin
    assign req_2_arb_data_agg[i] = {tcdm_in[i].wen, tcdm_in[i].be, tcdm_in[i].add, tcdm_in[i].wdata};
  end

  // (Arbiter<->Cache Subsystem)
  logic [31:0] arb_2_cache_addr, arb_2_cache_rdata, arb_2_cache_wdata;
  logic        arb_2_cache_req, arb_2_cache_gnt, arb_2_cache_rvalid, arb_2_cache_err;
  logic        arb_2_cache_wen;
  logic [ 3:0] arb_2_cache_be;
  logic [REQ_AGG_DATA_WIDTH-1:0] arb_2_cache_data_agg; // Disaggregate the output data from the arbiter
  assign {arb_2_cache_wen, arb_2_cache_be, arb_2_cache_addr, arb_2_cache_wdata} = arb_2_cache_data_agg;


  // update outstanding_cache_response status
  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      outstanding_cache_response <= '0;
    end else begin
      if (arb_2_cache_req && arb_2_cache_gnt) begin
        outstanding_cache_response <= 1'b1; // new granted request for cache
      end else if ((outstanding_cache_response == 1'b1) && arb_2_cache_rvalid) begin
        outstanding_cache_response <= 1'b0; // response but no new granted request
      end else begin
        outstanding_cache_response <= outstanding_cache_response; // no new request or response
      end
    end
  end

  // Request & Response routing to/from arbiter and regular outputs
  for (genvar i = 0; i < NR_MASTER_PORTS; i++) begin
    always_comb begin
      // Check whether the req has to go to cache or memory. Also send the gnt signal back correctly.
      if ((tcdm_in[i].add >= PRIV_BANK_0_MIN_ADDR) && (tcdm_in[i].add < PRIV_BANK_0_MAX_ADDR)) begin
        req_2_arb_req[i] = tcdm_in[i].req;
        tcdm_out[i].req = 0;
        tcdm_in[i].gnt = req_2_arb_gnt[i];
      end else begin
        req_2_arb_req[i] = 0;
        tcdm_out[i].req = tcdm_in[i].req;
        tcdm_in[i].gnt = tcdm_out[i].gnt;
      end
      // Always forward all the other the request signals to the regular outputs
      tcdm_out[i].add = tcdm_in[i].add;
      tcdm_out[i].wdata = tcdm_in[i].wdata;
      tcdm_out[i].wen = tcdm_in[i].wen;
      tcdm_out[i].be = tcdm_in[i].be;
      // Forward the responses back to the correct requesters
      if (outstanding_cache_response && (i == arb_curr_idx)) begin
          tcdm_in[i].r_valid = arb_2_cache_rvalid;
          tcdm_in[i].r_rdata = arb_2_cache_rdata;
          tcdm_in[i].r_opc = arb_2_cache_err;
      end else begin
          tcdm_in[i].r_valid = tcdm_out[i].r_valid;
          tcdm_in[i].r_rdata = tcdm_out[i].r_rdata;
          tcdm_in[i].r_opc = tcdm_out[i].r_opc;
      end
    end
  end

  // Arbiter for access to the cache
  rr_arb_tree #(
    .NumIn     ( NR_MASTER_PORTS ),
    .DataWidth ( REQ_AGG_DATA_WIDTH )
  ) i_rr_arb_tree (
    .clk_i   ( clk_i      ),
    .rst_ni  ( rst_ni     ),
    .flush_i ( '0         ),
    .rr_i    ( '0         ),
    .idx_o   ( arb_next_idx    ),
    // Masters <-> Arbiter
    .req_i   ( req_2_arb_req  ),
    .data_i  ( req_2_arb_data_agg ),
    .gnt_o   ( req_2_arb_gnt  ),
    // Arbiter <-> Cache Subsystem
    .gnt_i   ( arb_2_cache_gnt   ),
    .req_o   ( arb_2_cache_req   ),
    .data_o  ( arb_2_cache_data_agg )
  );

  // Store the grant index of the arbiter
  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      arb_curr_idx <= '0;
    end else begin
      if (arb_2_cache_req && arb_2_cache_gnt) begin
        arb_curr_idx <= arb_next_idx;
      end else begin
        arb_curr_idx <= arb_curr_idx;
      end
    end
  end

  // The cache subsystem might issue another request before having received the
  // response from the previous request, so we have to use an adapter
  logic tcdm_priv0_req;
  obi_pulp_adapter i_obi_pulp_adapter_data (
      .rst_ni         (rst_ni),
      .clk_i          (clk_i),
      .core_req_i     (tcdm_priv0_req),
      .mem_gnt_i      (tcdm_priv0.gnt),
      .mem_rvalid_i   (tcdm_priv0.r_valid),
      .mem_req_o      (tcdm_priv0.req)
  );

  logic [ADDR_WIDTH-1:0] arb_2_cache_addr_remapped, tcdm_priv0_add;
  assign arb_2_cache_addr_remapped = arb_2_cache_addr - PRIV_BANK_0_MIN_ADDR;
  assign tcdm_priv0.add = tcdm_priv0_add + PRIV_BANK_0_MIN_ADDR;

  // Create the cache subsystem. Connect it to the arbiter and the priv0 output.
  pulpissimo_cache_subsystem cache_subsystem (
      .rst                (~rst_ni),
      .clk                (clk_i),
      .requestor__req       (arb_2_cache_req),
      .requestor__add      (arb_2_cache_addr_remapped),
      .requestor__wen       (arb_2_cache_wen),
      .requestor__wdata     (arb_2_cache_wdata),
      .requestor__be        (arb_2_cache_be),
      .requestor__gnt       (arb_2_cache_gnt),
      .requestor__r_valid    (arb_2_cache_rvalid),
      .requestor__r_rdata     (arb_2_cache_rdata),
      .requestor__r_opc       (arb_2_cache_err),
      .target__req     (tcdm_priv0_req),
      .target__add    (tcdm_priv0_add),
      .target__wen      (tcdm_priv0.wen),
      .target__wdata   (tcdm_priv0.wdata),
      .target__be      (tcdm_priv0.be),
      .target__gnt     (tcdm_priv0.gnt),
      .target__r_valid  (tcdm_priv0.r_valid),
      .target__r_rdata   (tcdm_priv0.r_rdata),
      .target__r_opc     (tcdm_priv0.r_opc)
  );
endmodule
