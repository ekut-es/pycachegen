from math import ceil, log2
from veriloggen import (
    Module,
    Submodule,
    Posedge,
    Negedge,
    If,
    For,
    AndList,
    OrList,
    Not,
)

# from acadl import ACADLObject

# from .acadl_object_generator import ACADLObjectGenerator


# class CacheGenerator(ACADLObjectGenerator):
class CacheGenerator:

    # def __init__(
    #     self,
    #     acadl_object: ACADLObject,
    # ) -> None:
    #     super().__init__(acadl_object)

    def __init__(self, data_width: int, address_width: int) -> None:
        self.DATA_WIDTH = data_width
        self.ADDRESS_WIDTH = address_width
        # non configurable atm, because everything will be pulled from the acadl object anyway
        self.NUM_SETS = 4
        self.HIT_LATENCY = 8
        self.MISS_LATENCY = 10
        
        self.LATENCY_COUNTER_SIZE = ceil(log2(max(self.HIT_LATENCY, self.MISS_LATENCY)))
        self.INDEX_WIDTH = int(log2(self.NUM_SETS))
        self.TAG_WIDTH = self.ADDRESS_WIDTH - self.INDEX_WIDTH

    def generate_module(self) -> Module:
        # m = Module(self.base_file_name)
        m = Module("cache")

        # Front End Inputs
        clk_i = m.Input("clk_i")
        reset_n_i = m.Input("reset_n_i")
        address_i = m.Input("address_i", self.ADDRESS_WIDTH)
        address_valid_i = m.Input("address_valid_i")
        write_data_i = m.Input("write_data_i", self.DATA_WIDTH)
        write_data_valid_i = m.Input("write_data_valid_i")
        read_write_select_i = m.Input("read_write_select_i")

        # Front End Outputs
        read_data_o = m.Output("read_data_o", self.DATA_WIDTH)
        read_data_valid_o = m.Output("read_data_valid_o")
        write_done_o = m.Output("write_done_o")
        port_ready_o = m.Output("port_ready_o")

        # Back End Inputs
        read_data_i = m.Input("read_data_i", self.DATA_WIDTH)
        read_data_valid_i = m.Input("read_data_valid_i")
        write_done_i = m.Input("write_done_i")
        port_ready_i = m.Input("port_ready_i")

        # Back End Outputs
        address_o = m.Output("address_o", self.ADDRESS_WIDTH)
        address_valid_o = m.Output("address_valid_o")
        write_data_o = m.Output("write_data_o", self.DATA_WIDTH)
        write_data_valid_o = m.Output("write_data_valid_o")
        read_write_select_o = m.Output("read_write_select_o")

        # Front End Input Buffers
        address_i_reg = m.Reg("address_i_reg", self.ADDRESS_WIDTH)
        # address_valid_i_reg = m.Reg("address_valid_i_reg")
        write_data_i_reg = m.Reg("write_data_i_reg", self.DATA_WIDTH)
        # write_data_valid_i_reg = m.Reg("write_data_valid_i_reg")
        read_write_select_i_reg = m.Reg("read_write_select_i_reg")

        # Front End Output Buffers
        read_data_o_reg = m.Reg("read_data_o_reg", self.DATA_WIDTH)
        read_data_valid_o_reg = m.Reg("read_data_valid_o_reg")
        write_done_o_reg = m.Reg("write_done_o_reg")
        port_ready_o_reg = m.Reg("port_ready_o_reg")

        # Back End Input Buffers
        read_data_i_reg = m.Reg("read_data_i_reg", self.DATA_WIDTH)
        # read_data_valid_i_reg = m.Reg("read_data_valid_i_reg")
        # write_done_i_reg = m.Reg("write_done_i_reg")
        # port_ready_i_reg = m.Reg("port_ready_i_reg")

        # Back End Output Buffers
        address_o_reg = m.Reg("address_o_reg", self.ADDRESS_WIDTH)
        address_valid_o_reg = m.Reg("address_valid_o_reg")
        write_data_o_reg = m.Reg("write_data_o_reg", self.DATA_WIDTH)
        write_data_valid_o_reg = m.Reg("write_data_valid_o_reg")
        read_write_select_o_reg = m.Reg("read_write_select_o_reg")

        # Frontend Output Buffer Assignments
        m.Assign(read_data_o(read_data_o_reg))
        m.Assign(read_data_valid_o(read_data_valid_o_reg))
        m.Assign(write_done_o(write_done_o_reg))
        m.Assign(port_ready_o(port_ready_o_reg))

        # Backend Output Buffer Assignments
        m.Assign(address_o(address_o_reg))
        m.Assign(address_valid_o(address_valid_o_reg))
        m.Assign(write_data_o(write_data_o_reg))
        m.Assign(write_data_valid_o(write_data_valid_o_reg))
        m.Assign(read_write_select_o(read_write_select_o_reg))

        # Internal
        latency_counter = m.Reg("read_latency_counter", self.LATENCY_COUNTER_SIZE)
        read_in_progress = m.Reg("read_in_progress")
        write_in_progress = m.Reg("write_in_progress")
        req_processed = m.Reg("req_processed")
        hit_lookup_en = m.Reg("hit_lookup_en")
        hit = m.Reg("hit")
        hit_valid = m.Reg("hit_valid")
        address_tag = m.Wire("address_tag", self.TAG_WIDTH)
        address_index = m.Wire("address_index", self.INDEX_WIDTH)
        tag_memory = m.Reg("tag_memory", self.TAG_WIDTH, dims=self.NUM_SETS)
        valid_memory = m.Reg("valid_memory", 1, dims=self.NUM_SETS)
        data_memory = m.Reg("data_memory", self.DATA_WIDTH, dims=self.NUM_SETS)

        m.Assign(
            port_ready_o_reg(AndList(read_in_progress == 0, write_in_progress == 0))
        )
        m.Assign(address_tag(address_i_reg[self.INDEX_WIDTH: ]))
        m.Assign(address_index(address_i_reg[:self.INDEX_WIDTH]))

        m.Always(Posedge(clk_i))(
            If(port_ready_o_reg == 1)(
                # Cache is ready for a new request
                If(AndList(read_write_select_i == 0, address_valid_i == 1))(
                    # Read Request
                    read_in_progress(1),
                    hit_lookup_en(1),
                    latency_counter(self.MISS_LATENCY),
                    address_i_reg(address_i),
                    read_data_valid_o_reg(0),
                    write_done_o_reg(0),
                    hit(0),
                    hit_valid(0),
                    req_processed(0),
                ),
                If(
                    AndList(
                        read_write_select_i == 1,
                        address_valid_i == 1,
                        write_data_valid_i == 1,
                    )
                )(
                    # Write Request
                    write_in_progress(1),
                    hit_lookup_en(1),
                    latency_counter(self.MISS_LATENCY),
                    address_i_reg(address_i),
                    write_data_i_reg(write_data_i),
                    read_data_valid_o_reg(0),
                    write_done_o_reg(0),
                    hit(0),
                    hit_valid(0),
                ),
            )
            .Elif(hit_lookup_en == 1)(
                # Check whether we have a hit
                hit(
                    AndList(
                        tag_memory[address_index] == address_tag,
                        valid_memory[address_index] == 1,
                    )
                ),
                hit_valid(1),
                latency_counter.dec(),
                hit_lookup_en(0),
            )
            .Elif(hit_valid == 1)(
                # Hit lookup has finished
                latency_counter.dec(),
                hit_valid(0),
                If(hit == 1)(
                    # We have a hit
                    If(read_in_progress == 1)(
                        read_data_o_reg(data_memory[address_index]),
                    ).Elif(write_in_progress == 1)(
                        data_memory[address_index](write_data_i_reg),
                        # valid_memory[address_index](1),
                        # tag_memory[address_index](address_tag),
                    ),
                    req_processed(1),
                ).Else(
                    # We have a miss
                    # Request read/write from lower memory
                    address_o_reg(address_i_reg),
                    address_valid_o_reg(1),
                    read_write_select_o_reg(read_write_select_i_reg),
                    write_data_o_reg(write_data_i_reg),
                ),
            )
            .Elif(
                AndList(address_valid_o == 1, OrList(read_data_valid_i, write_done_i))
            )(
                # Request to main memory was processed, we can now
                # a) hand the data out and write it to the cache in case of a read
                # b) do nothing in case of a write
                req_processed(1),
                address_valid_o_reg(0),  # this might happen one cycle too late I think ._.
                latency_counter.dec(),
                If(read_write_select_i_reg == 0)(
                    read_data_o_reg(read_data_i),
                    data_memory[address_index](read_data_i),
                    valid_memory[address_index](1),
                    tag_memory[address_index](address_tag),
                ),
            )
            .Elif(AndList(req_processed, latency_counter != 0))(
                # Stall for the remaining time (or error if this took too much time...?)
                latency_counter.dec()
            )
            .Elif(latency_counter == 0)(
                # We have stalled enough, finish the request
                read_data_valid_o_reg(read_write_select_i_reg),
                write_done_o_reg(Not(read_write_select_i_reg)),
                read_in_progress(0),
                write_in_progress(0),
            )
        )
        return m


if __name__ == "__main__":
    cache_generator = CacheGenerator(data_width=16, address_width=8)
    m = cache_generator.generate_module()
    m.to_verilog("../src/cache.v", for_verilator=True)
