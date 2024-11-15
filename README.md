# PyCacheGen

PyCacheGen is a python package for generating data caches written in the [Amaranth HDL](https://github.com/amaranth-lang/amaranth). It can also be converted to Verilog.

## Feature overview

- Configurable number of sets, block size, associativity, word width, address width, byte size
- Supports write back and write through which can both be combined with write allocate and write no-allocate
- Supports the LRU, tree-based PLRU and MRU based PLRU replacement policies
- Read and write hits can be answered within one cycle
- Uses critical word first for read misses
- Caches with a block size greater than 1 can take advantage of bigger backend data widths
- Offers priority and round robin arbiters for generating multiple memory ports
- Offers a cache delay module for simulating slower caches

## Installation

The package can simply be installed using

    python -m pip install path/to/pycachegen

To install it for development, run the following from within this repository:

    python -m pip install -e .\[dev\]g

## Creating a Cache Wrapper

The `CacheWrapper` class can generate a top level module containing an arbitrary number of caches in a linear hierarchy as well as a simple data memory. It also supports multiple ports using an arbiter. See the internal documentation of the `CacheWrapper`, `CacheConfig` and `MemoryConfig` classes for more information.

The cache wrapper has one memory interface (see section *Memory Interface*) per port. Each signal is prefixed with `fe_x__`, *x* being the respective port index. It also has one signal `hit_o_x` per port, indicating whether the request yielded a hit or a miss.

Note that multiple ports get generated using an arbiter. This arbiter includes input buffers, meaning that requests can be issued even while the cache is busy from a request of another port. The arbiter also includes output buffers, meaning that requests from other ports also won't affect outgoing signals of the other ports.

`src/pycachegen/export.py` shows an example on how to configure a `CacheWrapper`. It also shows how to generate the Verilog code for a module (this can be done similarly for other modules like the `Cache`).

## Creating only a Cache

Caches can also be created individually using the `Cache` class. It can be configured using the `pycachegen.cache_config_validation.InternalCacheConfig` class, which is created using the standard `CacheConfig` class as well as some additional parameters. These parameters usually get inferred by the configuration of the `CacheWrapper` class. Also note that the latency parameters of the `CacheConfig` class only get processed by the `CacheWrapper` class and don't do anything otherwise.

The `Cache` uses one front end and one back end memory interface, prefixed with `fe__` and `be__` respectively.

## Memory Interface

All modules share a common memory interface composed of the following signals:

- `address` (In): The request address. Note that this address uses word addressing so it does not contain byte offset bits.
- `write_data` (In): The data to be written.
- `write_strobe` (In): If this signal is 0 it specifies a read request. Otherwise it specifies a write request. It contains one bit per byte of the write data so that each byte can be selected individually.
- `request_valid` (In): Specifies whether the request is valid.
- `flush` (In): Used request a write back of all data in the cache that is both valid and dirty. The flush action does not require the `request_valid` signal to be set. The cache will request a flush of the the level cache after it is done.
- `read_data` (Out): The requested data.
- `read_data_valid` (Out): Whether the `read_data` Signal holds valid data.
- `port_ready` (Out): Whether the port is ready to accept a new request.

## FPGA

Synthesis of the cache has been tested on a Xilinx XCZU3EG-1SFVA625I on a Avnet UltraZed-3EG IO Carrier Card using Vivado 2023.2. The project files are located at `vivado/amaranth_cache`. It has a block design that instantiates the cache inside an AXI Lite slave that is connected to the programmable system (PS). There is also small program for testing the synthesized cache that runs on the PS. The program was tested using Vitis 2023.2 and it is located at `vitis/`.
