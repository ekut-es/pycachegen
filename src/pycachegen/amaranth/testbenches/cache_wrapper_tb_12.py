from pycachegen.amaranth.testbenches.tb_utils import (
    CacheWrapperBenchHelper,
    run_bench,
)
from pycachegen.amaranth.cache_wrapper import CacheWrapper
from pycachegen.cache_config_validation import CacheConfig, MemoryConfig


# Testbench for testing flushes can be queued whilst another request is being processed
def test():
    dut = CacheWrapper(
        num_ports=1,
        arbiter_policy="priority",
        byte_size=8,
        enable_reset=False,
        address_width=8,
        cache_configs=[
            CacheConfig(
                data_width=16,
                num_ways=1,
                num_sets=4,
                replacement_policy="plru_tree",
                hit_latency=10,
                miss_latency=15,
                write_through=False,
                write_allocate=True,
                block_size=1,
            )
        ],
        memory_config=MemoryConfig(
            data_width=16,
            read_latency=10,
            write_latency=15,
            min_address=0,
            max_address=512,
        ),
    )

    helper = CacheWrapperBenchHelper(dut)

    async def bench(ctx):
        # Write some data to the cache and flush it after sending the last request
        await helper.write(ctx, 0, 0x1000, False)
        await helper.write(ctx, 1, 0x1010, False)

        # request write
        address = 2
        write_data = 0x1020
        print(f"{helper._get_timestamp()}: R addr {helper._addr_to_str(address)}")
        ctx.set(helper._dut.fe.address, address)
        ctx.set(helper._dut.fe.write_data, write_data)
        ctx.set(helper._dut.fe.write_strobe, -1)
        ctx.set(helper._dut.fe.request_valid, 1)

        # invalidate write request, request flush
        await helper._tick(ctx)
        ctx.set(helper._dut.fe.request_valid, 0)
        print(f"{helper._get_timestamp()}: Flush")
        ctx.set(helper._dut.fe.flush, 1)

        # invalidate flush request
        await helper._tick(ctx)
        ctx.set(helper._dut.fe.flush, 0)

        # wait until flush is done
        while not ctx.get(helper._dut.fe.flush_done):
            await helper._tick(ctx)

        # check that the data is still there
        await helper.read(ctx, 0, 0x1000, True)
        await helper.read(ctx, 1, 0x1010, True)
        await helper.read(ctx, 2, 0x1020, True)

        # manually check that this doesn't cause a write-back
        await helper.write(ctx, 4, 0x1040, False)

    run_bench(dut=dut, bench=bench)
