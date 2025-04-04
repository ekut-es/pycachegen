# Pulpissimo SoC integration

The cache has successfully been integrated into the Pulpissimo SoC as a pure data cache. [pulpissimo_cache_subsystem_wrapper.sv](pulpissimo_cache_subsystem_wrapper.sv) provides a SystemVerilog module that can be used for this purpose. That module uses the [cache_subsystem.py](cache_subsystem.py) which generates a CacheWrapper with an adapted interface.

See [pulpissimo_cache_subsystem_wrapper.sv](pulpissimo_cache_subsystem_wrapper.sv) for how to integrate the Cache into the SoC.
