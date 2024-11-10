from enum import Enum
from amaranth import *
from amaranth.lib import wiring
from amaranth.lib.wiring import In, Out
from pycachegen.memory_bus import MemoryBusSignature, MemoryBusInterface


class ArbitrationScheme(Enum):
    PRIORITY = 0
    ROUND_ROBIN = 1


class Arbiter(wiring.Component):
    def __init__(
        self,
        num_ports,
        bus_signature: MemoryBusSignature,
        arbitration_scheme: ArbitrationScheme,
    ):
        self.num_ports = num_ports
        self.bus_signature = bus_signature
        self.arbitration_scheme = arbitration_scheme

        ports = {"be": Out(bus_signature), "hit_i": In(unsigned(1))}

        for i in range(num_ports):
            ports[f"fe_{i}"] = In(bus_signature)
            ports[f"hit_o_{i}"] = Out(unsigned(1))

        super().__init__(ports)

    def elaborate(self, platform):
        m = Module()

        # An array of the fe interfaces
        fe_interface_array = Array(
            [getattr(self, f"fe_{i}") for i in range(self.num_ports)]
        )

        # a buffer for each port so that we can buffer one request per port
        # while the BE is busy with the request of another port
        fe_buffers = Array(
            [
                {
                    "address": Signal(
                        self.bus_signature.address_width, name=f"fe_buffer_{i}_address"
                    ),
                    "request_valid": Signal(name=f"fe_buffer_{i}_request_valid"),
                    "write_strobe": Signal(
                        self.bus_signature.bytes_per_word,
                        name=f"fe_buffer_{i}_write_strobe",
                    ),
                    "write_data": Signal(
                        self.bus_signature.data_width, name=f"fe_buffer_{i}_write_data"
                    ),
                    "flush": Signal(name=f"fe_buffer_{i}_flush"),
                    "read_data": Signal(
                        self.bus_signature.data_width, name=f"fe_buffer_{i}_read_data"
                    ),
                    "read_data_valid": Signal(name=f"fe_buffer_{i}_read_data_valid"),
                    "hit": Signal(name=f"fe_buffer_{i}_hit"),
                }
                for i in range(self.num_ports)
            ]
        )
        # bit vector indicating whether a port has a valid request
        request_vector = Signal(unsigned(self.num_ports))
        # index of the port whose request should be sent to the BE
        grant_index = Signal(range(self.num_ports))
        # Whether a request has been sent to the BE
        request_sent = Signal()
        # Port index of the request sent to the BE
        previous_grant_index = Signal(range(self.num_ports))

        for i in range(self.num_ports):
            fe_interface = getattr(self, f"fe_{i}")
            fe_buffer = fe_buffers[i]

            with m.If(fe_interface.port_ready & fe_interface.request_valid):
                # Buffer new requests if the buffer is empty
                m.d.sync += fe_buffer["address"].eq(fe_interface.address)
                m.d.sync += fe_buffer["request_valid"].eq(1)
                m.d.sync += fe_buffer["write_strobe"].eq(fe_interface.write_strobe)
                m.d.sync += fe_buffer["write_data"].eq(fe_interface.write_data)
                m.d.sync += fe_buffer["flush"].eq(fe_interface.flush)

            # This port has a valid request if the buffer contains a valid request
            # or if there is an incoming request
            m.d.comb += request_vector[i].eq(
                fe_interface.request_valid | fe_buffer["request_valid"]
            )

            # assign the output buffers to the FE interface by default
            m.d.comb += fe_interface.read_data.eq(fe_buffer["read_data"])
            m.d.comb += fe_interface.read_data_valid.eq(fe_buffer["read_data_valid"])
            m.d.comb += fe_interface.port_ready.eq(~fe_buffer["request_valid"])
            m.d.comb += getattr(self, f"hit_o_{i}").eq(self.hit_i)

            # Check if this port's request was granted & the request is in progress (request_sent)
            with m.If(request_sent & (previous_grant_index == i)):
                # If that is the case, hand the BE interface data out instead of the buffered data
                m.d.comb += fe_interface.read_data.eq(self.be.read_data)
                m.d.comb += fe_interface.read_data_valid.eq(self.be.read_data_valid)
                m.d.comb += fe_interface.port_ready.eq(self.be.port_ready)
                m.d.comb += getattr(self, f"hit_o_{i}").eq(self.hit_i)
                with m.If(self.be.port_ready):
                    # The BE port is ready and so it is done processing the last request
                    # Buffer the BE response into this port's buffer
                    # That way once a request of another port gets sent, this port
                    # can still read its own response
                    # port ready does not need to be buffered, it is derived from the buffered request_valid
                    m.d.sync += fe_buffer["read_data"].eq(self.be.read_data)
                    m.d.sync += fe_buffer["read_data_valid"].eq(self.be.read_data_valid)
                    m.d.sync += fe_buffer["hit"].eq(self.hit_i)
                    # Also reset request_sent (if we send a new request in the same cycle, it will be overwritten)
                    m.d.sync += request_sent.eq(0)

        with m.If(request_vector.any() & self.be.port_ready):
            # The BE is ready and we have a request to send
            # If the FE interface has a valid request, we use it - else there must be a
            # valid buffered request
            with m.If(fe_interface_array[grant_index].request_valid):
                m.d.comb += self.be.address.eq(fe_interface_array[grant_index].address)
                m.d.comb += self.be.request_valid.eq(
                    fe_interface_array[grant_index].request_valid
                )
                m.d.comb += self.be.write_strobe.eq(
                    fe_interface_array[grant_index].write_strobe
                )
                m.d.comb += self.be.write_data.eq(
                    fe_interface_array[grant_index].write_data
                )
                m.d.comb += self.be.flush.eq(fe_interface_array[grant_index].flush)
            with m.Else():
                m.d.comb += self.be.address.eq(fe_buffers[grant_index]["address"])
                m.d.comb += self.be.request_valid.eq(
                    fe_buffers[grant_index]["request_valid"]
                )
                m.d.comb += self.be.write_strobe.eq(
                    fe_buffers[grant_index]["write_strobe"]
                )
                m.d.comb += self.be.write_data.eq(fe_buffers[grant_index]["write_data"])
                m.d.comb += self.be.flush.eq(fe_buffers[grant_index]["flush"])

            # Set internal busy variable and set granted index
            m.d.sync += request_sent.eq(1)
            m.d.sync += previous_grant_index.eq(grant_index)
            # Invalidate the buffered request
            m.d.sync += fe_buffers[grant_index]["request_valid"].eq(0)

        if self.arbitration_scheme == ArbitrationScheme.PRIORITY:
            for i in reversed(range(self.num_ports)):
                with m.If(request_vector[i]):
                    m.d.comb += grant_index.eq(i)

        return m
