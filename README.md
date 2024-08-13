# Generating Verilog Code

Inside the `generators/` directory there are python files that can generate verilog source code. There are generators for a functional memory (based on the normal memory, but modified so that it can also hold data), for the cache and for a cache wrapper. There's also some generators for other modules that get instantiated within the named modules, so they're not relevant to the user.

The cache wrapper wraps the cache and the functional memory in one module. It can create linear cache architectures (so no two caches on the same level). It can also create an arbiter so that you can have multiple access ports. Creating caches is optional - the cache wrapper can also simply create a memory, optionally with an arbiter.

## Creating Verilog Code for the testbenches

There are many testbenches for different cache wrapper configurations. Go inside the `testbenches/` directory. There's a `CMakeLists.txt` that will call the `cache_wrapper_generator.py` to create verilog source files, put them in the `src/` directory and verilate them. Inside `tb/` there are several testbenches for different configurations of the cache wrapper. The `CMakeLists.txt` will create the necessary source files for all configurations and each test bench will use the correct one. Create a `build/` directory and change into it, then call `cmake -GNinja ..` and then `ninja`. Then you can execute the individual testbenches, or you can can call the bash script `../run_testbenches.sh` to execute all testbenches.

## Creating Verilog Code for custom cache hierarchies

To actually generate Verilog files for custom cache hierarchies, go to the `custom/` folder. There you'll find a `custom_cache_wrapper_generator.py` where you can configure a cache/memory hierarchy and generate an output file. There's also a `CMakeLists.txt` that will call the python script just mentioned, verilate the verilog code and compile it with a testbench for executing memory traces. The section below shows how to create trace files. In the testbench, change the variables for things like the address and data width at the top of the file accordingly. You can then call the executable with the path to the binary trace file. As a second parameter you can specify the path to a file to which the total number of cycles needed will be written, which is useful for doing automated testing.

# Memory traces

You can execute memory traces one the FPGA or in simulation. Both methods use binaries with an arbitrary number of trace instruction that use the following format:

        +-------------------+-------+----------------------------------------------+-----------+
        |       [w-1]       |       |               [d + a - 1 : a]                | [a-1 : 0] |
        +-------------------+-------+----------------------------------------------+-----------+
        | write: 1, read: 0 | empty | write data (ignored if write bit is not set) | address   |
        +-------------------+-------+----------------------------------------------+-----------+
        
Where `w` is the width of the whole instruction, `d` is the width of the write data and `a` is the address width. `w` needs to be of the form `n*8` with `n>0` if used for simulation or `2^n*8` with `n>=0` if used for the FPGA. When used for the simulation, `a` and `d` can only be up to 32 bits wide (you'd just have to change the signal widths in the testbench otherwise).

The tracing testbench just reads this binary, but for executing it on the FPGA you'll need to convert it to a C header file so that it can be compiled into the executable. To do so, you can use `xxd -i <filename.bin> > <filename.h>`. You can then include it in the C/C++ program for the FPGA and then make sure that the program uses the correct data and length variables. If you named the binary `mem_trace.bin`, it will already be included correctly and also use the correct variables.

# FPGA

The cache can also be synthesized and used on an FPGA. The vivado project files are inside `/vivado`. There's currently two projects:

- `cache` simply connects the cache's in and outputs to the registers of an AXI lite slave. You can edit the block design and use any cache wrapper verilog file you want, as long as the L1 cache has only one port (the other ports simply are not connected to anything) and as long as the address and data width of the L1 cache are not bigger than 32 bits, because thats how wide the AXI4 lite registers are. In software, you can then write to the registers of the AXI lite slave and the values will be passed onto the cache. The mappings of the registers to the cache ports are documented inside the AXI slave verilog file.
- Then there's also the `bram_cache` project. It allows writing a trace to a BRAM that will then be processed by the cache. After executing the trace, the total execution time will be written to another BRAM. Note: If you get a critical warning about the bus interface property `AWUSER_WIDTH` or `MASTER_TYPE` not matching during synthesis (`[BD 41-237]`), don't worry, it doesn't matter.

Inside `/vitis` directories with programs for the Vivado designs:
- `cache` contains programs for the normal `cache` design without the tracing BRAMs. There are multiple programs because they are designed for different cache configurations (they match some of the testbench configurations - at least if you disable the reset).
- `bram_cache` is made for the `bram_cache` design and allows you to write a trace into an array manually. It is designed for using small traces and verifying that they got executed correctly. It already contains one such trace.
- `trace_file_bram_cache` is also made for the `bram_cache` design, but it is used for executing memory traces (see the section above). To synthesize a matching cache wrapper, you will, in addition to the general steps listed below, need to do a few things:
    1. In the controller for the trace BRAM, set the data width you need (depends on your data and address width of course).
    2. In the address editor, set the width of the address range for the trace BRAM so it fits all your instructions. Note that the addresses are BYTE addressed, so if you select 4k and your instructions are 4 byte wide then you can fit 1024 instructions.
    3. Right click the cache wrapper AXI slave and select "Customize Block". Then enter the data and address width (log2 of the address range width) you just set. You also need to specify the address and data width (`a` and `d` in the above diagram) of the L1 cache so that it knows how to interpret the instructions.

To execute these programs on the FPGA, you will need to 
1. synthesize and export the hardware into an `.xsa` file
2. create a new project in Vitis
3. copy the program files into that project

To synthesize the setup you need,
1. open the design in Vivado
2. In the block design, right click the cache wrapper AXI slave and select "Edit in IP packager"
3. In the sources list, right click the cache wrapper source file and select "Replace File...". Select the cache wrapper verilog file you need, then repackage the IP.
4. Right click the cache wrapper AXI slave and select "Customize Block". Then enter your data and address width.
5. synthesize, implement, generate bitstream and export the hardware including the bitstream.
