#include <memory>
#include <vector>
#include <systemc.h>
#include <verilated.h>
#include <verilated_vcd_sc.h>

#include "V{{ name }}_Scoreboard.h"

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

    //const std::unique_ptr<V{{ name }}_Memory> memory{new V{{ name }}_Memory{"{{ name }}_Memory"}};
    const std::unique_ptr<V{{ name }}_Scoreboard> scoreboard{new V{{ name }}_Scoreboard{"{{ name }}_Scoreboard"}};

	scoreboard->clk_i(clk_i);
	scoreboard->reset_n_i(reset_n_i);
	
	// start simulation and trace
    std::cout << "{{ name }}_Memory start!" << std::endl;

	sc_start(0, SC_NS);

    VerilatedVcdSc* trace = new VerilatedVcdSc();
    scoreboard->trace(trace, 99);

    if(vcd_file_path.empty()) {
        trace->open("{{ name }}_Scoreboard.vcd");
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
    sc_start(15, SC_NS);

	// end simulation with reset
    reset_n_i.write(0);
    sc_start(2, SC_NS);

    scoreboard->final();

    trace->flush();
    trace->close();

    delete trace;

    std::cout << "{{ name }}_Scoreboard done!" << std::endl;

    return 0;
}