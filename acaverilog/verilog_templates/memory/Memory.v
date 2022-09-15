/* verilator lint_off CMPCONST */

module {{ name }}_Memory
#(
	parameter DATA_WIDTH = {{ data_width }}, 
	parameter MAX_DATA_WORD_DISTANCE = {{ max_data_word_distance }}, 
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

	// TODO add input that indicates the distance between data words
	{%- for i in range(read_write_ports) %}
	input read_write_select_{{ i }}_i,
	input unsigned[ADDRESS_WIDTH-1:0] address_{{ i }}_i,
	input[$clog2(MAX_DATA_WORD_DISTANCE)-1:0] data_word_distance_{{ i }}_i,
	input address_valid_{{ i }}_i,
	input[PORT_WIDTH_BITS-1:0] write_data_{{ i }}_i,
	input unsigned[PORT_WIDTH-1:0] write_data_valid_{{ i }}_i,
	output write_done_{{ i }}_o,
	output[PORT_WIDTH_BITS-1:0] read_data_{{ i }}_o,
	output unsigned[PORT_WIDTH-1:0] read_data_valid_{{ i }}_o,
	output port_ready_{{ i }}_o,
	{% endfor -%}

	output ready_o
);

	// TODO find better way to get max(READ_LATENCY, WRITE_LATENCY)
	localparam LATENCY_COUNTER_SIZE = $clog2(READ_LATENCY+WRITE_LATENCY)+1;
	localparam INTERNAL_ADDRESS_WIDTH = $clog2(MEMORY_LINES);

	reg[DATA_WIDTH-1:0] mem [MEMORY_LINES-1:0];
	{% if load_from_memory_file %}
	// load data into mem
	initial begin
		$display("Loading data into memory from '{{ memory_file_path }}'.");
		$readmemh("{{ memory_file_path }}", mem);
	end
	{% endif %}

	{%- for i in range(read_write_ports) %}
	reg[LATENCY_COUNTER_SIZE-1:0] latency_counter_{{ i }};
	reg write_in_progress_{{ i }};
	reg write_done_{{ i }};
	assign write_done_{{ i }}_o = write_done_{{ i }};
	reg read_in_progress_{{ i }};
	reg[ADDRESS_WIDTH-1:0] address_{{ i }};
	reg[PORT_WIDTH_BITS-1:0] write_data_{{ i }};
	reg[PORT_WIDTH-1:0] write_data_valid_{{ i }};
	reg[PORT_WIDTH_BITS-1:0] read_data_{{ i }};
	assign read_data_{{ i }}_o = read_data_{{ i }};
	reg[PORT_WIDTH-1:0] read_data_valid_{{ i }};
	assign read_data_valid_{{ i }}_o = read_data_valid_{{ i }};
	assign port_ready_{{ i }}_o = ~read_in_progress_{{ i }} & ~write_in_progress_{{ i }};
	reg hold_read_data_{{ i }}_o;

	// this is necessary as the AddressTranslator address_o port is 32 bits wide
	// however the actual address might be smaller than that.
	wire[32-1:0] address_internal_{{ i }}_32_bit;

	{{ name }}_AddressTranslator at_{{ i }}(
		.address_i({ {32-ADDRESS_WIDTH{1'b0} },address_{{ i }}}),
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
			{% if enable_data_reset %}
			for(i = 0; i < MEMORY_LINES; i = i + 1) begin
				mem[i] = {DATA_WIDTH{1'b0}};
			end
			{% endif %}

			// reset all regs for each port
			{%- for i in range(read_write_ports) %}
			latency_counter_{{ i }} <= {LATENCY_COUNTER_SIZE{1'b0}};
			write_in_progress_{{ i }} <= 1'b0;
			write_done_{{ i }} <= 1'b0;
			read_in_progress_{{ i }} <= 1'b0;
			write_data_{{ i }} <= {PORT_WIDTH_BITS{1'b0}};
			write_data_valid_{{ i }} <= {PORT_WIDTH{1'b0}};
			read_data_{{ i }} <= {PORT_WIDTH_BITS{1'b0}};
			read_data_valid_{{ i }} <= {PORT_WIDTH{1'b0}}; 
			{% endfor %}
		end
		else begin
			{%- for i in range(read_write_ports) %}
			// decrease read/write latency counter
			if(latency_counter_{{ i }} != {LATENCY_COUNTER_SIZE{1'b0}}) begin
				latency_counter_{{ i }} <= latency_counter_{{ i }}-1;
			end
			// write at port {{ i }}
			if(latency_counter_{{ i }} == {LATENCY_COUNTER_SIZE{1'b0}} 
				&& write_in_progress_{{ i }} == 1'b0 
				&& read_in_progress_{{ i }} == 1'b0 
				&& read_write_select_{{ i }}_i == 1'b1 
				&& address_valid_{{ i }}_i == 1'b1 
				&& write_data_valid_{{ i }}_i != 0) begin

				latency_counter_{{ i }} <= WRITE_LATENCY-1;
				write_in_progress_{{ i }} <= 1'b1;
				// copy data, address and valid signals to internal registers
				write_data_{{ i }} <= write_data_{{ i }}_i;
				write_data_valid_{{ i }} <= write_data_valid_{{ i }}_i;
				address_{{ i }} <= address_{{ i }}_i;
				$display("t=%0t: %m write at port {{ i }} to address=%d with data=%d initialized.", $time, address_0_i, write_data_0_i);
			end
			// latency counter is 0 and a write is in progress
			// write data to memory
			if(latency_counter_{{ i }} == {LATENCY_COUNTER_SIZE{1'b0}}
				&& write_in_progress_{{ i }} == 1'b1) begin
				// depending on the port width and the valid bits write data at write_data_i port into mem
				write_done_{{ i }} <= 1'b1;
				{% for j in range(port_width) -%}
				if(write_data_valid_{{ i }}[{{ j }}] == 1'b1) begin
					mem[address_internal_{{ i }}+{{ j }}] <= write_data_{{ i }}[{{ (j+1)*data_width }}-1:{{ j*data_width }}];
				end
				write_in_progress_{{ i }} <= 1'b0;
				$display("t=%0t: %m data from port {{ i }} is now in memory.", $time);
				{% endfor %}
			end
			// write_done signal is only 1 (high) for one clock cycle
			if(write_done_{{ i }} == 1'b1) begin
				write_done_{{ i }} <= 1'b0;
			end

			// read at port {{ i }}
			if(latency_counter_{{ i }} == {LATENCY_COUNTER_SIZE{1'b0}}
				&& write_in_progress_{{ i }} == 1'b0
				&& read_in_progress_{{ i }} == 1'b0
				&& read_write_select_{{ i }}_i == 1'b0
				&& address_valid_{{ i }}_i == 1'b1) begin

				latency_counter_{{ i }} <= READ_LATENCY-1;
				read_in_progress_{{ i }} <= 1'b1;
				address_{{ i }} <= address_{{ i }}_i;
				$display("t=%0t: %m read at port {{ i }} initialized.", $time);
			end
			// latency counter is 0 and a read is in progress
			// put data at output ports
			if(latency_counter_{{ i }} == {LATENCY_COUNTER_SIZE{1'b0}}
				&& read_in_progress_{{ i }} == 1'b1) begin
				{% for j in range(port_width) -%}
				read_data_{{ i }}[{{ (j+1)*data_width }}-1:{{ j*data_width }}] <= mem[address_internal_{{ i }}+{{ j }}];
				{% endfor %}
				read_data_valid_{{ i }} <= {PORT_WIDTH{1'b1}};
				hold_read_data_{{ i }}_o <= 1;
				$display("t=%0t: %m data from memory {{ i }} is now at read_data_{{ i }}_o.", $time);
			end
			// make sure the read data is at least 2 cycles available at the read_data_o port
			if(hold_read_data_{{ i }}_o != 0) begin
				hold_read_data_{{ i }}_o <= hold_read_data_{{ i }}_o - 1;
			end
			// drive read_data_o ports to low
			if(read_data_valid_{{ i }} != 0 && hold_read_data_{{ i }}_o == 1'b0) begin
				read_data_valid_{{ i }} <= {PORT_WIDTH{1'b0}};
				read_data_{{ i }} <= {PORT_WIDTH_BITS{1'b0}};
				read_in_progress_{{ i }} <= 1'b0;
			end
			{% endfor %}
		end
	end

endmodule