#include <memory>
#include <vector>
#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include "V{{ name }}_PipelineStage.h"

int sc_main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);

    // signals
    sc_clock clk_i{"clk", 1, SC_NS, 0.5, 0, SC_NS, true};
    sc_signal<bool> reset_n_i;

    // CAUTION!
    // when input/output wire of verilog module has less than 32 bits
    // sc_signal<uint32_t> is inferred instead of sc_signal<sc_bv<X>>
    sc_signal<uint32_t> instruction_i;
    sc_signal<bool> instruction_valid_i;

	// TODO extend data types beyond 32 bit

    sc_vector<sc_signal<bool>> next_stage_ready_is("next_stage_ready_is", {{ forward_ports }});
    sc_vector<sc_signal<uint32_t>> instruction_os("instruction_os", {{ forward_ports }});
    sc_vector<sc_signal<bool>> instruction_valid_os("instruction_valid_os", {{ forward_ports }});

    sc_signal<bool> ready_o;

    const std::unique_ptr<V{{ name }}_PipelineStage> pipeline_stage{new V{{ name }}_PipelineStage{"{{ name }}_PipelineStage"}};

    pipeline_stage->clk_i(clk_i);
    pipeline_stage->reset_n_i(reset_n_i);

    pipeline_stage->instruction_i(instruction_i);
    pipeline_stage->instruction_valid_i(instruction_valid_i);

    {%- for i in range(forward_ports) %}
    pipeline_stage->next_stage_ready_{{ i }}_i(next_stage_ready_is[{{ i }}]);
    pipeline_stage->instruction_{{ i }}_o(instruction_os[{{ i }}]);
    pipeline_stage->instruction_valid_{{ i }}_o(instruction_valid_os[{{ i }}]);
    {% endfor -%}

    pipeline_stage->ready_o(ready_o);

    int latency = {{ latency }}; 

    // start simulation and trace
    std::cout << "{{ name }}_PipelineStage start!" << std::endl;

    sc_start(0, SC_NS);

    VerilatedVcdSc* trace = new VerilatedVcdSc();
    pipeline_stage->trace(trace, 99);
    trace->open("{{ name }}_PipelineStage.vcd");

    // reset
    sc_start(1, SC_NS);
    reset_n_i.write(0);
    sc_start(1, SC_NS);
    reset_n_i.write(1);
    sc_start(1, SC_NS);

    // check that pipeline stage is ready
    assert(ready_o.read() == 1);

    // check if all output are set to 0
    {%- for i in range(forward_ports) %}
    assert(instruction_os[{{ i }}] == 0);
    assert(instruction_valid_os[{{ i }}] == 0);
    {% endfor -%}

    // for each forward port insert one instruction
    {%- for i in range(forward_ports) %}
    uint32_t instruction_{{ i }} = 0xF0000000 | {{ i }} << {{ target_id_start_bit }};
    instruction_i.write(instruction_{{ i }});
    instruction_valid_i.write(1);

    // make corresponding next stage ready
    next_stage_ready_is[{{ forward_port_map[i] }}].write(1);

    for(int i = 0; i <= latency; i++) {
        assert(instruction_os[{{ forward_port_map[i] }}].read() == 0);
        assert(instruction_valid_os[{{ forward_port_map[i] }}].read() == 0);
        sc_start(1, SC_NS);
        instruction_i.write(0);
        instruction_valid_i.write(0);
    }

    assert(instruction_os[{{ forward_port_map[i] }}].read() == instruction_{{ i }});
    assert(instruction_valid_os[{{ forward_port_map[i] }}].read() == 1);

    {% endfor -%}
    sc_start(1, SC_NS);
    assert(ready_o.read() == 1);

    std::cout << std::endl;

    // set all next stages ready and insert instructions as fast as possible
    {%- for i in range(forward_ports) %}
    next_stage_ready_is[{{ i }}].write(1);
    {% endfor -%}

    for(int i = 0; i < 2*{{ forward_ports }}; i++) {
        uint32_t instruction = 0xB0000000 | i % {{ forward_ports }} << {{ target_id_start_bit }};
        instruction_i.write(instruction);
        instruction_valid_i.write(1);
        for(int j = 0; j < latency; j++) {
            sc_start(1, SC_NS);
        }
    }

    // end simulation with reset
    reset_n_i.write(0);
    sc_start(2, SC_NS);

    pipeline_stage->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "{{ name }}_PipelineStage done!" << std::endl;
    return 0;
}
