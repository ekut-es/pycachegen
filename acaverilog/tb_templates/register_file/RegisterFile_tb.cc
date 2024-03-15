#include <memory>
#include <vector>
#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#define USE_CASSERT 0
#include "assertv.h"

#include "V{{ name }}_RegisterFile.h"

int sc_main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);

    // get vcd file path from command line arguments
    std::string vcd_file_path;

    if(argc == 2) {
        vcd_file_path = std::string(argv[1]);
    }

    // signals
    sc_clock clk_i{"clk", 1, SC_NS, 0.5, 0, SC_NS, true};
    sc_signal<bool> reset_n_i;

    sc_signal<uint32_t> read_address_i;
    sc_signal<uint32_t> write_address_i;
    sc_signal<uint32_t> write_data_i;
    sc_signal<bool> read_write_select_i;

    sc_signal<bool> read_address_valid_o;
    sc_signal<bool> write_address_valid_o;
    sc_signal<uint32_t> read_data_o;
    sc_signal<bool> write_done_o;

    const std::unique_ptr<V{{ name }}_RegisterFile> register_file{new V{{ name }}_RegisterFile{"{{ name }}_RegisterFile"}};

    register_file->clk_i(clk_i);
    register_file->reset_n_i(reset_n_i);

    register_file->read_address_i(read_address_i);
    register_file->write_address_i(write_address_i);
    register_file->write_data_i(write_data_i);
    register_file->read_write_select_i(read_write_select_i);

    register_file->read_address_valid_o(read_address_valid_o);
    register_file->write_address_valid_o(write_address_valid_o);
    register_file->read_data_o(read_data_o);
    register_file->write_done_o(write_done_o);

    // start simulation and trace
    std::cout << "{{ name }}_RegisterFile start!" << std::endl;

    sc_start(0, SC_NS);

    VerilatedVcdSc* trace = new VerilatedVcdSc();
    register_file->trace(trace, 99);

    if(vcd_file_path.empty()) {
        trace->open("{{ vcd_dir_path }}/{{ name }}_RegisterFile.vcd");
    } else {
        trace->open(vcd_file_path.c_str());
    }
    
    // reset
    sc_start(1, SC_NS);
    reset_n_i.write(0);
    sc_start(1, SC_NS);
    reset_n_i.write(1);
    sc_start(1, SC_NS);

    // check whether register file is ready
    assertv(read_address_valid_o.read(), 1);
    assertv(write_address_valid_o.read(), 0);
    assertv(read_data_o.read(), 0);
    assertv(write_done_o.read(), 0);

    read_write_select_i.write(0);
    write_address_i.write(0);
    write_data_i.write(0);
    sc_start(1, SC_NS);

    // check all registers
    for(int i = 0; i < {{ register_size }}; i++) {
        read_address_i.write(i);
        sc_start(1, SC_NS);
        assertv(read_data_o.read(), 0);
        assertv(write_done_o.read(), 0);
    }

    // insert data
    uint32_t data[] = {
        {% for i in range(register_size) %}
        {{ i }},
        {% endfor %}
    };

    for(int i = 0; i < {{ register_size }}; i++) {
        write_address_i.write(i);
        write_data_i.write(data[i]);
        read_write_select_i.write(1);
        sc_start(1, SC_NS);
        read_write_select_i.write(0);
        sc_start(1, SC_NS);
        read_address_i.write(i);
        sc_start(1, SC_NS);
        assertv(read_data_o.read(), data[i]);
    }

    sc_start(2, SC_NS);

    // end simulation with reset
    reset_n_i.write(0);
    sc_start(2, SC_NS);

    register_file->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "{{ name }}_RegisterFile done!" << std::endl;
    return 0;
}
