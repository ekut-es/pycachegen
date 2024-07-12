# Generating Verilog Code

Inside the `generators/` directory there are python files that can generate verilog source code. There are generators for a functional memory (based on the normal memory, but modified so that it can also hold data), for the cache and for a cache wrapper. There's also some generators for other modules that get instantiated within the named modules, so they're not relevant to the user.

The cache wrapper wraps the cache and the functional memory in one module. It can create linear cache architectures (so no two caches on the same level). It can also create an arbiter so that you can have multiple access ports.

# Testbenches
To run the testbenches, create a `/build` directory. There's a `CMakeLists.txt` that will call the `cache_wrapper_generator.py` and the `functional_memory_generator.py` to create verilog source files in the `src/` directory and to verilate them. Inside `tb/` there are testbenches for the functional memory as well as several for the cache wrapper with different configurations. The `CMakeLists.txt` will create the necessary source files for all configurations and each test bench will use the correct one.

You can then call ninja and execute the executables of the testbenches as well as inspect the traces.

Keep in mind that when changing the python generator files, CMake has to be called again (not just ninja).

# FPGA

The cache can also be synthesized and used on an FPGA. The vivado project files are inside `/vivado`. There's currently two projects:

- `cache` simply connects the cache's in and outputs to the registers of an AXI lite slave. You can edit the block design and use any cache wrapper verilog file you want, as long as the L1 cache has only one port (the other ports simply are not connected to anything) and uses data width 16 and address width 8. The widths can be changed pretty easily in the AXI slave's source file, so this is not a huge restriction. If however the widths are bigger than 32 bits, you'll need to find out how to make the registers bigger. In software, you can then write to the registers of the AXI lite slave and the values will be passed onto the cache. The mappings of the registers to the cache ports are documented inside the AXI slave verilog file.
- Then there's also the `bram_cache` project. It allows writing a trace to a BRAM that will then be processed by the cache. After executing the trace, the total execution time will be written to another BRAM.

Inside `/vitis` directories with programs for the Vivado designs:
- `cache` contains programs for the normal `cache` design without the tracing BRAMs. There are multiple programs because they are designed for different cache configurations (they match some of the testbench configurations).
- `bram_cache` is made for the `bram_cache` design and allows you to write a trace into an array manually. It is designed for using small traces and verifying that they got executed correctly. It already contains one such trace.
- `trace_file_bram_cache` is also made for the `bram_cache` design, but it is used for executing big traces from binary files. The binaries hold an arbitrary amount of instructions. Instructions have the following format:

        +-------------------+-------+----------------------------------------------+-----------+
        |       [w-1]       |       |               [d + a - 1 : a]                | [a-1 : 0] |
        +-------------------+-------+----------------------------------------------+-----------+
        | write: 1, read: 0 | empty | write data (ignored if write bit is not set) | address   |
        +-------------------+-------+----------------------------------------------+-----------+
    Where `w` is the width of the whole instruction, `d` is the width of the write data and `a` is the address width.

    To synthesize a matching cache wrapper, you will, in addition to the general steps listed below, need to do a few things:
    1. In the controller for the trace BRAM, set the data width you need (depends on your data and address width of course).
    2. In the address editor, set the width of the address range for the trace BRAM so it fits all your instructions. Note that the addresses are word addressed, so if you select 4k you can fit 4096 instructions no matter how wide they are.
    3. Right click the cache wrapper AXI slave and select "Customize Block". Then enter the data and address width (log2 of the address range width) you just set. You also need to specify the address and data width (`a` and `d` in the above diagram) of the L1 cache so that it knows how to interpret the instructions.

To execute these programs on the FPGA, you will need to 
1. synthesize and export the hardware into an `.xsa` file
2. create a new project in Vitis
3. copy the program files into that project

To synthesize the setup you need,
1. open the design in Vivado
2. In the block design, right click the cache wrapper AXI slave and select "Edit in IP packager"
3. In the sources list, right click the cache wrapper source file and select "Replace File...". Select the cache wrapper verilog file you need, then repackage the IP.
4. synthesize, implement, generate bitstream and export the hardware including the bitstream.