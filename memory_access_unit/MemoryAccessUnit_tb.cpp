#include "VMemoryAccessUnit.h"
#include "VMemoryAccessUnit_MemoryAccessUnit.h"
#include "VMemoryAccessUnit__Dpi.h"
#include "verilated_vcd_sc.h"

int sc_main(int argc, char** argv) {
    Verilated::commandArgs(argc, argv);
    Verilated::traceEverOn(true);

    // input signals
    sc_clock clk{"clk", 1, SC_NS, 0.5, 0, SC_NS, true};
    sc_signal<bool> reset_n;

    const int parameter_latency = VMemoryAccessUnit_MemoryAccessUnit::LATENCY;
    const int parameter_data_width =
        VMemoryAccessUnit_MemoryAccessUnit::DATA_WIDTH;
    const int parameter_instruction_length =
        VMemoryAccessUnit_MemoryAccessUnit::INSTRUCTION_LENGTH;
    const int parameter_opcode_length =
        VMemoryAccessUnit_MemoryAccessUnit::OPCODE_LENGTH;
    const int parameter_register_read_ports =
        VMemoryAccessUnit_MemoryAccessUnit::REGISTER_READ_PORTS;
    const int parameter_num_read_registers =
        VMemoryAccessUnit_MemoryAccessUnit::NUM_READ_REGISTERS;
    const int parameter_register_write_ports =
        VMemoryAccessUnit_MemoryAccessUnit::REGISTER_WRITE_PORTS;
    const int parameter_num_write_registers =
        VMemoryAccessUnit_MemoryAccessUnit::NUM_WRITE_REGISTERS;
    const int parameter_memory_read_ports =
        VMemoryAccessUnit_MemoryAccessUnit::MEMORY_READ_PORTS;
    const int parameter_num_read_memories =
        VMemoryAccessUnit_MemoryAccessUnit::NUM_READ_MEMORIES;
    const int parameter_memory_write_ports =
        VMemoryAccessUnit_MemoryAccessUnit::MEMORY_WRITE_PORTS;
    const int parameter_num_write_memories =
        VMemoryAccessUnit_MemoryAccessUnit::NUM_WRITE_MEMORIES;

    std::cout << "LATENCY:              " << parameter_latency << std::endl;
    std::cout << "DATA_WIDTH:           " << parameter_data_width << std::endl;
    std::cout << "INSTRUCTION_LENGTH:   " << parameter_instruction_length
              << std::endl;
    std::cout << "OPCODE_LENGTH:        " << parameter_opcode_length
              << std::endl;
    std::cout << "REGISTER_READ_PORTS:  " << parameter_register_read_ports
              << std::endl;
    std::cout << "NUM_READ_REGISTERS:   " << parameter_num_read_registers
              << std::endl;
    std::cout << "REGISTER_WRITE_PORTS: " << parameter_register_write_ports
              << std::endl;
    std::cout << "NUM_WRITE_REGISTERS:  " << parameter_num_write_registers
              << std::endl;
    std::cout << "MEMORY_READ_PORTS:    " << parameter_memory_read_ports
              << std::endl;
    std::cout << "NUM_READ_MEMORIES:    " << parameter_num_read_memories
              << std::endl;
    std::cout << "MEMORY_WRITE_PORTS:   " << parameter_memory_write_ports
              << std::endl;
    std::cout << "NUM_WRITE_MEMORIES:   " << parameter_num_write_memories
              << std::endl;

    // CAUTION!!!
    // when input/output wire of verilog module has less than 32 bits
    // sc_signal<uint32_t> is inferred instead of sc_signal<sc_bv<X>>
    sc_signal<uint32_t> instruction_i;
    sc_signal<bool> instruction_valid_i;

    sc_signal<uint64_t> register_data_i;

    sc_signal<uint32_t> register_select_o;
    sc_signal<bool> write_register_select_o;

    sc_signal<uint32_t> register_data_o;

    sc_signal<bool> ready_o;
    sc_signal<bool> instruction_done_o;

    // instantiate verilog module and connect signals
    VMemoryAccessUnit* memory_access_unit =
        new VMemoryAccessUnit{"memory_access_unit"};

    memory_access_unit->clk_i(clk);
    memory_access_unit->reset_n_i(reset_n);

    memory_access_unit->instruction_i(instruction_i);
    memory_access_unit->instruction_valid_i(instruction_valid_i);

    memory_access_unit->register_data_i(register_data_i);
    memory_access_unit->register_select_o(register_select_o);
    memory_access_unit->write_register_select_o(write_register_select_o);

    memory_access_unit->register_data_o(register_data_o);

    memory_access_unit->ready_o(ready_o);
    memory_access_unit->instruction_done_o(instruction_done_o);

    // start simulation, trace, and get parameters
    sc_start(0, SC_NS);

    VerilatedVcdSc* trace = new VerilatedVcdSc();
    memory_access_unit->trace(trace, 99);
    trace->open("MemoryAccessUnit_tb.vcd");

    // run simulation further
    sc_start(1, SC_NS);
    reset_n.write(1);
    sc_start(1, SC_NS);
    reset_n.write(1);
    sc_start(1, SC_NS);

    // insert instruction
    uint32_t instruction = 0xdeadbeef;
    instruction_i.write(instruction);
    instruction_valid_i.write(1);
    sc_start(1, SC_NS);

    instruction_i.write(0);
    instruction_valid_i.write(0);

    for (int i = 0; i < parameter_latency; i++) {
        sc_start(1, SC_NS);
    }

    sc_start(1, SC_NS);

    // check if instructions is done after latency
    assert(instruction_done_o.read() == 1);

    // end simulation with reset
    reset_n.write(0);
    sc_start(2, SC_NS);

    memory_access_unit->final();

    trace->flush();
    trace->close();

    delete memory_access_unit;
    delete trace;

    std::cout << "Done!" << std::endl;

    return 0;
}
