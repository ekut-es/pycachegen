module {{ name }}_ForwardLookupTable (
	input[{{ target_id_length }}-1:0] target_id_i,
	output reg[{{ forward_ports_size }}-1:0] forward_port_o
);

	always @(target_id_i) begin
		case(target_id_i)
			{% for key, value in forward_port_map.items() -%}
			{{ key }}: forward_port_o = {{ forward_ports_size }}'d{{ value }};
			{% endfor -%}
			default: forward_port_o = {{ forward_ports_size }}'d0;
		endcase
	end
endmodule