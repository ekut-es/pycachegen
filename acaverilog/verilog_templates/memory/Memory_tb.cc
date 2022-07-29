#include <memory>
#include <vector>
#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include "V{{ name }}_Memory.h"

int sc_main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);

    // signals
    sc_clock clk_i{"clk", 1, SC_NS, 0.5, 0, SC_NS, true};
    sc_signal<bool> reset_n_i;

    sc_vector<sc_signal<bool>> read_write_select_is("read_write_select_is", {{ read_write_ports }});
    sc_vector<sc_signal<uint32_t>> address_is("address_is", {{ read_write_ports }});
    sc_vector<sc_signal<uint32_t>> write_data_is("write_data_is", {{ read_write_ports }});
    sc_vector<sc_signal<uint32_t>> write_data_valid_is("write_data_valid_is", {{ read_write_ports }});
    sc_vector<sc_signal<uint32_t>> read_data_os("read_data_os", {{ read_write_ports }});
    sc_vector<sc_signal<uint32_t>> read_data_valid_os("read_data_valid_os", {{ read_write_ports }});

    sc_signal<bool> ready_o;

    const std::unique_ptr<V{{ name }}_Memory> memory{new V{{ name }}_Memory{"{{ name }}_Memory"}};

	memory->clk_i(clk_i);
	memory->reset_n_i(reset_n_i);

	{%- for i in range(read_write_ports) %}
	memory->read_write_select_{{ i }}_i(read_write_select_is[{{ i }}]);
	memory->address_{{ i }}_i(address_is[{{ i }}]);
	memory->write_data_{{ i }}_i(write_data_is[{{ i }}]);
	memory->write_data_valid_{{ i }}_i(write_data_valid_is[{{ i }}]);
	memory->read_data_{{ i }}_o(read_data_os[{{ i }}]);
	memory->read_data_valid_{{ i }}_o(read_data_valid_os[{{ i }}]);
	{% endfor -%}

	memory->ready_o(ready_o);

	// start simulation and trace
    std::cout << "{{ name }}_Memory start!" << std::endl;

    sc_start(0, SC_NS);

    VerilatedVcdSc* trace = new VerilatedVcdSc();
    memory->trace(trace, 99);
    trace->open("{{ name }}_Memory.vcd");

	memory->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "{{ name }}_Memory done!" << std::endl;
    return 0;
}