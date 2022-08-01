/* verilator lint_off CMPCONST */

module {{ name }}_Memory
#(
	parameter DATA_WIDTH = {{ data_width }}, 
	parameter PORT_WIDTH = {{ port_width }},
	parameter PORT_WIDTH_BITS = {{ data_width*port_width }},
	parameter MAX_CONCURRENT_REQUESTS = {{ max_concurrent_requests }},
	parameter READ_LATENCY = {{ read_latency }},
	parameter WRITE_LATENCY = {{ write_latency }},
	parameter ADDRESS_WIDTH = {{ address_width }},
	parameter MEMORY_LINES = {{ memory_lines }}
)
(
	input clk_i,
	input reset_n_i,

	// when writing into the memory the signals at the input ports have to be
	// driven as long as write_done is 0 (low)
	{%- for i in range(read_write_ports) %}
	input read_write_select_{{ i }}_i,
	input unsigned[ADDRESS_WIDTH-1:0] address_{{ i }}_i,
	input[PORT_WIDTH_BITS-1:0] write_data_{{ i }}_i,
	input unsigned[PORT_WIDTH-1:0] write_data_valid_{{ i }}_i,
	output write_done_{{ i }}_o,
	output[PORT_WIDTH_BITS-1:0] read_data_{{ i }}_o,
	output unsigned[PORT_WIDTH-1:0] read_data_valid_{{ i }}_o,
	{% endfor -%}

	output ready_o
);

	localparam LATENCY_COUNTER_SIZE = $clog2(READ_LATENCY+WRITE_LATENCY)+1;
	localparam INTERNAL_ADDRESS_WIDTH = $clog2(MEMORY_LINES);

	reg[DATA_WIDTH-1:0] mem [MEMORY_LINES-1:0];

	{%- for i in range(read_write_ports) %}
	// TODO find better way to get max(READ_LATENCY, WRITE_LATENCY)
	reg[LATENCY_COUNTER_SIZE-1:0] latency_counter_{{ i }};
	reg write_in_progress_{{ i }};
	reg write_done_{{ i }};
	assign write_done_{{ i }}_o = write_done_{{ i }};
	reg read_in_progress_{{ i }};

	// this is necessary as the AddressTranslator address_o port is 32 bits wide
	// however the actual address might be smaller than that.
	wire[32-1:0] address_internal_{{ i }}_32_bit;

	{{ name }}_AddressTranslator at_{{ i }}(
		.address_i({ {32-ADDRESS_WIDTH{1'b0} },address_{{ i }}_i}),
		.address_o(address_internal_{{ i }}_32_bit)
	);
	wire[INTERNAL_ADDRESS_WIDTH-1:0] address_internal_{{ i }};
	assign address_internal_{{ i }} = address_internal_{{ i }}_32_bit[INTERNAL_ADDRESS_WIDTH-1:0];

	{% endfor %}

	reg ready;
	assign ready_o = ready;


	integer i;

	always @(posedge clk_i, negedge reset_n_i) begin
		if(reset_n_i == 1'b0) begin
			ready <= 1'b1;

			// reset whole memory
			for(i = 0; i < MEMORY_LINES; i = i + 1) begin
				mem[i] = {DATA_WIDTH{1'b0}};
			end

			// reset all regs for each port
			{%- for i in range(read_write_ports) %}
			latency_counter_{{ i }} <= {LATENCY_COUNTER_SIZE{1'b0}};
			write_in_progress_{{ i }} <= 1'b0;
			write_done_{{ i }} <= 1'b0;
			read_in_progress_{{ i }} <= 1'b0;
			{% endfor %}
		end
		else begin
			// write at port 0
			if(latency_counter_0 == {LATENCY_COUNTER_SIZE{1'b0}} 
				&& write_in_progress_0 == 1'b0 
				&& read_in_progress_0 == 1'b0 
				&& read_write_select_0_i == 1'b1 
				&& write_data_valid_0_i > 1) begin
				latency_counter_0 <= WRITE_LATENCY-1;
				$display("t=%0t: %m write at port {{ i }} initialized.", $time);
			end
			// decrease latency counter
			if(latency_counter_0 != {LATENCY_COUNTER_SIZE{1'b0}}) begin
				latency_counter_0 <= latency_counter_0-1;
			end
			// latency counter is 0 and a write is in progress
			if(latency_counter_0 == {LATENCY_COUNTER_SIZE{1'b0}}
				&& write_in_progress_0 == 1'b1) begin
				// depending on the port width and the valid bits write data at write_data_i port into mem
				$display("t=%0t: %m data from port {{ i }} is now in memory.", $time);
				write_done_0 <= 1'b1;
				{% for j in range(port_width) -%}
				if(write_data_valid_0_i[{{ j }}] == 1'b1) begin
					mem[address_internal_0+{{ j }}] <= write_data_0_i[{{ (j+1)*data_width }}-1:{{ j*data_width }}];
				end
				{% endfor %}
			end
			// write_done signal is only 1 (high) for one clock cycle
			if(write_done_0 == 1'b1) begin
				write_done_0 <= 1'b0;
			end
		end
	end

endmodule