Things are a bit messy atm; outside of this directory there are the following files: `cache_generator.py`, `functional_memory_generator.py` and `cache_wrapper_generator.py`. The functional memery is based on the normal memory but modified so that it can also store data. The cache generator contains the actual cache and the cache wrapper is a module that connects one cache to one functional memory. Right now these doesn't inherit from the ModuleGenerator class because of import errors, but one day they will.

Anyway, inside of this directory you've got a CMakeLists.txt that will call the cache_wrapper_generator.py and the functional_memory_generator.py to create verilog source files in the ./src directory. There's also test benches here for the functional memory as well as several (2 atm) for the cache wrapper. There's multiple for the cache wrapper to test different configurations. The CMakeLists.txt will create the necessary source files for all configurations and each test bench will use the correct one.

You can then call ninja and execute the executables of the testbenches as well as inspect the traces.

Keep in mind that when changing the python generator files, CMake has to be called again (not just ninja).
