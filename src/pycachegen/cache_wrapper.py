from amaranth import Module
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from amaranth.utils import exact_log2

from .arbiter import Arbiter, ArbitrationScheme
from .cache import Cache
from .cache_config import (
    CacheConfig,
    InternalCacheConfig,
    InternalMemoryConfig,
    assert_delays_valid,
)
from .delay_unit import DelayUnit
from .main_memory import MainMemory


class CacheWrapper(wiring.Component):
    def __init__(
        self,
        address_width: int,
        cache_configs: list[CacheConfig],
        main_memory_data_width: int,
        create_main_memory: bool = True,
        num_ports: int = 1,
        read_delay: int = 0,
        write_delay: int = 0,
        arbitration_scheme: ArbitrationScheme = ArbitrationScheme.ROUND_ROBIN,
        byte_size: int = 8,
    ) -> None:
        """The top level module for using caches.

        Generates an arbitrary amount of caches and optionally a main memory and an arbiter for the L1 cache.
        The caches are set up in a linear hierarchy.

        Args:
            address_width (int): Address width of the first cache. Note that addresses do not include a byte offset.
                All other address widths will be derived from this address width and the data widths of the caches and
                the memory.
            cache_configs (tuple[CacheConfig, ...]): Configurations for the caches in the order of L1, L2, ... Can be
                left empty if no caches shall be generated.
            main_memory_data_width (int): Width of one data word of the main memory in bits. Must be a power of two and
                must be at lest as big as the last cache's data width.
            create_main_memory (bool): Whether a main memory should be created. If False, a BE interface will be
                created instead. The specified main_memory_data_width will be used for configuring this interface, so
                you must still specify it even if you set this parameter to False. Also note that you can just ignore
                the be__flush signal and always assign be__flush_done to 1 unless you want to do something specific
                with them.
            num_ports (int): Number of request ports.
            read_delay (int): The amount of cycles by which read requests to the main memory should be delayed. Can be
                set to 0, in which case write_delay must also be 0.
            write_delay (int): The amount of cycles by which write requests to the main memory should be delayed. Can
                be set to 0, in which case read_delay must also be 0.
            arbitration_scheme (ArbitrationScheme): Scheme for the arbiter in case there is more than one port.
                Supports priority and round robin scheme.
            byte_size (int): Number of bits per byte. A byte is the smallest unit that can be individually written to
                with the write strobe. If you only need to write to whole words, you can set the byte_size to be equal
                to the data_width.
        """
        assert_delays_valid(read_delay, write_delay)
        self.num_ports = num_ports
        self.arbitration_scheme = arbitration_scheme
        self.byte_size = byte_size
        self.num_caches = len(cache_configs)
        self.fe_address_width = address_width
        self.create_main_memory = create_main_memory
        self.read_delay = read_delay
        self.write_delay = write_delay

        if self.num_caches:
            self.fe_data_width = cache_configs[0].data_width
        else:
            self.fe_data_width = main_memory_data_width

        # create internal cache configs
        self.cache_configs: list[InternalCacheConfig] = []
        for i in range(len(cache_configs)):
            config = cache_configs[i]
            cache_address_width = self.fe_address_width - exact_log2(config.data_width // self.fe_data_width)
            if i < len(cache_configs) - 1:
                be_data_width = cache_configs[i + 1].data_width
            else:
                be_data_width = main_memory_data_width
            be_address_width = self.fe_address_width - exact_log2(be_data_width // self.fe_data_width)
            self.cache_configs.append(
                InternalCacheConfig(
                    cache_config=config,
                    address_width=cache_address_width,
                    be_data_width=be_data_width,
                    be_address_width=be_address_width,
                    byte_size=self.byte_size,
                )
            )

        # create internal memory config
        memory_address_width = self.fe_address_width - exact_log2(main_memory_data_width // self.fe_data_width)
        self.memory_config = InternalMemoryConfig(
            data_width=main_memory_data_width,
            address_width=memory_address_width,
            byte_size=self.byte_size,
        )

        ports = {}

        # Get signature of BE port and create it if needed
        self.be_memory_bus_signature = self.memory_config.memory_bus_signature
        if not create_main_memory:
            ports["be"] = Out(self.be_memory_bus_signature)

        # Get signatures of the FE ports and create them
        if self.cache_configs:
            self.fe_memory_bus_signature = self.cache_configs[0].fe_signature
        else:
            self.fe_memory_bus_signature = self.be_memory_bus_signature
        for i in range(num_ports):
            ports[f"fe_{i}"] = In(self.fe_memory_bus_signature)
            ports[f"hit_o_{i}"] = Out(1)

        super().__init__(ports)

    def elaborate(self, platform):
        m = Module()

        # lists of Out() and In() of MemoryBusInterfaces that will be connected together
        out_ports, in_ports = [], []

        # create an arbiter if necessary
        if self.num_ports > 1:
            m.submodules.arbiter = arbiter = Arbiter(
                num_ports=self.num_ports,
                bus_signature=self.fe_memory_bus_signature,
                arbitration_scheme=self.arbitration_scheme,
            )
            # connect the arbiter to the FE ports
            for i in range(self.num_ports):
                wiring.connect(
                    m,
                    wiring.flipped(getattr(self, f"fe_{i}")),
                    getattr(arbiter, f"fe_{i}"),
                )
            out_ports.append(arbiter.be)
            l1_hit = arbiter.hit_i
        else:
            out_ports.append(wiring.flipped(self.fe_0))
            l1_hit = self.hit_o_0

        # create the actual caches
        for i, cache_config in enumerate(self.cache_configs):
            m.submodules[f"l{i+1}_cache"] = cache = Cache(config=cache_config)
            in_ports.append(cache.fe)
            out_ports.append(cache.be)
            if i == 0:
                m.d.comb += l1_hit.eq(cache.hit_o)

        # optionally create a delay module
        if self.read_delay:
            m.submodules.delay_unit = delay_unit = DelayUnit(
                mem_signature=self.be_memory_bus_signature,
                read_delay=self.read_delay,
                write_delay=self.write_delay,
            )
            in_ports.append(delay_unit.requestor)
            out_ports.append(delay_unit.target)

        if self.create_main_memory:
            # create the main memory
            m.submodules.main_memory = main_memory = MainMemory(config=self.memory_config)
            in_ports.append(main_memory.fe)
        else:
            # else add the flipped BE port to the in_ports
            in_ports.append(wiring.flipped(self.be))

        # connect the cachewrapper/arbiter/caches/delayunit/memory with each other
        assert len(out_ports) == len(in_ports)
        for out_if, in_if in zip(out_ports, in_ports):
            wiring.connect(m, out_if, in_if)

        return m
