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
    MemoryConfig,
    assert_delays_valid,
)
from .delay_unit import DelayUnit
from .interfaces import MemoryBusSignature
from .main_memory import MainMemory


class CacheWrapper(wiring.Component):
    def __init__(
        self,
        num_ports: int,
        address_width: int,
        memory_config: MemoryConfig,
        cache_configs: list[CacheConfig],
        read_delay: int = 0,
        write_delay: int = 0,
        create_main_memory: bool = True,
        arbitration_scheme: ArbitrationScheme = ArbitrationScheme.ROUND_ROBIN,
        byte_size: int = 8,
    ) -> None:
        """The top level module for using caches.

        Generates an arbitrary amount of caches and optionally a main memory and an arbiter for the L1 cache.
        The caches are set up in a linear hierarchy.

        Args:
            num_ports (int): Number of access ports.
            address_width (int): Address width. Note that addresses do not include a byte offset.
            memory_config (Optional[MemoryConfig]): Configuration for the main memory.
            cache_configs (tuple[CacheConfig, ...]): Configurations for the caches in the order of L1, L2, ... Can be left empty if no caches shall be generated.
            create_main_memory (bool): Whether a main memory should be created. If False, a BE interface will be created instead. This interface will be configured in the way described by the memory_config.
            arbitration_scheme (ArbitrationScheme): Scheme for the arbiter in case there is more than one port. Supports priority and round robin scheme.
            byte_size (int): Number of bits per byte.
            read_delay (int): The amount of cycles by which read requests to the main memory should be delayed. Can be set to 0, in which case write_delay must also be 0.
            write_delay (int): The amount of cycles by which write requests to the main memory should be delayed. Can be set to 0, in which case read_delay must also be 0.
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
            self.fe_data_width = memory_config.data_width

        self.fe_bytes_per_word = self.fe_data_width // self.byte_size

        # create internal cache configs
        self.cache_configs: list[InternalCacheConfig] = []
        for i in range(len(cache_configs)):
            config = cache_configs[i]
            cache_address_width = self.fe_address_width - exact_log2(
                config.data_width // self.fe_data_width
            )
            if i < len(cache_configs) - 1:
                be_data_width = cache_configs[i + 1].data_width
            else:
                be_data_width = memory_config.data_width
            be_address_width = self.fe_address_width - exact_log2(
                be_data_width // self.fe_data_width
            )
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
        memory_address_width = self.fe_address_width - exact_log2(
            memory_config.data_width // self.fe_data_width
        )
        self.memory_config = InternalMemoryConfig(
            memory_config=memory_config,
            address_width=memory_address_width,
            byte_size=self.byte_size,
        )

        self.be_memory_bus_signature = MemoryBusSignature(
            address_width=self.memory_config.address_width,
            data_width=self.memory_config.data_width,
            bytes_per_word=self.memory_config.bytes_per_word,
        )

        # TODO move creating this signature into the internal config?
        self.fe_memory_bus_signature = MemoryBusSignature(
            address_width=self.fe_address_width,
            data_width=self.fe_data_width,
            bytes_per_word=self.fe_bytes_per_word,
        )

        ports = {}

        for i in range(num_ports):
            ports[f"fe_{i}"] = In(self.fe_memory_bus_signature)
            ports[f"hit_o_{i}"] = Out(1)

        if not create_main_memory:
            ports["be"] = Out(self.fe_memory_bus_signature)

        super().__init__(ports)

    def elaborate(self, platform):
        m = Module()

        # lists of Out() and In() of MemoryBusInterfaces that will be connected together
        out_list, in_list = [], []

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
            out_list.append(arbiter.be)
            l1_hit = arbiter.hit_i
        else:
            out_list.append(wiring.flipped(self.fe_0))
            l1_hit = self.hit_o_0

        # create the actual caches
        for i, cache_config in enumerate(self.cache_configs):
            m.submodules[f"l{i+1}_cache"] = cache = Cache(config=cache_config)
            in_list.append(cache.fe)
            out_list.append(cache.be)
            if i == 0:
                m.d.comb += l1_hit.eq(cache.hit_o)

        # optionally create a delay module
        if self.read_delay:
            m.submodules.delay_unit = delay_unit = DelayUnit(
                mem_signature=self.be_memory_bus_signature,
                read_delay=self.read_delay,
                write_delay=self.write_delay,
                min_addr=self.memory_config.min_address,
                max_addr=self.memory_config.max_address,
            )
            in_list.append(delay_unit.requestor)
            out_list.append(delay_unit.target)

        # create the main memory
        if self.create_main_memory:
            m.submodules.main_memory = main_memory = MainMemory(
                config=self.memory_config
            )
            in_list.append(main_memory.fe)
        else:
            in_list.append(wiring.flipped(self.be))

        # connect the caches/memory/cachewrapper with each other
        assert len(out_list) == len(in_list)
        for out_if, in_if in zip(out_list, in_list):
            wiring.connect(m, out_if, in_if)

        return m
