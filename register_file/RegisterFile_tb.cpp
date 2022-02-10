#include "VRegisterFile.h"
#include "verilated_vcd_sc.h"

#include "VRegisterFile_RegisterFile.h"
#include "VRegisterFile__Dpi.h"

int sc_main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);

    // input signals
    sc_clock clk{"clk", 1, SC_NS, 0.5, 0, SC_NS, true};
    sc_signal<bool> reset_n;

    const int parameter_data_width = VRegisterFile_RegisterFile::DATA_WIDTH;
    const int parameter_num_registers = VRegisterFile_RegisterFile::NUM_REGISTERS;
    const int parameter_read_write_ports = VRegisterFile_RegisterFile::READ_WRITE_PORTS;

    std::cout << "DATA_WIDTH:       " << parameter_data_width << std::endl;
    std::cout << "NUM_REGISTERS:    " << parameter_num_registers << std::endl;
    std::cout << "READ_WRITE_PORTS: " << parameter_read_write_ports << std::endl;

    // CAUTION!!! 
    // when input/output wire of verilog module has less than 32 bits sc_signal<uint32_t> is inferred
    // instreand of sc_signal<sc_bv<X>>
    sc_signal<sc_bv<parameter_data_width*parameter_read_write_ports*parameter_num_registers>> data_i;
    sc_signal<u_int32_t> write_select_i;

    sc_signal<sc_bv<parameter_data_width*parameter_read_write_ports*parameter_num_registers>> data_o;

    // instantiate verilog module and connect signals
    VRegisterFile* register_file = new VRegisterFile{"register_file"};


    register_file->clk_i(clk);
    register_file->reset_n_i(reset_n);

    register_file->data_i(data_i);
    register_file->write_select_i(write_select_i);
    register_file->data_o(data_o);

    // start simulation, trace, and get parameters
    sc_start(0, SC_NS);

    sc_start(1, SC_NS);

    VerilatedVcdSc *trace = new VerilatedVcdSc();
    register_file->trace(trace, 99);
    trace->open("RegisterFile_tb.vcd");

    // run simulation further
    reset_n.write(0);

    sc_start(1, SC_NS);
    reset_n.write(1);

    sc_start(1, SC_NS);
    reset_n.write(1);

    for(int i = 0; i < parameter_num_registers; i++) {
        for(int j = 0; j < parameter_read_write_ports; j++) {
            write_select_i.write(0x1 << parameter_read_write_ports*i+j);
            data_i.write(0x1 << (parameter_read_write_ports*i+j)*parameter_data_width);
            sc_start(1, SC_NS);
            //write_select_i.set_bit(parameter_read_write_ports*i+j, 1);
        }
    }

    sc_start(1, SC_NS);
    register_file->final();

    trace->flush();
    trace->close();

    delete register_file;
    delete trace;

    std::cout << "Done!" << std::endl;

    return 0;
}