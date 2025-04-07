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

The cache wrapper has one memory interface (see section _Memory Interface_) per port. Each signal is prefixed with `fe_x__`, _x_ being the respective port index. It also has one signal `hit_o_x` per port, indicating whether the request resulted in a hit or a miss.

Note that multiple ports get generated using an arbiter. This arbiter includes input buffers, meaning that requests can be issued even while the cache is busy from a request of another port. The arbiter also includes output buffers, meaning that requests from other ports also won't affect outgoing signals of the other ports.

`example_usage.py` shows an example on how to configure a `CacheWrapper`. It also shows how to generate the Verilog code for a module (this can be done similarly for other modules like the `Cache`, should you want to do so). Note that in the exported Verilog code, Amaranth (or rather Yosys) will initialize every register individually, which means also means that you will get one line per data word in both the cache store and the main memory. If you want to create large caches or a large main memory, generation would thus take long and create a very big file. Instead you should thus use your own memory modules for them. You can specify that when creating the `CacheWrapper` and `CacheConfig` objects.

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

## pulp_soc integration

We've successfully integrated PyCacheGen Caches into the [Pulpissimo SoC](https://github.com/pulp-platform/pulpissimo) as a pure data cache. [pulpissimo_cache_subsystem_wrapper.sv](src/pycachegen/pulpissimo/pulpissimo_cache_subsystem_wrapper.sv) provides a SystemVerilog module that can be used for integrating the cache into the Pulpissimo or other SoCs based on the [PULP SoC](https://github.com/pulp-platform/pulp_soc). The `pulpissimo_cache_subsystem_wrapper` itself uses the [PulpissimoCacheSubsytem](src/pycachegen/pulpissimo/cache_subsystem.py), which will itself create a `CacheWrapper`. You will thus need to configure the caches in the `PulpissimoCacheSubsystem` and then generate the Verilog code from it.

This module is designed to go into the `soc_interconnect_wrap`. There it will take all tcdm master ports which are part of the `master_ports` array (`tcdm_fc_data_addr_remapped`, `tcdm_fc_instr`, `tcdm_udma_tx`, `tcdm_udma_rx`, `tcdm_debug` and all `axi_bridge_2_interconnect` ports) as input to `tcdm_in`. Requests that are addressed for private bank 0 (which is where all data and nothing else should be) are then arbitrated and sent to the cache. If your linker script works differently, you might get poor performance. Requests that are not destined for private bank 0 will instead be output on the `tcdm_out` ports. These then need to be connected to the `master_ports` of the `soc_interconnect` (replacing the original `master_ports` array since that is now used as input for this module), where they'll go through a demux and the crossbars. The cache's own request interface is output as `tcdm_priv0`. Since all requests for private bank 0 will come from it, the contiguous crossbar should not get a rule for this address range and it also needs one less output port. This output port then has to be replaced by this module's `tcdm_priv0`. This is also done in the `soc_interconnect_wrap`: The `l2_private_slaves` array will still get one of its ports from the `contiguous_slaves` array output from the crossbar in the soc_interconnect, but the other port will be `tcdm_priv0`. The other `contiguous_slave` still has to be connected to the bootrom. Make sure you connect the ports in the correct order based on your contiguous crossbar rules and the order of the ports/memory banks in the l2 ram.
