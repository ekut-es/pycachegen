#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include "Vcache_wrapper.h"

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

    const std::unique_ptr<Vcache_wrapper> cache_wrapper{new Vcache_wrapper{"cache_wrapper"}};

    cache_wrapper->clk_i(clk_i);
    cache_wrapper->reset_n_i(reset_n_i);

    cache_wrapper->address_i(address_i);
    cache_wrapper->address_valid_i(address_valid_i);
    cache_wrapper->write_data_i(write_data_i);
    cache_wrapper->write_data_valid_i(write_data_valid_i);
    cache_wrapper->read_write_select_i(read_write_select_i);

    cache_wrapper->read_data_o(read_data_o);
    cache_wrapper->read_data_valid_o(read_data_valid_o);
    cache_wrapper->write_done_o(write_done_o);
    cache_wrapper->port_ready_o(port_ready_o);

    std::cout << "Vcache_wrapper start!" << std::endl;

    sc_start(0, SC_NS);

    VerilatedVcdSc *trace = new VerilatedVcdSc();
    cache_wrapper->trace(trace, 99);

    if (vcd_file_path.empty())
    {
        trace->open("Vcache_wrapper_tb.vcd");
    }
    else
    {
        trace->open(vcd_file_path.c_str());
    }

    // do stuff
    sc_start(1, SC_NS);
    reset_n_i.write(1);
    sc_start(1, SC_NS);

    address_i.write(4);
    address_valid_i.write(1);
    write_data_i.write(242);
    write_data_valid_i.write(1);
    read_write_select_i.write(1);
    sc_start(1, SC_NS);

    address_valid_i.write(0);
    sc_start(1, SC_NS);

    while(!write_done_o.read()){
        sc_start(1, SC_NS);
    }
    sc_start(1, SC_NS);

    address_valid_i.write(1);
    read_write_select_i.write(0);
    sc_start(1, SC_NS);

    address_valid_i.write(0);
    sc_start(1, SC_NS);

    while(!read_data_valid_o.read()){
        sc_start(1, SC_NS);
    }
    sc_start(1, SC_NS);


    sc_start(10, SC_NS);

    cache_wrapper->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "Vcache_wrapper done!" << std::endl;
    return 0;
}