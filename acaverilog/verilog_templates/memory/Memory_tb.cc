#include <memory>
#include <vector>
#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include "V{{ name }}_Memory.h"

// signals
sc_clock clk_i{"clk", 1, SC_NS, 0.5, 0, SC_NS, true};
sc_signal<bool> reset_n_i;

sc_vector<sc_signal<bool>> read_write_select_is("read_write_select_is", {{ read_write_ports }});
sc_vector<sc_signal<uint32_t>> address_is("address_is", {{ read_write_ports }});
sc_vector<sc_signal<uint32_t>> data_word_distance_is("data_word_distance_is", {{ read_write_ports }});
sc_vector<sc_signal<bool>> address_valid_is("address_valid_is", {{ read_write_ports }});
sc_vector<sc_signal<uint32_t>> write_data_is("write_data_is", {{ read_write_ports }});
sc_vector<sc_signal<uint32_t>> read_data_os("read_data_os", {{ read_write_ports }});
sc_vector<sc_signal<uint32_t>> write_data_valid_is("write_data_valid_is", {{ read_write_ports }});
sc_vector<sc_signal<uint32_t>> read_data_valid_os("read_data_valid_os", {{ read_write_ports }});
sc_vector<sc_signal<bool>> write_done_os("write_done_os", {{ read_write_ports }});
sc_vector<sc_signal<bool>> port_ready_os("port_ready_os", {{ read_write_ports }});

sc_signal<bool> ready_o;

void reset() {
    sc_start(1, SC_NS);
    reset_n_i.write(0);
    sc_start(1, SC_NS);
    reset_n_i.write(1);
    sc_start(1, SC_NS);   

    // check that all output are 0 except for port_ready
	{%- for i in range(read_write_ports) %}
    assert(ready_o.read() == 1);
    assert(write_done_os[{{ i }}].read() == 0);
    assert(read_data_os[{{ i }}].read() == 0);
    assert(read_data_valid_os[{{ i }}].read() == 0);
    assert(port_ready_os[{{ i }}].read() == 1);
	{% endfor %}
}

void set_init_write_signals(int port, int address, int data, int data_word_distance, int valid_bits) {
    read_write_select_is[port].write(1);
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

int sc_main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);

    // get vcd file path from command line arguments
    std::string vcd_file_path;

    if(argc == 2) {
        vcd_file_path = std::string(argv[1]);
    }

    const std::unique_ptr<V{{ name }}_Memory> memory{new V{{ name }}_Memory{"{{ name }}_Memory"}};

	memory->clk_i(clk_i);
	memory->reset_n_i(reset_n_i);

	{%- for i in range(read_write_ports) %}
	memory->read_write_select_{{ i }}_i(read_write_select_is[{{ i }}]);
	memory->address_{{ i }}_i(address_is[{{ i }}]);
	memory->data_word_distance_{{ i }}_i(data_word_distance_is[{{ i }}]);
	memory->address_valid_{{ i }}_i(address_valid_is[{{ i }}]);
	memory->write_data_{{ i }}_i(write_data_is[{{ i }}]);
	memory->write_data_valid_{{ i }}_i(write_data_valid_is[{{ i }}]);
	memory->write_done_{{ i }}_o(write_done_os[{{ i }}]);
	memory->read_data_{{ i }}_o(read_data_os[{{ i }}]);
	memory->read_data_valid_{{ i }}_o(read_data_valid_os[{{ i }}]);
    memory->port_ready_{{ i }}_o(port_ready_os[{{ i }}]);
	{% endfor %}

	memory->ready_o(ready_o);

    // set bits from 0 to data_width-1 in data_mask
    uint32_t data_mask = 0;
    for(int i = 0; i < {{ data_width }}; i++) {
        data_mask = data_mask << 1;
        data_mask = data_mask | 0x1;
    }

    uint32_t data = 0;

	// start simulation and trace
    std::cout << "{{ name }}_Memory start!" << std::endl;

    sc_start(0, SC_NS);

    VerilatedVcdSc* trace = new VerilatedVcdSc();
    memory->trace(trace, 99);

    if(vcd_file_path.empty()) {
        trace->open("{{ name }}_Memory.vcd");
    } else {
        trace->open(vcd_file_path.c_str());
    }

    // reset
    reset(); 

    sc_start(1, SC_NS);

    data = 42 & data_mask;

    // write into memory at port 0 to first address in address range
    set_init_write_signals(0, {{ address_ranges[0][0] }}, data, 1, 0x1);
    sc_start(2, SC_NS);
    unset_write_signals(0);

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
    std::cout << "t=" << sc_time_stamp() << ": " << read_data_os[0].read() << std::endl;

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
    std::cout << "t=" << sc_time_stamp() << ": " << read_data_os[0].read() << std::endl;

    reset();
    sc_start(1, SC_NS);

    // for each port write to every address
    int port = 0;
    data = 1; 

    // write at each address of the memory
    {%- for address_range in address_ranges %}
    for(int address = {{ address_range[0] }}; address < {{ address_range[1] }}; address+={{ port_width }}) {
        uint32_t data_words;
        //data_words = data;

        for(int i = 0; i < {{ port_width }}; i++) {
            data_words = (data_words << {{ data_width }}) | (data++ & data_mask);
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
    for(int address = {{ address_range[0] }}; address < {{ address_range[1] }}; address+={{ port_width }}) {
        set_init_read_signals(port, address, 1);
        sc_start(1, SC_NS);

        // wait until read_data_o is valid
        while(read_data_valid_os[port].read() != 0) {
            sc_start(1, SC_NS);
        }

        std::cout << "read_data: " << std::hex << read_data_os[port].read() << std::endl;

        // wait until port is ready again
        while(port_ready_os[port].read() != 1) {
            sc_start(1, SC_NS);
        }
    }
    {% endfor %}

	memory->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "{{ name }}_Memory done!" << std::endl;
    return 0;
}