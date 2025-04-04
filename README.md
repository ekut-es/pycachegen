# PyCacheGen

PyCacheGen is a python package for generating data caches written in the [Amaranth HDL](https://github.com/amaranth-lang/amaranth). The generated caches can be converted into synthesizable Verilog code.

## Feature overview

- Configurable number of sets, block size, associativity, word width, address width, byte size
- Supports write back and write through which can both be combined with write allocate and write no-allocate
- Supports the FIFO, LRU, tree-based PLRU and MRU based PLRU replacement policies
- Read and write hits can be answered within one cycle
- Uses critical word first for read misses
- Caches with a block size greater than 1 can take advantage of bigger backend data widths
- Offers priority and round robin arbiters for generating multiple memory ports

## Installation

The package can simply be installed using

    python -m pip install path/to/pycachegen

To install it for development, run the following from within this repository:

    python -m pip install -e .\[dev\]


## Example Usage

The `CacheWrapper` class can generate a top-level module containing an arbitrary number of caches in a linear hierarchy. It can also generate an arbiter for creating multiple request ports and a simple data memory. All modules in the cache wrapper are optional, meaning that you can also use it for just creating a single cache, which is the recommended way for doing so. See the internal documentation of the `CacheWrapper`, `CacheConfig` and `MemoryConfig` classes for more information.

The cache wrapper has one memory interface (see section *Memory Interface*) per port. Each signal is prefixed with `fe_x__`, *x* being the respective port index. It also has one signal `hit_o_x` per port, indicating whether the request resulted in a hit or a miss.

Note that multiple ports get generated using an arbiter. This arbiter includes input buffers, meaning that requests can be issued even while the cache is busy from a request of another port. The arbiter also includes output buffers, meaning that requests from other ports also won't affect outgoing signals of the other ports.

`example_usage.py` shows an example on how to configure a `CacheWrapper`. It also shows how to generate the Verilog code for a module (this can be done similarly for other modules like the `Cache`, should you want to do so).

## Memory Interface

All modules share a common memory interface composed of the following signals:

- `address` (In): The request address. Note that this address uses word addressing and so it does not contain byte offset bits.
- `write_data` (In): The data to be written.
- `write_strobe` (In): If this signal is 0 it signals a read request, else it signals a write request. It contains one bit per byte of the write data so that each byte can be selected individually.
- `request_valid` (In): Specifies whether the request is valid.
- `flush` (In): Used to request a write back of all data in the cache that is both valid and dirty. The flush action does not require the `request_valid` signal to be set. The cache will request a flush of the next level cache after it is done to ensure that the whole cache hierarchy gets flushed.
- `read_data` (Out): The requested data. Note that this signal may not change until the next request gets sent.
- `read_data_valid` (Out): Whether the `read_data` Signal holds valid data. Note that this signal may not change until the next request gets sent.
- `port_ready` (Out): Whether the port is ready to accept a new request. The requester assumes that his request was accepted if he set `request_valid` (or `flush`) and `port_ready` is also set. If a target is not ready to accept a new request, it must either set this signal to 0 or it must buffer the accepted request. This port is also allowed to be used like a grant signal which only gets set to 1 if there is an incoming request. Note that flushes currently don't work if you do so though.
