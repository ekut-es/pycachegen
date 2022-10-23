# VScoreboard_tb
add_executable(VScoreboard_tb {{name}}_Scoreboard_tb.cc)

set_property(
	TARGET VScoreboard_tb
	PROPERTY CXX_STANDARD ${SystemC_CXX_STANDARD}
)

verilate(VScoreboard_tb 
	SOURCES {{name}}_Scoreboard.v
	TRACE SYSTEMC COVERAGE
	INCLUDE_DIRECTORIES "."
)

verilator_link_systemc(VScoreboard_tb)