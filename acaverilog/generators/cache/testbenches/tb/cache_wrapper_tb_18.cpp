#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include <iostream>

#include "Vcache_wrapper_18.h"

// Testbench for testing multiple ports with an arbiter with fifo policy
// num_ports=4, arbiter_policy=fifo, byte_size=8
// enable_reset=false, address_width=9
// L1: data_width=16, num_ways=4, num_sets=2,
// replacement_policy=plru_mru, hit_latency=4, miss_latency=11,
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
    const int miss_latency = 11;
    const int read_latency = 10;
    const int write_latency = 15;

    sc_clock clk_i{"clk_i", 1, SC_NS, 0.5, 0, SC_NS, true};
    sc_signal<bool> reset_n_i;
    sc_signal<bool> flush_i;
    sc_signal<bool> hit_o;
    sc_signal<bool> flush_done_o;

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

    sc_signal<uint32_t> address_2_i;
    sc_signal<bool> address_valid_2_i;
    sc_signal<uint32_t> write_data_2_i;
    sc_signal<bool> write_data_valid_2_i;
    sc_signal<bool> read_write_select_2_i;

    sc_signal<uint32_t> read_data_2_o;
    sc_signal<bool> read_data_valid_2_o;
    sc_signal<bool> write_done_2_o;
    sc_signal<bool> port_ready_2_o;

    sc_signal<uint32_t> address_3_i;
    sc_signal<bool> address_valid_3_i;
    sc_signal<uint32_t> write_data_3_i;
    sc_signal<bool> write_data_valid_3_i;
    sc_signal<bool> read_write_select_3_i;

    sc_signal<uint32_t> read_data_3_o;
    sc_signal<bool> read_data_valid_3_o;
    sc_signal<bool> write_done_3_o;
    sc_signal<bool> port_ready_3_o;

    const std::unique_ptr<Vcache_wrapper_18> cache_wrapper{
        new Vcache_wrapper_18{"cache_wrapper"}};

    cache_wrapper->clk_i(clk_i);
    cache_wrapper->reset_n_i(reset_n_i);
    cache_wrapper->flush_i(flush_i);
    cache_wrapper->hit_o(hit_o);
    cache_wrapper->flush_done_o(flush_done_o);

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

    cache_wrapper->address_2_i(address_2_i);
    cache_wrapper->address_valid_2_i(address_valid_2_i);
    cache_wrapper->write_data_2_i(write_data_2_i);
    cache_wrapper->write_data_valid_2_i(write_data_valid_2_i);
    cache_wrapper->read_write_select_2_i(read_write_select_2_i);

    cache_wrapper->read_data_2_o(read_data_2_o);
    cache_wrapper->read_data_valid_2_o(read_data_valid_2_o);
    cache_wrapper->write_done_2_o(write_done_2_o);
    cache_wrapper->port_ready_2_o(port_ready_2_o);

    cache_wrapper->address_3_i(address_3_i);
    cache_wrapper->address_valid_3_i(address_valid_3_i);
    cache_wrapper->write_data_3_i(write_data_3_i);
    cache_wrapper->write_data_valid_3_i(write_data_valid_3_i);
    cache_wrapper->read_write_select_3_i(read_write_select_3_i);

    cache_wrapper->read_data_3_o(read_data_3_o);
    cache_wrapper->read_data_valid_3_o(read_data_valid_3_o);
    cache_wrapper->write_done_3_o(write_done_3_o);
    cache_wrapper->port_ready_3_o(port_ready_3_o);

    int exit_code = 0;

    std::cout << "Vcache_wrapper_18 start!" << std::endl;

    sc_start(0, SC_NS);

    VerilatedVcdSc* trace = new VerilatedVcdSc();
    cache_wrapper->trace(trace, 99);

    if (vcd_file_path.empty()) {
        trace->open("Vcache_wrapper_tb_18.vcd");
    } else {
        trace->open(vcd_file_path.c_str());
    }

    try {
        sc_start(1, SC_NS);
        reset_n_i.write(1);
        sc_start(1, SC_NS);

        address_0_i.write(2);
        address_valid_0_i.write(1);
        write_data_0_i.write(14);
        write_data_valid_0_i.write(1);
        read_write_select_0_i.write(1);

        address_1_i.write(2);
        address_valid_1_i.write(1);
        read_write_select_1_i.write(0);

        sc_start(1, SC_NS);  // wait one cycle for the next positive clock edge
        address_valid_0_i.write(0);
        address_valid_1_i.write(0);
        sc_start(
            3, SC_NS);  // wait two cycles for the arbiter to buffer the
                        // request, insert it into the fifo and then output it

        address_2_i.write(3);
        address_valid_2_i.write(1);
        write_data_2_i.write(22);
        write_data_valid_2_i.write(1);
        read_write_select_2_i.write(1);

        sc_start(1, SC_NS);

        address_valid_2_i.write(0);

        address_3_i.write(3);
        address_valid_3_i.write(1);
        read_write_select_3_i.write(0);

        sc_start(1, SC_NS);
        address_valid_3_i.write(0);

        sc_start(miss_latency - 2,
                 SC_NS);  // write request from 0 should be done now

        sc_start(
            1,
            SC_NS);  // result of write request should now be accessible on the
                     // fe port and the request from port 1 should be sent

        if (!write_done_0_o.read()) {
            std::cerr << "Write failed" << std::endl;
            exit_code = 1;
        } else {
            std::cout << "Write successful" << std::endl;
        }

        // send another request from port 0 which should be queued behind those
        // from 2 and 3
        address_0_i.write(3);
        address_valid_0_i.write(1);
        write_data_0_i.write(2);
        write_data_valid_0_i.write(1);
        read_write_select_0_i.write(1);

        sc_start(1, SC_NS);  // after another cycle the cache should have
                             // registered the request

        address_valid_0_i.write(0);  // invalidate request from 0

        sc_start(hit_latency, SC_NS);  // read request should be done now

        sc_start(
            1, SC_NS);  // wait for the result to be handed out on the fe port

        if (read_data_1_o.read() != 14 || !read_data_valid_1_o.read()) {
            std::cerr << "Read failed" << std::endl;
            exit_code = 1;
        } else {
            std::cout << "Read successful" << std::endl;
        }

        sc_start(1, SC_NS);  // wait for cache to register request from port 2

        sc_start(miss_latency, SC_NS);  // request should now be processed

        sc_start(1, SC_NS);  // wait another cycle for the result

        if (!write_done_2_o.read()) {
            std::cerr << "Write failed" << std::endl;
            exit_code = 1;
        } else {
            std::cout << "Write successful" << std::endl;
        }

        sc_start(1, SC_NS);  // wait for cache to register request from port 3

        sc_start(hit_latency, SC_NS);  // request should now be processed

        sc_start(1, SC_NS);  // wait another cycle for the result

        if (read_data_3_o.read() != 22 || !read_data_valid_3_o.read()) {
            std::cerr << "Read failed" << std::endl;
            exit_code = 1;
        } else {
            std::cout << "Read successful" << std::endl;
        }

        assert(write_done_0_o ==
               0);  // write done from first request should not be set anymore

        sc_start(1, SC_NS);  // wait for cache to register request from port 0

        sc_start(hit_latency, SC_NS);  // request should now be processed

        sc_start(1, SC_NS);  // wait another cycle for the result

        sc_start(10, SC_NS);
    } catch (std::runtime_error& e) {
        std::cerr << e.what() << std::endl;
        exit_code = 1;
    }
    cache_wrapper->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "Vcache_wrapper_18 done!" << std::endl;
    return exit_code;
}
