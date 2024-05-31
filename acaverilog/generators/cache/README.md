Things are a tiny bit messy atm; Inside the `generators/` directory there are python files that can generate verilog source code. There are generators for a functional memory (based on the normal memory, but modified so that it can also hold data), the cache and for a cache wrapper. The cache wrapper wraps the cache and the functional memory in one module. Right now these generators don't inherit from the ModuleGenerator class because of import errors, but one day they will.

Anyway, there's also a `CMakeLists.txt` that will call the `cache_wrapper_generator.py` and the `functional_memory_generator.py` to create verilog source files in the `src/` directory. Inside `tb/` there are testbenches for the functional memory as well as several for the cache wrapper. There's multiple for the cache wrapper to test different configurations. The `CMakeLists.txt` will create the necessary source files for all configurations and each test bench will use the correct one.

You can then call ninja and execute the executables of the testbenches as well as inspect the traces.

Keep in mind that when changing the python generator files, CMake has to be called again (not just ninja).
