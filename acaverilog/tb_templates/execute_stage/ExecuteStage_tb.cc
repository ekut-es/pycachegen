#include <memory>
#include <vector>
#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#define USE_CASSERT 0
#include "assertv.h"

#include "V{{ name }}_ExecuteStage.h"

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

    // CAUTION!
    // when input/output wire of verilog module has less than 32 bits
    // sc_signal<uint32_t> is inferred instead of sc_signal<sc_bv<X>>
    sc_signal<uint32_t> instruction_i;
    sc_signal<bool> instruction_valid_i;
    sc_signal<bool> next_stage_ready_i;

    sc_signal<uint32_t> instruction_o;
    sc_signal<bool> instruction_valid_o;
    sc_signal<bool> ready_o;

    const std::unique_ptr<V{{ name }}_ExecuteStage> execute_stage{new V{{ name }}_ExecuteStage{"{{ name }}_ExecuteStage"}};

    execute_stage->clk_i(clk_i);
    execute_stage->reset_n_i(reset_n_i);

    execute_stage->instruction_i(instruction_i);
    execute_stage->instruction_valid_i(instruction_valid_i);
    execute_stage->next_stage_ready_i(next_stage_ready_i);

    execute_stage->instruction_o(instruction_o);
    execute_stage->instruction_valid_o(instruction_valid_o);
    execute_stage->ready_o(ready_o);

    int latency = {{ latency }}; 

    // start simulation and trace
    std::cout << "{{ name }}_ExecuteStage start!" << std::endl;

    sc_start(0, SC_NS);

    VerilatedVcdSc* trace = new VerilatedVcdSc();
    execute_stage->trace(trace, 99);

    if(vcd_file_path.empty()) {
        trace->open("{{ vcd_dir_path }}/{{ name }}_ExecuteStage.vcd");
    } else {
        trace->open(vcd_file_path.c_str());
    }
    
    // reset
    sc_start(1, SC_NS);
    reset_n_i.write(0);
    sc_start(1, SC_NS);
    reset_n_i.write(1);
    sc_start(1, SC_NS);

    // check whether execute stage is ready
    assertv(ready_o.read(), 1);
    assertv(instruction_o.read(), 0);
    assertv(instruction_valid_o.read(), 0);

    // insert instruction
    uint32_t instruction = 42;

    instruction_i.write(instruction);
    instruction_valid_i.write(1);
    next_stage_ready_i.write(0);

    sc_start(2, SC_NS);

    instruction_i.write(0);
    instruction_valid_i.write(0);

    // ensure that instruction is not forwarded until the latency is reached and the next stage is ready
    for(int i = latency; i >= 0; i--) {
        assertv(ready_o.read(), 0);
        assertv(instruction_o.read(), 0);
        assertv(instruction_valid_o.read(), 0);
        sc_start(1, SC_NS);
    }
    next_stage_ready_i.write(1);
    sc_start(1, SC_NS);
    assertv(instruction_o.read(), instruction);
    assertv(instruction_valid_o.read(), 1);

    sc_start(1, SC_NS);

    assertv(ready_o.read(), 1);
    assertv(instruction_o.read(), 0);
    assertv(instruction_valid_o.read(), 0);

    sc_start(1, SC_NS);
    assertv(ready_o.read(), 1);

    // end simulation with reset
    reset_n_i.write(0);
    sc_start(2, SC_NS);

    execute_stage->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "{{ name }}_ExecuteStage done!" << std::endl;
    return 0;
}
