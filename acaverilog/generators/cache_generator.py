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
        fe_address_i = m.Input("fe_address_i", self.ADDRESS_WIDTH)
        fe_address_valid_i = m.Input("fe_address_valid_i")
        fe_write_data_i = m.Input("fe_write_data_i", self.DATA_WIDTH)
        fe_write_data_valid_i = m.Input("fe_write_data_valid_i")
        fe_read_write_select_i = m.Input("fe_read_write_select_i")

        # Front End Outputs
        fe_read_data_o = m.Output("fe_read_data_o", self.DATA_WIDTH)
        fe_read_data_valid_o = m.Output("fe_read_data_valid_o")
        fe_write_done_o = m.Output("fe_write_done_o")
        fe_port_ready_o = m.Output("fe_port_ready_o")

        # Back End Inputs
        be_read_data_i = m.Input("be_read_data_i", self.DATA_WIDTH)
        be_read_data_valid_i = m.Input("be_read_data_valid_i")
        be_write_done_i = m.Input("be_write_done_i")
        be_port_ready_i = m.Input("be_port_ready_i")

        # Back End Outputs
        be_address_o = m.Output("be_address_o", self.ADDRESS_WIDTH)
        be_address_valid_o = m.Output("be_address_valid_o")
        be_write_data_o = m.Output("be_write_data_o", self.DATA_WIDTH)
        be_write_data_valid_o = m.Output("be_write_data_valid_o")
        be_read_write_select_o = m.Output("be_read_write_select_o")

        # Front End Input Buffers
        fe_address_i_reg = m.Reg("fe_address_i_reg", self.ADDRESS_WIDTH)
        fe_write_data_i_reg = m.Reg("fe_write_data_i_reg", self.DATA_WIDTH)
        fe_read_write_select_i_reg = m.Reg("fe_read_write_select_i_reg")

        # Front End Output Buffers
        fe_read_data_o_reg = m.Reg("fe_read_data_o_reg", self.DATA_WIDTH)
        fe_read_data_valid_o_reg = m.Reg("fe_read_data_valid_o_reg")
        fe_write_done_o_reg = m.Reg("fe_write_done_o_reg")
        fe_port_ready_o_reg = m.Reg("fe_port_ready_o_reg")

        # Back End Input Buffers
        be_read_data_i_reg = m.Reg("be_read_data_i_reg", self.DATA_WIDTH)

        # Back End Output Buffers
        be_address_o_reg = m.Reg("be_address_o_reg", self.ADDRESS_WIDTH)
        be_address_valid_o_reg = m.Reg("be_address_valid_o_reg")
        be_write_data_o_reg = m.Reg("be_write_data_o_reg", self.DATA_WIDTH)
        be_write_data_valid_o_reg = m.Reg("be_write_data_valid_o_reg")
        be_read_write_select_o_reg = m.Reg("be_read_write_select_o_reg")

        # Frontend Output Buffer Assignments
        m.Assign(fe_read_data_o(fe_read_data_o_reg))
        m.Assign(fe_read_data_valid_o(fe_read_data_valid_o_reg))
        m.Assign(fe_write_done_o(fe_write_done_o_reg))
        m.Assign(fe_port_ready_o(fe_port_ready_o_reg))

        # Backend Output Buffer Assignments
        m.Assign(be_address_o(be_address_o_reg))
        m.Assign(be_address_valid_o(be_address_valid_o_reg))
        m.Assign(be_write_data_o(be_write_data_o_reg))
        m.Assign(be_write_data_valid_o(be_write_data_valid_o_reg))
        m.Assign(be_read_write_select_o(be_read_write_select_o_reg))

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
            fe_port_ready_o_reg(AndList(read_in_progress == 0, write_in_progress == 0))
        )
        m.Assign(address_tag(fe_address_i_reg[self.INDEX_WIDTH: ]))
        m.Assign(address_index(fe_address_i_reg[:self.INDEX_WIDTH]))

        m.Always(Posedge(clk_i))(
            If(fe_port_ready_o_reg == 1)(
                # Cache is ready for a new request
                If(AndList(fe_read_write_select_i == 0, fe_address_valid_i == 1))(
                    # Read Request
                    read_in_progress(1),
                    hit_lookup_en(1),
                    latency_counter(self.MISS_LATENCY),
                    fe_address_i_reg(fe_address_i),
                    fe_read_data_valid_o_reg(0),
                    fe_write_done_o_reg(0),
                    hit(0),
                    hit_valid(0),
                    req_processed(0),
                ),
                If(
                    AndList(
                        fe_read_write_select_i == 1,
                        fe_address_valid_i == 1,
                        fe_write_data_valid_i == 1,
                    )
                )(
                    # Write Request
                    write_in_progress(1),
                    hit_lookup_en(1),
                    latency_counter(self.MISS_LATENCY),
                    fe_address_i_reg(fe_address_i),
                    fe_write_data_i_reg(fe_write_data_i),
                    fe_read_data_valid_o_reg(0),
                    fe_write_done_o_reg(0),
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
                        fe_read_data_o_reg(data_memory[address_index]),
                    ).Elif(write_in_progress == 1)(
                        data_memory[address_index](fe_write_data_i_reg),
                        # valid_memory[address_index](1),
                        # tag_memory[address_index](address_tag),
                    ),
                    req_processed(1),
                ).Else(
                    # We have a miss
                    # Request read/write from lower memory
                    be_address_o_reg(fe_address_i_reg),
                    be_address_valid_o_reg(1),
                    be_read_write_select_o_reg(fe_read_write_select_i_reg),
                    be_write_data_o_reg(fe_write_data_i_reg),
                ),
            )
            .Elif(
                AndList(be_address_valid_o == 1, OrList(be_read_data_valid_i, be_write_done_i))
            )(
                # Request to main memory was processed, we can now
                # a) hand the data out and write it to the cache in case of a read
                # b) do nothing in case of a write
                req_processed(1),
                be_address_valid_o_reg(0),  # this might happen one cycle too late I think ._.
                latency_counter.dec(),
                If(fe_read_write_select_i_reg == 0)(
                    fe_read_data_o_reg(be_read_data_i),
                    data_memory[address_index](be_read_data_i),
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
                fe_read_data_valid_o_reg(fe_read_write_select_i_reg),
                fe_write_done_o_reg(Not(fe_read_write_select_i_reg)),
                read_in_progress(0),
                write_in_progress(0),
            )
        )
        return m


if __name__ == "__main__":
    cache_generator = CacheGenerator(data_width=16, address_width=8)
    m = cache_generator.generate_module()
    m.to_verilog("../src/cache.v", for_verilator=True)
