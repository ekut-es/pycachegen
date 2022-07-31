/* verilator lint_off UNSIGNED */

module {{ name }}_AddressTranslator
#(
	parameter ADDRESS_WIDTH = {{ address_width }}
)
(
	input unsigned [ADDRESS_WIDTH-1:0] address_i,
	output unsigned [ADDRESS_WIDTH-1:0] address_o
);

	assign address_o = 
	{% for address_range, offset in address_translation_map.items() -%}	
	(address_i >= {{ address_range[0] }} && address_i < {{ address_range[1] }}) ? address_i + {{ offset }} :
	{% endfor -%}	
	0;

endmodule