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

	{%- for i in range(read_write_ports) %}
	input read_write_select_{{ i }}_i,
	input unsigned [ADDRESS_WIDTH-1:0] address_{{ i }}_i,
	input[PORT_WIDTH_BITS-1:0] write_data_{{ i }}_i,
	input[PORT_WIDTH-1:0] write_data_valid_{{ i }}_i,
	output[PORT_WIDTH_BITS-1:0] read_data_{{ i }}_o,
	output[PORT_WIDTH-1:0] read_data_valid_{{ i }}_o,
	{% endfor -%}

	output ready_o
);

	{%- for i in range(read_write_ports) %}
	wire[ADDRESS_WIDTH-1:0] address_internal_{{ i }};

	{{ name }}_AddressTranslator at_{{ i }}(
		.address_i(address_{{ i }}_i),
		.address_o(address_internal_{{ i }})
	);
	{% endfor %}

	reg[DATA_WIDTH-1:0] mem [MEMORY_LINES-1:0];

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
		end
		else begin
		end
	end

endmodule