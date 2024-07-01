# Generating Verilog Code

Things are a tiny bit messy atm; Inside the `generators/` directory there are python files that can generate verilog source code. There are generators for a functional memory (based on the normal memory, but modified so that it can also hold data), the cache and for a cache wrapper. The cache wrapper wraps the cache and the functional memory in one module. Right now these generators don't inherit from the ModuleGenerator class because of import errors, but one day they will.

Anyway, there's also a `CMakeLists.txt` that will call the `cache_wrapper_generator.py` and the `functional_memory_generator.py` to create verilog source files in the `src/` directory. Inside `tb/` there are testbenches for the functional memory as well as several for the cache wrapper. There's multiple for the cache wrapper to test different configurations. The `CMakeLists.txt` will create the necessary source files for all configurations and each test bench will use the correct one.

You can then call ninja and execute the executables of the testbenches as well as inspect the traces.

Keep in mind that when changing the python generator files, CMake has to be called again (not just ninja).

# FPGA

The cache can also be synthesized and used on an FPGA. The vivado project files are inside `/vivado`. There's currently two projects:

`cache` is for caches with a single port - other than that, there are no restrictions. You can edit the block design and use any cache wrapper verilog file you want, as long as the L1 cache has only one port (the other ports simply are not connected to anything). The cache wrapper gets instantiated in a custom AXI slave. In software, you can then write to the registers of the AXI lite slave and the values will be passed onto the cache. The mappings of the registers to the cache ports are documented inside the AXI slave verilog file.

Then there's also the `bram_cache` project which is currently under development. It allows using a memory trace that will be processed by the trace.

Inside `/vitis` there's also directories corresponding to those in `/vivado` containing c source code for some designs. You will have to synthesize and export the xsa file from vivado and use that to create a Vitis project on your own.

