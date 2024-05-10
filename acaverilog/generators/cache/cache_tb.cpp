#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include "Vcache.h"

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

    sc_clock clk_i{"clk_i", 1, SC_NS, 0.5, 0, SC_NS, true};
    sc_signal<bool> reset_n_i;
    sc_signal<uint32_t> address_i;
    sc_signal<bool> address_valid_i;
    sc_signal<uint32_t> write_data_i;
    sc_signal<bool> write_data_valid_i;
    sc_signal<bool> read_write_select_i;

    sc_signal<uint32_t> read_data_o;
    sc_signal<bool> read_data_valid_o;
    sc_signal<bool> write_done_o;
    sc_signal<bool> port_ready_o;

    sc_signal<uint32_t> read_data_i;
    sc_signal<bool> read_data_valid_i;
    sc_signal<bool> write_done_i;
    sc_signal<bool> port_ready_i;

    sc_signal<uint32_t> address_o;
    sc_signal<bool> address_valid_o;
    sc_signal<uint32_t> write_data_o;
    sc_signal<bool> write_data_valid_o;
    sc_signal<bool> read_write_select_o;

    const std::unique_ptr<Vcache> cache{new Vcache{"cache"}};

    cache->clk_i(clk_i);
    cache->reset_n_i(reset_n_i);
    cache->address_i(address_i);
    cache->address_valid_i(address_valid_i);
    cache->write_data_i(write_data_i);
    cache->write_data_valid_i(write_data_valid_i);
    cache->read_write_select_i(read_write_select_i);
    cache->read_data_o(read_data_o);
    cache->read_data_valid_o(read_data_valid_o);
    cache->write_done_o(write_done_o);
    cache->port_ready_o(port_ready_o);
    cache->read_data_i(read_data_i);
    cache->read_data_valid_i(read_data_valid_i);
    cache->write_done_i(write_done_i);
    cache->port_ready_i(port_ready_i);
    cache->address_o(address_o);
    cache->address_valid_o(address_valid_o);
    cache->write_data_o(write_data_o);
    cache->write_data_valid_o(write_data_valid_o);
    cache->read_write_select_o(read_write_select_o);

    std::cout << "Vcache start!" << std::endl;

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

    // do stuff

    sc_start(10, SC_NS);

    cache->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "Vcache done!" << std::endl;
    return 0;
}