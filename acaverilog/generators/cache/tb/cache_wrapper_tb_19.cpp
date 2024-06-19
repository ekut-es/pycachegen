#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include <iostream>

#include "Vcache_wrapper_19.h"

// Testbench for testing multiple ports with an arbiter with round robin policy
// data_width=16, address_width=8, num_ports=5, arbiter_policy=round_robin
// num_ways=4, num_sets=2,
// replacement_policy=plru_mru, hit_latency=4, miss_latency=11,
// write_through=false, write_allocate=true,
// block_size=1

int sc_main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);

    std::string vcd_file_path;

    if (argc == 2) {
        vcd_file_path = std::string(argv[1]);
    }

    const int hit_latency = 4;
    const int miss_latency = 11;
    const int read_latency = 11;
    const int write_latency = 16;

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

    sc_signal<uint32_t> address_4_i;
    sc_signal<bool> address_valid_4_i;
    sc_signal<uint32_t> write_data_4_i;
    sc_signal<bool> write_data_valid_4_i;
    sc_signal<bool> read_write_select_4_i;

    sc_signal<uint32_t> read_data_4_o;
    sc_signal<bool> read_data_valid_4_o;
    sc_signal<bool> write_done_4_o;
    sc_signal<bool> port_ready_4_o;

    const std::unique_ptr<Vcache_wrapper_19> cache_wrapper{
        new Vcache_wrapper_19{"cache_wrapper"}};

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

    cache_wrapper->address_4_i(address_4_i);
    cache_wrapper->address_valid_4_i(address_valid_4_i);
    cache_wrapper->write_data_4_i(write_data_4_i);
    cache_wrapper->write_data_valid_4_i(write_data_valid_4_i);
    cache_wrapper->read_write_select_4_i(read_write_select_4_i);

    cache_wrapper->read_data_4_o(read_data_4_o);
    cache_wrapper->read_data_valid_4_o(read_data_valid_4_o);
    cache_wrapper->write_done_4_o(write_done_4_o);
    cache_wrapper->port_ready_4_o(port_ready_4_o);

    const int MAX_SIMULATION_TIME = 1000;

    auto tick = [&](int amount) {
        if (sc_time_stamp().to_default_time_units() > MAX_SIMULATION_TIME) {
            throw std::runtime_error("Exceeded maximum simulation time");
        }
        sc_start(amount, SC_NS);
    };

    std::cout << "Vcache_wrapper_19 start!" << std::endl;

    tick(0);

    VerilatedVcdSc* trace = new VerilatedVcdSc();
    cache_wrapper->trace(trace, 99);

    if (vcd_file_path.empty()) {
        trace->open("Vcache_wrapper_tb_19.vcd");
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

    tick(1); // wait one cycle for the next positive clock edge
    address_valid_0_i.write(0);
    address_valid_1_i.write(0);
    tick(2); // wait two cycles for the arbiter to buffer the request and output it

    tick(miss_latency); // write request from 0 should be done now

    tick(1); // result of write request should now be accessible on the fe port
            // and the request from port 1 should be sent
    
    if(!write_done_0_o.read()) {
        std::cerr << "Write failed" << std::endl;
    } else {
        std::cout << "Write successful" << std::endl;
    }

    // send requests from 0 and 1, 1 should be prioritized here
    address_0_i.write(2);
    address_valid_0_i.write(1);
    read_write_select_0_i.write(0);

    address_1_i.write(2);
    address_valid_1_i.write(1);
    write_data_1_i.write(15);
    write_data_valid_1_i.write(1);
    read_write_select_1_i.write(1);

    tick(1); // wait for the next positive clock edge

    address_valid_0_i.write(0);
    address_valid_1_i.write(0);

    // send another request which should again have higher priority than from port 0
    address_3_i.write(2);
    address_valid_3_i.write(1);
    write_data_3_i.write(16);
    write_data_valid_3_i.write(1);
    read_write_select_3_i.write(1);

    tick(2); // wait two more cycles so the request can be outputted and accepted by the cache

    address_valid_3_i.write(0);

    tick(hit_latency); // request from 1 should be processed now

    tick(1); // wait one more cycle so we can read the result and request from port 3 should be sent now

    if(!write_done_1_o.read()) {
        std::cerr << "Write failed" << std::endl;
    } else {
        std::cout << "Write successful" << std::endl;
    }

    tick(1); // cache should now have registered the request

    tick(hit_latency); // cache should now be done with request from 3

    tick(1); // wait one more cycle so we can see the result

    if(!write_done_3_o.read()) {
        std::cerr << "Write failed" << std::endl;
    } else {
        std::cout << "Write successful" << std::endl;
    }

    tick(1); // cache should now have registered the request

    tick(hit_latency); // cache should now be done with request from 0

    tick(1); // wait one more cycle so we can see the result

    if(read_data_0_o.read() != 16 || !read_data_valid_0_o.read()) {
        std::cerr << "Read failed" << std::endl;
    } else {
        std::cout << "Read successful" << std::endl;
    }

    cache_wrapper->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "Vcache_wrapper_19 done!" << std::endl;
    return 0;
}
