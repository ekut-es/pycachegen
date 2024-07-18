#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include <chrono>
#include <iostream>

#include "Vcustom_cache_wrapper.h"
#include "mem_trace.h"

// Testbench for executing traces on custom cache wrapper configurations

// Trace and cache configuration variables
// adjust these based on your own setup
const int trace_data_width = 32;
const int cache_address_width = 15;
const int cache_data_width = 16;

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

    const std::unique_ptr<Vcustom_cache_wrapper> cache_wrapper{
        new Vcustom_cache_wrapper{"cache_wrapper"}};

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

    std::cout << "Trace simulation start!" << std::endl;

    const auto start_time = std::chrono::system_clock::now();

    sc_start(0, SC_NS);

    VerilatedVcdSc* trace = new VerilatedVcdSc();
    cache_wrapper->trace(trace, 99);

    if (vcd_file_path.empty()) {
        trace->open("Vtracing_tb.vcd");
    } else {
        trace->open(vcd_file_path.c_str());
    }

    const int trace_bytes_per_word = (trace_data_width / 8);


    // Send all instructions to the cache, one after the other
    const int word_buffer_width = 64; // mem trace is a char array so I first read one trace word into a buffer
    // the size of that buffer must be known for shifting which I need to do for extracting the address, data, and write enable
    for (uint64_t i = 0; i < mem_trace_bin_len; i += 4) {
        // send the next instruction
        uint64_t word = 0;
        for (int j = 0; j < trace_bytes_per_word; j++) {
            word |= (mem_trace_bin[i + j] << (trace_data_width - (j + 1) * 8));
        }
        address_i.write((word << (word_buffer_width - cache_address_width)) >> (word_buffer_width - cache_address_width));
        address_valid_i.write(1);
        write_data_i.write((word << (word_buffer_width - cache_address_width - cache_data_width)) >> (word_buffer_width - cache_data_width));
        write_data_valid_i.write((word >> (word_buffer_width - 1)));
        read_write_select_i.write((word >> (word_buffer_width - 1)));
        // wait at least one cycle
        sc_start(1, SC_NS);
        // as soon as port_ready_o becomes true, the cache will have accepted the request we just sent
        // so wait until it becomes ready and then proceed with the next request
        while (!port_ready_o.read()) {
            sc_start(1, SC_NS);
        }
        address_valid_i.write(0);
    }
    // wait until the last instruction was processed
    sc_start(1, SC_NS);
    while (!port_ready_o.read()) {
        sc_start(1, SC_NS);
    }

    cache_wrapper->final();

    trace->flush();
    trace->close();

    delete trace;

    const auto simulated_time =
        sc_time_stamp().to_default_time_units() - 1; // subtract 1 because we wasted one cycle right at the beginning
    const auto end_time = std::chrono::system_clock::now();
    const auto elapsed_time = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time).count();

    std::cout << "Trace simulation done!" << std::endl;
    std::cout << "Trace execution took " << simulated_time << " cycles (simulation took " << elapsed_time << " ms)" << std::endl;
    return 0;
}