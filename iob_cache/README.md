# IOb-cache

This directory contains source files from the [IOb-cache](https://github.com/IObundle/iob-cache) github repository. IOb-cache is a highly configurable verilog cache module.

## Obtaining the source files

To create the source files for the cache, you need to clone the [IOb-soc](https://github.com/IObundle/iob-soc) repository as described on their github page (with `--recursive` for submodules).

You then need to install [Nix](https://nixos.org/download/#nix-install-linux) locally, because IOb use the `nix-shell` in their build process.

Then, go to `submodules/CACHE` in the IOb-soc repository and call `make sim-build BE_IF=AXI4`. `BE_IF` determines the type of interface between the cache and the main memory. Choosing AXI4 will create all the files you need for the native (IOb) interface plus the ones needed for AXI4. Note: `BE_DATA_W` only changes stuff in `iob_cache_conf.vh`, which is where we'll configure the entire cache anyway, so specifying it during the build process is not necessary.

After that, there will be a directory `submodules/iob_cache_VX.XX`. From there you will need all files inside `hardware/src` as well as all the ones from `hardware/simulation/src` except for the `_tb` files. Those are the files that I copied into `iob_cache/src` of this repository.

## Configuring the cache

All the configuration to the cache can be done from `src/iob_cache_conf.vh`. The parameters are described inside in IOb-cache repository in the iob_cache.py, but I will describe them (at least the relevant ones that I've tested) here as well.

### Cache configuration parameters

- `ADDR_W
- `FE_ADDR_W`: Address width of the cache
- `FE_DATA_W`: Word width of the cache. Needs to be either 32 or 64.
- `BE_ADDR_W`: Address width of the main memory. What happens when this is higher than `FE_ADDR_W` is untested. The address space is also somehow restricted by `ADDR_W`, but I dont know what it does.
- `BE_DATA_W`: Word width of the main memory. Needs to be a multiple of `FE_DATA_W`.
- `IOB_CACHE_NWAYS_W`: log_2(associativity) - 0 creates a direct mapped cache, higher values will create a set associative cache.
- `IOB_CACHE_NLINES_W`: log_2(number of lines) - needs to be at least 1, so there will always be at least two lines, meaning that a fully associative cache is not possible.
- `IOB_CACHE_WORD_OFFSET_W`: log_2(words per line) - needs to be at least 1, so there will always be at least two words per line.
- `IOB_CACHE_WTBUF_DEPTH_W`: log_2(number of positions in the write buffer for write-through)
- `IOB_CACHE_REP_POLICY`: 0: LRU, 1: PLRU_MRU, 2: PLRU_TREE
- `IOB_CACHE_WRITE_POL`: 0: Write-through with write no-allocate, 1: Write-back with write allocate
- `USE_CTRL`: Adds a "Cache-Control" unit that adds memory mapped registers to the cache. The cache input address will get one bit wider and if the MSB is 1, the Cache-Control registers will get accessed. The registers allow invalidating the cache contents and monitoring the write through buffers.
- `USE_CTRL_CNT`: This setting adds Cache-Control registers that contain
    - read and write hits (address 0x4)
    - read and write misses (address 0x8)
    - read hits (address 0xC)
    - read misses (address 0x10)
    - write hits (address 0x14)
    - write misses (address 0x18)
    
    Note that these addresses are the full addresses including the bits for the byte offset. The verilog cache model doesn't include those bits, so the addresses have to be shifted right by 2 bits. I'm not sure if the functions added by only using `USE_CTRL` will still work after also using this option.

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