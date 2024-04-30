# IOb-cache

This directory contains source files from the [IOb-cache](https://github.com/IObundle/iob-cache) github repository. IOb-cache is a highly configurable verilog cache module.

## Obtaining the source files

To create the source files for the cache, you need to clone the [IOb-soc](https://github.com/IObundle/iob-soc) repository as described on their github page (with `--recursive` for submodules).

You then need to install [Nix](https://nixos.org/download/#nix-install-linux) locally, because IOb use the `nix-shell` in their build process.

Then, go to `submodules/CACHE` in the IOb-soc repository and call `make sim-build BE_IF=AXI4`. `BE_IF` determines the type of interface between the cache and the main memory. Choosing AXI4 will create all the files you need for the native (IOb) interface plus the ones needed for AXI4. Note: `BE_DATA_W` only changes stuff in `iob_cache_conf.vh`, which is where I plan to configure all the other cache options anyway, so specifying it during the build process shouldn't be necessary, I hope.

After that, there will be a directory `submodules/iob_cache_VX.XX`. From there you will need all files inside `hardware/src` as well as all the ones from `hardware/simulation/src` except for the `_tb` files. Those are the files that I copied into `iob_cache/src` of this repository.

## Configuring the cache

I hope that all configuration to the cache (aside from the back end interface, probably) can be done from `src/iob_cache_conf.vh`, but this is untested.

### Cache configuration parameters

This is a very experimental documentation of the parameters that can be configured.

- `IOB_CACHE_NWAYS_W`: log_2(associativity) (confirmed)
- `IOB_CACHE_NLINES_W`: log_2(number of lines) ???
- `IOB_CACHE_WORD_OFFSET_W`: Has something to do with the number of words per block/way, but I don't know how they are related
- `IOB_CACHE_WTBUF_DEPTH_W`: log_2(number of positions in the write buffer for write-through)
- `IOB_CACHE_REP_POLICY`: 0: LRU, 1: PLRU_MRU, 2: PLRU_TREE
- `IOB_CACHE_WRITE_POL`: 0: Write-through with write no-allocate, 1: Write-back with write allocate

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