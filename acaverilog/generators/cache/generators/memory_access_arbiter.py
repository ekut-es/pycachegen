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
    Or,
    And,
)
from enum import Enum
from math import ceil, log2

from acaverilog.generators.cache.generators.priority_encoder_generator import (
    PriorityEncoderGenerator,
)


class States(Enum):
    READY = 0
    WAITING_FOR_MEMORY = 1


class MemoryAccessArbiter:
    def __init__(
        self, num_ports: int, address_width: int, data_width: int, policy: str
    ) -> None:
        """Generator for an arbiter for memories/caches with the native memory interface.

        Args:
            num_ports (int): Number of front end ports.
            address_width (int): Address width.
            data_width (int): Data word width.
            policy (str): Policy for the order in which incoming request will be processed. Can be either "priority" or "fifo".
        """
        self.NUM_PORTS = num_ports
        self.ADDRESS_WIDTH = address_width
        self.DATA_WIDTH = data_width
        self.POLICY = policy
        self.NUM_PORTS_CEILED_W = ceil(log2(self.NUM_PORTS))
        self.NUM_PORTS_CEILED = 2 ** (self.NUM_PORTS_CEILED_W)
        # Fifo buffer must have one additional element so we know when it's full and empty
        self.FIFO_BUFFER_LENGTH_W = ceil(log2(self.NUM_PORTS + 1))
        self.FIFO_BUFFER_LENGTH = 2 ** (self.FIFO_BUFFER_LENGTH_W)

    def generate_module(self) -> Module:
        m = Module("memory_access_arbiter")

        clk_i = m.Input("clk_i")
        reset_n_i = m.Input("reset_n_i")

        ## backend
        # inputs
        be_port_ready_i = m.Input("be_port_ready_i")
        be_read_data_i = m.Input("be_read_data_i", self.DATA_WIDTH)
        be_read_data_valid_i = m.Input("be_read_data_valid_i")
        be_write_done_i = m.Input("be_write_done_i")
        # outputs
        be_address_o = m.Output("be_address_o", self.ADDRESS_WIDTH)
        be_address_valid_o = m.Output("be_address_valid_o")
        be_write_data_o = m.Output("be_write_data_o", self.DATA_WIDTH)
        be_write_data_valid_o = m.Output("be_write_data_valid_o")
        be_read_write_select_o = m.Output("be_read_write_select_o")
        # output buffers
        be_address = m.Reg("be_address", self.ADDRESS_WIDTH)
        be_address_valid = m.Reg("be_address_valid")
        be_write_data = m.Reg("be_write_data", self.DATA_WIDTH)
        be_write_data_valid = m.Reg("be_write_data_valid")
        be_read_write_select = m.Reg("be_read_write_select")
        # output buffer assignments
        m.Assign(be_address_o(be_address))
        m.Assign(be_address_valid_o(be_address_valid))
        m.Assign(be_write_data_o(be_write_data))
        m.Assign(be_write_data_valid_o(be_write_data_valid))
        m.Assign(be_read_write_select_o(be_read_write_select))

        ## frontend
        # inputs
        fe_address_i = []
        fe_address_valid_i = []
        fe_write_data_i = []
        fe_write_data_valid_i = []
        fe_read_write_select_i = []
        # outputs
        fe_read_data_o = []
        fe_read_data_valid_o = []
        fe_write_done_o = []
        fe_port_ready_o = []
        # input buffers
        fe_address = m.Reg("fe_address", self.ADDRESS_WIDTH, self.NUM_PORTS)
        fe_write_data = m.Reg("fe_write_data", self.DATA_WIDTH, self.NUM_PORTS)
        fe_read_write_select = m.Reg("fe_read_write_select", self.NUM_PORTS)
        # output buffers
        fe_read_data = m.Reg("fe_read_data", self.DATA_WIDTH, self.NUM_PORTS)
        fe_read_data_valid = m.Reg("fe_read_data_valid", self.NUM_PORTS)
        fe_write_done = m.Reg("fe_write_done", self.NUM_PORTS)
        fe_port_ready = m.Reg("fe_port_ready", self.NUM_PORTS)
        for i in range(self.NUM_PORTS):
            fe_address_i.append(m.Input(f"fe_address_{i}_i", self.ADDRESS_WIDTH))
            fe_address_valid_i.append(m.Input(f"fe_address_valid_{i}_i"))
            fe_write_data_i.append(m.Input(f"fe_write_data_{i}_i", self.DATA_WIDTH))
            fe_write_data_valid_i.append(m.Input(f"fe_write_data_valid_{i}_i"))
            fe_read_write_select_i.append(m.Input(f"fe_read_write_select_{i}_i"))
            # outputs
            fe_read_data_o.append(m.Output(f"fe_read_data_{i}_o", self.DATA_WIDTH))
            fe_read_data_valid_o.append(m.Output(f"fe_read_data_valid_{i}_o"))
            fe_write_done_o.append(m.Output(f"fe_write_done_{i}_o"))
            fe_port_ready_o.append(m.Output(f"fe_port_ready_{i}_o"))
            # output buffer assignments
            m.Assign(fe_read_data_o[i](fe_read_data[i]))
            m.Assign(fe_read_data_valid_o[i](fe_read_data_valid[i]))
            m.Assign(fe_write_done_o[i](fe_write_done[i]))
            m.Assign(fe_port_ready_o[i](fe_port_ready[i]))

        # internal
        request_valid = m.Wire("request_valid", self.NUM_PORTS)
        buffered_request_valid = m.Reg("buffered_request_valid", self.NUM_PORTS)
        for i in range(self.NUM_PORTS):
            m.Assign(
                request_valid[i](
                    And(
                        fe_address_valid_i[i],
                        Or(Not(fe_read_write_select_i[i]), fe_write_data_valid_i[i]),
                    )
                )
            )
        next_request = m.Wire("next_request", self.NUM_PORTS_CEILED_W)
        selected_request = m.Reg("selected_request", self.NUM_PORTS_CEILED_W)
        state_reg = m.Reg("state_reg", ceil(log2(len(States))))

        if self.POLICY == "round_robin":
            rr_last_accessed = m.Reg("rr_last_accessed", self.NUM_PORTS_CEILED_W)
            rr_ordered_requests = m.Wire("rr_ordered_requests", self.NUM_PORTS)
            # Reorder the buffered requests so that the priority encoder gives priority to the
            # bit which is next according to the round robin policy
            m.Assign(
                rr_ordered_requests(
                    (buffered_request_valid << rr_last_accessed)
                    | (buffered_request_valid >> (self.NUM_PORTS - rr_last_accessed))
                )
            )

        Submodule(
            m,
            PriorityEncoderGenerator(self.NUM_PORTS, False).generate_module(),
            "arbiter_priority_encoder",
            arg_ports=(
                (
                    "unencoded_i",
                    (
                        rr_ordered_requests
                        if self.POLICY == "round_robin"
                        else buffered_request_valid
                    ),
                ),
                ("encoded_o", next_request),
            ),
        )

        if self.POLICY == "fifo":
            # make fifo queue as long as the next power of 2 of the num of ports
            # so we dont need to apply modulo to the indices
            fifo_queue = m.Reg(
                "fifo_queue", self.NUM_PORTS_CEILED_W, self.FIFO_BUFFER_LENGTH
            )
            fifo_read_idx = m.Reg("fifo_read_idx", self.FIFO_BUFFER_LENGTH_W)
            fifo_write_idx = m.Reg("fifo_write_idx", self.FIFO_BUFFER_LENGTH_W)

        m.Always(Posedge(clk_i), Negedge(reset_n_i))(
            If(Not(reset_n_i))(
                # backend buffers
                be_address(0),
                be_address_valid(0),
                be_write_data(0),
                be_write_data_valid(0),
                # frontend buffers
                [
                    (
                        fe_address[i](0),
                        fe_write_data[i](0),
                        fe_read_write_select[i](0),
                        fe_read_data[i](0),
                        fe_read_data_valid[i](0),
                        fe_write_done[i](0),
                        fe_port_ready[i](1),
                    )
                    for i in range(self.NUM_PORTS)
                ],
                # internal
                state_reg(States.READY.value),
                selected_request(0),
                # fifo
                (
                    [
                        fifo_read_idx(0),
                        fifo_write_idx(0),
                        [fifo_queue[i](0) for i in range(self.NUM_PORTS_CEILED)],
                    ]
                    if self.POLICY == "fifo"
                    else []
                ),
            ).Else(
                # Always buffer new requests
                [
                    If(And(fe_port_ready[i], request_valid[i]))(
                        fe_port_ready[i](0),
                        fe_address[i](fe_address_i[i]),
                        fe_write_data[i](fe_write_data_i[i]),
                        fe_read_write_select[i](fe_read_write_select_i[i]),
                        fe_read_data_valid[i](0),
                        fe_write_done[i](0),
                        buffered_request_valid[i](1),
                    )
                    for i in range(self.NUM_PORTS)
                ],
                # insert into fifo queue if fifo is used
                (
                    [
                        If(buffered_request_valid != 0)(
                            # Note: We can always insert new requests into the fifo without overfilling it
                            # since each client has to wait for its request to be processed
                            fifo_queue[fifo_write_idx](next_request),
                            fifo_write_idx.inc(),
                            # invalidate buffered request so we dont insert it into the fifo twice
                            buffered_request_valid[next_request](0),
                        )
                    ]
                    if self.POLICY == "fifo"
                    else []
                ),
                If(state_reg == States.READY.value)(
                    If(AndList(be_port_ready_i, fifo_read_idx != fifo_write_idx))(
                        # There is a new request in the fifo, lets process it
                        be_address(fe_address[fifo_queue[fifo_read_idx]]),
                        be_address_valid(1),
                        be_write_data(fe_write_data[fifo_queue[fifo_read_idx]]),
                        be_write_data_valid(
                            fe_read_write_select[fifo_queue[fifo_read_idx]]
                        ),
                        be_read_write_select(
                            fe_read_write_select[fifo_queue[fifo_read_idx]]
                        ),
                        selected_request(fifo_queue[fifo_read_idx]),
                        fifo_read_idx.inc(),
                        state_reg(States.WAITING_FOR_MEMORY.value),
                    )
                    if self.POLICY == "fifo"
                    else If(
                        AndList(
                            be_port_ready_i,
                            buffered_request_valid != 0,
                        )
                    )(
                        be_address(fe_address[next_request]),
                        be_address_valid(1),
                        be_write_data(fe_write_data[next_request]),
                        be_write_data_valid(fe_read_write_select[next_request]),
                        be_read_write_select(fe_read_write_select[next_request]),
                        selected_request(next_request),
                        # invalidate buffered request
                        buffered_request_valid[next_request](0),
                        state_reg(States.WAITING_FOR_MEMORY.value),
                        (
                            rr_last_accessed(next_request) # FIXME I think we might have to give priority to the element after that?
                            if self.POLICY == "round_robin"
                            else []
                        ),
                    )
                ).Elif(state_reg == States.WAITING_FOR_MEMORY.value)(
                    If(be_address_valid)(
                        # invalidate the request
                        be_address_valid(0),
                        be_write_data_valid(0),
                    ).Elif(be_port_ready_i)(
                        state_reg(States.READY.value),
                        fe_port_ready[selected_request](1),
                        If(And(be_read_write_select, be_write_done_i))(
                            # write done
                            fe_write_done[selected_request](1),
                        ).Elif(And(Not(be_read_write_select), be_read_data_valid_i))(
                            # read done
                            fe_read_data[selected_request](be_read_data_i),
                            fe_read_data_valid[selected_request](1),
                        ),
                    ),
                ),
            )
        )

        return m
