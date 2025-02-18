module pulpissimo_cache_wrapper
    #(
      parameter int  NR_MASTER_PORTS = 4
    )(
       input logic clk_i,
       input logic rst_ni,
       XBAR_TCDM_BUS.Master tcdm_masters[NR_MASTER_PORTS],
       XBAR_TCDM_BUS.Slave tcdm_mem_if
    );
    // Do **not** change. The TCDM interface uses hardcoded bus widths so we cannot just change them here.
    localparam int unsigned BE_WIDTH = 4;
    localparam int unsigned ADDR_WIDTH = 32;
    localparam int unsigned DATA_WIDTH = 32;
    localparam int unsigned REQ_AGG_DATA_WIDTH  = 1+BE_WIDTH+ADDR_WIDTH+DATA_WIDTH; // +1 is for the write enable (wen),
    
    //Cache Data Bus (Arbiter<->Cache)
    logic [31:0] arb_2_cache_addr, arb_2_cache_rdata, arb_2_cache_wdata;
    logic        arb_2_cache_req, arb_2_cache_gnt, arb_2_cache_rvalid, arb_2_cache_err;
    logic        arb_2_cache_wen;
    logic [ 3:0]  arb_2_cache_be ;

    // index of the request chosen by the arbiter
    logic [$clog2(NR_MASTER_PORTS)-1:0] arbiter_idx ;
    // reg for previous index
    reg [$clog2(NR_MASTER_PORTS)-1:0] last_idx ;

    //Aggregated Request Data
    logic [NR_MASTER_PORTS-1:0][REQ_AGG_DATA_WIDTH-1:0] req_data_agg_in;
    logic [REQ_AGG_DATA_WIDTH-1:0] req_data_agg_out;
    //Aggreagate the input data
    for (genvar i = 0; i < NR_MASTER_PORTS; i++) begin
        assign req_data_agg_in[i] = {tcdm_masters[i].wen, tcdm_masters[i].be, tcdm_masters[i].add, tcdm_masters[i].wdata};
    end
    //Disaggregate the output data
    assign {arb_2_cache_wen, arb_2_cache_be, arb_2_cache_addr, arb_2_cache_wdata} = req_data_agg_out;

    // create arrays of req and gnt for arbiter
    logic [NR_MASTER_PORTS-1:0] tcdm_masters_req;
    logic [NR_MASTER_PORTS-1:0] tcdm_masters_gnt;
    for(genvar i = 0; i < NR_MASTER_PORTS; i++) begin
      assign tcdm_masters_req[i] = tcdm_masters[i].req;
      assign tcdm_masters[i].gnt = tcdm_masters_gnt[i];  
    end

    // Abitrate fc data, udma rx, udma tx and debug
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
      .req_i   ( tcdm_masters_req ),
      .gnt_o   ( tcdm_masters_gnt  ),
      .data_i  ( req_data_agg_in ),
      // Arbiter <-> Cache
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

    for (genvar i = 0; i < NR_MASTER_PORTS; i++) begin
    // forward the rvalid response to the correct master
      assign tcdm_masters[i].r_valid = (i == last_idx) ? arb_2_cache_rvalid : '0;
      // connect all other response channels to all masters
      assign tcdm_masters[i].r_rdata = arb_2_cache_rdata;
      assign tcdm_masters[i].r_opc = arb_2_cache_err;
    end


    // Create a separate signal for req and a obi pulp adapter, because req shall
    // not be asserted while another request is being processed, I think
    logic tcdm_mem_if_req;
    obi_pulp_adapter i_obi_pulp_adapter_data (
        .rst_ni         (rst_ni),
        .clk_i          (clk_i),
        .core_req_i     (tcdm_mem_if_req),
        .mem_gnt_i      (tcdm_mem_if.gnt),
        .mem_rvalid_i   (tcdm_mem_if.r_valid),
        .mem_req_o      (tcdm_mem_if.req)
    );
    // Create the data cache. Connect it to to arbiter and the slave port
    pulpissimo_data_cache data_cache (
        .rst                (~rst_ni),
        .clk                (clk_i),
        .core_if__req       (arb_2_cache_req),
        .core_if__add      (arb_2_cache_addr),
        .core_if__wen       (arb_2_cache_wen),
        .core_if__wdata     (arb_2_cache_wdata),
        .core_if__be        (arb_2_cache_be),
        .core_if__gnt       (arb_2_cache_gnt),
        .core_if__r_valid    (arb_2_cache_rvalid),
        .core_if__r_rdata     (arb_2_cache_rdata),
        .core_if__r_opc       (arb_2_cache_err),
        .memory_if__req     (tcdm_mem_if_req),
        .memory_if__add    (tcdm_mem_if.add),
        .memory_if__wen      (tcdm_mem_if.wen),
        .memory_if__wdata   (tcdm_mem_if.wdata),
        .memory_if__be      (tcdm_mem_if.be),
        .memory_if__gnt     (tcdm_mem_if.gnt),
        .memory_if__r_valid  (tcdm_mem_if.r_valid),
        .memory_if__r_rdata   (tcdm_mem_if.r_rdata),
        .memory_if__r_opc     (tcdm_mem_if.r_opc)
    );
endmodule