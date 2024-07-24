#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include <iostream>

#include "Vcache_wrapper_3.h"

// Testbench for testing the FIFO replacement policy
// num_ports=1, arbiter_policy=priority, byte_size=8
// enable_reset=false, address_width=9
// L1: data_width=16, num_ways=4, num_sets=2,
// replacement_policy=fifo, hit_latency=6, miss_latency=8,
// write_through=true, write_allocate=false, block_size=1
// Main Memory: data_width=16, read_latency=10, write_latency=15
// min_address=0, max_address=512

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

    sc_signal<uint32_t> address_i;
    sc_signal<bool> address_valid_i;
    sc_signal<uint32_t> write_data_i;
    sc_signal<bool> write_data_valid_i;
    sc_signal<bool> read_write_select_i;

    sc_signal<uint32_t> read_data_o;
    sc_signal<bool> read_data_valid_o;
    sc_signal<bool> write_done_o;
    sc_signal<bool> port_ready_o;
    sc_signal<bool> hit_o;
    sc_signal<bool> flush_done_o;

    const std::unique_ptr<Vcache_wrapper_3> cache_wrapper{
        new Vcache_wrapper_3{"cache_wrapper"}};

    cache_wrapper->clk_i(clk_i);
    cache_wrapper->reset_n_i(reset_n_i);
    cache_wrapper->flush_i(flush_i);
    cache_wrapper->hit_o(hit_o);
    cache_wrapper->flush_done_o(flush_done_o);

    cache_wrapper->address_0_i(address_i);
    cache_wrapper->address_valid_0_i(address_valid_i);
    cache_wrapper->write_data_0_i(write_data_i);
    cache_wrapper->write_data_valid_0_i(write_data_valid_i);
    cache_wrapper->read_write_select_0_i(read_write_select_i);

    cache_wrapper->read_data_0_o(read_data_o);
    cache_wrapper->read_data_valid_0_o(read_data_valid_o);
    cache_wrapper->write_done_0_o(write_done_o);
    cache_wrapper->port_ready_0_o(port_ready_o);

    const int MAX_SIMULATION_TIME = 1000;
    int exit_code = 0;

    auto tick = [&](int amount) {
        if (sc_time_stamp().to_default_time_units() > MAX_SIMULATION_TIME) {
            throw std::runtime_error("Exceeded maximum simulation time");
        }
        sc_start(amount, SC_NS);
    };

    auto read_assert = [&](int address, int expected) {
        if (read_data_o.read() == expected) {
            std::cout << "Read  at address " << address << " at cycle "
                      << sc_time_stamp().to_default_time_units()
                      << " successful" << std::endl;
        } else {
            std::cerr << "Read  at address " << address << " at cycle "
                      << sc_time_stamp().to_default_time_units()
                      << " FAILED; expected " << std::to_string(expected)
                      << " got " << std::to_string(read_data_o.read())
                      << "; continuing" << std::endl;
            exit_code = 1;
        }
    };

    auto hit_assert = [&](bool expected) {
        if (hit_o.read() != expected) {
            std::cerr << "Error: Expected hit to be "
                      << std::to_string(expected) << " but got "
                      << std::to_string(hit_o.read()) << std::endl;
            exit_code = 1;
        }
    };

    auto read = [&](int address, int expected, bool hit) {
        address_i.write(address);
        address_valid_i.write(1);
        read_write_select_i.write(0);
        tick(1);
        address_valid_i.write(0);
        tick(1);
        while (!port_ready_o.read()) {
            tick(1);
        }
        read_assert(address, expected);
        hit_assert(hit);
    };

    auto write = [&](int address, int data, bool hit) {
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
        std::cout << "Write at address " << std::to_string(address)
                  << " at cycle " << sc_time_stamp().to_default_time_units()
                  << " successful" << std::endl;
        hit_assert(hit);
    };

    auto flush = [&]() {
        flush_i.write(1);
        tick(1);
        flush_i.write(0);
        tick(1);
        while (!flush_done_o.read()) {
            tick(1);
        }
        std::cout << "Flush complete" << std::endl;
    };


    std::cout << "Vcache_wrapper_3 start!" << std::endl;

    tick(0);

    VerilatedVcdSc* trace = new VerilatedVcdSc();
    cache_wrapper->trace(trace, 99);

    if (vcd_file_path.empty()) {
        trace->open("Vcache_wrapper_tb_3.vcd");
    } else {
        trace->open(vcd_file_path.c_str());
    }

    try {
        // do stuff
        tick(1);
        reset_n_i.write(1);
        tick(1);

        read(2, 0, false);
        read(2, 0, true);
        read(4, 0, false);
        read(4, 0, true);
        read(6, 0, false);
        read(6, 0, true);
        read(8, 0, false);
        read(8, 0, true);

        write(2, 2, true);
        write(4, 4, true);
        write(6, 6, true);
        write(8, 8, true);

        read(2, 2, true);
        read(2, 2, true);
        read(10, 0, false);
        read(2, 2, false);
        read(2, 2, true);
        read(10, 0, true);
        read(6, 6, true);
        read(8, 8, true);
        read(4, 4, false);

        tick(10);
    } catch (std::runtime_error& e) {
        std::cerr << e.what() << std::endl;
        exit_code = 1;
    }

    cache_wrapper->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "Vcache_wrapper_3 done!" << std::endl;
    return exit_code;
}