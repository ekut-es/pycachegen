#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include "Viob_cache_sim_wrapper.h"

#include <iostream>

int sc_main(int argc, char **argv)
{
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);

    std::string vcd_file_path;

    if (argc == 2)
    {
        vcd_file_path = std::string(argv[1]);
    }

    // Create Signals

    // Front-end interface (IOb native slave)
    sc_signal<bool> iob_valid_i;
    sc_signal<uint32_t> iob_addr_i;
    sc_signal<uint32_t> iob_wdata_i;
    sc_signal<uint32_t> iob_wstrb_i;
    sc_signal<uint32_t> iob_rdata_o;
    sc_signal<bool> iob_rvalid_o;
    sc_signal<bool> iob_ready_o;

    // Cache invalidate and write-trough buffer IO chain
    sc_signal<bool> invalidate_i;
    sc_signal<bool> invalidate_o;
    sc_signal<bool> wtb_empty_i;
    sc_signal<bool> wtb_empty_o;

    //General Interface Signals
    sc_clock clk_i{"clk_i", 1, SC_NS, 0.5, 0, SC_NS, true};
    sc_signal<bool> arst_i;

    const std::unique_ptr<Viob_cache_sim_wrapper> cache(new Viob_cache_sim_wrapper{"cache"});

    // Assign Signals
    cache->iob_valid_i(iob_valid_i);
    cache->iob_addr_i(iob_addr_i);
    cache->iob_wdata_i(iob_wdata_i);
    cache->iob_wstrb_i(iob_wstrb_i);
    cache->iob_rdata_o(iob_rdata_o);
    cache->iob_rvalid_o(iob_rvalid_o);
    cache->iob_ready_o(iob_ready_o);
    cache->invalidate_i(invalidate_i);
    cache->invalidate_o(invalidate_o);
    cache->wtb_empty_i(wtb_empty_i);
    cache->wtb_empty_o(wtb_empty_o);
    cache->clk_i(clk_i);
    cache->arst_i(arst_i);

    std::cout << "Viob_cache_sim_wrapper start!" << std::endl;

    sc_start(0, SC_NS);

    VerilatedVcdSc *trace = new VerilatedVcdSc();
    cache->trace(trace, 99);

    if (vcd_file_path.empty())
    {
        trace->open("Vcache_tb.vcd");
    }
    else
    {
        trace->open(vcd_file_path.c_str());
    }
    arst_i.write(1);
    sc_start(1, SC_NS);
    arst_i.write(0);
    sc_start(1, SC_NS);

    iob_valid_i.write(1);
    iob_wstrb_i.write(15);
    iob_addr_i.write(16);
    iob_wdata_i.write(100);
    sc_start(1, SC_NS);
    iob_addr_i.write(20);
    iob_wdata_i.write(200);
    sc_start(1, SC_NS);
    iob_addr_i.write(24);
    iob_wdata_i.write(300);
    sc_start(1, SC_NS);
    iob_addr_i.write(28);
    iob_wdata_i.write(400);
    sc_start(1, SC_NS);
    iob_addr_i.write(32);
    iob_wdata_i.write(500);
    sc_start(1, SC_NS);
    iob_valid_i.write(0);
    iob_wstrb_i.write(0);
    iob_addr_i.write(0);
    iob_wdata_i.write(0);
    sc_start(10, SC_NS);

    iob_valid_i.write(1);
    iob_wstrb_i.write(0);
    iob_addr_i.write(16);
    // sc_start(1, SC_NS);
    // iob_valid_i.write(0);
    // sc_start(1, SC_NS);
    // iob_addr_i.write(24);
    // sc_start(2, SC_NS);
    // iob_addr_i.write(28);
    // sc_start(2, SC_NS);
    // iob_addr_i.write(32);
    // sc_start(2, SC_NS);
    
    sc_start(10, SC_NS);

    cache->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "Viob_cache_sim_wrapper done!" << std::endl;
    return 0;
}