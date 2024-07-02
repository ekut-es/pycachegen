
`timescale 1 ns / 1 ps

	module axi_slave_bram_cache_v1_1_S00_AXI #
	(
		// Users to add parameters here,
        parameter integer CACHE_DATA_WIDTH = 16,
        parameter integer CACHE_ADDRESS_WIDTH = 8,
        parameter integer TRACE_BRAM_DATA_WIDTH = 32,
        parameter integer TRACE_BRAM_ADDRESS_WIDTH = 12,
        parameter integer TRACE_BRAM_READ_LATENCY = 2,
        parameter integer STATS_BRAM_DATA_WIDTH = 64,
        parameter integer STATS_BRAM_ADDRESS_WIDTH = 12,
		// User parameters ends
		// Do not modify the parameters beyond this line

		// Width of S_AXI data bus
		parameter integer C_S_AXI_DATA_WIDTH	= 32,
		// Width of S_AXI address bus
		parameter integer C_S_AXI_ADDR_WIDTH	= 5
	)
	(
		// Users to add ports here
		// ports for trace BRAM
        output reg[TRACE_BRAM_ADDRESS_WIDTH-1 : 0] trace_bram_address,
        output reg[TRACE_BRAM_DATA_WIDTH-1 : 0] trace_bram_write_data,
        input wire[TRACE_BRAM_DATA_WIDTH-1 : 0] trace_bram_read_data,
        output reg trace_bram_enable,
        output wire trace_bram_reset,
        output wire trace_bram_write_enable,
		// ports for stats BRAM
        output reg[STATS_BRAM_ADDRESS_WIDTH-1 : 0] stats_bram_address,
        output reg[STATS_BRAM_DATA_WIDTH-1 : 0] stats_bram_write_data,
        input wire[STATS_BRAM_DATA_WIDTH-1 : 0] stats_bram_read_data,
        output reg stats_bram_enable,
        output wire stats_bram_reset,
        output reg stats_bram_write_enable,
		// User ports ends
		// Do not modify the ports beyond this line

		// Global Clock Signal
		input wire  S_AXI_ACLK,
		// Global Reset Signal. This Signal is Active LOW
		input wire  S_AXI_ARESETN,
		// Write address (issued by master, acceped by Slave)
		input wire [C_S_AXI_ADDR_WIDTH-1 : 0] S_AXI_AWADDR,
		// Write channel Protection type. This signal indicates the
    		// privilege and security level of the transaction, and whether
    		// the transaction is a data access or an instruction access.
		input wire [2 : 0] S_AXI_AWPROT,
		// Write address valid. This signal indicates that the master signaling
    		// valid write address and control information.
		input wire  S_AXI_AWVALID,
		// Write address ready. This signal indicates that the slave is ready
    		// to accept an address and associated control signals.
		output wire  S_AXI_AWREADY,
		// Write data (issued by master, acceped by Slave) 
		input wire [C_S_AXI_DATA_WIDTH-1 : 0] S_AXI_WDATA,
		// Write strobes. This signal indicates which byte lanes hold
    		// valid data. There is one write strobe bit for each eight
    		// bits of the write data bus.    
		input wire [(C_S_AXI_DATA_WIDTH/8)-1 : 0] S_AXI_WSTRB,
		// Write valid. This signal indicates that valid write
    		// data and strobes are available.
		input wire  S_AXI_WVALID,
		// Write ready. This signal indicates that the slave
    		// can accept the write data.
		output wire  S_AXI_WREADY,
		// Write response. This signal indicates the status
    		// of the write transaction.
		output wire [1 : 0] S_AXI_BRESP,
		// Write response valid. This signal indicates that the channel
    		// is signaling a valid write response.
		output wire  S_AXI_BVALID,
		// Response ready. This signal indicates that the master
    		// can accept a write response.
		input wire  S_AXI_BREADY,
		// Read address (issued by master, acceped by Slave)
		input wire [C_S_AXI_ADDR_WIDTH-1 : 0] S_AXI_ARADDR,
		// Protection type. This signal indicates the privilege
    		// and security level of the transaction, and whether the
    		// transaction is a data access or an instruction access.
		input wire [2 : 0] S_AXI_ARPROT,
		// Read address valid. This signal indicates that the channel
    		// is signaling valid read address and control information.
		input wire  S_AXI_ARVALID,
		// Read address ready. This signal indicates that the slave is
    		// ready to accept an address and associated control signals.
		output wire  S_AXI_ARREADY,
		// Read data (issued by slave)
		output wire [C_S_AXI_DATA_WIDTH-1 : 0] S_AXI_RDATA,
		// Read response. This signal indicates the status of the
    		// read transfer.
		output wire [1 : 0] S_AXI_RRESP,
		// Read valid. This signal indicates that the channel is
    		// signaling the required read data.
		output wire  S_AXI_RVALID,
		// Read ready. This signal indicates that the master can
    		// accept the read data and response information.
		input wire  S_AXI_RREADY
	);

	// AXI4LITE signals
	reg [C_S_AXI_ADDR_WIDTH-1 : 0] 	axi_awaddr;
	reg  	axi_awready;
	reg  	axi_wready;
	reg [1 : 0] 	axi_bresp;
	reg  	axi_bvalid;
	reg [C_S_AXI_ADDR_WIDTH-1 : 0] 	axi_araddr;
	reg  	axi_arready;
	reg [C_S_AXI_DATA_WIDTH-1 : 0] 	axi_rdata;
	reg [1 : 0] 	axi_rresp;
	reg  	axi_rvalid;

	// Example-specific design signals
	// local parameter for addressing 32 bit / 64 bit C_S_AXI_DATA_WIDTH
	// ADDR_LSB is used for addressing 32/64 bit registers/memories
	// ADDR_LSB = 2 for 32 bits (n downto 2)
	// ADDR_LSB = 3 for 64 bits (n downto 3)
	localparam integer ADDR_LSB = (C_S_AXI_DATA_WIDTH/32) + 1;
	localparam integer OPT_MEM_ADDR_BITS = 2;
	//----------------------------------------------
	//-- Signals for user logic register space example
	//------------------------------------------------
	//-- Number of Slave Registers 8
	reg [C_S_AXI_DATA_WIDTH-1:0]	slv_reg0;
	reg [C_S_AXI_DATA_WIDTH-1:0]	slv_reg1;
	reg [C_S_AXI_DATA_WIDTH-1:0]	slv_reg2;
	reg [C_S_AXI_DATA_WIDTH-1:0]	slv_reg3;
	reg [C_S_AXI_DATA_WIDTH-1:0]	slv_reg4;
	reg [C_S_AXI_DATA_WIDTH-1:0]	slv_reg5;
	reg [C_S_AXI_DATA_WIDTH-1:0]	slv_reg6;
	reg [C_S_AXI_DATA_WIDTH-1:0]	slv_reg7;
	wire	 slv_reg_rden;
	wire	 slv_reg_wren;
	reg [C_S_AXI_DATA_WIDTH-1:0]	 reg_data_out;
	integer	 byte_index;
	reg	 aw_en;

	// I/O Connections assignments

	assign S_AXI_AWREADY	= axi_awready;
	assign S_AXI_WREADY	= axi_wready;
	assign S_AXI_BRESP	= axi_bresp;
	assign S_AXI_BVALID	= axi_bvalid;
	assign S_AXI_ARREADY	= axi_arready;
	assign S_AXI_RDATA	= axi_rdata;
	assign S_AXI_RRESP	= axi_rresp;
	assign S_AXI_RVALID	= axi_rvalid;
	// Implement axi_awready generation
	// axi_awready is asserted for one S_AXI_ACLK clock cycle when both
	// S_AXI_AWVALID and S_AXI_WVALID are asserted. axi_awready is
	// de-asserted when reset is low.

	always @( posedge S_AXI_ACLK )
	begin
	  if ( S_AXI_ARESETN == 1'b0 )
	    begin
	      axi_awready <= 1'b0;
	      aw_en <= 1'b1;
	    end 
	  else
	    begin    
	      if (~axi_awready && S_AXI_AWVALID && S_AXI_WVALID && aw_en)
	        begin
	          // slave is ready to accept write address when 
	          // there is a valid write address and write data
	          // on the write address and data bus. This design 
	          // expects no outstanding transactions. 
	          axi_awready <= 1'b1;
	          aw_en <= 1'b0;
	        end
	        else if (S_AXI_BREADY && axi_bvalid)
	            begin
	              aw_en <= 1'b1;
	              axi_awready <= 1'b0;
	            end
	      else           
	        begin
	          axi_awready <= 1'b0;
	        end
	    end 
	end       

	// Implement axi_awaddr latching
	// This process is used to latch the address when both 
	// S_AXI_AWVALID and S_AXI_WVALID are valid. 

	always @( posedge S_AXI_ACLK )
	begin
	  if ( S_AXI_ARESETN == 1'b0 )
	    begin
	      axi_awaddr <= 0;
	    end 
	  else
	    begin    
	      if (~axi_awready && S_AXI_AWVALID && S_AXI_WVALID && aw_en)
	        begin
	          // Write Address latching 
	          axi_awaddr <= S_AXI_AWADDR;
	        end
	    end 
	end       

	// Implement axi_wready generation
	// axi_wready is asserted for one S_AXI_ACLK clock cycle when both
	// S_AXI_AWVALID and S_AXI_WVALID are asserted. axi_wready is 
	// de-asserted when reset is low. 

	always @( posedge S_AXI_ACLK )
	begin
	  if ( S_AXI_ARESETN == 1'b0 )
	    begin
	      axi_wready <= 1'b0;
	    end 
	  else
	    begin    
	      if (~axi_wready && S_AXI_WVALID && S_AXI_AWVALID && aw_en )
	        begin
	          // slave is ready to accept write data when 
	          // there is a valid write address and write data
	          // on the write address and data bus. This design 
	          // expects no outstanding transactions. 
	          axi_wready <= 1'b1;
	        end
	      else
	        begin
	          axi_wready <= 1'b0;
	        end
	    end 
	end       

	// Implement memory mapped register select and write logic generation
	// The write data is accepted and written to memory mapped registers when
	// axi_awready, S_AXI_WVALID, axi_wready and S_AXI_WVALID are asserted. Write strobes are used to
	// select byte enables of slave registers while writing.
	// These registers are cleared when reset (active low) is applied.
	// Slave register write enable is asserted when valid address and data are available
	// and the slave is ready to accept the write address and write data.
	assign slv_reg_wren = axi_wready && S_AXI_WVALID && axi_awready && S_AXI_AWVALID;

	always @( posedge S_AXI_ACLK )
	begin
	  if ( S_AXI_ARESETN == 1'b0 )
	    begin
	      slv_reg0 <= 0;
	      slv_reg1 <= 0;
	      slv_reg2 <= 0;
	      slv_reg3 <= 0;
	    end 
	  else begin
	    if (slv_reg_wren)
	      begin
	        case ( axi_awaddr[ADDR_LSB+OPT_MEM_ADDR_BITS:ADDR_LSB] )
	          3'h0:
	            for ( byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index+1 )
	              if ( S_AXI_WSTRB[byte_index] == 1 ) begin
	                // Respective byte enables are asserted as per write strobes 
	                // Slave register 0
	                slv_reg0[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
	              end  
	          3'h1:
	            for ( byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index+1 )
	              if ( S_AXI_WSTRB[byte_index] == 1 ) begin
	                // Respective byte enables are asserted as per write strobes 
	                // Slave register 1
	                slv_reg1[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
	              end  
	          3'h2:
	            for ( byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index+1 )
	              if ( S_AXI_WSTRB[byte_index] == 1 ) begin
	                // Respective byte enables are asserted as per write strobes 
	                // Slave register 2
	                slv_reg2[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
	              end  
	          3'h3:
	            for ( byte_index = 0; byte_index <= (C_S_AXI_DATA_WIDTH/8)-1; byte_index = byte_index+1 )
	              if ( S_AXI_WSTRB[byte_index] == 1 ) begin
	                // Respective byte enables are asserted as per write strobes 
	                // Slave register 3
	                slv_reg3[(byte_index*8) +: 8] <= S_AXI_WDATA[(byte_index*8) +: 8];
	              end  
	          default : begin
	                      slv_reg0 <= slv_reg0;
	                      slv_reg1 <= slv_reg1;
	                      slv_reg2 <= slv_reg2;
	                      slv_reg3 <= slv_reg3;
	                    end
	        endcase
	      end
	  end
	end    

	// Implement write response logic generation
	// The write response and response valid signals are asserted by the slave 
	// when axi_wready, S_AXI_WVALID, axi_wready and S_AXI_WVALID are asserted.  
	// This marks the acceptance of address and indicates the status of 
	// write transaction.

	always @( posedge S_AXI_ACLK )
	begin
	  if ( S_AXI_ARESETN == 1'b0 )
	    begin
	      axi_bvalid  <= 0;
	      axi_bresp   <= 2'b0;
	    end 
	  else
	    begin    
	      if (axi_awready && S_AXI_AWVALID && ~axi_bvalid && axi_wready && S_AXI_WVALID)
	        begin
	          // indicates a valid write response is available
	          axi_bvalid <= 1'b1;
	          axi_bresp  <= 2'b0; // 'OKAY' response 
	        end                   // work error responses in future
	      else
	        begin
	          if (S_AXI_BREADY && axi_bvalid) 
	            //check if bready is asserted while bvalid is high) 
	            //(there is a possibility that bready is always asserted high)   
	            begin
	              axi_bvalid <= 1'b0; 
	            end  
	        end
	    end
	end   

	// Implement axi_arready generation
	// axi_arready is asserted for one S_AXI_ACLK clock cycle when
	// S_AXI_ARVALID is asserted. axi_awready is 
	// de-asserted when reset (active low) is asserted. 
	// The read address is also latched when S_AXI_ARVALID is 
	// asserted. axi_araddr is reset to zero on reset assertion.

	always @( posedge S_AXI_ACLK )
	begin
	  if ( S_AXI_ARESETN == 1'b0 )
	    begin
	      axi_arready <= 1'b0;
	      axi_araddr  <= 32'b0;
	    end 
	  else
	    begin    
	      if (~axi_arready && S_AXI_ARVALID)
	        begin
	          // indicates that the slave has acceped the valid read address
	          axi_arready <= 1'b1;
	          // Read address latching
	          axi_araddr  <= S_AXI_ARADDR;
	        end
	      else
	        begin
	          axi_arready <= 1'b0;
	        end
	    end 
	end       

	// Implement axi_arvalid generation
	// axi_rvalid is asserted for one S_AXI_ACLK clock cycle when both 
	// S_AXI_ARVALID and axi_arready are asserted. The slave registers 
	// data are available on the axi_rdata bus at this instance. The 
	// assertion of axi_rvalid marks the validity of read data on the 
	// bus and axi_rresp indicates the status of read transaction.axi_rvalid 
	// is deasserted on reset (active low). axi_rresp and axi_rdata are 
	// cleared to zero on reset (active low).  
	always @( posedge S_AXI_ACLK )
	begin
	  if ( S_AXI_ARESETN == 1'b0 )
	    begin
	      axi_rvalid <= 0;
	      axi_rresp  <= 0;
	    end 
	  else
	    begin    
	      if (axi_arready && S_AXI_ARVALID && ~axi_rvalid)
	        begin
	          // Valid read data is available at the read data bus
	          axi_rvalid <= 1'b1;
	          axi_rresp  <= 2'b0; // 'OKAY' response
	        end   
	      else if (axi_rvalid && S_AXI_RREADY)
	        begin
	          // Read data is accepted by the master
	          axi_rvalid <= 1'b0;
	        end                
	    end
	end    

	// Implement memory mapped register select and read logic generation
	// Slave register read enable is asserted when valid address is available
	// and the slave is ready to accept the read address.
	assign slv_reg_rden = axi_arready & S_AXI_ARVALID & ~axi_rvalid;
	always @(*)
	begin
	      // Address decoding for reading registers
	      case ( axi_araddr[ADDR_LSB+OPT_MEM_ADDR_BITS:ADDR_LSB] )
	        3'h0   : reg_data_out <= slv_reg0;
	        3'h1   : reg_data_out <= slv_reg1;
	        3'h2   : reg_data_out <= slv_reg2;
	        3'h3   : reg_data_out <= slv_reg3;
	        3'h4   : reg_data_out <= slv_reg4;
	        3'h5   : reg_data_out <= slv_reg5;
	        3'h6   : reg_data_out <= slv_reg6;
	        3'h7   : reg_data_out <= slv_reg7;
	        default : reg_data_out <= 0;
	      endcase
	end

	// Output register or memory read data
	always @( posedge S_AXI_ACLK )
	begin
	  if ( S_AXI_ARESETN == 1'b0 )
	    begin
	      axi_rdata  <= 0;
	    end 
	  else
	    begin    
	      // When there is a valid read address (S_AXI_ARVALID) with 
	      // acceptance of read address by the slave (axi_arready), 
	      // output the read dada 
	      if (slv_reg_rden)
	        begin
	          axi_rdata <= reg_data_out;     // register read data
	        end   
	    end
	end    

	// Add user logic here
	
	// Register functionality
	// Inputs (reg0-reg2 are currently non functional)
	// slv_reg0: flags for normal operation (flush, rw_select, wdata_valid, addr_valid)
	// slv_reg1: address
	// slv_reg2: write data
	// slv_reg3: amount of data in the trace
	// Outputs
	// slv_reg5: rdata
	// slv_reg6: hit, rdata_valid, w_done, p_ready
	// slv_reg7: trace done
	
	// Trace structure: one instruction/request per word in the format of {write_enable, (padding), write data, address}
	// If write_enable is 0, the request is a read request, else it is a write request

	// do some assignments to signals that are currently static
	assign trace_bram_write_enable = 0;
	assign trace_bram_reset = 0;
	assign stats_bram_reset = 0;
    
	// Cache input/output signals
    reg[CACHE_ADDRESS_WIDTH-1 : 0] cache_address;
    reg cache_address_valid;
    reg[CACHE_DATA_WIDTH-1 : 0] cache_write_data;
    reg cache_write_data_valid;
    reg cache_read_write_select;
	reg cache_flush;
    
    wire[CACHE_DATA_WIDTH-1 : 0] cache_read_data;
    wire cache_read_data_valid;
    wire cache_write_done;
    wire cache_port_ready;
	wire cache_hit;
    
    // State of the trace
    reg[C_S_AXI_DATA_WIDTH-1 : 0] trace_index; // the index (not the address) of the current instruction
    reg[C_S_AXI_DATA_WIDTH-1 : 0] trace_length; // the number of instructions in the trace
    reg[$clog2(TRACE_BRAM_READ_LATENCY+1)-1 : 0] bram_stall; // time for stalling until the bram is done
    reg[2 : 0] trace_state;   // 0: not started, 1: send bram request, 2: stall for bram/wait for cache/send trace instruction to cache
                            // 3: wait for cache to process the last instruction/write back statistics to bram, 4: report trace done
    reg[STATS_BRAM_DATA_WIDTH-1 : 0] latency_counter; // total time spent waiting for the cache
                            
    always @(posedge S_AXI_ACLK, negedge S_AXI_ARESETN) begin
        if (S_AXI_ARESETN == 0) begin
            cache_address <= 0;
            cache_address_valid <= 0;
            cache_write_data <= 0;
            cache_write_data_valid <= 0;
            cache_read_write_select <= 0;
            trace_bram_enable <= 0;
            trace_bram_address <= 0;
            trace_bram_write_data <= 0;
            stats_bram_enable <= 0;
            stats_bram_address <= 0;
            stats_bram_write_data <= 0;
            stats_bram_write_enable <= 0;
            trace_index <= 0;
            trace_length <= 0;
            cache_flush <= 0;
            trace_state <= 0;
            bram_stall <= 0;
            latency_counter <= 0;
            slv_reg4 <= 0;
            slv_reg5 <= 0;
            slv_reg6 <= 0;
            slv_reg7 <= 0;
        end else begin
            // write cache outputs to the slave registers so we can at least see something
            slv_reg5 <= {28'b0, cache_hit, cache_read_data_valid, cache_write_done, cache_port_ready};
            slv_reg6 <= {{CACHE_DATA_WIDTH{1'b0}}, cache_read_data};
            if (trace_state == 0) begin
                // not currently processing the trace
                trace_length <= slv_reg3; // always accept the new length
                if (slv_reg3 != 0 && slv_reg3 != trace_length) begin
                    // start processing the trace
                    // input trace length (slv_reg3) must be not 0 and not the previous length so we don't repeat the trace accidentally
                    trace_state <= 1;
                    trace_index <= 0;
                    slv_reg7 <= 0; // reset trace_done
                end else begin
                    // just pass on normal requests to the cache
                    cache_address_valid <= slv_reg0[0];
                    cache_write_data_valid <= slv_reg0[1];
                    cache_read_write_select <= slv_reg0[2];
                    cache_flush <= slv_reg0[3];
                    cache_address <= slv_reg1[CACHE_ADDRESS_WIDTH-1 : 0];
                    cache_write_data <= slv_reg2[CACHE_DATA_WIDTH-1 : 0];
                end
            end else if (trace_state == 1) begin
                cache_address_valid <= 0;    // invalidate request to cache that we might have sent if
                cache_write_data_valid <= 0; // this is not the first instruction we're currently processing
                if (trace_index != 0) begin
                    // increment latency counter, unless we haven't even sent a request yet.
                    // every cache needs at least one cycle, so we don't need to check if it is done yet.
                    latency_counter <= latency_counter + 1; 
                end
                if (trace_index < trace_length) begin
                    // send a new request to the bram
                    // Each byte must be 8 bits and word size (TRACE_BRAM_DATA_WIDTH) must be a power of two
                    trace_bram_address <= {trace_index[TRACE_BRAM_ADDRESS_WIDTH-$clog2(TRACE_BRAM_DATA_WIDTH / 8)-1:0], {$clog2(TRACE_BRAM_DATA_WIDTH / 8){1'b0}}};
                    trace_bram_enable <= 1'b1;
                    trace_index <= trace_index + 1;
                    trace_state <= 2;
                    bram_stall <= TRACE_BRAM_READ_LATENCY + 1; // + 1 so the bram can accept the request?
                end else begin
                    // this was the final instruction. Waste one cycle so the cache can accept the request.
                    trace_state <= 3;
                end
            end else if (trace_state == 2) begin
                if (cache_port_ready != 1) begin
                    // increment latency
                    latency_counter <= latency_counter + 1;
                end
                if (bram_stall != 0) begin
                    // stall until the bram has processed the request. Should be 2 cycles.
                    bram_stall <= bram_stall - 1;
                end else if (cache_port_ready == 1) begin
                    // bram is done, send request to cache as soon as it becomes ready
                    cache_read_write_select <= trace_bram_read_data[TRACE_BRAM_DATA_WIDTH-1];
                    cache_write_data_valid <= trace_bram_read_data[TRACE_BRAM_DATA_WIDTH-1];
                    cache_address_valid <= 1'b1;
                    cache_address <= trace_bram_read_data[CACHE_ADDRESS_WIDTH-1 : 0];
                    cache_write_data <= trace_bram_read_data[CACHE_DATA_WIDTH + CACHE_ADDRESS_WIDTH - 1 : CACHE_ADDRESS_WIDTH];
                    trace_state <= 1; // fetch the next instruction
                end
            end else if (trace_state == 3) begin
                if (cache_port_ready == 1) begin
                    // cache is done with the last instruction - write latency to bram
                    stats_bram_address <= 0;
                    stats_bram_write_data <= latency_counter;
                    stats_bram_enable <= 1;
                    stats_bram_write_enable <= 1;
                    trace_state <= 4;                    
                end else begin
                    latency_counter <= latency_counter + 1;
                end
            end else if (trace_state == 4) begin
                stats_bram_enable <= 0; // stop writing latency to bram
                stats_bram_write_enable <= 0;
                trace_state <= 0;
                slv_reg7 <= 1; // set trace_done
            end
        end     
    end
    
    cache_wrapper
    cache_wrapper_1 (
        .clk_i(S_AXI_ACLK),
        .reset_n_i(S_AXI_ARESETN),
        .flush_i(cache_flush),
        .hit_o(cache_hit),
        .address_0_i(cache_address),
        .address_valid_0_i(cache_address_valid),
        .write_data_0_i(cache_write_data),
        .write_data_valid_0_i(cache_write_data_valid),
        .read_write_select_0_i(cache_read_write_select),
        .read_data_0_o(cache_read_data),
        .read_data_valid_0_o(cache_read_data_valid),
        .write_done_0_o(cache_write_done),
        .port_ready_0_o(cache_port_ready)
    );
	// User logic ends

	endmodule
