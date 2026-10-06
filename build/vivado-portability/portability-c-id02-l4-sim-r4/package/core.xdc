# Module-level synchronous interface budget; not an AMD board constraint.
create_clock -name clk -period 20.000 [get_ports clk]
set_input_delay -clock clk -max 2.000 [get_ports -filter {DIRECTION == IN && NAME != clk}]
set_input_delay -clock clk -min 2.000 [get_ports -filter {DIRECTION == IN && NAME != clk}]
set_output_delay -clock clk -max 2.000 [get_ports -filter {DIRECTION == OUT}]
set_output_delay -clock clk -min 2.000 [get_ports -filter {DIRECTION == OUT}]
