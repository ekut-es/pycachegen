# IOb-cache

This directory contains source files from the [IOb-cache](https://github.com/IObundle/iob-cache) github repository. IOb-cache is a highly configurable verilog cache module.

## Obtaining the source files

To create the source files for the cache, you need to clone the [IOb-soc](https://github.com/IObundle/iob-soc) repository as described on their github page (with `--recursive` for submodules).

You then need to install [Nix](https://nixos.org/download/#nix-install-linux) locally, because IOb use the `nix-shell` in their build process.

Then, go to `submodules/CACHE` in the IOb-soc repository and call `make sim-build [BE_IF=AXI4|IOb] [BE_DATA_W=32|64|128|256|etc]`. `BE_IF` determines the type of interface between the cache and the main memory. `BE_DATA_W` determines the word size of the main memory, but I hope that this can still be changed after the build process.

After that, there will be a directory `submodules/iob_cache_VX.XX`. From there you will need all files inside `hardware/src` as well as `bsp.vh`, `iob_cache_sim_wrapper.v`, `iob_ram_2p.v`, `iob_ram_sp_be.v` and `iob_ram_sp.v` from `hardware/simulation/src`. Those are the files that I copied into `iob_cache/src` of this repository.

## Configuring the cache

I hope that all configuration to the cache (aside from the back end interface, probably) can be done from `src/iob_cache_conf.vh`, but this is untested.

## Building and running the cache

Go to the `build` directory und call

```
cmake -GNinja ..
ninja
```

to verilate the cache module. You can then use
```
./Vcache_tb
```
to execute the test bench. This will also create a `Vcache_tb.vcd` waveform file.