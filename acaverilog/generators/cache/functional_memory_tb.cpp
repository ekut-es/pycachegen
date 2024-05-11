#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include "Vfunctional_memory.h"

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

    const std::unique_ptr<Vfunctional_memory> memory{new Vfunctional_memory{"memory"}};

    memory->clk_i(clk_i);
    memory->reset_n_i(reset_n_i);

    memory->address_0_i(address_i);
    memory->address_valid_0_i(address_valid_i);
    memory->write_data_0_i(write_data_i);
    memory->write_data_valid_0_i(write_data_valid_i);
    memory->read_write_select_0_i(read_write_select_i);

    memory->read_data_0_o(read_data_o);
    memory->read_data_valid_0_o(read_data_valid_o);
    memory->write_done_0_o(write_done_o);
    memory->port_ready_0_o(port_ready_o);

    std::cout << "Vfunctional_memory start!" << std::endl;

    sc_start(0, SC_NS);

    VerilatedVcdSc *trace = new VerilatedVcdSc();
    memory->trace(trace, 99);

    if (vcd_file_path.empty())
    {
        trace->open("Vfunctional_memory_tb.vcd");
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

    memory->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "Vfunctional_memory done!" << std::endl;
    return 0;
}