#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include <iostream>

#include "Vcache_wrapper_16.h"

// Testbench for testing multiple ports with an arbiter
// data_width=16, address_width=8, num_ways=4, num_sets=2,
// write_through=false, write_allocate=true,
// replacement_policy=plru_mru, hit_latency=8, miss_latency=10
// block_size=1, num_ports=2

int sc_main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);

    std::string vcd_file_path;

    if (argc == 2) {
        vcd_file_path = std::string(argv[1]);
    }

    sc_clock clk_i{"clk_i", 1, SC_NS, 0.5, 0, SC_NS, true};
    sc_signal<bool> reset_n_i;
    sc_signal<bool> flush_i;
    sc_signal<bool> hit_o;

    sc_signal<uint32_t> address_0_i;
    sc_signal<bool> address_valid_0_i;
    sc_signal<uint32_t> write_data_0_i;
    sc_signal<bool> write_data_valid_0_i;
    sc_signal<bool> read_write_select_0_i;

    sc_signal<uint32_t> read_data_0_o;
    sc_signal<bool> read_data_valid_0_o;
    sc_signal<bool> write_done_0_o;
    sc_signal<bool> port_ready_0_o;

    sc_signal<uint32_t> address_1_i;
    sc_signal<bool> address_valid_1_i;
    sc_signal<uint32_t> write_data_1_i;
    sc_signal<bool> write_data_valid_1_i;
    sc_signal<bool> read_write_select_1_i;

    sc_signal<uint32_t> read_data_1_o;
    sc_signal<bool> read_data_valid_1_o;
    sc_signal<bool> write_done_1_o;
    sc_signal<bool> port_ready_1_o;

    const std::unique_ptr<Vcache_wrapper_16> cache_wrapper{
        new Vcache_wrapper_16{"cache_wrapper"}};

    cache_wrapper->clk_i(clk_i);
    cache_wrapper->reset_n_i(reset_n_i);
    cache_wrapper->flush_i(flush_i);
    cache_wrapper->hit_o(hit_o);

    cache_wrapper->address_0_i(address_0_i);
    cache_wrapper->address_valid_0_i(address_valid_0_i);
    cache_wrapper->write_data_0_i(write_data_0_i);
    cache_wrapper->write_data_valid_0_i(write_data_valid_0_i);
    cache_wrapper->read_write_select_0_i(read_write_select_0_i);

    cache_wrapper->read_data_0_o(read_data_0_o);
    cache_wrapper->read_data_valid_0_o(read_data_valid_0_o);
    cache_wrapper->write_done_0_o(write_done_0_o);
    cache_wrapper->port_ready_0_o(port_ready_0_o);

    cache_wrapper->address_1_i(address_1_i);
    cache_wrapper->address_valid_1_i(address_valid_1_i);
    cache_wrapper->write_data_1_i(write_data_1_i);
    cache_wrapper->write_data_valid_1_i(write_data_valid_1_i);
    cache_wrapper->read_write_select_1_i(read_write_select_1_i);

    cache_wrapper->read_data_1_o(read_data_1_o);
    cache_wrapper->read_data_valid_1_o(read_data_valid_1_o);
    cache_wrapper->write_done_1_o(write_done_1_o);
    cache_wrapper->port_ready_1_o(port_ready_1_o);

    const int MAX_SIMULATION_TIME = 1000;

    auto tick = [&](int amount) {
        if (sc_time_stamp().to_default_time_units() > MAX_SIMULATION_TIME) {
            throw std::runtime_error("Exceeded maximum simulation time");
        }
        sc_start(amount, SC_NS);
    };

    std::cout << "Vcache_wrapper_16 start!" << std::endl;

    tick(0);

    VerilatedVcdSc* trace = new VerilatedVcdSc();
    cache_wrapper->trace(trace, 99);

    if (vcd_file_path.empty()) {
        trace->open("Vcache_wrapper_tb_16.vcd");
    } else {
        trace->open(vcd_file_path.c_str());
    }

    tick(1);
    reset_n_i.write(1);
    tick(1);

    address_0_i.write(2);
    address_valid_0_i.write(1);
    write_data_0_i.write(14);
    write_data_valid_0_i.write(1);
    read_write_select_0_i.write(1);

    address_1_i.write(2);
    address_valid_1_i.write(1);
    read_write_select_1_i.write(0);

    tick(1);
    address_valid_0_i.write(0);
    address_valid_1_i.write(0);

    tick(30);

    if(!write_done_0_o.read()) {
        std::cerr << "Write failed" << std::endl;
    }

    if(read_data_1_o.read() != 14 || !read_data_valid_1_o.read()) {
        std::cerr << "Read failed" << std::endl;
    }
        
    tick(10);

    cache_wrapper->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "Vcache_wrapper_16 done!" << std::endl;
    return 0;
}
