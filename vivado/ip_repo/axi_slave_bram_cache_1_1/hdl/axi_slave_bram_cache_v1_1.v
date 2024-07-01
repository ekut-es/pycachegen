
`timescale 1 ns / 1 ps

	module axi_slave_bram_cache_v1_1 #
	(
		// Users to add parameters here
        parameter integer CACHE_DATA_WIDTH = 16,
        parameter integer CACHE_ADDRESS_WIDTH = 8,
        parameter integer TRACE_BRAM_DATA_WIDTH = 32,
        parameter integer TRACE_BRAM_ADDRESS_WIDTH = 12,
        parameter integer TRACE_BRAM_READ_LATENCY = 2,
        parameter integer STATS_BRAM_DATA_WIDTH = 64,
        parameter integer STATS_BRAM_ADDRESS_WIDTH = 12,
		// User parameters ends
		// Do not modify the parameters beyond this line


		// Parameters of Axi Slave Bus Interface S00_AXI
		parameter integer C_S00_AXI_DATA_WIDTH	= 32,
		parameter integer C_S00_AXI_ADDR_WIDTH	= 5
	)
	(
		// Users to add ports here
		output wire bram_clk, // common clock for all BRAMs
        // ports for trace BRAM
        output wire[TRACE_BRAM_ADDRESS_WIDTH-1 : 0] trace_bram_address,
        output wire[TRACE_BRAM_DATA_WIDTH-1 : 0] trace_bram_write_data,
        input wire[TRACE_BRAM_DATA_WIDTH-1 : 0] trace_bram_read_data,
        output wire trace_bram_enable,
        output wire trace_bram_reset,
        output wire trace_bram_write_enable,
		// ports for stats BRAM
        output wire[STATS_BRAM_ADDRESS_WIDTH-1 : 0] stats_bram_address,
        output wire[STATS_BRAM_DATA_WIDTH-1 : 0] stats_bram_write_data,
        input wire[STATS_BRAM_DATA_WIDTH-1 : 0] stats_bram_read_data,
        output wire stats_bram_enable,
        output wire stats_bram_reset,
        output wire stats_bram_write_enable,
		// User ports ends
		// Do not modify the ports beyond this line


		// Ports of Axi Slave Bus Interface S00_AXI
		input wire  s00_axi_aclk,
		input wire  s00_axi_aresetn,
		input wire [C_S00_AXI_ADDR_WIDTH-1 : 0] s00_axi_awaddr,
		input wire [2 : 0] s00_axi_awprot,
		input wire  s00_axi_awvalid,
		output wire  s00_axi_awready,
		input wire [C_S00_AXI_DATA_WIDTH-1 : 0] s00_axi_wdata,
		input wire [(C_S00_AXI_DATA_WIDTH/8)-1 : 0] s00_axi_wstrb,
		input wire  s00_axi_wvalid,
		output wire  s00_axi_wready,
		output wire [1 : 0] s00_axi_bresp,
		output wire  s00_axi_bvalid,
		input wire  s00_axi_bready,
		input wire [C_S00_AXI_ADDR_WIDTH-1 : 0] s00_axi_araddr,
		input wire [2 : 0] s00_axi_arprot,
		input wire  s00_axi_arvalid,
		output wire  s00_axi_arready,
		output wire [C_S00_AXI_DATA_WIDTH-1 : 0] s00_axi_rdata,
		output wire [1 : 0] s00_axi_rresp,
		output wire  s00_axi_rvalid,
		input wire  s00_axi_rready
	);
// Instantiation of Axi Bus Interface S00_AXI
	axi_slave_bram_cache_v1_1_S00_AXI # ( 
		.C_S_AXI_DATA_WIDTH(C_S00_AXI_DATA_WIDTH),
		.C_S_AXI_ADDR_WIDTH(C_S00_AXI_ADDR_WIDTH),
		.CACHE_DATA_WIDTH(CACHE_DATA_WIDTH),
        .CACHE_ADDRESS_WIDTH(CACHE_ADDRESS_WIDTH),
        .TRACE_BRAM_DATA_WIDTH(TRACE_BRAM_DATA_WIDTH),
        .TRACE_BRAM_ADDRESS_WIDTH(TRACE_BRAM_ADDRESS_WIDTH),
        .TRACE_BRAM_READ_LATENCY(TRACE_BRAM_READ_LATENCY),
        .STATS_BRAM_DATA_WIDTH(STATS_BRAM_DATA_WIDTH),
        .STATS_BRAM_ADDRESS_WIDTH(STATS_BRAM_ADDRESS_WIDTH)
	) axi_slave_bram_cache_v1_1_S00_AXI_inst (
		.S_AXI_ACLK(s00_axi_aclk),
		.S_AXI_ARESETN(s00_axi_aresetn),
		.S_AXI_AWADDR(s00_axi_awaddr),
		.S_AXI_AWPROT(s00_axi_awprot),
		.S_AXI_AWVALID(s00_axi_awvalid),
		.S_AXI_AWREADY(s00_axi_awready),
		.S_AXI_WDATA(s00_axi_wdata),
		.S_AXI_WSTRB(s00_axi_wstrb),
		.S_AXI_WVALID(s00_axi_wvalid),
		.S_AXI_WREADY(s00_axi_wready),
		.S_AXI_BRESP(s00_axi_bresp),
		.S_AXI_BVALID(s00_axi_bvalid),
		.S_AXI_BREADY(s00_axi_bready),
		.S_AXI_ARADDR(s00_axi_araddr),
		.S_AXI_ARPROT(s00_axi_arprot),
		.S_AXI_ARVALID(s00_axi_arvalid),
		.S_AXI_ARREADY(s00_axi_arready),
		.S_AXI_RDATA(s00_axi_rdata),
		.S_AXI_RRESP(s00_axi_rresp),
		.S_AXI_RVALID(s00_axi_rvalid),
		.S_AXI_RREADY(s00_axi_rready),
		.trace_bram_address(trace_bram_address),
        .trace_bram_write_data(trace_bram_write_data),
        .trace_bram_read_data(trace_bram_read_data),
        .trace_bram_enable(trace_bram_enable),
        .trace_bram_reset(trace_bram_reset),
        .trace_bram_write_enable(trace_bram_write_enable),
        .stats_bram_address(stats_bram_address),
        .stats_bram_write_data(stats_bram_write_data),
        .stats_bram_read_data(stats_bram_read_data),
        .stats_bram_enable(stats_bram_enable),
        .stats_bram_reset(stats_bram_reset),
        .stats_bram_write_enable(stats_bram_write_enable)
	);

	// Add user logic here
    assign bram_clk = s00_axi_aclk;
	// User logic ends

	endmodule
