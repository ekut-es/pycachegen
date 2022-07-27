#include "V{{ name }}_PipelineStage.h"
#include "verilated_vcd_sc.h"

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

    // output signals
    sc_signal<bool> ready_o;

    V {
        { name }
    }
    _PipelineStage* pipeline_stage = new V {
        { name }
    }
    _PipelineStage{"{{ name }}_PipelineStage"};

    pipeline_stage->clk_i(clk_i);
    pipeline_stage->reset_n_i(reset_n_i);

    pipeline_stage->instruction_i(instruction_i);
    pipeline_stage->instruction_valid_i(instruction_valid_i);

    pipeline_stage->ready_o(ready_o);

    delete pipeline_stage;

    std::cout << "{{ name }}_PipelineStage done!" << std::endl;
    return 0;
}
