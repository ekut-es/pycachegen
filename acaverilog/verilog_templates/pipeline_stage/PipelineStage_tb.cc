#include <memory>
#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include "V{{ name }}_PipelineStage.h"

int sc_main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);

    // input signals
    sc_clock clk_i{"clk", 1, SC_NS, 0.5, 0, SC_NS, true};
    sc_signal<bool> reset_n_i;

    // CAUTION!
    // when input/output wire of verilog module has less than 32 bits
    // sc_signal<uint32_t> is inferred instead of sc_signal<sc_bv<X>>
    sc_signal<uint32_t> instruction_i;
    sc_signal<bool> instruction_valid_i;

    sc_signal<bool> next_stage_ready_i;
    sc_signal<uint32_t> instruction_o;
    sc_signal<bool> instruction_valid_o;

    // output signals
    sc_signal<bool> ready_o;

    const std::unique_ptr<V{{ name }}_PipelineStage> pipeline_stage{new V{{ name }}_PipelineStage{"{{ name }}_PipelineStage"}};

    pipeline_stage->clk_i(clk_i);
    pipeline_stage->reset_n_i(reset_n_i);

    pipeline_stage->instruction_i(instruction_i);
    pipeline_stage->instruction_valid_i(instruction_valid_i);

    pipeline_stage->next_stage_ready_i(next_stage_ready_i);
    pipeline_stage->instruction_o(instruction_o);
    pipeline_stage->instruction_valid_o(instruction_valid_o);

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
    reset_n_i.write(1);
    sc_start(1, SC_NS);
    reset_n_i.write(1);
    sc_start(1, SC_NS);

    // insert single instruction
    uint32_t instruction = 0xdeadbeef;

    instruction_i.write(instruction);
    instruction_valid_i.write(1);
    sc_start(1, SC_NS);

    instruction_i.write(0);
    instruction_valid_i.write(0);

    next_stage_ready_i.write(1);

    // wait for latency
    for(int i = 0; i <= latency; i++) {
        sc_start(1, SC_NS);
    }

    assert(instruction_o.read() == instruction);
    assert(instruction_valid_o.read() == 1);

    // check that after the instruction was read the signals are back to 0
    sc_start(1, SC_NS);
    assert(instruction_o.read() == 0);
    assert(instruction_valid_o.read() == 0);

    next_stage_ready_i.write(0);

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
