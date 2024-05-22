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

    const int MAX_SIMULATION_TIME = 1000;

    auto tick = [&](int amount) {
        if (sc_time_stamp().to_default_time_units() > MAX_SIMULATION_TIME) {
            throw std::runtime_error("Exceeded maximum simulation time");
        }
        sc_start(amount, SC_NS);
    };

    auto read_assert = [&](int expected) {
        if (read_data_o.read() == expected) {
            std::cout << "Read Successful at cycle "
                      << sc_time_stamp().to_default_time_units() << std::endl;
        } else {
            cerr << "Read failed at "
                 << sc_time_stamp().to_default_time_units() << "; expected "
                 << std::to_string(expected) << " got "
                 << std::to_string(read_data_o.read()) << "; continuing"
                 << std::endl;
        }
    };

    auto read = [&](int address, int expected) {
        address_i.write(address);
        address_valid_i.write(1);
        read_write_select_i.write(0);
        tick(1);
        address_valid_i.write(0);
        tick(1);
        while (!port_ready_o.read()) {
            tick(1);
        }
        read_assert(expected);
    };

    auto write = [&](int address, int data) {
        address_i.write(address);
        address_valid_i.write(1);
        write_data_i.write(data);
        write_data_valid_i.write(1);
        read_write_select_i.write(1);
        tick(1);
        address_valid_i.write(0);
        tick(1);
        while (!port_ready_o.read()) {
            tick(1);
        }
        std::cout << "Write to address " << std::to_string(address)
                  << std::endl;
    };

    std::cout << "Vfunctional_memory start!" << std::endl;

    tick(0);

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
    tick(1);
    reset_n_i.write(1);
    tick(1);

    read(0, 0);
    read(1, 0);
    read(2, 0);
    read(3, 0);
    
    write(4, 333);
    read(4, 333);
    read(0, 0);

    sc_start(10, SC_NS);

    memory->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "Vfunctional_memory done!" << std::endl;
    return 0;
}