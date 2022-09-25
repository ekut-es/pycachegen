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

    // signals
    sc_clock clk_i{"clk", 1, SC_NS, 0.5, 0, SC_NS, true};
    sc_signal<bool> reset_n_i;

    const std::unique_ptr<V{{ instruction_memory_fetch_stage_wrapper_name }}_InstructionMemoryFetchStageWrapper> imfsw{new V{{ instruction_memory_fetch_stage_wrapper_name }}_InstructionMemoryFetchStageWrapper{"{{ instruction_memory_fetch_stage_wrapper_name }}_InstructionMemoryFetchStageWrapper"}};

    imfsw->clk_i(clk_i);
    imfsw->reset_n_i(reset_n_i);

    // start simulation and trace
    std::cout << "{{ instruction_memory_fetch_stage_wrapper_name }}_InstructionMemoryFetchStageWrapper start!" << std::endl;

    sc_start(0, SC_NS);

    VerilatedVcdSc* trace = new VerilatedVcdSc();
    imfsw->trace(trace, 99);

    if(vcd_file_path.empty()) {
        trace->open("{{ instruction_memory_fetch_stage_wrapper_name }}_InstructionMemoryFetchStageWrapper.vcd");
    } else {
        trace->open(vcd_file_path.c_str());
    }

    // reset
    sc_start(1, SC_NS);
    reset_n_i.write(0);
    sc_start(1, SC_NS);
    reset_n_i.write(1);
    sc_start(1, SC_NS);

    // run test bench
    sc_start(50, SC_NS);


    // end simulation with reset
    reset_n_i.write(0);
    sc_start(2, SC_NS);

    imfsw->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "{{ instruction_memory_fetch_stage_wrapper_name }}_InstructionMemoryFetchStageWrapper done!" << std::endl;

    return 0;
}
