`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 07/02/2024 10:12:58 AM
// Design Name: 
// Module Name: tb
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////


module tb;
    reg tb_ACLK;
    reg tb_ARESETn;
   
    wire temp_clk;
    wire temp_rstn; 

    reg resp;
    reg[127:0] trace_done; // for some reason, when reading from an axi lite interface, you have to do a 128 bit aligned 128 bit read
    reg[31:0] total_latency;
    
    initial 
    begin       
        tb_ACLK = 1'b0;
    end
    
    //------------------------------------------------------------------------
    // Simple Clock Generator
    //------------------------------------------------------------------------
    
    always #5 tb_ACLK = !tb_ACLK; // 100 MHz clock?
       
    initial
    begin
    
        $display ("running the tb");
        
        tb_ARESETn = 1'b0;
        repeat(20)@(posedge tb_ACLK);        
        tb_ARESETn = 1'b1;
        @(posedge tb_ACLK);
        
        repeat(5) @(posedge tb_ACLK);
        tb.design_1_wrapper.design_1_i.zynq_ultra_ps_e_0.inst.por_srstb_reset(1'b1);
  	    tb.design_1_wrapper.design_1_i.zynq_ultra_ps_e_0.inst.por_srstb_reset(1'b1);
        #200;
        tb.design_1_wrapper.design_1_i.zynq_ultra_ps_e_0.inst.por_srstb_reset(1'b0);
        tb.design_1_wrapper.design_1_i.zynq_ultra_ps_e_0.inst.fpga_soft_reset(32'h1);
        #2000;  // This delay depends on your clock frequency. It should be at least 16 clock cycles. 
        tb.design_1_wrapper.design_1_i.zynq_ultra_ps_e_0.inst.por_srstb_reset(1'b1);
        tb.design_1_wrapper.design_1_i.zynq_ultra_ps_e_0.inst.fpga_soft_reset(32'h0);
		#2000;
        
        //Write to trace BRAM
        $display ("Writing trace to BRAM");
        tb.design_1_wrapper.design_1_i.zynq_ultra_ps_e_0.inst.write_data(32'h82000000, 4, 32'h80111100, resp); // write 0x1111 to 0x01
        tb.design_1_wrapper.design_1_i.zynq_ultra_ps_e_0.inst.write_data(32'h82000004, 4, 32'h80222201, resp); // write 0x2222 to 0x01
        tb.design_1_wrapper.design_1_i.zynq_ultra_ps_e_0.inst.write_data(32'h82000008, 4, 32'h80DEAD05, resp); // write 0xDEAD to 0x05
        tb.design_1_wrapper.design_1_i.zynq_ultra_ps_e_0.inst.write_data(32'h8200000C, 4, 32'h80BEEFAA, resp); // write 0xBEEF to 0xAA
		
        $display ("Starting trace execution");
        tb.design_1_wrapper.design_1_i.zynq_ultra_ps_e_0.inst.write_data(32'h8000000C, 4, 32'h00000004, resp); // set trace length to 4 to start the trace
        
        tb.design_1_wrapper.design_1_i.zynq_ultra_ps_e_0.inst.read_data(32'h80000010, 16, trace_done, resp);
        while (trace_done[3 * 32] == 0) begin
            tb.design_1_wrapper.design_1_i.zynq_ultra_ps_e_0.inst.read_data(32'h80000010, 16, trace_done, resp);
        end
        
        tb.design_1_wrapper.design_1_i.zynq_ultra_ps_e_0.inst.read_data(32'h84000000, 4, total_latency, resp);
        $display ("Trace execution finished");
        $display("Total execution time: 0x%0h", total_latency);
        $stop;
    end

    assign temp_clk = tb_ACLK;
    assign temp_rstn = tb_ARESETn;
    
    design_1_wrapper
    design_1_wrapper();
    
endmodule
