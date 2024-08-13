#include <math.h>
#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <vector>

#include "Vcustom_cache_wrapper.h"

// Testbench for executing traces on custom cache wrapper configurations

// Trace and cache configuration variables
// adjust these based on your own setup
const int trace_data_width =
    32;  // must fit in the IntegerType and needs to be a multiple of 8
const int cache_address_width = 15;
const int cache_data_width = 16;
const int cache_address_byte_offset_width =
    2;  // number of byte offset bits in an address (usually
        // log2(cache_data_width/8)). only affects the reads at the end
const bool create_csv =
    false;  // whether to create CSV files showing which instructions created
            // hits and how long their execution took
using IntegerType =
    uint64_t;  // select an integer type that fits one instruction

/// @brief Extract bits from an integer.
/// @param num Number from which to extract the bits
/// @param start Start index (inclusive)
/// @param end End index (exclusive)
/// @return The extracted bits, shifted to the start
uint32_t extract_bits(IntegerType num, size_t start, size_t end) {
    size_t num_bits = end - start;
    size_t mask = (1 << num_bits) - 1;
    return (num >> start) & mask;
}

int sc_main(int argc, char** argv) {
    // argv[1]: path to trace file
    // argv[2]: path to result file (optional)

    if (argc < 2) {
        std::cerr << "Program needs to be called with at least one argument "
                     "specifying the trace file to use."
                  << std::endl;
        return 1;
    }
    std::string trace_file = std::string(argv[1]);

    // Create signals and connect them to the Cache Wrapper

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

    uint32_t sim_time = 0;  // amount of cycles that the simulation used

    // Functions for use during the simulation

    auto tick = [&](int amount) {
        sc_start(amount, SC_NS);
        sim_time += amount;
    };

    auto read = [&](int address) {
        address_i.write(address);
        address_valid_i.write(1);
        read_write_select_i.write(0);
        sc_start(1, SC_NS);
        address_valid_i.write(0);
        sc_start(1, SC_NS);
        while (!port_ready_o.read()) {
            sc_start(1, SC_NS);
        }
        std::cout << "Reading from address " << address << "... "
                  << read_data_o.read() << std::endl;
    };

    const size_t trace_bytes_per_word = (trace_data_width / 8);

    // Read the file
    std::ifstream file(trace_file, std::ios::in | std::ios::binary);
    if (!file) {
        std::cerr << "File could not be opened." << std::endl;
        return 1;
    }

    // Turn the file into a vector of instructions
    std::vector<IntegerType> instructions;
    uint8_t buffer[trace_bytes_per_word];
    while (file.read(reinterpret_cast<char*>(buffer), trace_bytes_per_word)) {
        IntegerType current_instruction = 0;

        for (size_t i = 0; i < trace_bytes_per_word; i++) {
            current_instruction |= (static_cast<IntegerType>(buffer[i])
                                    << (trace_data_width - (1 + i) * 8));
        }

        instructions.push_back(current_instruction);
    }
    file.close();
    const size_t instruction_count = instructions.size();

    // Start the simulation
    std::cout << "Trace simulation start!" << std::endl;
    const auto start_time = std::chrono::system_clock::now();
    sc_start(0, SC_NS);
    reset_n_i.write(1);  // deactivate reset

    // Send all instructions to the cache, one after the other
    const int word_buffer_width = sizeof(IntegerType) * 8;
    int progress = -1;  // progress of the simulation in percent
    bool hits[instruction_count];
    int instruction_durations[instruction_count];
    int instruction_start_time = 0;
    for (size_t i = 0; i < instruction_count; i++) {
        int new_progress = int((float(i) / float(instruction_count)) * 100.0);
        if (new_progress != progress) {
            progress = new_progress;
            std::cout.flush();
            std::cout << "Progress: " << i << " of " << instruction_count
                      << " (" << progress << "%)\r";
        }

        // send the next instruction
        IntegerType current_instruction = instructions[i];
        uint32_t address =
            extract_bits(current_instruction, 0, cache_address_width);
        uint32_t write_data =
            extract_bits(current_instruction, cache_address_width,
                         cache_address_width + cache_data_width);
        uint32_t write_select = extract_bits(
            current_instruction, trace_data_width - 1, trace_data_width);

        address_i.write(address);
        address_valid_i.write(1);
        write_data_i.write(write_data);
        write_data_valid_i.write(write_select);
        read_write_select_i.write(write_select);

        // wait at least one cycle
        tick(1);
        // as soon as port_ready_o becomes true, the cache will have accepted
        // the request we just sent so wait until it becomes ready and then
        // proceed with the next request
        while (!port_ready_o.read()) {
            tick(1);
        }
        address_valid_i.write(0);
        if (create_csv) {
            if (i != 0) {
                hits[i - 1] = hit_o.read();
                instruction_durations[i - 1] =
                    sim_time - instruction_start_time;
            }
            instruction_start_time = sim_time;
        }
    }
    std::cout.flush();
    // wait until the last instruction was processed
    tick(1);
    while (!port_ready_o.read()) {
        tick(1);
    }

    const auto end_time = std::chrono::system_clock::now();
    const auto elapsed_time =
        std::chrono::duration_cast<std::chrono::milliseconds>(end_time -
                                                              start_time)
            .count();

    if (create_csv) {
        hits[instruction_count - 1] = hit_o.read();
        instruction_durations[instruction_count - 1] =
            sim_time - instruction_start_time;
        std::cout
            << "Writing hit and instruction execution times to CSV files..."
            << std::endl;
        ofstream hit_file("tracing_tb_hits.csv");
        ofstream durations_file("tracing_tb_instruction_execution_times.csv");
        for (size_t i = 0; i < instruction_count; i++) {
            hit_file << hits[i] << ",";
            durations_file << instruction_durations[i] << ",";
        }
        hit_file.close();
        durations_file.close();
    }

    // sanity check
    std::cout << "Doing some reads as sanity check (execution time will not "
                 "be counted)."
              << std::endl;
    for (size_t i = 0; i < 8; i++) {
        read(i << cache_address_byte_offset_width);
    }

    cache_wrapper->final();

    if (argc >= 3) {
        // Write the result to the file name given in argv[3] if it exists.
        ofstream result_file(argv[2]);
        result_file << sim_time - 1;
        result_file.close();
    }

    std::cout << "Trace simulation done!" << std::endl;

    // One cycle gets wasted at the beginning, do not count that one
    std::cout << "Trace execution took " << sim_time - 1
              << " cycles (simulation took " << elapsed_time << " ms)"
              << std::endl;
    return 0;
}
