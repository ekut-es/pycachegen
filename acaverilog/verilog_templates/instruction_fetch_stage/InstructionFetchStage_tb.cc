#include <memory>
#include <vector>
#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include "V{{ instruction_memory_fetch_stage_wrapper_name }}_InstructionMemoryFetchStageWrapper.h"

int sc_main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);

    // get vcd file path from command line arguments
    std::string vcd_file_path;

    if(argc == 2) {
        vcd_file_path = std::string(argv[1]);
    }

    /*
    // signals
    sc_clock clk_i{"clk", 1, SC_NS, 0.5, 0, SC_NS, true};
    sc_signal<bool> reset_n_i;

    sc_signal<bool> read_write_select_0_i;
    sc_signal<uint32_t> address_0_i;
    sc_signal<uint32_t> data_word_distance_0_i;
    sc_signal<bool> address_valid_0_i;
    sc_signal<uint32_t> write_data_0_i;
    sc_signal<uint32_t> read_data_0_o;

    {%- if port_width == 1 %}
    sc_signal<bool> write_data_valid_0_i;
    sc_signal<bool> read_data_valid_0_o;
    {% else %}
    sc_signal<uint32_t> write_data_valid_0_i;
    sc_signal<uint32_t> read_data_valid_0_o;
    {% endif -%}

    sc_signal<bool> write_done_0_o;
    sc_signal<bool> port_ready_0_o;
    sc_signal<bool> ready_o;

    const std::unique_ptr<V{{ name }}_Memory> instruction_memory{new V{{ name }}_Memory{"{{ name }}_Memory"}};

    instruction_memory->clk_i(clk_i);
    instruction_memory->reset_n_i(reset_n_i);

    instruction_memory->read_write_select_0_i(read_write_select_0_i);
    instruction_memory->address_0_i(address_0_i);
    instruction_memory->data_word_distance_0_i(data_word_distance_0_i);
    instruction_memory->address_valid_0_i(address_valid_0_i);
    instruction_memory->write_data_0_i(write_data_0_i);
    instruction_memory->read_data_0_o(read_data_0_o);
    instruction_memory->write_data_valid_0_i(write_data_valid_0_i);
    instruction_memory->read_data_valid_0_o(read_data_valid_0_o);
    instruction_memory->write_done_0_o(write_done_0_o);
    instruction_memory->port_ready_0_o(port_ready_0_o);
    instruction_memory->ready_o(ready_o);

    // start simulation and trace
    std::cout << "{{ name }}_Memory start!" << std::endl;

    sc_start(0, SC_NS);

    VerilatedVcdSc* trace = new VerilatedVcdSc();
    instruction_memory->trace(trace, 99);

    if(vcd_file_path.empty()) {
        trace->open("{{ name }}_Memory.vcd");
    } else {
        trace->open(vcd_file_path.c_str());
    }


    // reset
    sc_start(1, SC_NS);
    reset_n_i.write(0);
    sc_start(1, SC_NS);
    reset_n_i.write(1);
    sc_start(1, SC_NS);

    // end simulation with reset
    reset_n_i.write(0);
    sc_start(2, SC_NS);

    instruction_memory->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "{{ name }}_Memory done!" << std::endl;
    */
    return 0;
}
