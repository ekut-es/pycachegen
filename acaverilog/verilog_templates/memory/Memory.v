module {{ name }}_Memory
#(
	parameter DATA_WIDTH = {{ data_width }}, 
	parameter PORT_WIDTH = {{ port_width }},
	parameter PORT_WIDTH_BITS = {{ data_width*port_width }},
	parameter MAX_CONCURRENT_REQUESTS = {{ max_concurrent_requests }},
	parameter READ_LATENCY = {{ read_latency }},
	parameter WRITE_LATENCY = {{ write_latency }},
	parameter ADDRESS_WIDTH = {{ address_width }}
)
(
	input clk_i,
	input reset_n_i,

	{%- for i in range(read_write_ports) %}
	input read_write_select_{{ i }}_i,
	input[ADDRESS_WIDTH-1:0] address_{{ i }}_i,
	input[PORT_WIDTH_BITS-1:0] write_data_{{ i }}_i,
	input[PORT_WIDTH-1:0] write_data_valid_{{ i }}_i,
	output[PORT_WIDTH_BITS-1:0] read_data_{{ i }}_o,
	output[PORT_WIDTH-1:0] read_data_valid_{{ i }}_o,
	{% endfor -%}

	output ready_o
);

endmodule