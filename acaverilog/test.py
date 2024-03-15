#from memory_verilog_template import *
from pipeline_stage_verilog_template import *
from register_file_verilog_template import *
from memory_verilog_template import *
from memory_access_unit_verilog_template import *
from instruction_memory_access_unit_verilog_template import *
from functional_unit_verilog_template import *
from execute_stage_verilog_template import *
from veriloggen import *
from acadl import (
    generate,
    latency_t,
    acadl_edge_t,
    create_ag,
    Data,
    Memory,
    InstructionMemoryAccessUnit,
    RegisterFile,
    InstructionFetchStage,
    PipelineStage,
    ExecuteStage,
    FunctionalUnit,
    MemoryAccessUnit,
    ACADLEdge,
)
from utils import *

imem0 = Memory(
        name="imem",
        data_width=32,
        max_concurrent_requests=1,
        read_write_ports=1,
        port_width=1,
        data={},
        read_latency=latency_t(1),
        write_latency=latency_t(1),
        address_ranges={(0, 0x1000)},
    )

imau0 = InstructionMemoryAccessUnit(
    name="imau",
    to_process={"jump", "jal", "beq", "bne", "blt", "bge"},
    latency=latency_t(1),
)

pcrf0 = RegisterFile(name="pcrf", registers={"pc": Data(32, 0)}, data_width=32)

ifs0 = InstructionFetchStage(
    name="ifs", latency=latency_t(1), issue_buffer_size=1
)

ds0 = PipelineStage(name="ds", latency=latency_t(1))

ex0 = ExecuteStage(name="ex", latency=latency_t(1))

fu0 = FunctionalUnit(
    name="fu", to_process={"mov", "add", "mul", "mac"}, latency=latency_t(1)
)

mau0 = MemoryAccessUnit(
    name="mau", to_process={"load", "store"}, latency=latency_t(1)
)

rf0 = RegisterFile(
    name="rf",
    data_width=32,
    registers={
        "r0": Data(32, 0),
        "r1": Data(32, 0),
        "r2": Data(32, 0),
        "r3": Data(32, 0),
        "r4": Data(32, 0),
        "r5": Data(32, 0),
        "r6": Data(32, 0),
        "r7": Data(32, 0),
        "r8": Data(32, 0),
        "r9": Data(32, 0),
        "r10": Data(32, 0),
        "r11": Data(32, 0),
        "r12": Data(32, 0),
        "r13": Data(32, 0),
        "r14": Data(32, 0),
        "r15": Data(32, 0),
        "sp": Data(32, 0),
    },
)

dmem0 = Memory(
    name="dmem",
    data_width=32,
    max_concurrent_requests=1,
    read_write_ports=1,
    port_width=1,
    data={},
    read_latency=latency_t(1),
    write_latency=latency_t(1),
    address_ranges={(0x1000, 0x4000)},
)

ACADLEdge(imem0, imau0, acadl_edge_t.READ_DATA)
ACADLEdge(pcrf0, imau0, acadl_edge_t.READ_DATA)
ACADLEdge(imau0, pcrf0, acadl_edge_t.WRITE_DATA)
ACADLEdge(ifs0, imau0, acadl_edge_t.CONTAINS)
ACADLEdge(ifs0, ds0, acadl_edge_t.FORWARD)
ACADLEdge(ds0, ex0, acadl_edge_t.FORWARD)
ACADLEdge(ex0, fu0, acadl_edge_t.CONTAINS)
ACADLEdge(fu0, rf0, acadl_edge_t.WRITE_DATA)
ACADLEdge(rf0, fu0, acadl_edge_t.READ_DATA)
ACADLEdge(ex0, mau0, acadl_edge_t.CONTAINS)
ACADLEdge(mau0, rf0, acadl_edge_t.WRITE_DATA)
ACADLEdge(rf0, mau0, acadl_edge_t.READ_DATA)
ACADLEdge(mau0, dmem0, acadl_edge_t.WRITE_DATA)
ACADLEdge(dmem0, mau0, acadl_edge_t.READ_DATA)

dmem = MemoryVerilogTemplate(dmem0, enable_data_reset = False)
dmem.generate_test_bench("./build", True)
verilate("./build", "./build")
simulate("./build/sim/VMemory_tb")

imem = MemoryVerilogTemplate(imem0, enable_data_reset = False)
imem.generate_test_bench("./build", True)
verilate("./build", "./build")
simulate("./build/sim/VMemory_tb")

ds = PipelineStageVerilogTemplate(ds0)
ds.generate_test_bench("./build", True)
verilate("./build", "./build")
simulate("./build/sim/VPipelineStage_tb")

rf = RegisterFileVerilogTemplate(rf0)
rf.generate_test_bench("./build", True)
verilate("./build", "./build")
simulate("./build/sim/VRegisterFile_tb")

pcrf = RegisterFileVerilogTemplate(pcrf0)
pcrf.generate_test_bench("./build", True)
verilate("./build", "./build")
simulate("./build/sim/VRegisterFile_tb")

ex = ExecuteStageVerilogTemplate(ex0)
ex.generate_test_bench("./build", True)
verilate("./build", "./build")
simulate("./build/sim/VExecuteStage_tb")

fu = FunctionalUnitVerilogTemplate(fu0)
fu.generate_test_bench("./build", True)
verilate("./build", "./build")
simulate("./build/sim/VFunctionalUnit_tb")

imau = InstructionMemoryAccessUnitVerilogTemplate(imau0)
#imau.generate_module("./build")
#imau.generate_test_bench("./build", True)
#verilate("./build", "./build")
#simulate("./build/sim/VInstructionMemoryAccessUnit_tb")