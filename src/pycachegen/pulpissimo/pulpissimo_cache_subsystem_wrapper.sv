module pulpissimo_cache_subsystem_wrapper #(
  parameter int NR_MASTER_PORTS = 4,
  parameter int PRIV_BANK_0_MIN_ADDR = 32'h1C00_0000,
  parameter int PRIV_BANK_0_MAX_ADDR = 32'h1C02_0000
)(
  input logic clk_i,
  input logic rst_ni,
  XBAR_TCDM_BUS.Master tcdm_in[NR_MASTER_PORTS],
  XBAR_TCDM_BUS.Slave tcdm_out[NR_MASTER_PORTS],
  XBAR_TCDM_BUS.Slave tcdm_priv0
);
  localparam int unsigned BE_WIDTH = 4;
  localparam int unsigned ADDR_WIDTH = 32;
  localparam int unsigned DATA_WIDTH = 32;
  localparam int unsigned REQ_AGG_DATA_WIDTH  = 1+BE_WIDTH+ADDR_WIDTH+DATA_WIDTH; // +1 is for the write enable (wen),

  // Response status of each master port:
  //  0: No ouststanding responses
  //  1: Outstanding response from cache
  //  2: Outstanding response from memory
  logic [1:0] outstanding_response [NR_MASTER_PORTS-1:0];
  logic [NR_MASTER_PORTS-1:0] arb_masters_gnt;
  
  //Cache Data Bus (Arbiter<->Cache Subsystem)
  logic [31:0] arb_2_cache_addr, arb_2_cache_rdata, arb_2_cache_wdata;
  logic        arb_2_cache_req, arb_2_cache_gnt, arb_2_cache_rvalid, arb_2_cache_err;
  logic        arb_2_cache_wen;
  logic [ 3:0]  arb_2_cache_be;
      
  logic [NR_MASTER_PORTS-1:0] arbiter_req_in;
  logic [NR_MASTER_PORTS-1:0] new_request_allowed;
  logic [NR_MASTER_PORTS-1:0] address_for_cache;

  // update outstanding_response status
  for (genvar i = 0; i < NR_MASTER_PORTS; i++) begin
    always_ff @(posedge clk_i, negedge rst_ni) begin
      if (!rst_ni) begin
        outstanding_response[i] <= 2'd0;
      end else if (arbiter_req_in[i] && arb_masters_gnt[i]) begin
        outstanding_response[i] <= 2'd1; // new granted request for cache
      end else if (tcdm_out[i].req && tcdm_out[i].gnt) begin
        outstanding_response[i] <= 2'd2; // new granted request for memory
      end else if ((outstanding_response[i] == 2'd1 && arb_2_cache_rvalid) || (outstanding_response[i] == 2'd2 && tcdm_out[i].r_valid)) begin
        outstanding_response[i] <= 2'd0; // response but no new granted request
      end else begin
        outstanding_response[i] <= outstanding_response[i]; // no response
      end
    end
  end

  // forward the responses back to the correct requesters
  for (genvar i = 0; i < NR_MASTER_PORTS; i++) begin
    always_comb begin
      case (outstanding_response[i])
        1: begin
          tcdm_in[i].r_valid = arb_2_cache_rvalid;
          tcdm_in[i].r_rdata = arb_2_cache_rdata;
          tcdm_in[i].r_opc = arb_2_cache_err;
        end
        2: begin
          tcdm_in[i].r_valid = tcdm_out[i].r_valid;
          tcdm_in[i].r_rdata = tcdm_out[i].r_rdata;
          tcdm_in[i].r_opc = tcdm_out[i].r_opc;
        end
        default:  begin
          tcdm_in[i].r_valid = 0;
          tcdm_in[i].r_rdata = 0;
          tcdm_in[i].r_opc = 0;
        end
      endcase
    end
  end

  for (genvar i = 0; i < NR_MASTER_PORTS; i++) begin
    always_comb begin
      // always forward the request signals (except for req) to the outputs
      tcdm_out[i].add = tcdm_in[i].add;
      tcdm_out[i].wdata = tcdm_in[i].wdata;
      tcdm_out[i].wen = tcdm_in[i].wen;
      tcdm_out[i].be = tcdm_in[i].be;
      // New requests are allowed if there is no outstanding response or if there is a response
      new_request_allowed[i] = (!outstanding_response[i] || (outstanding_response[i] == 1 && arb_2_cache_rvalid) || (outstanding_response[i] == 2 && tcdm_out[i].r_valid));
      // If we can send a new request, check where it has to go to (cache or memory).
      // Also send the gnt signal back correctly.
      address_for_cache[i] = (tcdm_in[i].add >= PRIV_BANK_0_MIN_ADDR) && (tcdm_in[i].add < PRIV_BANK_0_MAX_ADDR);
      if (new_request_allowed[i]) begin
        if (address_for_cache[i]) begin
          arbiter_req_in[i] = tcdm_in[i].req;
          tcdm_out[i].req = 0;
          tcdm_in[i].gnt = arb_masters_gnt[i];
        end else begin
          arbiter_req_in[i] = 0;
          tcdm_out[i].req = tcdm_in[i].req;
          tcdm_in[i].gnt = tcdm_out[i].gnt;
        end
      end else begin
        arbiter_req_in[i] = 0;
        tcdm_out[i].req = 0;
        tcdm_in[i].gnt = 0;
      end
    end
  end


  //Aggregated Request Data
  logic [NR_MASTER_PORTS-1:0][REQ_AGG_DATA_WIDTH-1:0] req_data_agg_in;
  logic [REQ_AGG_DATA_WIDTH-1:0] req_data_agg_out;
  //Aggreagate the input data
  for (genvar i = 0; i < NR_MASTER_PORTS; i++) begin
    assign req_data_agg_in[i] = {tcdm_in[i].wen, tcdm_in[i].be, tcdm_in[i].add, tcdm_in[i].wdata};
  end
  //Disaggregate the output data
  assign {arb_2_cache_wen, arb_2_cache_be, arb_2_cache_addr, arb_2_cache_wdata} = req_data_agg_out;

  // index of the request chosen by the arbiter
  logic [$clog2(NR_MASTER_PORTS)-1:0] arbiter_idx ;
  // reg for previous index
  reg [$clog2(NR_MASTER_PORTS)-1:0] last_idx ;

  rr_arb_tree #(
    .NumIn     ( NR_MASTER_PORTS ),
    .DataWidth ( REQ_AGG_DATA_WIDTH ),
    .LockIn (1'b1)
  ) i_rr_arb_tree (
    .clk_i   ( clk_i      ),
    .rst_ni  ( rst_ni     ),
    .flush_i ( 1'b0       ),
    .rr_i    (            ),
    // Masters <-> Arbiter
    .req_i   ( arbiter_req_in ),
    .gnt_o   ( arb_masters_gnt  ),
    .data_i  ( req_data_agg_in ),
    // Arbiter <-> Cache Subsystem
    .gnt_i   ( arb_2_cache_gnt   ),
    .req_o   ( arb_2_cache_req   ),
    .data_o  ( req_data_agg_out ),
    .idx_o   ( arbiter_idx )
  );

  // store the grant index
  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      last_idx <= '0;
    end else begin
      if (arb_2_cache_req & arb_2_cache_gnt) begin
        last_idx <= arbiter_idx;
      end else begin
        last_idx <= last_idx;
      end
    end
  end

  // Create a separate signal for req and a obi pulp adapter, because req shall
  // not be asserted while another request is being processed, I think
  logic tcdm_priv0_req;
  obi_pulp_adapter i_obi_pulp_adapter_data (
      .rst_ni         (rst_ni),
      .clk_i          (clk_i),
      .core_req_i     (tcdm_priv0_req),
      .mem_gnt_i      (tcdm_priv0.gnt),
      .mem_rvalid_i   (tcdm_priv0.r_valid),
      .mem_req_o      (tcdm_priv0.req)
  );
  // Create the data cache. Connect it to the arbiter and the slave port
  pulpissimo_cache_subsystem cache_subsystem (
      .rst                (~rst_ni),
      .clk                (clk_i),
      .requestor__req       (arb_2_cache_req),
      .requestor__add      (arb_2_cache_addr),
      .requestor__wen       (arb_2_cache_wen),
      .requestor__wdata     (arb_2_cache_wdata),
      .requestor__be        (arb_2_cache_be),
      .requestor__gnt       (arb_2_cache_gnt),
      .requestor__r_valid    (arb_2_cache_rvalid),
      .requestor__r_rdata     (arb_2_cache_rdata),
      .requestor__r_opc       (arb_2_cache_err),
      .target__req     (tcdm_priv0_req),
      .target__add    (tcdm_priv0.add),
      .target__wen      (tcdm_priv0.wen),
      .target__wdata   (tcdm_priv0.wdata),
      .target__be      (tcdm_priv0.be),
      .target__gnt     (tcdm_priv0.gnt),
      .target__r_valid  (tcdm_priv0.r_valid),
      .target__r_rdata   (tcdm_priv0.r_rdata),
      .target__r_opc     (tcdm_priv0.r_opc)
  );
endmodule
