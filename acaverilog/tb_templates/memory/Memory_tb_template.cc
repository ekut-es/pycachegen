#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include <memory>
#include <vector>

#define USE_CASSERT 0
#include "V{{ name }}_Memory.h"
#include "assertv.h"

// signals
sc_clock clk_i{"clk", 1, SC_NS, 0.5, 0, SC_NS, true};
sc_signal<bool> reset_n_i;

sc_signal<uint32_t> address_i;
sc_signal<bool> address_valid_i;
sc_signal<uint32_t> write_data_i;
sc_signal<bool> write_data_valid_i;
sc_signal<bool> read_write_select_i;

sc_signal<uint32_t> read_data_o;
sc_signal<bool> read_data_valid_o;
sc_signal<bool> write_done_o;
sc_signal<bool> ready_o;

void reset() {
    sc_start(1, SC_NS);
    reset_n_i.write(0);
    sc_start(1, SC_NS);
    reset_n_i.write(1);
    sc_start(1, SC_NS);

    // check all outputs
    assertv(read_data_o.read(), 0);
    assertv(read_data_valid_o.read(), 0);
    assertv(write_done_o.read(), 0);
    assertv(ready_o.read(), 1);
}

/*
void set_init_write_signals(int port, int address, int data, int
data_word_distance, int valid_bits) { read_write_select_is[port].write(1);
    address_is[port].write(address);
    address_valid_is[port].write(1);
    data_word_distance_is[port].write(data_word_distance);
    write_data_is[port].write(data);
    write_data_valid_is[port].write(valid_bits);
}

void unset_write_signals(int port) {
    read_write_select_is[port].write(0);
    address_is[port].write(0);
    address_valid_is[port].write(0);
    data_word_distance_is[port].write(0);
    write_data_is[port].write(0);
    write_data_valid_is[port].write(0);
}

void set_init_read_signals(int port, int address, int data_word_distance) {
    read_write_select_is[port].write(0);
    address_is[port].write(address);
    address_valid_is[port].write(1);
    data_word_distance_is[port].write(data_word_distance);
}

void unset_read_signals(int port) {
    read_write_select_is[port].write(0);
    address_is[port].write(0);
    address_valid_is[port].write(0);
    data_word_distance_is[port].write(0);
}
*/

int sc_main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);

    // get vcd file path from command line arguments
    std::string vcd_file_path;

    if (argc == 2) {
        vcd_file_path = std::string(argv[1]);
    }

    const std::unique_ptr < V {
        { name }
    }
    _Memory > memory{new V{{name}} _Memory{"{{ name }}_Memory"}};

    memory->clk_i(clk_i);
    memory->reset_n_i(reset_n_i);

    memory->address_i(address_i);
    memory->address_valid_i(address_valid_i);
    memory->write_data_i(write_data_i);
    memory->write_data_valid_i(write_data_valid_i);
    memory->read_write_select_i(read_write_select_i);

    memory->read_data_o(read_data_o);
    memory->read_data_valid_o(read_data_valid_o);
    memory->write_done_o(write_done_o);
    memory->ready_o(ready_o);

    // start simulation and trace
    std::cout << "{{ name }}_Memory start!" << std::endl;

    sc_start(0, SC_NS);

    VerilatedVcdSc* trace = new VerilatedVcdSc();
    memory->trace(trace, 99);

    if (vcd_file_path.empty()) {
        trace->open("{{ vcd_dir_path }}/{{ name }}_Memory.vcd");
    } else {
        trace->open(vcd_file_path.c_str());
    }

    // reset
    reset();

    sc_start(1, SC_NS);

    uint32_t data = 42;

    // write into memory to first address in address range
    address_i.write({{address_ranges[0][0]}});
    address_valid_i.write(1);
    write_data_i.write(data);
    write_data_valid_i.write(1);
    read_write_select_i.write(1);

    sc_start(2, SC_NS);

    assertv(read_data_valid_o.read(), 0);
    assertv(write_done_o.read(), 0);
    assertv(ready_o.read(), 0);

    sc_start(2, SC_NS);

    assertv(write_done_o.read(), 1);
    assertv(ready_o.read(), 1);

    address_i.write({{address_ranges[0][0]}});
    address_valid_i.write(1);
    read_write_select_i.write(0);

    sc_start(2, SC_NS);

    assertv(read_data_valid_o.read(), 0);
    assertv(read_data_o.read(), 0);
    assertv(ready_o.read(), 0);

    sc_start(3, SC_NS);

    assertv(read_data_valid_o.read(), 1);
    assertv(read_data_o.read(), data);
    assertv(ready_o.read(), 1);

    /*
    // wait until port is ready again
    while(port_ready_os[0].read() != 1) {
        sc_start(1, SC_NS);
    }

    // read from memory at port 0
    set_init_read_signals(0, {{ address_ranges[0][0] }}, 1);
    sc_start(2, SC_NS);
    unset_read_signals(0);

    // wait for data at read_data_o
    while(read_data_valid_os[0].read() == 0) {
        sc_start(1, SC_NS);
    }

    assert(read_data_os[0].read() == data);
    std::cout << "t=" << sc_time_stamp() << ": " << read_data_os[0].read() <<
    std::endl;

    // wait until port is ready again
    while(port_ready_os[0].read() != 1) {
        sc_start(1, SC_NS);
    }

    // read from memory at port 0
    set_init_read_signals(0, {{ address_ranges[0][0] }}, 1);
    sc_start(2, SC_NS);
    unset_read_signals(0);

    // wait for data at read_data_o
    while(read_data_valid_os[0].read() == 0) {
        sc_start(1, SC_NS);
    }

    assert(read_data_os[0].read() == 42);
    std::cout << "t=" << sc_time_stamp() << ": " << read_data_os[0].read() <<
    std::endl;

    reset();
    sc_start(1, SC_NS);

    // for each port write to every address
    int port = 0;
    data = 1;

    // write at each address of the memory
    {%- for address_range in address_ranges %}
    for(int address = {{ address_range[0] }}; address < {{ address_range[1] }};
    address+={{ port_width }}) { uint32_t data_words;
        //data_words = data;

        for(int i = 0; i < {{ port_width }}; i++) {
            data_words = (data_words << {{ data_width }}) | (data++ &
    data_mask);
        }
        set_init_write_signals(port, address, data_words, 1, 0xF);
        sc_start(2, SC_NS);

        // wait until port is ready again
        while(port_ready_os[port].read() != 1) {
            sc_start(1, SC_NS);
        }
    }
    {% endfor %}

    // wait some cycles so it is visible in the VCD
    sc_start(4, SC_NS);

    // read from each address of the memory
    {%- for address_range in address_ranges %}
    for(int address = {{ address_range[0] }}; address < {{ address_range[1] }};
    address+={{ port_width }}) { set_init_read_signals(port, address, 1);
        sc_start(1, SC_NS);

        // wait until read_data_o is valid
        while(read_data_valid_os[port].read() != 0) {
            sc_start(1, SC_NS);
        }

        std::cout << "read_data: " << std::hex << read_data_os[port].read() <<
    std::endl;

        // wait until port is ready again
        while(port_ready_os[port].read() != 1) {
            sc_start(1, SC_NS);
        }
    }
    {% endfor %}
    */

    sc_start(2, SC_NS);

    memory->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "{{ name }}_Memory done!" << std::endl;
    return 0;
}
