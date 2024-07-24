#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include <iostream>

#include "Vcache_wrapper_26.h"

// Testbench for testing the write-back, write allocate policy
// num_ports=1, arbiter_policy=priority, byte_size=8
// enable_reset=false, address_width=9
// L1: data_width=16, num_ways=1, num_sets=2,
// replacement_policy=fifo, hit_latency=0, miss_latency=0,
// write_through=false, write_allocate=true, block_size=1
// Main Memory: data_width=16, read_latency=10, write_latency=15
// min_address=0, max_address=512

int sc_main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);

    std::string vcd_file_path;

    if (argc == 2) {
        vcd_file_path = std::string(argv[1]);
    }

    const int hit_latency = 4;
    const int miss_dirty_write_latency = 8;
    const int miss_dirty_read_latency = 11;
    const int miss_ndirty_write_latency = 5;
    const int miss_ndirty_read_latency = 8;

    const int mem_read_latency = 10;
    const int mem_write_latency = 15;

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

    const std::unique_ptr<Vcache_wrapper_26> cache_wrapper{
        new Vcache_wrapper_26{"cache_wrapper"}};

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

    int exit_code = 0;

    std::cout << "Vcache_wrapper_26 start!" << std::endl;

    sc_start(0, SC_NS);

    VerilatedVcdSc* trace = new VerilatedVcdSc();
    cache_wrapper->trace(trace, 99);

    if (vcd_file_path.empty()) {
        trace->open("Vcache_wrapper_tb_26.vcd");
    } else {
        trace->open(vcd_file_path.c_str());
    }

    try {
        // do stuff
        sc_start(1, SC_NS);
        reset_n_i.write(1);
        sc_start(1, SC_NS);

        address_i.write(4);
        address_valid_i.write(1);
        write_data_i.write(0x12);
        write_data_valid_i.write(1);
        read_write_select_i.write(1);
        sc_start(1, SC_NS);
        address_valid_i.write(0);
        sc_start(miss_ndirty_write_latency + 1, SC_NS);
        assert(write_done_o.read());

        address_i.write(4);
        address_valid_i.write(1);
        write_data_valid_i.write(0);
        read_write_select_i.write(0);
        sc_start(1, SC_NS);
        address_valid_i.write(0);   
        sc_start(hit_latency + 1, SC_NS);
        assert(read_data_valid_o.read() == 1 && read_data_o.read() == 0x12);

        address_i.write(6);
        address_valid_i.write(1);
        write_data_valid_i.write(0);
        read_write_select_i.write(0);
        sc_start(1, SC_NS);
        address_valid_i.write(0);   
        sc_start(miss_ndirty_read_latency + mem_read_latency + 1, SC_NS);
        assert(read_data_valid_o.read() == 1 && read_data_o.read() == 0x0);

        address_i.write(6);
        address_valid_i.write(1);
        write_data_i.write(0x13);
        write_data_valid_i.write(1);
        read_write_select_i.write(1);
        sc_start(1, SC_NS);
        address_valid_i.write(0);
        sc_start(hit_latency + 1, SC_NS);
        assert(write_done_o.read());

        address_i.write(8);
        address_valid_i.write(1);
        write_data_valid_i.write(0);
        read_write_select_i.write(0);
        sc_start(1, SC_NS);
        address_valid_i.write(0);   
        sc_start(miss_dirty_read_latency + mem_write_latency + mem_read_latency + 1, SC_NS);
        assert(read_data_valid_o.read() == 1 && read_data_o.read() == 0x0);

        address_i.write(10);
        address_valid_i.write(1);
        write_data_i.write(0x15);
        write_data_valid_i.write(1);
        read_write_select_i.write(1);
        sc_start(1, SC_NS);
        address_valid_i.write(0);
        sc_start(miss_dirty_write_latency + mem_write_latency + 1, SC_NS);
        assert(write_done_o.read());

        sc_start(10, SC_NS);
    } catch (std::runtime_error& e) {
        std::cerr << e.what() << std::endl;
        exit_code = 1;
    }

    cache_wrapper->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "Vcache_wrapper_26 done!" << std::endl;
    return exit_code;
}