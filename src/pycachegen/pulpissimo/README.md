# Pulpissimo SoC integration

The cache has successfully been integrated into the Pulpissimo SoC as a pure data cache. [pulpissimo_cache_subsystem_wrapper.sv](pulpissimo_cache_subsystem_wrapper.sv) provides a SystemVerilog module that can be used for this purpose.

[cache_subsystem.py](cache_subsystem.py) can be used to generate a cache with an adapted interface for the Pulpissimo. It can also generate a write buffer and a delay unit and connect them to the cache. The delay unit delays all reads and writes by a configurable amount to simulate a slow main memory.
